"""SQLite-backed typo-tolerant search for campus places and departments."""

from contextlib import closing
from pathlib import Path
import sqlite3

from rapidfuzz import fuzz, process

from src.database import DB_FILE, initialize_database


def search_places(
    query: str,
    limit: int = 5,
    score_threshold: float = 60.0,
    database_path: Path = DB_FILE,
) -> list[dict[str, str | float]]:
    """Return ranked matches across place names, aliases, categories, and departments."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not 0 <= score_threshold <= 100:
        raise ValueError("score_threshold must be between 0 and 100")
    normalized_query = query.strip()
    if not normalized_query:
        return []

    database_path = Path(database_path)
    if not database_path.exists():
        initialize_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        places = connection.execute(
            """SELECT place_id, name, category, department, floor, floor_name,
                      aliases, description
               FROM places"""
        ).fetchall()

    candidates: list[tuple[str, int]] = []
    for index, place in enumerate(places):
        searchable_fields = [
            place["name"],
            place["place_id"],
            place["category"],
            place["department"],
            place["description"],
            *place["aliases"].split("|"),
        ]
        candidates.extend(
            (field.strip(), index)
            for field in searchable_fields
            if field and field.strip()
        )

    matches = process.extract(
        normalized_query,
        [candidate for candidate, _ in candidates],
        scorer=fuzz.WRatio,
        score_cutoff=score_threshold,
        limit=None,
    )
    best_scores: dict[int, float] = {}
    for _, score, candidate_index in matches:
        place_index = candidates[candidate_index][1]
        best_scores[place_index] = max(score, best_scores.get(place_index, 0.0))

    ranked_places = sorted(
        ((places[index], score) for index, score in best_scores.items()),
        key=lambda item: (-item[1], item[0]["name"].casefold(), item[0]["place_id"]),
    )
    return [
        {
            "place_id": place["place_id"],
            "name": place["name"],
            "category": place["category"],
            "department": place["department"],
            "floor": place["floor"],
            "floor_name": place["floor_name"],
            "score": score,
        }
        for place, score in ranked_places[:limit]
    ]