"""
Ghana region + severity classification for /report and /detections/export.

Region assignment is nearest-centroid (haversine distance to each of
Ghana's 16 administrative regions, using each region's capital as a proxy
centroid) — there's no region boundary polygon data available, so this is
a coarse approximation good for grouping/prioritizing by area, not
survey-grade GIS work.
"""

import math

# Proxy centroid (regional capital) for each of Ghana's 16 administrative regions.
GHANA_REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "Greater Accra": (5.6037, -0.1870),   # Accra
    "Ashanti": (6.6885, -1.6244),         # Kumasi
    "Western": (4.9346, -1.7554),         # Sekondi-Takoradi
    "Western North": (6.2044, -2.4806),   # Sefwi Wiawso
    "Central": (5.1053, -1.2466),         # Cape Coast
    "Eastern": (6.0941, -0.2591),         # Koforidua
    "Volta": (6.6008, 0.4713),            # Ho
    "Oti": (7.7514, 0.3489),              # Dambai
    "Northern": (9.4008, -0.8393),        # Tamale
    "Savannah": (9.0833, -1.8167),        # Damongo
    "North East": (10.5297, -0.3689),     # Nalerigu
    "Upper East": (10.7856, -0.8514),     # Bolgatanga
    "Upper West": (10.0601, -2.5099),     # Wa
    "Bono": (7.3389, -2.3267),            # Sunyani
    "Bono East": (7.5920, -1.9395),       # Techiman
    "Ahafo": (6.7975, -2.5211),           # Goaso
}

SEVERITY_HIGH_THRESHOLD = 0.75
SEVERITY_MEDIUM_THRESHOLD = 0.5


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def nearest_region(lat: float, lng: float) -> str:
    return min(
        GHANA_REGION_CENTROIDS,
        key=lambda region: _haversine_km(lat, lng, *GHANA_REGION_CENTROIDS[region]),
    )


def severity_bucket(confidence: float) -> str:
    if confidence >= SEVERITY_HIGH_THRESHOLD:
        return "high"
    if confidence >= SEVERITY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"
