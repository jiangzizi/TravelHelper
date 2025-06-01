import os
import datetime as _dt
from typing import List, Dict, Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

DUFFEL_TOKEN = os.getenv("DEFFEL_ACCESS_TOKEN", "duffel_test_Li5UOd_hOzpiAwxv3GLp4lQ23Y8bkaXo86R216FMgD-")
DUFFEL_BASE_URL = "https://api.duffel.com"
HEADERS = {
    "Authorization": f"Bearer {DUFFEL_TOKEN}",
    "Accept": "application/json",
    "Duffel-Version": "v2",
    "Accept-Encoding": "gzip",
}

mcp = FastMCP("flight_search")

# ────────── helpers ────────────────────────────────────────────────────────────

def _tomorrow() -> _dt.date:
    return _dt.date.today() + _dt.timedelta(days=1)


def _ensure_future(date_str: str | None) -> str | None:
    """Return a YYYY-MM-DD string that is strictly > today."""
    if date_str is None:
        return None
    d = _dt.date.fromisoformat(date_str)
    if d <= _dt.date.today():
        d = _tomorrow()
    return d.isoformat()


def _build_passengers(count: int) -> List[Dict[str, str]]:
    return [{"type": "adult"} for _ in range(max(1, count))]


def _build_slices(
    origin: str, destination: str, dep_date: str, ret_date: Optional[str]
) -> List[Dict[str, str]]:
    slices = [
        {"origin": origin, "destination": destination, "departure_date": dep_date}
    ]
    if ret_date:
        slices.append(
            {
                "origin": destination,
                "destination": origin,
                "departure_date": ret_date,
            }
        )
    return slices


async def _create_offer_request(
    client: httpx.AsyncClient, payload: Dict[str, Any]
) -> Dict[str, Any]:
    res = await client.post(
        f"{DUFFEL_BASE_URL}/air/offer_requests",
        params={"return_offers": "true"},
        json={"data": payload},
    )
    res.raise_for_status()
    return res.json()["data"]


# 🔄 NEW implementation uses /places/suggestions --------------------------------
async def _resolve_iata(term: str, client: httpx.AsyncClient) -> str:
    """Return an IATA code for a city/airport name or pass-through 3-letter code."""
    term_clean = term.strip()
    if len(term_clean) == 3 and term_clean.isalpha():
        return term_clean.upper()

    res = await client.get(
        f"{DUFFEL_BASE_URL}/places/suggestions",
        params={"query": term_clean, "limit": 1},  # limit is accepted but optional
    )
    res.raise_for_status()
    data = res.json().get("data", [])
    if not data:
        raise ValueError(
            f"无法将“{term}”解析为有效的机场/城市 IATA 代码。请检查拼写或直接提供三字代码。"
        )
    return data[0]["iata_code"]
# ───────────────────────────────────────────────────────────────────────────────

from typing import List, Dict, Any
from datetime import datetime

def _format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if hours else f"{mins}m"

def _parse_time(t: str) -> str:
    # You can change the format here if needed
    return datetime.fromisoformat(t).strftime("%Y-%m-%d %H:%M")

def _summarise_offers(offers: List[Dict[str, Any]], limit: int = 5) -> str:
    if not offers:
        return "No offers found."

    offers_sorted = sorted(offers, key=lambda off: float(off["total_amount"]))
    flight_results = {}
    flight_count = 0

    for off_id, off in enumerate(offers_sorted[:limit]):
        #new_str = str(off)
        total_flight = {}
        #return new_str
        total_flight["price"] = off["total_amount"]
        total_flight["currency"] = off["total_currency"]
        # total_duration = _format_duration(off.get("total_duration_mins", 0))
        total_flight["emissions"] = off.get("total_emissions_kg", "N/A")
        total_flight["cabin_class"] = off.get("cabin_class", "N/A")
        include_duffel = False

        
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("hotelsearch")

        for slice_idx, slc in enumerate(off.get("slices", [])):

            for seg_idx, seg in enumerate(slc.get("segments", [])):
                logger.info(f"Processing segment {seg_idx} {seg}")
                current_flight = {}
                current_flight["carrier"] = seg["marketing_carrier"]["name"]
                if "duffel" in current_flight["carrier"].lower():
                    include_duffel = True
                current_flight["flight_number"] = seg.get("marketing_carrier_flight_number", "N/A")
                current_flight["origin"] = seg["origin"]
                current_flight["dest"] = seg["destination"]
                current_flight["dep_time"] = _parse_time(seg["departing_at"])
                current_flight["arr_time"] = _parse_time(seg["arriving_at"])
                # duration = _format_duration(seg.get("duration_mins", 0))
                aircraft_data = seg.get("aircraft") or {}
                current_flight["aircraft"] = aircraft_data.get("name", "N/A")

                passenger_setting = seg.get("passengers")[0]

                current_flight["cabin"] = passenger_setting.get("cabin_class_marketing_name", "N/A")
                # emissions = seg.get("emissions_kg", "N/A")

                # Amenities
                current_flight["amenities"] = passenger_setting.get("cabin", {}).get("amenities", {})
                total_flight[str(seg_idx)] = current_flight
        if not include_duffel:
            flight_results[str(flight_count)] = total_flight    
            flight_count += 1
    return flight_results


# ────────── MCP tool ───────────────────────────────────────────────────────────


@mcp.tool()
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    cabin_class: str = "economy",
) -> str:
    """灵活搜索航班。

    参数说明:
    origin/destination : 三字 IATA 代码，或中/英文城市、机场名称 (例：“北京”“Beijing”“PEK”)。
    departure_date     : YYYY-MM-DD (必须晚于今天；若≤今天，则自动调整为明天)。
    return_date        : 同上，可选。
    passengers         : 成人旅客数量 (≥1)。
    cabin_class        : "economy", "premium_economy", "business", "first"。
    """
    if not DUFFEL_TOKEN:
        return "DUFFEL_ACCESS_TOKEN env var not set."

    departure_date = _ensure_future(departure_date)
    return_date = _ensure_future(return_date)

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            origin_code = await _resolve_iata(origin, client)
            destination_code = await _resolve_iata(destination, client)

            payload = {
                "slices": _build_slices(
                    origin_code, destination_code, departure_date, return_date
                ),
                "passengers": _build_passengers(passengers),
                "cabin_class": cabin_class,
            }

            data = await _create_offer_request(client, payload)
            return _summarise_offers(data.get("offers", []))

    except httpx.HTTPStatusError as exc:
        return f"HTTP error {exc.response.status_code}: {exc.response.text}"
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
