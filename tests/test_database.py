import csv
import sqlite3
from contextlib import closing

import pytest

from src.database import CONNECTIONS_FILE, PLACES_FILE, initialize_database


def _copy_csv_with_update(source_path, destination_path, row_index, field, value):
	with source_path.open(newline="", encoding="utf-8") as source_file:
		reader = csv.DictReader(source_file)
		fieldnames = reader.fieldnames
		rows = list(reader)
	rows[row_index][field] = value
	with destination_path.open("w", newline="", encoding="utf-8") as destination_file:
		writer = csv.DictWriter(destination_file, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(rows)


def test_ingestion_loads_places_and_connections(tmp_path):
	database_path = tmp_path / "campus.db"
	initialize_database(database_path)

	with closing(sqlite3.connect(database_path)) as connection:
		place_count = connection.execute("SELECT COUNT(*) FROM places").fetchone()[0]
		connection_count = connection.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
		lab = connection.execute(
			"SELECT department, aliases FROM places WHERE place_id = 'LAB101'"
		).fetchone()

	assert place_count == 6
	assert connection_count == 5
	assert lab == ("Physics", "lab 101|physics lab|phy lab|physics laboratory")


def test_ingestion_rejects_duplicate_place_ids(tmp_path):
	places_path = tmp_path / "places.csv"
	_copy_csv_with_update(PLACES_FILE, places_path, 1, "place_id", "GATE")

	with pytest.raises(ValueError, match="Duplicate place_id: GATE"):
		initialize_database(tmp_path / "campus.db", places_path, CONNECTIONS_FILE)


def test_ingestion_rejects_non_finite_coordinates(tmp_path):
	places_path = tmp_path / "places.csv"
	_copy_csv_with_update(PLACES_FILE, places_path, 0, "x", "nan")

	with pytest.raises(ValueError, match="must be finite"):
		initialize_database(tmp_path / "campus.db", places_path, CONNECTIONS_FILE)


def test_ingestion_rejects_invalid_cross_floor_transition(tmp_path):
	connections_path = tmp_path / "connections.csv"
	_copy_csv_with_update(CONNECTIONS_FILE, connections_path, 2, "transition_type", "corridor")

	with pytest.raises(ValueError, match="must use stairs or a lift"):
		initialize_database(tmp_path / "campus.db", PLACES_FILE, connections_path)


def test_ingestion_rejects_unknown_connection_endpoint(tmp_path):
	connections_path = tmp_path / "connections.csv"
	_copy_csv_with_update(CONNECTIONS_FILE, connections_path, 0, "to_place_id", "MISSING")

	with pytest.raises(ValueError, match="unknown place"):
		initialize_database(tmp_path / "campus.db", PLACES_FILE, connections_path)
