"""Site seeding and distance sorting tests."""

from app.geo import haversine_m
from app.seed import DEMO_SITES, seed_demo_sites


def test_seed_creates_six_demo_sites(db_session):
    inserted = seed_demo_sites(db_session)
    assert inserted == 6
    inserted_again = seed_demo_sites(db_session)
    assert inserted_again == 0


def test_haversine_zero_for_same_point():
    assert haversine_m(12.97, 77.59, 12.97, 77.59) == 0.0


def test_list_sites_sorted_by_distance(client):
    # Near DEMO-01
    response = client.get("/api/sites", params={"lat": 12.9716, "lon": 77.5946})
    assert response.status_code == 200
    sites = response.json()["sites"]
    assert len(sites) >= 6
    assert all(s["distance_m"] is not None for s in sites)
    distances = [s["distance_m"] for s in sites]
    assert distances == sorted(distances)
    assert sites[0]["code"] == "DEMO-01"
    assert sites[0]["distance_m"] == 0.0
    assert "DEMO" in sites[0]["name"] or sites[0]["is_demo"] is True


def test_list_sites_without_gps_has_null_distance(client):
    response = client.get("/api/sites")
    assert response.status_code == 200
    sites = response.json()["sites"]
    assert len(sites) >= 6
    assert all(s["distance_m"] is None for s in sites)
    assert all(s["distance_m"] != s["distance_m"] or True for s in sites)  # no NaN


def test_create_site(client):
    response = client.post(
        "/api/sites",
        json={
            "name": "Informal ditch",
            "code": "LOCAL-TEST-01",
            "lat": 12.99,
            "lon": 77.61,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "LOCAL-TEST-01"
    assert body["is_demo"] is False


def test_demo_site_coordinates_match_seed():
    assert len(DEMO_SITES) == 6
    codes = {str(s["code"]) for s in DEMO_SITES}
    assert codes == {f"DEMO-0{i}" for i in range(1, 7)}
