# AI Campus Navigator

An AI-assisted indoor navigation and campus information system. Search for a room, pick a starting point, and get floor-specific, step-by-step directions on a floor map.

**Status:** prototype / design stage. All map data in this repository is **illustrative sample data**, not the real campus. No accuracy or performance figures have been measured.

> Project by CSE (AIML) students, Asansol Engineering College, 2026-27.
> Team: Atul Raj, Ansuman Shaw, Ananya Srivastava, Kumar Anish, Arsalan Safdar. Guide: Dr. Joyshree Maji.

## How it works

1. The campus is stored as a graph: rooms, junctions, entrances, stairs and lifts are nodes; walkable links are edges with a cost in metres.
2. The user chooses a start point and searches for a destination (fuzzy matching tolerates typos and nicknames).
3. The route is found with **A\*** (built on **Dijkstra's algorithm**, which is also used as a reference check).
4. The route is drawn on the correct floor map with step-by-step directions, total distance and a rough walking-time estimate (distance / 1.2 m/s).

The "AI" in search is fuzzy string matching plus simple query parsing (e.g. "from main gate to physics lab"). It is not a language model.

## Tech stack

- Python, FastAPI (`/search`, `/route`)
- rapidfuzz (fuzzy search)
- CSV data files (`places.csv`, `connections.csv`)
- HTML, CSS and JavaScript frontend with SVG floor maps, served by FastAPI
- pytest

## Setup and run

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Validate the map data
python validate_data.py

# 4. Start the server
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000> in your browser.

Run the tests with:

```bash
pytest
```

> Adjust the file and module names above if your folder layout differs.

## Data format

**places.csv:** `id, building, floor, name, room_no, type, also_called, landmark, x, y`
IDs follow `building-floor-room` (e.g. `B-2-204`); floors are `G, 1, 2, 3`; `x, y` are metres on the floor plan.

**connections.csv:** `from_id, to_id, cost, type, both_ways, hint, hint_back`
`type` is `walk`, `stairs` or `lift`.

The validator checks for duplicate IDs, unknown IDs, missing coordinates, edge costs below straight-line distance (required for A\*), unreachable places, and floors without stairs or lifts.

## Replacing the sample data

Edit the two CSV files with verified floor-plan measurements, run `python validate_data.py`, and restart the server. No code changes are needed.

## Not yet implemented / needs real data

- Verified real-campus floor plans (current data is fictional and labelled as such)
- OCR room-sign confirmation (optional module)
- QR checkpoint starting points
- Voice guidance, live corridor closures, continuous real-time tracking
- Measured evaluation results (accuracy, response time, usability)

## References

Dijkstra (1959); Hart, Nilsson and Raphael (1968) for A\*; RapidFuzz and FastAPI documentation.