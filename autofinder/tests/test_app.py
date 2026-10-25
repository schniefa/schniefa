"""Tests für die Autofinder-Web-App mit simulierten Fahrzeugen."""
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import carconnectivity_config, create_app

CONFIG = {
    "google_maps_api_key": "TESTKEY",
    "web_username": "wir",
    "web_password": "geheim",
    "vw_accounts": [{"username": "a@example.com", "password": "pw1"}, {"username": "b@example.com", "password": "pw2"}],
    "cars": {"VIN1": {"name": "Golf", "color": "#123456"}},
}
AUTH = ("wir", "geheim")


def attr(value, updated=None):
    return SimpleNamespace(enabled=value is not None, value=value, last_updated=updated)


def vehicle(vin, lat, lon, road=None, house_number=None, model="Passat"):
    updated = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        vin=attr(vin), name=attr(None), model=attr(model),
        position=SimpleNamespace(
            latitude=attr(lat, updated), longitude=attr(lon, updated),
            location=SimpleNamespace(road=attr(road), house_number=attr(house_number)),
        ),
    )


class FakeCarConnectivity:
    def __init__(self, vehicles):
        self.vehicles = vehicles
        self.shut_down = False

    def get_garage(self):
        return SimpleNamespace(list_vehicles=lambda: self.vehicles)

    def shutdown(self):
        self.shut_down = True


def client(vehicles):
    return TestClient(create_app(CONFIG, FakeCarConnectivity(vehicles)))


def test_login_required():
    with client([]) as c:
        assert c.get("/api/cars").status_code == 401
        assert c.get("/api/cars", auth=("wir", "falsch")).status_code == 401


def test_cars_with_and_without_position():
    cars = [vehicle("VIN1", 48.15, 11.58, "Leopoldstraße", "12"), vehicle("VIN2", None, None)]
    with client(cars) as c:
        data = c.get("/api/cars", auth=AUTH).json()
    assert data[0] == {
        "vin": "VIN1", "name": "Golf", "color": "#123456", "latitude": 48.15, "longitude": 11.58,
        "address": "Leopoldstraße 12", "updated": "2026-10-25T12:00:00+00:00",
    }
    assert data[1]["name"] == "Passat"
    assert data[1]["latitude"] is None and data[1]["address"] is None and data[1]["updated"] is None


def test_index_contains_api_key():
    with client([]) as c:
        html = c.get("/", auth=AUTH).text
    assert "key=TESTKEY" in html and "__GOOGLE_MAPS_API_KEY__" not in html


def test_one_connector_per_vw_account():
    connectors = carconnectivity_config(CONFIG)["carConnectivity"]["connectors"]
    assert [c["connector_id"] for c in connectors] == ["volkswagen_0", "volkswagen_1"]
    assert connectors[1]["config"]["username"] == "b@example.com"
