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
