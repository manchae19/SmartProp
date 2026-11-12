"""Fixed backend routes and parameterized SQL projections. There is no text-to-SQL API."""
import json
import re
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


class PublishedPropertyRepository:
    """Only the publication projection already used by Hybrid V1.1; no crawler table access."""
    def __init__(self, settings):
        self.settings = settings

    def lookup(self, ids):
        if not self.settings.sql_enabled:
            raise RagUnavailable("READ_ONLY_SQL_NOT_CONFIGURED")
        if not ids:
            return []
        if len(ids) > 10 or not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", i) for i in ids):
            raise GroundingError("INVALID_PROPERTY_IDS")
        try:
            import pymysql
            with pymysql.connect(host="127.0.0.1", port=3306, database="smartprop",
                    user=self.settings.db_user, password=self.settings.db_password, charset="utf8mb4",
                    autocommit=False, init_command="SET SESSION TRANSACTION READ ONLY",
                    connect_timeout=3, read_timeout=5, cursorclass=pymysql.cursors.DictCursor) as conn:
                conn.begin()
                with conn.cursor() as cur:
                    cur.execute("SELECT DATABASE() db, @@port port, @@transaction_read_only read_only")
                    identity = cur.fetchone()
                    if identity != {"db": "smartprop", "port": 3306, "read_only": 1}:
                        raise GroundingError("WRONG_SQL_TARGET")
                    placeholders = ",".join(["%s"] * len(ids))
                    cur.execute("SELECT /*+ MAX_EXECUTION_TIME(3000) */ id,price,area_sqm,district,ward,ST_SRID(location) coordinate_srid,"
                        "CASE WHEN ST_SRID(location)=4326 THEN ST_Latitude(location) END latitude,"
                        "CASE WHEN ST_SRID(location)=4326 THEN ST_Longitude(location) END longitude FROM properties "
                        "WHERE status='PUBLISHED' AND deleted_at IS NULL AND (expires_at IS NULL OR expires_at>UTC_TIMESTAMP(6)) "
                        "AND transaction_type='SALE' AND currency='VND' AND price_unit='TOTAL' AND price>0 AND area_sqm>0 "
                        f"AND id IN ({placeholders}) ORDER BY id LIMIT 10", tuple(ids))
                    rows = cur.fetchall()
                conn.rollback()
            return list(rows)
        except GroundingError:
            raise
        except Exception as e:
            raise RagUnavailable("READ_ONLY_SQL_UNAVAILABLE") from e
