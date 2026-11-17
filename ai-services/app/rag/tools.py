"""Fixed backend routes and parameterized SQL projections. There is no text-to-SQL API."""
import json
import math
import re
import time
from decimal import Decimal
import httpx
from .config import GroundingError, RagUnavailable


def _is_number(value):
    """json.loads(parse_float=Decimal) yields Decimal, so accept any finite real."""
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool) and Decimal(str(value)).is_finite()


class UpstreamError(RuntimeError):
    def __init__(self, status=502):
        self.status = status if status in (401, 403, 404) else 502
        super().__init__("BACKEND_TOOL_UNAVAILABLE")


# A nearby search reads every page of the box, but never without bound.
NEARBY_MAX_PAGES = 20


class OutboundRateLimited(UpstreamError):
    """Our own request budget is spent — not the routing vendor's.

    The backend answers 429 when SmartProp's per-IP or daily cap trips; the vendor's own
    limit arrives as a different code and is reported separately. Retrying immediately is
    pointless in both cases, so the caller gets a retry hint instead.
    """

    def __init__(self, retry_after=60):
        super().__init__(429)
        self.retry_after = max(1, int(retry_after))
        self.args = ("CLIENT_RATE_LIMITED",)


class BackendTools:
    def __init__(self, settings):
        self.settings = settings
        self.client = httpx.Client(base_url=settings.backend_url, timeout=httpx.Timeout(settings.backend_timeout_seconds, connect=2),
                                   trust_env=False, follow_redirects=False)

    def close(self):
        self.client.close()

    def _call(self, method, path, payload=None, token=None):
        headers = {}
        if token is not None:
            if not self.settings.research_enabled or not self.settings.demo_key:
                raise UpstreamError(403)
            if not token.startswith("Bearer ") or len(token) > 8192:
                raise UpstreamError(401)
            headers = {"Authorization": token, "X-SmartProp-Demo-Key": self.settings.demo_key}
        try:
            response = self.client.request(method, path, headers=headers, json=payload)
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            return json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e

    def account_context(self, token):
        if not isinstance(token,str) or not token.startswith("Bearer ") or len(token)>8192:
            raise UpstreamError(401)
        try:
            response=self.client.get("/api/v1/users/me/advisor-context",headers={"Authorization":token})
            if response.status_code!=200:
                raise UpstreamError(response.status_code)
            result=response.json()
            if not re.fullmatch(r"[0-9]{1,19}",str(result.get("subject",""))) or type(result.get("enabled")) is not bool:
                raise UpstreamError()
            return result
        except (httpx.HTTPError,ValueError) as e:
            raise UpstreamError() from e

    def authorize_research(self, token):
        if not token:
            raise UpstreamError(401)
        result = self._call("GET", "/api/v1/recommendations/research/config", token=token)
        if result.get("enabled") is not True:
            raise UpstreamError(403)
        # /config checks ADMIN but not the demo key. Use an existing guarded,
        # bounded amenity route to verify the second factor even without a budget.
        self._call("GET", "/api/v1/amenities/research/areas?level=DISTRICT", token=token)

    def recommend(self, criteria, *, research=False, token=None):
        route = "/api/v1/recommendations/research" if research else "/api/v1/recommendations"
        body = self._call("POST", route, criteria, token if research else None)
        if body.get("method") != "HEURISTIC_V1_1" or body.get("mode") != ("INTERNAL_DEMO" if research else "SAFE"):
            raise GroundingError("UNEXPECTED_RECOMMENDATION_MODE")
        properties = body.get("topProperties")
        if not isinstance(properties, list) or len(properties) > 10:
            raise GroundingError("INVALID_RECOMMENDATION_RESULT")
        if not research:
            public_blob = json.dumps(body, default=str)
            if any(marker in public_blob for marker in ("TINIX_AI", "tinix:", "HYBRID_ELIGIBLE_RESEARCH", "sampleListingCount", "raw_payload")):
                raise GroundingError("PUBLIC_RESEARCH_LEAK")
        seen, groups = set(), set()
        for p in properties:
            price, area = Decimal(str(p["priceVnd"])), Decimal(str(p["areaSqm"]))
            if not price.is_finite() or not area.is_finite() or not 0 < price <= Decimal(str(criteria["budgetVnd"])) or area <= 0:
                raise GroundingError("INVALID_RECOMMENDATION_NUMBER")
            if p["id"] in seen or p.get("qualityStatus") in ("REJECTED", "EXCLUDED") or p.get("isProtectedHoldout") or p.get("holdout") or p.get("groupHasHoldout"):
                raise GroundingError("INELIGIBLE_RECOMMENDATION")
            seen.add(p["id"])
            group = p.get("duplicateGroup")
            if group is not None:
                if group in groups:
                    raise GroundingError("DUPLICATE_RECOMMENDATION_GROUP")
                groups.add(group)
            kind = p.get("source", {}).get("kind")
            if not research and not ((kind == "PROPERTY" and p.get("qualityStatus") == "PLATFORM_PUBLISHED") or
                                     (kind == "EXTERNAL" and p.get("qualityStatus") == "VALID" and p.get("verificationStatus") == "VERIFIED")):
                raise GroundingError("PUBLIC_RESEARCH_LEAK")
            if kind == "TINIX_AI" and (not research or p.get("qualityStatus") != "HYBRID_ELIGIBLE_RESEARCH"):
                raise GroundingError("PUBLIC_RESEARCH_LEAK")
        return body

    def market_analytics(self, district=None):
        """Read-only aggregate market statistics; no property ids or contact data."""
        params = {"includeResearch": "false"}
        if district:
            params["district"] = district
        try:
            response = self.client.get("/api/v1/properties/market-analytics", params=params)
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if (not isinstance(body, dict) or not isinstance(body.get("meta"), dict)
                or not isinstance(body.get("overall"), dict)
                or body["meta"].get("priceBasis") != "ASKING_SALE_VND_TOTAL"):
            raise GroundingError("INVALID_MARKET_ANALYTICS")
        return body

    def amenity_summary(self):
        return self._call("GET", "/api/v1/amenities/summary")

    def amenity_areas(self):
        return self._call("GET", "/api/v1/amenities/areas")

    AMENITY_CATEGORIES = ("SCHOOL", "HOSPITAL", "PHARMACY", "MARKET", "SUPERMARKET", "PARK", "BEACH", "PUBLIC_TRANSPORT")

    def amenity_map(self, district, category):
        """Read-only POI evidence lookup already proven public. Never invents or geocodes."""
        if not district or category not in self.AMENITY_CATEGORIES:
            raise GroundingError("INVALID_AMENITY_CATEGORY")
        try:
            response = self.client.get("/api/v1/amenities/map", params={"district": district, "category": category})
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if body.get("version") != "POI_MAP_V1" or body.get("visibility") != "PUBLIC":
            raise GroundingError("INVALID_AMENITY_MAP_EVIDENCE")
        if body.get("district") != district or body.get("category") != category:
            raise GroundingError("AMENITY_SCOPE_MISMATCH")
        items = body.get("items")
        if not isinstance(items, list) or len(items) > 80:
            raise GroundingError("INVALID_AMENITY_MAP_EVIDENCE")
        for i in items:
            if (i.get("category") != category or i.get("district") != district or i.get("reviewStatus") != "VALID"
                    or i.get("sourceName") != "openstreetmap_overpass" or not i.get("sourceUrl", "").startswith("https://www.openstreetmap.org/")
                    or not _is_number(i.get("latitude")) or not _is_number(i.get("longitude"))):
                raise GroundingError("INVALID_AMENITY_MAP_EVIDENCE")
        return body

    def nearby_pois(self, property_id, radius=1000, limit=6):
        """Existing public property-to-POI endpoint; distance is straight-line (ST_Distance_Sphere)."""
        if not isinstance(property_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", property_id):
            raise GroundingError("INVALID_PROPERTY_ID")
        if not 1 <= radius <= 50000 or not 1 <= limit <= 20:
            raise GroundingError("INVALID_POI_RANGE")
        try:
            response = self.client.get("/api/v1/properties/" + property_id + "/points-of-interest",
                                       params={"radiusMeters": radius, "limit": limit})
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            items = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if not isinstance(items, list) or len(items) > 20:
            raise GroundingError("INVALID_NEARBY_POI_EVIDENCE")
        clean = []
        for item in items:
            if (not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip()
                    or not isinstance(item.get("category"), str) or not item["category"].strip()
                    or not _is_number(item.get("distanceMeters")) or item["distanceMeters"] < 0):
                raise GroundingError("INVALID_NEARBY_POI_EVIDENCE")
            clean.append({"name": item["name"].strip(), "category": item["category"].strip(),
                          "distanceMeters": float(item["distanceMeters"])})
        return clean

    def property_detail(self, property_id):
        """Public listing detail. Drafts and private listings are not served by this route."""
        if not isinstance(property_id, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", property_id):
            raise GroundingError("INVALID_PROPERTY_ID")
        try:
            response = self.client.get("/api/v1/properties/" + property_id)
            if response.status_code == 404:
                raise GroundingError("PROPERTY_NOT_PUBLIC")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if not isinstance(body, dict) or str(body.get("id", "")).lower() != property_id.lower():
            raise GroundingError("INVALID_PROPERTY_DETAIL")
        if body.get("status") != "PUBLISHED":
            raise GroundingError("PROPERTY_NOT_PUBLIC")
        price = body.get("price")
        if not _is_number(price) or price <= 0:
            raise GroundingError("INVALID_PROPERTY_DETAIL")
        return {
            "id": body["id"],
            "title": str(body.get("title") or "").strip(),
            "priceVnd": float(price),
            "areaSqm": float(body["areaSqm"]) if _is_number(body.get("areaSqm")) else None,
            "district": str(body.get("district") or "").strip(),
            "ward": str(body.get("ward") or "").strip(),
            "propertyType": str(body.get("propertyType") or "").strip(),
            "transactionType": str(body.get("transactionType") or "").strip(),
            "listingCode": str(body.get("listingCode") or "").strip(),
            "contentVersion": body.get("contentVersion"),
        }

    def _commute_request(self, property_id, latitude, longitude, label, mode):
        """One route call, retried once when the shared provider budget is momentarily full.

        The backend answers 429 when the outbound egress bucket is exhausted. That is a
        transient throttle, not a missing route, so a single short retry is honest.
        """
        params = {"latitude": float(latitude), "longitude": float(longitude),
                  "label": str(label or "")[:200], "mode": mode}
        response = self.client.get("/api/v1/properties/" + property_id + "/commute", params=params)
        if response.status_code == 429:
            time.sleep(1.2)
            response = self.client.get("/api/v1/properties/" + property_id + "/commute", params=params)
        return response

    def commute(self, property_id, latitude, longitude, label="", mode="drive"):
        """Driving/walking time from a public listing to a user-confirmed point."""
        if not isinstance(property_id, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", property_id):
            raise GroundingError("INVALID_PROPERTY_ID")
        if not _is_number(latitude) or not _is_number(longitude):
            raise GroundingError("INVALID_COMMUTE_DESTINATION")
        if mode not in ("walk", "drive"):
            raise GroundingError("INVALID_COMMUTE_MODE")
        try:
            response = self._commute_request(property_id, latitude, longitude, label, mode)
            if response.status_code == 404:
                raise GroundingError("PROPERTY_NOT_PUBLIC")
            if response.status_code == 429:
                raise OutboundRateLimited()
            if response.status_code in (422, 400):
                raise GroundingError("COMMUTE_UNAVAILABLE")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if (not isinstance(body, dict) or not _is_number(body.get("distanceMeters"))
                or not _is_number(body.get("durationSeconds"))):
            raise GroundingError("INVALID_COMMUTE_RESULT")
        return {"distanceMeters": float(body["distanceMeters"]),
                "durationSeconds": float(body["durationSeconds"]),
                "mode": body.get("mode") or mode,
                "provider": body.get("provider") or "GEOAPIFY"}

    def geocode_workplace(self, address):
        """Resolve a user-supplied workplace address to candidate points.

        The caller must have obtained consent first: this sends the address to the map
        provider. Only coordinates and a display label come back; nothing is stored.
        """
        text = (address or "").strip()
        if len(text) < 3 or len(text) > 300:
            raise GroundingError("INVALID_ADDRESS")
        try:
            response = self.client.post("/api/v1/advisor/geocoding",
                                        json={"address": text, "shareAddress": True})
            if response.status_code == 429:
                raise GroundingError("GEOCODING_RATE_LIMITED")
            if response.status_code in (422, 400):
                raise GroundingError("INVALID_ADDRESS")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if not isinstance(body, dict) or body.get("status") not in ("OK", "NO_MATCH"):
            raise GroundingError("INVALID_GEOCODING_RESULT")
        points = []
        for item in body.get("candidates") or []:
            if (not isinstance(item, dict) or not isinstance(item.get("label"), str)
                    or not item["label"].strip() or not isinstance(item.get("id"), str)):
                raise GroundingError("INVALID_GEOCODING_RESULT")
            if not _is_number(item.get("latitude")) or not _is_number(item.get("longitude")):
                raise GroundingError("INVALID_GEOCODING_RESULT")
            points.append({"id": item["id"], "label": item["label"].strip()[:300],
                           "latitude": float(item["latitude"]), "longitude": float(item["longitude"]),
                           "approximate": bool(item.get("approximate"))})
            if len(points) >= 5:
                break
        return points

    def saved_workplace(self, token):
        """Candidate points for the saved workplace, resolved server-side.

        The account's raw workplace string is never sent here: the backend geocodes it
        internally and answers with coordinates only.
        """
        if not isinstance(token, str) or not token.startswith("Bearer ") or len(token) > 8192:
            raise GroundingError("WORKPLACE_REQUIRES_ACCOUNT")
        try:
            response = self.client.get("/api/v1/users/me/advisor-context/workplace",
                                       headers={"Authorization": token})
            if response.status_code in (401, 403):
                raise GroundingError("WORKPLACE_REQUIRES_ACCOUNT")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if not isinstance(body, dict) or type(body.get("available")) is not bool:
            raise GroundingError("INVALID_WORKPLACE_RESULT")
        if not body["available"]:
            return {"available": False, "reason": str(body.get("reason") or "NOT_RESOLVED"), "points": []}
        points = []
        for item in body.get("candidates") or []:
            if not isinstance(item, dict) or not _is_number(item.get("latitude")) or not _is_number(item.get("longitude")):
                raise GroundingError("INVALID_WORKPLACE_RESULT")
            points.append({"latitude": float(item["latitude"]), "longitude": float(item["longitude"]),
                           "label": str(item.get("label") or "").strip()[:300],
                           "approximate": bool(item.get("approximate"))})
            if len(points) >= 3:
                break
        return {"available": bool(points), "reason": "OK" if points else "NOT_RESOLVED", "points": points}

    def commute_matrix(self, property_ids, latitude, longitude, label="", mode="drive"):
        """Duration from several listings to one confirmed destination in a single call.

        Returns one entry per requested id, in the same order. A null duration means the
        vendor had no route; it is never treated as zero.
        """
        if not isinstance(property_ids, list) or not property_ids or len(property_ids) > 6:
            raise GroundingError("INVALID_COMMUTE_MATRIX")
        for property_id in property_ids:
            if not isinstance(property_id, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", property_id):
                raise GroundingError("INVALID_PROPERTY_ID")
        if not _is_number(latitude) or not _is_number(longitude):
            raise GroundingError("INVALID_COMMUTE_DESTINATION")
        if mode not in ("walk", "drive"):
            raise GroundingError("INVALID_COMMUTE_MODE")
        payload = {"propertyIds": property_ids, "latitude": float(latitude), "longitude": float(longitude),
                   "label": str(label or "")[:200], "mode": mode}
        try:
            response = self.client.post("/api/v1/advisor/commute-matrix", json=payload)
            if response.status_code == 429:
                raise OutboundRateLimited()
            if response.status_code in (422, 400):
                raise GroundingError("COMMUTE_UNAVAILABLE")
            if response.status_code == 503:
                raise GroundingError("ROUTE_NOT_CONFIGURED")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        if not isinstance(body, dict) or not isinstance(body.get("cells"), list):
            raise GroundingError("INVALID_COMMUTE_MATRIX")
        cells = []
        for item in body["cells"]:
            if not isinstance(item, dict) or not isinstance(item.get("propertyId"), str):
                raise GroundingError("INVALID_COMMUTE_MATRIX")
            seconds = item.get("durationSeconds")
            meters = item.get("distanceMeters")
            cells.append({
                "propertyId": item["propertyId"],
                "status": str(item.get("status") or "NO_ROUTE"),
                "distanceMeters": float(meters) if _is_number(meters) else None,
                "durationSeconds": float(seconds) if _is_number(seconds) else None,
            })
        return {"provider": body.get("provider") or "", "mode": body.get("mode") or mode, "cells": cells}

    def search_by_address(self, address, limit=5):
        """Public listings whose address column matches the given street address.

        The backend filters the address column itself, so prose that merely mentions
        the street in a title or description is not returned as a match.
        """
        text = str(address or "").strip()
        if len(text) < 3 or len(text) > 200:
            raise GroundingError("INVALID_ADDRESS")
        try:
            response = self.client.get("/api/v1/properties",
                                       params={"address": text, "size": max(1, min(int(limit), 10)),
                                               "sort": "newest"})
            if response.status_code == 429:
                raise OutboundRateLimited()
            if response.status_code in (400, 422):
                raise GroundingError("INVALID_ADDRESS")
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content, parse_float=Decimal)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        items = body.get("items") if isinstance(body, dict) else None
        if not isinstance(items, list):
            raise GroundingError("INVALID_PROPERTY_SEARCH")
        results = []
        for item in items:
            if not isinstance(item, dict) or item.get("status") != "PUBLISHED":
                continue
            price = item.get("price")
            if not _is_number(price) or price <= 0:
                continue
            results.append({
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or "").strip(),
                "priceVnd": float(price),
                "areaSqm": float(item["areaSqm"]) if _is_number(item.get("areaSqm")) else None,
                "address": str(item.get("address") or "").strip(),
                "district": str(item.get("district") or "").strip(),
                "ward": str(item.get("ward") or "").strip(),
                "propertyType": str(item.get("propertyType") or ""),
                "transactionType": str(item.get("transactionType") or ""),
                "listingCode": str(item.get("listingCode") or ""),
                "contentVersion": int(item.get("contentVersion") or 1),
            })
        return {"address": text, "total": int(body.get("totalElements") or 0), "items": results}

    def search_nearby(self, latitude, longitude, radius_meters=1000, limit=10, max_price=None):
        """Every public listing inside a bounding box around a point, with coordinates.

        The list endpoint sorts by creation time, not by distance, so one page is not
        enough: the nearest listing can sit on any page. All pages are read (bounded) and
        the caller still computes the real distance before filtering.
        """
        if not _is_number(latitude) or not _is_number(longitude):
            raise GroundingError("INVALID_COORDINATES")
        if not _is_number(radius_meters) or not 50 <= float(radius_meters) <= 50000:
            raise GroundingError("INVALID_RADIUS")
        lat = float(latitude)
        lon = float(longitude)
        # A degree of latitude is ~111 km; longitude shrinks with latitude.
        dlat = float(radius_meters) / 111_000.0
        dlon = float(radius_meters) / (111_000.0 * max(0.2, math.cos(math.radians(lat))))
        bbox = f"{lon - dlon:.6f},{lat - dlat:.6f},{lon + dlon:.6f},{lat + dlat:.6f}"
        page_size = 50
        results = []
        seen = set()
        page = 0
        complete = False
        while page < NEARBY_MAX_PAGES:
            params = {"bbox": bbox, "size": page_size, "page": page, "sort": "newest"}
            if max_price is not None:
                params["maxPrice"] = str(max_price)
            try:
                response = self.client.get("/api/v1/properties", params=params)
                if response.status_code == 429:
                    raise OutboundRateLimited()
                if response.status_code in (400, 422):
                    raise GroundingError("INVALID_BBOX")
                if response.status_code != 200:
                    raise UpstreamError(response.status_code)
                body = json.loads(response.content, parse_float=Decimal)
            except (httpx.HTTPError, ValueError) as e:
                raise UpstreamError() from e
            items = body.get("items") if isinstance(body, dict) else None
            if not isinstance(items, list):
                raise GroundingError("INVALID_PROPERTY_SEARCH")
            for item in items:
                if not isinstance(item, dict) or item.get("status") != "PUBLISHED":
                    continue
                price = item.get("price")
                if not _is_number(price) or price <= 0:
                    continue
                item_lat, item_lon = item.get("latitude"), item.get("longitude")
                if not _is_number(item_lat) or not _is_number(item_lon):
                    continue
                listing_id = str(item.get("id") or "")
                # The API can repeat a row across pages if the data shifts mid-read.
                if not listing_id or listing_id in seen:
                    continue
                seen.add(listing_id)
                results.append({
                    "id": listing_id,
                    "title": str(item.get("title") or "").strip(),
                    "priceVnd": float(price),
                    "areaSqm": float(item["areaSqm"]) if _is_number(item.get("areaSqm")) else None,
                    "address": str(item.get("address") or "").strip(),
                    "district": str(item.get("district") or "").strip(),
                    "ward": str(item.get("ward") or "").strip(),
                    "latitude": float(item_lat),
                    "longitude": float(item_lon),
                    "propertyType": str(item.get("propertyType") or ""),
                    "transactionType": str(item.get("transactionType") or ""),
                    "listingCode": str(item.get("listingCode") or ""),
                    "contentVersion": int(item.get("contentVersion") or 1),
                })
            total_pages = body.get("totalPages")
            page += 1
            if not items or (isinstance(total_pages, int) and page >= total_pages):
                complete = True
                break
        return {"bbox": bbox, "radiusMeters": float(radius_meters),
                "items": results, "complete": complete, "pagesRead": page}

    def property_image(self, property_id):
        """Cover image from the existing public property detail; no generated or external image."""
        if not isinstance(property_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", property_id):
            raise GroundingError("INVALID_PROPERTY_ID")
        try:
            response = self.client.get("/api/v1/properties/" + property_id)
            if response.status_code != 200:
                raise UpstreamError(response.status_code)
            body = json.loads(response.content)
        except (httpx.HTTPError, ValueError) as e:
            raise UpstreamError() from e
        images = body.get("images") if isinstance(body, dict) else None
        if not isinstance(images, list):
            return None
        for image in images:
            url = image.get("url") if isinstance(image, dict) else None
            if (isinstance(url, str) and url.startswith("/api/v1/properties/")
                    and ".." not in url and "//" not in url and len(url) <= 500):
                return url
        return None

    def amenity_profile(self, area_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", area_id):
            raise GroundingError("INVALID_AREA_ID")
        profile = self._call("GET", "/api/v1/amenities/" + area_id)
        if "sampleListingCount" in json.dumps(profile, default=str):
            raise GroundingError("RESTRICTED_AMENITY_METADATA")
        return profile


def _public_text(value, max_length=1000):
    text = re.sub(r"<[^>]*>", " ", str(value or ""))
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted-email]", text)
    text = re.sub(r"(?<!\d)(?:\+84|0)(?:[\s.-]?\d){8,10}(?!\d)", "[redacted-phone]", text)
    text = re.sub(r"\b(?:UNVERIFIED|INTERNAL_RESEARCH|INTERNAL_DEMO|TINIX_AI|HYBRID_ELIGIBLE_RESEARCH|sampleListingCount|raw_payload)\b",
                  "[redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


class PublishedPropertyRepository:
    """Read-only public projection; private columns never leave SQL."""
    def __init__(self, settings):
        self.settings = settings

    def _public_row(self, row, images, legal):
        project = None
        if row.get("project_name"):
            project = {
                "name": _public_text(row["project_name"], 255),
                "developer": _public_text(row.get("project_developer"), 255),
                "address": _public_text(row.get("project_address"), 500),
                "handoverYear": row.get("project_handover_year"),
                "scale": _public_text(row.get("project_scale"), 500),
                "amenities": [_public_text(item, 80) for item in
                              (json.loads(row["project_amenities"]) if row.get("project_amenities") else [])],
            }
        return {
            "id": row["id"],
            "listing_code": row["listing_code"],
            "title": _public_text(row["title"], 255),
            "description": _public_text(row.get("description"), 1000),
            "price": row["price"],
            "area_sqm": row["area_sqm"],
            "property_type": row["property_type"],
            "transaction_type": row["transaction_type"],
            "district": row.get("district"),
            "ward": row.get("ward"),
            "address": _public_text(row.get("address"), 500),
            "city": row.get("city"),
            "bedrooms": row.get("bedrooms"),
            "bathrooms": row.get("bathrooms"),
            "floor": row.get("floor"),
            "direction": row.get("direction"),
            "declared_amenities": json.loads(row["declared_amenities"]) if row.get("declared_amenities") else [],
            "project": project,
            "images": images,
            "imageUrl": images[0]["url"] if images else None,
            "legal": legal or {"verified": 0, "pending": 0,
                               "note": "Không công khai tệp pháp lý riêng tư; chỉ số lượng hồ sơ đã duyệt."},
            "coordinate_srid": row.get("coordinate_srid"),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
        }

    def lookup(self, ids):
        if not self.settings.sql_enabled:
            raise RagUnavailable("READ_ONLY_SQL_NOT_CONFIGURED")
        if not ids:
            return []
        if len(ids) > 10 or not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", i) for i in ids):
            raise GroundingError("INVALID_PROPERTY_IDS")
        try:
            import pymysql
            # Only the approved publication projection may be read. The database,
            # host and port are explicit settings; there is no 3306 fallback.
            with pymysql.connect(host=self.settings.sql_host, port=self.settings.sql_port,
                    database=self.settings.sql_database,
                    user=self.settings.db_user, password=self.settings.db_password, charset="utf8mb4",
                    autocommit=False, init_command="SET SESSION TRANSACTION READ ONLY",
                    connect_timeout=3, read_timeout=5, cursorclass=pymysql.cursors.DictCursor) as conn:
                conn.begin()
                with conn.cursor() as cur:
                    cur.execute("SELECT DATABASE() db, @@port port, @@transaction_read_only read_only")
                    identity = cur.fetchone()
                    if identity != {"db": self.settings.sql_database, "port": self.settings.sql_port, "read_only": 1}:
                        raise GroundingError("WRONG_SQL_TARGET")
                    placeholders = ",".join(["%s"] * len(ids))
                    if self.settings.sql_use_views:
                        # The approved public views expose no private columns; the RAG
                        # account needs SELECT on these views only, not on base tables.
                        property_source = "rag_public_properties p"
                        project_join = ",p.project_name,p.project_developer,p.project_address,"
                        project_join += "p.project_handover_year,p.project_scale,p.project_amenities "
                        image_source = "rag_public_property_images"
                        legal_source = "rag_public_legal_status"
                    else:
                        property_source = "properties p LEFT JOIN projects pr ON pr.id=p.project_id AND pr.deleted_at IS NULL"
                        project_join = ",pr.name project_name,pr.developer project_developer,pr.address project_address,"
                        project_join += "pr.handover_year project_handover_year,pr.scale project_scale,pr.amenities project_amenities "
                        image_source = "property_images"
                        legal_source = "property_legal_documents"
                    cur.execute("SELECT /*+ MAX_EXECUTION_TIME(3000) */ p.id,p.listing_code,p.title,p.description,p.price,p.area_sqm,"
                        "p.property_type,p.transaction_type,p.district,p.ward,p.address,p.city,p.bedrooms,p.bathrooms,p.floor,p.direction,"
                        "p.declared_amenities,p.project_id,ST_SRID(p.location) coordinate_srid,"
                        "CASE WHEN ST_SRID(p.location)=4326 THEN ST_Latitude(p.location) END latitude,"
                        "CASE WHEN ST_SRID(p.location)=4326 THEN ST_Longitude(p.location) END longitude"
                        + project_join +
                        " FROM " + property_source + " "
                        "WHERE p.status='PUBLISHED' AND p.deleted_at IS NULL AND (p.expires_at IS NULL OR p.expires_at>UTC_TIMESTAMP(6)) "
                        "AND p.transaction_type='SALE' AND p.currency='VND' AND p.price_unit='TOTAL' AND p.price>0 AND p.area_sqm>0 "
                        f"AND p.id IN ({placeholders}) ORDER BY p.id LIMIT 10", tuple(ids))
                    rows = cur.fetchall()
                    image_map, legal_map = {}, {}
                    if rows:
                        cur.execute("SELECT property_id,id,sort_order,is_cover,mime_type,storage_provider,cloudinary_secure_url "
                            "FROM " + image_source + " WHERE property_id IN (" + placeholders + ") AND deleted_at IS NULL "
                            "ORDER BY property_id,sort_order,id", tuple(ids))
                        for image in cur.fetchall():
                            url = None
                            if image.get("storage_provider") == "CLOUDINARY" and str(image.get("cloudinary_secure_url") or "").startswith("https://res.cloudinary.com/"):
                                url = image["cloudinary_secure_url"]
                            else:
                                url = f"/api/v1/properties/{image['property_id']}/images/{image['id']}/content"
                            image_map.setdefault(image["property_id"], []).append({
                                "id": image["id"], "url": url, "sortOrder": image.get("sort_order"),
                                "cover": bool(image.get("is_cover")), "mimeType": image.get("mime_type"),
                            })
                        cur.execute("SELECT property_id,SUM(status='VERIFIED') verified,SUM(status='PENDING') pending "
                            "FROM " + legal_source + " WHERE property_id IN (" + placeholders + ") AND deleted_at IS NULL "
                            "GROUP BY property_id", tuple(ids))
                        for item in cur.fetchall():
                            legal_map[item["property_id"]] = {
                                "verified": int(item.get("verified") or 0),
                                "pending": int(item.get("pending") or 0),
                                "note": "Không công khai tệp pháp lý riêng tư; chỉ số lượng hồ sơ đã duyệt.",
                            }
                conn.rollback()
            return [self._public_row(row, image_map.get(row["id"], []), legal_map.get(row["id"])) for row in rows]
        except GroundingError:
            raise
        except Exception as e:
            raise RagUnavailable("READ_ONLY_SQL_UNAVAILABLE") from e

    def list_public_images(self, limit=250):
        """Return only public listing images for the duplicate-image index."""
        if not self.settings.sql_enabled:
            raise RagUnavailable("READ_ONLY_SQL_NOT_CONFIGURED")
        if not isinstance(limit, int) or not 1 <= limit <= 500:
            raise GroundingError("INVALID_IMAGE_LIMIT")
        try:
            import pymysql
            with pymysql.connect(host=self.settings.sql_host, port=self.settings.sql_port,
                    database=self.settings.sql_database, user=self.settings.db_user,
                    password=self.settings.db_password, charset="utf8mb4", autocommit=False,
                    init_command="SET SESSION TRANSACTION READ ONLY", connect_timeout=3,
                    read_timeout=8, cursorclass=pymysql.cursors.DictCursor) as conn:
                conn.begin()
                with conn.cursor() as cur:
                    cur.execute("SELECT DATABASE() db, @@port port, @@transaction_read_only read_only")
                    identity = cur.fetchone()
                    if identity != {"db": self.settings.sql_database, "port": self.settings.sql_port, "read_only": 1}:
                        raise GroundingError("WRONG_SQL_TARGET")
                    if self.settings.sql_use_views:
                        query = ("SELECT i.property_id,i.id image_id,i.sort_order,i.is_cover,i.mime_type,"
                                 "i.storage_provider,i.cloudinary_secure_url,p.listing_code,p.title,p.district,p.ward "
                                 "FROM rag_public_property_images i JOIN rag_public_properties p ON p.id=i.property_id "
                                 "WHERE i.deleted_at IS NULL ORDER BY i.property_id,i.sort_order,i.id LIMIT %s")
                    else:
                        query = ("SELECT i.property_id,i.id image_id,i.sort_order,i.is_cover,i.mime_type,"
                                 "i.storage_provider,i.cloudinary_secure_url,p.listing_code,p.title,p.district,p.ward "
                                 "FROM property_images i JOIN properties p ON p.id=i.property_id "
                                 "WHERE i.deleted_at IS NULL AND p.status='PUBLISHED' AND p.deleted_at IS NULL "
                                 "AND (p.expires_at IS NULL OR p.expires_at>UTC_TIMESTAMP(6)) "
                                 "AND p.transaction_type='SALE' AND p.currency='VND' AND p.price_unit='TOTAL' "
                                 "AND p.price>0 AND p.area_sqm>0 ORDER BY i.property_id,i.sort_order,i.id LIMIT %s")
                    cur.execute(query, (limit,))
                    rows = cur.fetchall()
                conn.rollback()
            result = []
            for row in rows:
                if row.get("storage_provider") == "CLOUDINARY" and str(row.get("cloudinary_secure_url") or "").startswith("https://res.cloudinary.com/"):
                    url = row["cloudinary_secure_url"]
                    public_url = url
                else:
                    public_url = f"/api/v1/properties/{row['property_id']}/images/{row['image_id']}/content"
                    base_url = self.settings.image_backend_url or self.settings.backend_url
                    url = f"{base_url}{public_url}"
                result.append({
                    "propertyId": row["property_id"], "imageId": row["image_id"], "url": url,
                    "publicUrl": public_url, "listingCode": row.get("listing_code"),
                    "title": _public_text(row.get("title"), 255),
                    "district": row.get("district"), "ward": row.get("ward"), "cover": bool(row.get("is_cover")),
                    "mimeType": row.get("mime_type"),
                })
            return result
        except GroundingError:
            raise
        except Exception as e:
            raise RagUnavailable("READ_ONLY_SQL_UNAVAILABLE") from e
