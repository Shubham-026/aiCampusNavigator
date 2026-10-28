"""Validate campus CSV data and load it into SQLite or a NetworkX graph."""

import csv
from contextlib import closing
import math
from pathlib import Path
import sqlite3
from typing import Any

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLACES_FILE = PROJECT_ROOT / "data" / "places.csv"
CONNECTIONS_FILE = PROJECT_ROOT / "data" / "connections.csv"
DB_FILE = PROJECT_ROOT / "data" / "campus.db"

PLACE_COLUMNS = {
    "place_id",
    "name",
    "category",
    "department",
    "floor",
    "x",
    "y",
    "floor_name",
    "aliases",
    "description",
}
CONNECTION_COLUMNS = {
    "connection_id",
    "from_place_id",
    "to_place_id",
    "distance_m",
    "transition_type",
}
TRANSITION_TYPES = {"corridor", "stairs", "stair", "lift", "elevator", "ramp", "door"}
VERTICAL_TRANSITIONS = {"stairs", "stair", "lift", "elevator"}


def _read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path} is missing required columns: {missing}")
        return [
            {key: (value or "").strip() for key, value in row.items() if key is not None}
            for row in reader
        ]


def _read_campus_data(
    places_path: Path,
    connections_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    places = _read_csv(places_path, PLACE_COLUMNS)
    connections = _read_csv(connections_path, CONNECTION_COLUMNS)
    places_by_id: dict[str, dict[str, Any]] = {}

    for row_number, place in enumerate(places, start=2):
        place_id = place["place_id"]
        if not place_id:
            raise ValueError(f"Missing place_id on {places_path} row {row_number}")
        if place_id in places_by_id:
            raise ValueError(f"Duplicate place_id: {place_id}")
        if not place["name"]:
            raise ValueError(f"Missing name for place_id: {place_id}")
        try:
            coordinates = {key: float(place[key]) for key in ("x", "y", "floor")}
        except ValueError as error:
            raise ValueError(f"Invalid coordinates or floor for place_id: {place_id}") from error
        if not all(math.isfinite(value) for value in coordinates.values()):
            raise ValueError(f"Coordinates and floor must be finite for place_id: {place_id}")
        if not place["floor_name"]:
            raise ValueError(f"Missing floor_name for place_id: {place_id}")
        place.update(coordinates)
        places_by_id[place_id] = place

    connection_ids: set[str] = set()
    connection_pairs: set[frozenset[str]] = set()
    for row_number, connection in enumerate(connections, start=2):
        connection_id = connection["connection_id"]
        source = connection["from_place_id"]
        target = connection["to_place_id"]
        if not connection_id or connection_id in connection_ids:
            raise ValueError(f"Missing or duplicate connection_id: {connection_id!r}")
        connection_ids.add(connection_id)
        if source not in places_by_id or target not in places_by_id:
            raise ValueError(f"Connection references an unknown place: {source!r} -> {target!r}")
        if source == target:
            raise ValueError(f"Connection cannot link a place to itself: {source}")
        pair = frozenset((source, target))
        if pair in connection_pairs:
            raise ValueError(f"Duplicate connection between {source} and {target}")
        connection_pairs.add(pair)

        try:
            distance_m = float(connection["distance_m"])
        except ValueError as error:
            raise ValueError(f"Invalid distance for connection_id: {connection_id}") from error
        if not math.isfinite(distance_m) or distance_m <= 0:
            raise ValueError(f"Connection distance must be positive: {connection_id}")

        transition_type = connection["transition_type"].lower()
        if transition_type not in TRANSITION_TYPES:
            raise ValueError(f"Invalid transition_type for connection_id: {connection_id}")
        source_floor = places_by_id[source]["floor"]
        target_floor = places_by_id[target]["floor"]
        if source_floor != target_floor and transition_type not in VERTICAL_TRANSITIONS:
            raise ValueError(
                f"Cross-floor connection {connection_id} must use stairs or a lift"
            )
        connection["distance_m"] = distance_m
        connection["transition_type"] = transition_type

    return places, connections


def initialize_database(
    database_path: Path = DB_FILE,
    places_path: Path = PLACES_FILE,
    connections_path: Path = CONNECTIONS_FILE,
) -> Path:
    """Validate the CSV datasets and transactionally synchronize them to SQLite."""
    places, connections = _read_campus_data(places_path, connections_path)
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS places (
                    place_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    department TEXT NOT NULL DEFAULT '',
                    floor REAL NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    floor_name TEXT NOT NULL,
                    aliases TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT ''
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS connections (
                    connection_id TEXT PRIMARY KEY,
                    from_place_id TEXT NOT NULL REFERENCES places(place_id),
                    to_place_id TEXT NOT NULL REFERENCES places(place_id),
                    distance_m REAL NOT NULL CHECK (distance_m > 0),
                    transition_type TEXT NOT NULL,
                    CHECK (from_place_id <> to_place_id)
                )"""
            )
            connection.execute("DELETE FROM connections")
            connection.execute("DELETE FROM places")
            connection.executemany(
                """INSERT INTO places (
                    place_id, name, category, department, floor, x, y,
                    floor_name, aliases, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        place["place_id"], place["name"], place["category"],
                        place["department"], place["floor"], place["x"],
                        place["y"], place["floor_name"], place["aliases"],
                        place["description"],
                    )
                    for place in places
                ],
            )
            connection.executemany(
                """INSERT INTO connections (
                    connection_id, from_place_id, to_place_id, distance_m, transition_type
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        edge["connection_id"], edge["from_place_id"],
                        edge["to_place_id"], edge["distance_m"],
                        edge["transition_type"],
                    )
                    for edge in connections
                ],
            )

    return database_path


def load_campus_graph(
    places_path: Path = PLACES_FILE,
    connections_path: Path = CONNECTIONS_FILE,
) -> nx.Graph:
    """Load places and undirected, distance-weighted connections from CSV files."""
    places, connections = _read_campus_data(places_path, connections_path)
    graph = nx.Graph()

    for place in places:
        place_id = place.pop("place_id")
        graph.add_node(place_id, **place)

    for connection in connections:
        source = connection["from_place_id"]
        target = connection["to_place_id"]
        graph.add_edge(
            source,
            target,
            distance_m=connection["distance_m"],
            transition_type=connection["transition_type"],
        )

    return graph