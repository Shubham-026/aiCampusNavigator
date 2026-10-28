"""FastAPI application for campus navigation."""

from contextlib import asynccontextmanager
from dataclasses import asdict
import os
import sqlite3
from typing import AsyncIterator

import networkx as nx
import pytesseract
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.database import DB_FILE, initialize_database, load_campus_graph
from src.ocr_module import extract_text, verify_destination
from src.router import astar_route, find_route
from src.search import search_places

DATABASE_PATH = DB_FILE


class SearchMatch(BaseModel):
    place_id: str
    name: str
    category: str
    department: str
    floor: float
    floor_name: str
    score: float


class SearchResponse(BaseModel):
    query: str
    matches: list[SearchMatch]


class RouteRequest(BaseModel):
    start_id: str = Field(min_length=1)
    destination_id: str = Field(min_length=1)


class RouteResponse(BaseModel):
    algorithm: str
    nodes: list[str]
    map_nodes: list["RouteMapNode"]
    instructions: list[str]
    total_distance_m: float
    estimated_walking_time_seconds: float


class RouteMapNode(BaseModel):
    place_id: str
    name: str
    x: float
    y: float
    floor: float
    floor_name: str


class SignVerificationResponse(BaseModel):
    destination_id: str
    matched: bool
    score: float
    matched_label: str | None
    extracted_text: str


MAX_SIGN_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database(DATABASE_PATH)
    yield


app = FastAPI(title="AI Campus Navigator", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CAMPUS_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=5, ge=1, le=50),
    score_threshold: float = Query(default=60.0, ge=0.0, le=100.0),
) -> SearchResponse:
    try:
        matches = search_places(
            q,
            limit=limit,
            score_threshold=score_threshold,
            database_path=DATABASE_PATH,
        )
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(status_code=503, detail="Campus search data is unavailable") from error
    return SearchResponse(query=q, matches=matches)


@app.post("/route", response_model=RouteResponse)
def create_route(request: RouteRequest) -> RouteResponse:
    try:
        graph = load_campus_graph()
        route = astar_route(request.start_id, request.destination_id, graph)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except nx.NetworkXNoPath as error:
        raise HTTPException(status_code=404, detail="No route exists between these places") from error

    return RouteResponse(
        algorithm=route.algorithm,
        nodes=route.nodes,
        map_nodes=[
            RouteMapNode(
                place_id=place_id,
                name=str(graph.nodes[place_id].get("name", place_id)),
                x=float(graph.nodes[place_id]["x"]),
                y=float(graph.nodes[place_id]["y"]),
                floor=float(graph.nodes[place_id]["floor"]),
                floor_name=str(graph.nodes[place_id].get("floor_name", "")),
            )
            for place_id in route.nodes
        ],
        instructions=route.directions,
        total_distance_m=route.total_cost_m,
        estimated_walking_time_seconds=round(route.total_cost_m / 1.2, 2),
    )


@app.post("/verify-sign", response_model=SignVerificationResponse)
async def verify_sign(
    image: UploadFile = File(...),
    destination_id: str = Form(min_length=1),
    destination_name: str = Form(min_length=1),
) -> SignVerificationResponse:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")

    image_bytes = await image.read(MAX_SIGN_IMAGE_BYTES + 1)
    await image.close()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(image_bytes) > MAX_SIGN_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller")

    try:
        extracted_text = await run_in_threadpool(extract_text, image_bytes)
        verification = verify_destination(
            extracted_text,
            destination_id=destination_id,
            destination_name=destination_name,
        )
    except pytesseract.TesseractNotFoundError as error:
        raise HTTPException(status_code=503, detail="Tesseract OCR is not installed on the server") from error
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return SignVerificationResponse(
        destination_id=verification.destination_id,
        matched=verification.matched,
        score=verification.score,
        matched_label=verification.matched_label,
        extracted_text=extracted_text,
    )


@app.get("/routes/{start_place_id}/{destination_place_id}")
def get_route(start_place_id: str, destination_place_id: str) -> dict[str, object]:
    try:
        route = find_route(start_place_id, destination_place_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except nx.NetworkXNoPath as error:
        raise HTTPException(status_code=404, detail="No route exists between these places") from error

    return asdict(route)