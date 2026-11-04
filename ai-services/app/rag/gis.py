"""GIS projection from SQL source coordinates only; no inferred research/property centroids."""
import math


def gis_evidence(rows, properties, retrieved):
    by_id = {p["source"]["recordKey"]: p for p in properties if p.get("source", {}).get("kind") == "PROPERTY"}
    features = []
    for row in rows:
        lat, lon = row.get("latitude"), row.get("longitude")
        if row["id"] not in by_id or row.get("coordinate_srid") != 4326 or lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180 or (lat == 0 and lon == 0):
            continue
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {"propertyId": by_id[row["id"]]["id"], "coordinateSource": "MYSQL_PUBLISHED_PROPERTY",
                                        "verification": "SOURCE_COORDINATES_NOT_SURVEY_VERIFIED"}})
    return {"type": "FeatureCollection", "features": features,
            "areaReferences": [{"sourceId": d["sourceId"], "areaId": d["metadata"].get("areaId")} for d in retrieved],
            "researchPropertyCoordinatesInferred": False, "propertyPoiDistancesComputed": False}
