"""Current GDACS events matched to graph coordinates, without changing the world."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter

from domino.config import settings
from domino.graph.run_query import run_query

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)
GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
FEED_TIMEOUT_SECONDS = 8
CACHE_SECONDS = 600
# Screening distances from each event centroid, not official hazard footprints.
RADII_KM = {"FL": 150, "EQ": 150, "TC": 400, "VO": 100, "DR": 300, "WF": 100}
EVENT_TYPES = {"FL": "Flood", "EQ": "Earthquake", "TC": "Tropical cyclone",
               "VO": "Volcano", "DR": "Drought", "WF": "Wildfire"}
_cache: tuple[float, str, dict[str, Any]] | None = None
_cache_lock = Lock()


def _fetch_type(event_type: str) -> list[dict[str, Any]]:
    # MAP requires a single eventtype. A combined latest-events feed can omit whole hazard types.
    headers = {"Accept": "application/geo+json, application/json", "User-Agent": "DOMINO/0.1 live-alerts"}
    deadline = time.monotonic() + FEED_TIMEOUT_SECONDS
    try:
        request = Request(f"{GDACS_URL}?eventtype={event_type}", headers=headers)
        with urlopen(request, timeout=FEED_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code != 404:
            raise
        # Some hazard types (notably volcanoes) have no MAP resource; SEARCH still serves them.
        today = datetime.now(UTC).date()
        params = urlencode({"eventlist": event_type, "alertlevel": "green;orange;red",
                            "fromdate": (today - timedelta(days=30)).isoformat(),
                            "todate": (today + timedelta(days=1)).isoformat()})
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("GDACS request exceeded its time budget") from exc
        request = Request(f"{GDACS_URL.rsplit('/', 1)[0]}/SEARCH?{params}", headers=headers)
        with urlopen(request, timeout=remaining) as response:
            payload = json.load(response)
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise ValueError("Invalid GDACS event collection")
    return payload["features"]


def _fetch_feed() -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=len(EVENT_TYPES)) as pool:
        collections = pool.map(_fetch_type, EVENT_TYPES)
        return {"type": "FeatureCollection", "features": [f for features in collections for f in features]}


def _feed() -> tuple[dict[str, Any], str]:
    global _cache
    with _cache_lock:
        if _cache is not None and time.monotonic() - _cache[0] < CACHE_SECONDS:
            return _cache[2], _cache[1]
        payload = _fetch_feed()
        updated_at = datetime.now(UTC).isoformat()
        _cache = (time.monotonic(), updated_at, payload)
        return payload, updated_at


def _date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC).isoformat()
    except ValueError:
        return None


def _coords(lat: Any, lng: Any) -> tuple[float, float] | None:
    try:
        lat, lng = float(lat), float(lng)
        if math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    a1, a2 = math.radians(lat1), math.radians(lat2)
    dlat, dlng = a2 - a1, math.radians(lng2 - lng1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlng / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, h))))


def match_events(payload: dict[str, Any], places: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match point centroids to all graph places; only supplier sites can be manually stopped."""
    events: dict[str, dict[str, Any]] = {}
    for feature in payload["features"]:
        if not isinstance(feature, dict):
            continue
        props, geometry = feature.get("properties") or {}, feature.get("geometry") or {}
        if not isinstance(props, dict) or not isinstance(geometry, dict):
            continue
        code = props.get("eventtype")
        point = geometry.get("coordinates")
        if not isinstance(code, str) or code not in EVENT_TYPES or geometry.get("type") != "Point" or not isinstance(point, list) or len(point) < 2:
            continue
        if props.get("Class") and props["Class"] != "Point_Centroid":
            continue
        coords = _coords(point[1], point[0])
        if coords is None or props.get("eventid") is None or str(props.get("iscurrent", "true")).lower() == "false":
            continue
        matches = []
        for place in places:
            location = _coords(place.get("lat"), place.get("lng"))
            if location is None:
                continue
            distance = haversine_km(*coords, *location)
            if distance <= RADII_KM[code]:
                matches.append({"id": place["id"], "name": place["name"], "kind": place["kind"],
                                "tier": place.get("tier"), "distance_km": round(distance, 2)})
        matches.sort(key=lambda p: (p["distance_km"], p["id"]))
        sites = [p for p in matches if p["kind"] == "Site"]
        title = " ".join(str(props.get("name") or props.get("description") or props.get("eventname") or EVENT_TYPES[code]).split())
        country = " ".join(str(props.get("country") or "Country not provided").split())
        level = str(props.get("alertlevel") or "Unknown").capitalize()
        starts_at, ends_at = _date(props.get("fromdate")), _date(props.get("todate"))
        modified_at = _date(props.get("datemodified")) or ends_at or starts_at
        event_id = f"{code}-{props['eventid']}"
        alert_text = f"GDACS {EVENT_TYPES[code]} alert ({level}): {title}. Country: {country}."
        if starts_at:
            alert_text += f" Started: {starts_at}."
        if modified_at:
            alert_text += f" Updated: {modified_at}."
        alert_text += f" Screening radius: {RADII_KM[code]} km from {coords[0]}, {coords[1]}; proximity is not confirmed damage."
        if sites:
            alert_text += " Nearby supplier sites: " + "; ".join(f"{s['name']} ({s['id']})" for s in sites) + "."
        elif matches:
            alert_text += " Nearby graph places: " + "; ".join(f"{p['name']} ({p['id']})" for p in matches) + ". No supplier sites within the screening radius."
        else:
            alert_text += " Not in the graph. Not being in the graph does not mean safe."
        event = {"id": event_id, "event_type": code, "type_label": EVENT_TYPES[code], "title": title,
                 "country": country, "alert_level": level, "lat": coords[0], "lng": coords[1],
                 "starts_at": starts_at, "ends_at": ends_at, "updated_at": modified_at,
                 "radius_km": RADII_KM[code], "places": matches, "sites": sites,
                 "site_ids": [s["id"] for s in sites], "in_graph": bool(matches), "alert_text": alert_text}
        previous = events.get(event_id)
        if previous is None or (modified_at or "") > (previous["updated_at"] or ""):
            events[event_id] = event
    # Surface graph matches first, then higher alert levels and the latest updates.
    return sorted(events.values(), key=lambda e: (e["in_graph"], {"Red": 3, "Orange": 2, "Green": 1}.get(e["alert_level"], 0), e["updated_at"] or "", e["id"]), reverse=True)


def _live_alerts() -> dict[str, Any]:
    try:
        payload, updated_at = _feed()
    except Exception as exc:
        log.warning("GDACS feed unavailable: %s", exc)
        return {"events": [], "source": "gdacs", "updated_at": None, "error": "GDACS feed is temporarily unavailable. Try again shortly."}
    try:
        places = run_query("graph/place_coords", graph=settings.world_graph_live)
        events = match_events(payload, places)
    except Exception as exc:
        log.warning("Live-alert graph matching unavailable: %s", exc)
        return {"events": [], "source": "gdacs", "updated_at": updated_at, "error": "Supply-chain locations are temporarily unavailable. Try again shortly."}
    return {"events": events, "source": "gdacs", "updated_at": updated_at}


@router.get("/live-alerts")
async def live_alerts() -> dict[str, Any]:
    return await asyncio.to_thread(_live_alerts)
