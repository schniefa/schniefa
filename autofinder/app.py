"""Autofinder: zeigt die Parkpositionen unserer VWs auf einer Google-Karte."""
from __future__ import annotations

import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

LOG = logging.getLogger("autofinder")

BASE_DIR = Path(__file__).parent
CONFIG_FILE = Path(os.environ.get("AUTOFINDER_CONFIG", BASE_DIR / "config.json"))
DATA_DIR = Path(os.environ.get("AUTOFINDER_DATA", BASE_DIR / "data"))


def load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    with open(path, encoding="utf8") as file:
        return json.load(file)


def carconnectivity_config(config: dict[str, Any]) -> dict[str, Any]:
    """Baut die CarConnectivity-Konfiguration aus unseren VW-Konten."""
    connectors = []
    for index, account in enumerate(config["vw_accounts"]):
        connectors.append({
            "type": "volkswagen",
            "connector_id": f"volkswagen_{index}",
            "config": {
                "username": account["username"],
                "password": account["password"],
                "interval": config.get("interval_seconds", 300),
            },
        })
    return {"carConnectivity": {"log_level": "warning", "connectors": connectors}}


def _value(attribute: Any) -> Any:
    if attribute is None or not getattr(attribute, "enabled", False):
        return None
    return attribute.value


def _address(location: Any) -> Optional[str]:
    road = _value(getattr(location, "road", None))
    if road is None:
        return None
    house_number = _value(getattr(location, "house_number", None))
    return f"{road} {house_number}" if house_number else road


def vehicle_to_dict(vehicle: Any, car_settings: dict[str, Any]) -> dict[str, Any]:
    """Wandelt ein CarConnectivity-Fahrzeug in das JSON für die Karte um."""
    vin = vehicle.vin.value
    settings = car_settings.get(vin, {})
    position = vehicle.position
    latitude = _value(position.latitude)
    longitude = _value(position.longitude)
    updated = position.latitude.last_updated if latitude is not None else None
    return {
        "vin": vin,
        "name": settings.get("name") or _value(vehicle.name) or _value(vehicle.model) or vin,
        "color": settings.get("color", "#1a73e8"),
        "latitude": latitude,
        "longitude": longitude,
        "address": _address(position.location) if latitude is not None else None,
        "updated": updated.isoformat() if updated else None,
    }


def create_app(config: dict[str, Any], car_connectivity: Any = None) -> FastAPI:
    """Erstellt die Web-App. car_connectivity kann für Tests ersetzt werden."""
    car_settings: dict[str, Any] = config.get("cars", {})
    security = HTTPBasic()

    def check_login(credentials: HTTPBasicCredentials = Depends(security)) -> None:
        user_ok = secrets.compare_digest(credentials.username.encode(), config["web_username"].encode())
        password_ok = secrets.compare_digest(credentials.password.encode(), config["web_password"].encode())
        if not (user_ok and password_ok):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal car_connectivity
        if car_connectivity is None:
            from carconnectivity import carconnectivity  # pylint: disable=import-outside-toplevel
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            car_connectivity = carconnectivity.CarConnectivity(
                config=carconnectivity_config(config),
                tokenstore_file=str(DATA_DIR / "tokenstore"),
                cache_file=str(DATA_DIR / "cache"),
            )
            car_connectivity.startup()
        yield
        car_connectivity.shutdown()

    app = FastAPI(lifespan=lifespan, dependencies=[Depends(check_login)])
    index_html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf8")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return index_html.replace("__GOOGLE_MAPS_API_KEY__", config["google_maps_api_key"])

    @app.get("/api/cars")
    def cars() -> JSONResponse:
        garage = car_connectivity.get_garage()
        vehicles = garage.list_vehicles() if garage is not None else []
        return JSONResponse([vehicle_to_dict(vehicle, car_settings) for vehicle in vehicles])

    return app


def main() -> None:
    import uvicorn  # pylint: disable=import-outside-toplevel

    logging.basicConfig(level=logging.INFO)
    config = load_config()
    uvicorn.run(create_app(config), host="0.0.0.0", port=int(config.get("port", 8080)))


if __name__ == "__main__":
    main()
