"""Weighted shortest-path algorithms and turn-by-turn campus directions."""

from dataclasses import dataclass
import math
from typing import Literal

import networkx as nx

from src.database import load_campus_graph

Algorithm = Literal["astar", "dijkstra"]


@dataclass
class RouteResult:
    algorithm: Algorithm
    nodes: list[str]
    directions: list[str]
    total_cost_m: float


def _heuristic_factors(graph: nx.Graph) -> tuple[float, float]:
    euclidean_scale = math.inf
    floor_change_penalty_m = math.inf

    for source, target, attributes in graph.edges(data=True):
        distance_m = float(attributes["distance_m"])
        source_data = graph.nodes[source]
        target_data = graph.nodes[target]
        planar_distance = math.hypot(
            float(source_data.get("x", 0.0)) - float(target_data.get("x", 0.0)),
            float(source_data.get("y", 0.0)) - float(target_data.get("y", 0.0)),
        )
        floor_change = abs(float(source_data.get("floor", 0.0)) - float(target_data.get("floor", 0.0)))

        if planar_distance > 0:
            euclidean_scale = min(euclidean_scale, distance_m / planar_distance)
        if floor_change > 0:
            floor_change_penalty_m = min(floor_change_penalty_m, distance_m / floor_change)

    return (
        euclidean_scale if math.isfinite(euclidean_scale) else 0.0,
        floor_change_penalty_m if math.isfinite(floor_change_penalty_m) else 0.0,
    )


def campus_heuristic(
    graph: nx.Graph,
    current_node: str,
    destination_node: str,
    *,
    euclidean_scale: float | None = None,
    floor_change_penalty_m: float | None = None,
) -> float:
    """Estimate remaining cost using planar distance and a floor-change lower bound."""
    if euclidean_scale is None or floor_change_penalty_m is None:
        calculated_scale, calculated_floor_penalty = _heuristic_factors(graph)
        if euclidean_scale is None:
            euclidean_scale = calculated_scale
        if floor_change_penalty_m is None:
            floor_change_penalty_m = calculated_floor_penalty

    current = graph.nodes[current_node]
    destination = graph.nodes[destination_node]
    planar_distance = math.hypot(
        float(current.get("x", 0.0)) - float(destination.get("x", 0.0)),
        float(current.get("y", 0.0)) - float(destination.get("y", 0.0)),
    )
    floor_change = abs(float(current.get("floor", 0.0)) - float(destination.get("floor", 0.0)))

    # Each term is bounded by the cost of every corresponding edge; max keeps
    # the estimate admissible when vertical edges also have horizontal offset.
    return max(planar_distance * euclidean_scale, floor_change * floor_change_penalty_m)


def _validate_endpoints(graph: nx.Graph, start: str, destination: str) -> None:
    for place_id in (start, destination):
        if place_id not in graph:
            raise ValueError(f"Unknown place_id: {place_id}")


def _place_name(graph: nx.Graph, place_id: str) -> str:
    return str(graph.nodes[place_id].get("name", place_id))


def _floor_name(graph: nx.Graph, place_id: str) -> str:
    attributes = graph.nodes[place_id]
    if "floor_name" in attributes:
        return str(attributes["floor_name"])
    return f"Floor {attributes.get('floor', 0)}"


def _directions_for_path(graph: nx.Graph, path: list[str]) -> list[str]:
    if len(path) == 1:
        return [f"You are already at {_place_name(graph, path[0])} ({_floor_name(graph, path[0])})."]

    directions = [f"Start at {_place_name(graph, path[0])} ({_floor_name(graph, path[0])})."]
    for source, target in zip(path, path[1:]):
        edge = graph.edges[source, target]
        source_floor = _floor_name(graph, source)
        target_floor = _floor_name(graph, target)
        transition_type = str(edge.get("transition_type", "corridor")).lower()
        if transition_type in {"stairs", "stair"}:
            action = "Take the stairs"
        elif transition_type in {"lift", "elevator"}:
            action = "Take the lift"
        else:
            action = "Walk"

        direction = (
            f"{action} {float(edge['distance_m']):g} m from {_place_name(graph, source)} "
            f"to {_place_name(graph, target)}"
        )
        if source_floor != target_floor:
            direction += f", changing from {source_floor} to {target_floor}"
        directions.append(direction + ".")

    return directions


def _make_result(
    graph: nx.Graph,
    path: list[str],
    algorithm: Algorithm,
) -> RouteResult:
    total_cost_m = sum(float(graph.edges[source, target]["distance_m"]) for source, target in zip(path, path[1:]))
    return RouteResult(
        algorithm=algorithm,
        nodes=path,
        directions=_directions_for_path(graph, path),
        total_cost_m=round(total_cost_m, 2),
    )


def dijkstra_route(
    start_place_id: str,
    destination_place_id: str,
    graph: nx.Graph | None = None,
) -> RouteResult:
    """Find a minimum-distance route using NetworkX's Dijkstra implementation."""
    campus_graph = graph if graph is not None else load_campus_graph()
    _validate_endpoints(campus_graph, start_place_id, destination_place_id)
    path = nx.dijkstra_path(
        campus_graph,
        source=start_place_id,
        target=destination_place_id,
        weight="distance_m",
    )
    return _make_result(campus_graph, path, "dijkstra")


def astar_route(
    start_place_id: str,
    destination_place_id: str,
    graph: nx.Graph | None = None,
) -> RouteResult:
    """Find a minimum-distance route using A* and an admissible campus heuristic."""
    campus_graph = graph if graph is not None else load_campus_graph()
    _validate_endpoints(campus_graph, start_place_id, destination_place_id)
    euclidean_scale, floor_change_penalty_m = _heuristic_factors(campus_graph)
    path = nx.astar_path(
        campus_graph,
        source=start_place_id,
        target=destination_place_id,
        heuristic=lambda current, destination: campus_heuristic(
            campus_graph,
            current,
            destination,
            euclidean_scale=euclidean_scale,
            floor_change_penalty_m=floor_change_penalty_m,
        ),
        weight="distance_m",
    )
    return _make_result(campus_graph, path, "astar")


def find_route(
    start_place_id: str,
    destination_place_id: str,
    graph: nx.Graph | None = None,
    algorithm: Algorithm = "astar",
) -> RouteResult:
    """Find a route and return its nodes, directions, and distance cost."""
    if algorithm == "dijkstra":
        return dijkstra_route(start_place_id, destination_place_id, graph)
    if algorithm == "astar":
        return astar_route(start_place_id, destination_place_id, graph)
    raise ValueError(f"Unsupported routing algorithm: {algorithm}")