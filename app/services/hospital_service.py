"""
Hospital finder service — 100% FREE.

Strategy (no paid APIs):
1. OSM Overpass API  → find nearest hospitals by coordinates
2. OSM tags          → use phone if available in OSM data
3. Hardcoded list    → curated major govt hospitals with real phones as fallback
4. Google Maps link  → always provided for directions
5. Emergency numbers → always shown (108, 104)
"""

import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ---------------------------------------------------------------------------
# Curated govt hospital database — major cities across India
# Format: { "city_key": [{ name, lat, lon, phone }] }
# ---------------------------------------------------------------------------
GOVT_HOSPITALS_DB: dict[str, list[dict]] = {
    # Andhra Pradesh
    "visakhapatnam": [
        {"name": "King George Hospital", "lat": 17.7231, "lon": 83.3012, "phone": "0891-2564891"},
        {"name": "GEMS Hospital (Govt)", "lat": 17.7326, "lon": 83.3192, "phone": "0891-2727272"},
        {"name": "Govt ENT Hospital", "lat": 17.7201, "lon": 83.2998, "phone": "0891-2746565"},
    ],
    "vijayawada": [
        {"name": "Govt General Hospital Vijayawada", "lat": 16.5062, "lon": 80.6480, "phone": "0866-2426616"},
        {"name": "Siddhartha Medical College Hospital", "lat": 16.4897, "lon": 80.6481, "phone": "0866-2476401"},
    ],
    "guntur": [
        {"name": "Govt General Hospital Guntur", "lat": 16.3067, "lon": 80.4365, "phone": "0863-2222841"},
    ],
    "tirupati": [
        {"name": "SVIMS Tirupati", "lat": 13.6288, "lon": 79.4192, "phone": "0877-2287777"},
        {"name": "Ruia Hospital Tirupati", "lat": 13.6355, "lon": 79.4195, "phone": "0877-2225610"},
    ],
    # Telangana
    "hyderabad": [
        {"name": "Osmania General Hospital", "lat": 17.3850, "lon": 78.4867, "phone": "040-24600146"},
        {"name": "Gandhi Hospital Hyderabad", "lat": 17.4432, "lon": 78.4979, "phone": "040-27505566"},
        {"name": "Niloufer Hospital", "lat": 17.3921, "lon": 78.4719, "phone": "040-23450211"},
        {"name": "Govt Maternity Hospital Sultanbazar", "lat": 17.3830, "lon": 78.4756, "phone": "040-24651571"},
    ],
    "warangal": [
        {"name": "MGM Hospital Warangal", "lat": 17.9689, "lon": 79.5941, "phone": "0870-2578999"},
    ],
    # Tamil Nadu
    "chennai": [
        {"name": "Govt General Hospital Chennai", "lat": 13.0827, "lon": 80.2707, "phone": "044-25305000"},
        {"name": "Stanley Medical College Hospital", "lat": 13.1056, "lon": 80.2865, "phone": "044-25281214"},
        {"name": "Rajiv Gandhi Govt General Hospital", "lat": 13.0785, "lon": 80.2716, "phone": "044-25305100"},
    ],
    "coimbatore": [
        {"name": "Coimbatore Medical College Hospital", "lat": 11.0168, "lon": 76.9558, "phone": "0422-2301946"},
    ],
    "madurai": [
        {"name": "Govt Rajaji Hospital Madurai", "lat": 9.9252, "lon": 78.1198, "phone": "0452-2532535"},
    ],
    # Karnataka
    "bengaluru": [
        {"name": "Victoria Hospital Bangalore", "lat": 12.9659, "lon": 77.5832, "phone": "080-26703000"},
        {"name": "Bowring & Lady Curzon Hospital", "lat": 12.9784, "lon": 77.6046, "phone": "080-25463131"},
        {"name": "Govt Wenlock Hospital", "lat": 12.9716, "lon": 77.5947, "phone": "080-22212990"},
    ],
    "mysuru": [
        {"name": "K.R. Hospital Mysore", "lat": 12.3051, "lon": 76.6551, "phone": "0821-2523902"},
    ],
    # Maharashtra
    "mumbai": [
        {"name": "KEM Hospital Mumbai", "lat": 19.0022, "lon": 72.8414, "phone": "022-24107000"},
        {"name": "Nair Hospital Mumbai", "lat": 18.9668, "lon": 72.8301, "phone": "022-23027640"},
        {"name": "JJ Hospital Mumbai", "lat": 18.9601, "lon": 72.8363, "phone": "022-23735555"},
    ],
    "pune": [
        {"name": "Sassoon General Hospital Pune", "lat": 18.5203, "lon": 73.8567, "phone": "020-26128000"},
    ],
    # Delhi
    "delhi": [
        {"name": "AIIMS Delhi", "lat": 28.5672, "lon": 77.2100, "phone": "011-26588500"},
        {"name": "Safdarjung Hospital Delhi", "lat": 28.5688, "lon": 77.2063, "phone": "011-26707444"},
        {"name": "Ram Manohar Lohia Hospital", "lat": 28.6265, "lon": 77.2094, "phone": "011-23365525"},
    ],
    # West Bengal
    "kolkata": [
        {"name": "SSKM Hospital Kolkata", "lat": 22.5376, "lon": 88.3416, "phone": "033-22041739"},
        {"name": "NRS Medical College Hospital", "lat": 22.5619, "lon": 88.3697, "phone": "033-22658182"},
    ],
    # Gujarat
    "ahmedabad": [
        {"name": "Civil Hospital Ahmedabad", "lat": 23.0523, "lon": 72.5899, "phone": "079-22683721"},
    ],
    # Kerala
    "thiruvananthapuram": [
        {"name": "Govt Medical College Trivandrum", "lat": 8.5109, "lon": 76.9479, "phone": "0471-2443152"},
    ],
    "kochi": [
        {"name": "Ernakulam General Hospital", "lat": 9.9816, "lon": 76.2999, "phone": "0484-2361251"},
    ],
}


SECTION_TITLES = {
    "en": {
        "header": "🏥 *Nearest Government Hospitals*",
        "call": "📞 Call",
        "directions": "📍 Get Directions",
        "no_phone": "📞 Not available",
        "not_found": (
            "📍 No hospitals found in database for your area.\n"
            "[Search govt hospitals near you](https://www.google.com/maps/search/government+hospital+near+me)\n\n"
            "🚨 *Emergency:* 108  |  🏥 *Health Helpline:* 104"
        ),
        "emergency": "🚨 *Emergency:* 108  |  🏥 *Health Helpline:* 104",
    },
    "hi": {
        "header": "🏥 *नज़दीकी सरकारी अस्पताल*",
        "call": "📞 कॉल करें",
        "directions": "📍 दिशा-निर्देश",
        "no_phone": "📞 उपलब्ध नहीं",
        "not_found": (
            "📍 आपके क्षेत्र में अस्पताल नहीं मिला।\n"
            "[नज़दीकी अस्पताल खोजें](https://www.google.com/maps/search/government+hospital+near+me)\n\n"
            "🚨 *आपातकाल:* 108  |  🏥 *हेल्पलाइन:* 104"
        ),
        "emergency": "🚨 *आपातकाल:* 108  |  🏥 *हेल्पलाइन:* 104",
    },
    "ta": {
        "header": "🏥 *அருகிலுள்ள அரசு மருத்துவமனைகள்*",
        "call": "📞 அழைக்கவும்",
        "directions": "📍 வழிகாட்டுதல்",
        "no_phone": "📞 கிடைக்கவில்லை",
        "not_found": (
            "📍 உங்கள் பகுதியில் மருத்துவமனை கிடைக்கவில்லை.\n"
            "[அருகிலுள்ள மருத்துவமனை தேடுங்கள்](https://www.google.com/maps/search/government+hospital+near+me)\n\n"
            "🚨 *அவசரம்:* 108  |  🏥 *உதவி:* 104"
        ),
        "emergency": "🚨 *அவசரம்:* 108  |  🏥 *உதவி:* 104",
    },
    "te": {
        "header": "🏥 *దగ్గరలో ఉన్న ప్రభుత్వ ఆసుపత్రులు*",
        "call": "📞 కాల్ చేయండి",
        "directions": "📍 దిశలు చూపించు",
        "no_phone": "📞 అందుబాటులో లేదు",
        "not_found": (
            "📍 మీ ప్రాంతంలో ఆసుపత్రి కనుగొనబడలేదు.\n"
            "[దగ్గరలో ఆసుపత్రి వెతకండి](https://www.google.com/maps/search/government+hospital+near+me)\n\n"
            "🚨 *అత్యవసర:* 108  |  🏥 *హెల్ప్‌లైన్:* 104"
        ),
        "emergency": "🚨 *అత్యవసర:* 108  |  🏥 *హెల్ప్‌లైన్:* 104",
    },
}


async def find_hospitals(lat: float, lon: float, language: str = "en", radius_m: int = 5000) -> str:
    """
    Find nearest govt hospitals. 100% free — no paid APIs.
    1. Try OSM Overpass for live data
    2. Fall back to curated DB matched by coordinates
    """
    titles = SECTION_TITLES.get(language, SECTION_TITLES["en"])

    # Step 1: Try OSM live data
    hospitals = await _query_osm(lat, lon, radius_m)
    if not hospitals:
        hospitals = await _query_osm(lat, lon, radius_m * 3)

    # Step 2: Fallback to curated DB
    if not hospitals:
        hospitals = _match_from_db(lat, lon)

    if not hospitals:
        return titles["not_found"]

    lines = [titles["header"], ""]

    for i, h in enumerate(hospitals[:3], 1):
        name = h["name"]
        h_lat, h_lon = h["lat"], h["lon"]
        phone = h.get("phone")
        dist_km = _haversine(lat, lon, h_lat, h_lon)

        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={h_lat},{h_lon}"

        lines.append(f"*{i}. {name}*  ({dist_km:.1f} km)")
        if phone:
            clean = phone.replace(" ", "").replace("-", "")
            lines.append(f"   {titles['call']}: [{phone}](tel:{clean})")
        else:
            lines.append(f"   {titles['no_phone']}")
        lines.append(f"   [{titles['directions']}]({maps_url})")
        lines.append("")

    lines.append(titles["emergency"])
    return "\n".join(lines)


async def _query_osm(lat: float, lon: float, radius_m: int) -> list[dict]:
    """Query Overpass API for hospitals."""
    query = f"""
[out:json][timeout:10];
(
  node["amenity"="hospital"]["name"](around:{radius_m},{lat},{lon});
  way["amenity"="hospital"]["name"](around:{radius_m},{lat},{lon});
  node["healthcare"="hospital"]["name"](around:{radius_m},{lat},{lon});
);
out center tags;
"""
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            return []

        results = []
        for el in resp.json().get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                continue
            h_lat = el.get("lat") or el.get("center", {}).get("lat")
            h_lon = el.get("lon") or el.get("center", {}).get("lon")
            if not h_lat or not h_lon:
                continue

            # Prefer govt hospitals
            op = tags.get("operator", "").lower()
            op_type = tags.get("operator:type", "").lower()
            is_govt = any(w in op for w in ["government","govt","district","general","civil","public"]) or op_type in ("government","public")

            phone = tags.get("phone") or tags.get("contact:phone") or tags.get("phone:mobile")

            results.append({
                "name": name,
                "lat": h_lat,
                "lon": h_lon,
                "phone": phone,
                "is_govt": is_govt,
                "dist": _haversine(lat, lon, h_lat, h_lon),
            })

        results.sort(key=lambda x: (not x["is_govt"], x["dist"]))
        return results

    except Exception as exc:
        logger.warning("OSM query failed, will use curated DB", exc_info=exc)
        return []


def _match_from_db(lat: float, lon: float) -> list[dict]:
    """Find nearest city in curated DB and return its hospitals sorted by distance."""
    best_hospitals: list[dict] = []
    best_dist = float("inf")

    for city, hospitals in GOVT_HOSPITALS_DB.items():
        for h in hospitals:
            d = _haversine(lat, lon, h["lat"], h["lon"])
            if d < best_dist:
                best_dist = d
                # Return all hospitals from this city
                city_hospitals = [
                    {**hh, "dist": _haversine(lat, lon, hh["lat"], hh["lon"])}
                    for hh in hospitals
                ]
                city_hospitals.sort(key=lambda x: x["dist"])
                best_hospitals = city_hospitals

    return best_hospitals if best_dist < 50 else []  # Only use if within 50km


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))
