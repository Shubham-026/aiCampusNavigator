import pytest
from fastapi.testclient import TestClient

import api.main as api_module


@pytest.fixture
def client(tmp_path, monkeypatch):
	monkeypatch.setattr(api_module, "DATABASE_PATH", tmp_path / "campus.db")
	with TestClient(api_module.app) as test_client:
		yield test_client


def test_search_endpoint_returns_ranked_matches(client):
	response = client.get("/search", params={"q": "phy lab"})

	assert response.status_code == 200
	payload = response.json()
	assert payload["query"] == "phy lab"
	assert payload["matches"][0]["place_id"] == "LAB101"
	assert payload["matches"][0]["score"] == 100


def test_search_endpoint_validates_query(client):
	response = client.get("/search", params={"q": ""})

	assert response.status_code == 422


def test_route_endpoint_returns_instructions_distance_and_time(client):
	response = client.post(
		"/route",
		json={"start_id": "GATE", "destination_id": "LAB101"},
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["algorithm"] == "astar"
	assert payload["nodes"] == ["GATE", "J1", "S1_GROUND", "S1_FIRST", "J2", "LAB101"]
	assert payload["map_nodes"][-1]["place_id"] == "LAB101"
	assert payload["map_nodes"][-1]["floor_name"] == "First Floor"
	assert payload["total_distance_m"] == pytest.approx(57.2)
	assert payload["estimated_walking_time_seconds"] == pytest.approx(57.2 / 1.2, abs=0.01)
	assert any("Take the stairs" in instruction for instruction in payload["instructions"])


def test_route_endpoint_rejects_unknown_place(client):
	response = client.post(
		"/route",
		json={"start_id": "UNKNOWN", "destination_id": "LAB101"},
	)

	assert response.status_code == 404


def test_sign_verification_endpoint_returns_ocr_match(client, monkeypatch):
	monkeypatch.setattr(api_module, "extract_text", lambda _: "LAB 101")
	response = client.post(
		"/verify-sign",
		data={"destination_id": "LAB101", "destination_name": "Lab 101"},
		files={"image": ("sign.png", b"fake image bytes", "image/png")},
	)

	assert response.status_code == 200
	assert response.json()["matched"] is True
	assert response.json()["extracted_text"] == "LAB 101"


def test_sign_verification_endpoint_rejects_non_image_upload(client):
	response = client.post(
		"/verify-sign",
		data={"destination_id": "LAB101", "destination_name": "Lab 101"},
		files={"image": ("notes.txt", b"not an image", "text/plain")},
	)

	assert response.status_code == 415
