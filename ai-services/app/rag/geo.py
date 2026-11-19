"""Great-circle distance, used to filter nearby listings by real distance.

The bounding box only narrows the candidate set; this is what decides whether a listing
is actually inside the radius the user was told about.
"""
import math

EARTH_RADIUS_METERS = 6_371_008.8


def haversine_meters(lat1, lon1, lat2, lon2):
    """Straight-line distance in metres between two WGS84 points."""
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = phi2 - phi1
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(a)))
