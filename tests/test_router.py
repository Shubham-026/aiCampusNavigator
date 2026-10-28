import networkx as nx
import pytest

from src.database import load_campus_graph
from src.router import astar_route, campus_heuristic, dijkstra_route, find_route


@pytest.mark.parametrize(
    ("start", "destination", "expected_cost"),
    [
        ("GATE", "LAB101", 57.2),
        ("S1_GROUND", "J2", 12.7),
        ("LAB101", "GATE", 57.2),
        ("GATE", "GATE", 0.0),
    ],
)
def test_astar_cost_matches_dijkstra_for_campus_routes(
    start: str,
    destination: str,
    expected_cost: float,
) -> None:
    graph = load_campus_graph()
    astar_result = astar_route(start, destination, graph)
    dijkstra_result = dijkstra_route(start, destination, graph)

    assert astar_result.total_cost_m == pytest.approx(expected_cost)
    assert astar_result.total_cost_m == pytest.approx(dijkstra_result.total_cost_m)
    assert astar_result.nodes[0] == start
    assert astar_result.nodes[-1] == destination
    assert astar_result.algorithm == "astar"


def test_cross_floor_route_returns_directions_and_traversed_nodes() -> None:
    result = find_route("GATE", "LAB101")

    assert result.nodes == ["GATE", "J1", "S1_GROUND", "S1_FIRST", "J2", "LAB101"]
    assert result.total_cost_m == pytest.approx(57.2)
    assert result.directions[0].startswith("Start at Gate")
    assert any("Take the stairs" in direction for direction in result.directions)
    assert any("Ground Floor to First Floor" in direction for direction in result.directions)


def test_database_loads_numeric_coordinates_and_transition_types() -> None:
    graph = load_campus_graph()

    assert graph.nodes["GATE"]["x"] == 0.0
    assert graph.nodes["GATE"]["y"] == 0.0
    assert graph.nodes["GATE"]["floor"] == 0.0
    assert graph.edges["S1_GROUND", "S1_FIRST"]["transition_type"] == "stairs"


def test_heuristic_includes_floor_change_lower_bound() -> None:
    graph = load_campus_graph()

    assert campus_heuristic(graph, "S1_GROUND", "S1_FIRST") == pytest.approx(4.2)


def test_astar_and_dijkstra_choose_the_lowest_cost_competing_path() -> None:
    graph = nx.Graph()
    graph.add_node("START", x=0.0, y=0.0, floor=0, name="Start", floor_name="Ground Floor")
    graph.add_node("LONG", x=1.0, y=0.0, floor=0, name="Long way", floor_name="Ground Floor")
    graph.add_node("SHORT", x=0.0, y=1.0, floor=0, name="Short way", floor_name="Ground Floor")
    graph.add_node("END", x=2.0, y=0.0, floor=0, name="End", floor_name="Ground Floor")
    graph.add_edge("START", "LONG", distance_m=3.0, transition_type="corridor")
    graph.add_edge("LONG", "END", distance_m=3.0, transition_type="corridor")
    graph.add_edge("START", "SHORT", distance_m=1.0, transition_type="corridor")
    graph.add_edge("SHORT", "END", distance_m=1.0, transition_type="corridor")

    astar_result = astar_route("START", "END", graph)
    dijkstra_result = dijkstra_route("START", "END", graph)

    assert astar_result.nodes == ["START", "SHORT", "END"]
    assert astar_result.total_cost_m == pytest.approx(2.0)
    assert astar_result.total_cost_m == pytest.approx(dijkstra_result.total_cost_m)


def test_rejects_unknown_place_id() -> None:
    with pytest.raises(ValueError, match="Unknown place_id: UNKNOWN"):
        find_route("UNKNOWN", "LAB101")


def test_rejects_unknown_algorithm() -> None:
    with pytest.raises(ValueError, match="Unsupported routing algorithm: breadth_first"):
        find_route("GATE", "LAB101", algorithm="breadth_first")


def test_unreachable_destination_raises_networkx_no_path() -> None:
    graph = nx.Graph()
    graph.add_node("START", x=0.0, y=0.0, floor=0)
    graph.add_node("END", x=1.0, y=0.0, floor=0)

    with pytest.raises(nx.NetworkXNoPath):
        astar_route("START", "END", graph)