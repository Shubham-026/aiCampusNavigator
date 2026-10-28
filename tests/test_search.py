import pytest

from src.database import initialize_database
from src.search import search_places


@pytest.fixture
def campus_database(tmp_path):
	database_path = tmp_path / "campus.db"
	initialize_database(database_path)
	return database_path


@pytest.mark.parametrize("query", ["phy lab", "lab 101", "lba 101"])
def test_search_finds_lab_by_alias_or_typo(campus_database, query):
	results = search_places(query, database_path=campus_database)

	assert results
	assert results[0]["place_id"] == "LAB101"
	assert results[0]["score"] >= 60


def test_search_finds_department(campus_database):
	results = search_places("physics", database_path=campus_database)

	assert results[0]["place_id"] == "LAB101"
	assert results[0]["department"] == "Physics"


def test_search_respects_threshold_and_limit(campus_database):
	results = search_places(
		"phy lab",
		limit=1,
		score_threshold=95,
		database_path=campus_database,
	)

	assert len(results) == 1
	assert results[0]["score"] == 100


def test_search_validates_parameters(campus_database):
	with pytest.raises(ValueError, match="limit must be at least 1"):
		search_places("lab", limit=0, database_path=campus_database)
	with pytest.raises(ValueError, match="score_threshold must be between 0 and 100"):
		search_places("lab", score_threshold=101, database_path=campus_database)


def test_empty_search_returns_no_results(campus_database):
	assert search_places("   ", database_path=campus_database) == []
