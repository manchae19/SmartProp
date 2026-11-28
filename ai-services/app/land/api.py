"""Read-only HTTP routes of the Hòa Xuân land demo (detail page and map).

Mounted on the chat service. Every route reads through app.land.engine, the same functions the
chatbot uses, so the detail page, the map and the chat answer cannot disagree about a record.
"""
import gzip
import json
import re
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from .paths import authorize_land_demo_request, land_runtime_mode

CODE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
RECORD_KEYS_DROP = {"geometry", "sourceFile", "reviewFlags"}


def _engine():
    from . import engine
    return engine


def _json(data, request: Request | None = None, cache: str = "no-store"):
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Cache-Control": cache}
    if request is not None and "gzip" in request.headers.get("accept-encoding", "") and len(raw) > 20000:
        raw = gzip.compress(raw, 5)
        headers["Content-Encoding"] = "gzip"
        headers["Vary"] = "Accept-Encoding"
    return Response(raw, media_type="application/json; charset=utf-8", headers=headers)


@lru_cache(maxsize=1)
def _planning_cells_gzip():
    raw = json.dumps(_engine().planning_cells(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return raw, gzip.compress(raw, 6)


def record_view(code):
    """Detail-page projection of one record: identity, cadastral, price, documents (demo), planning,
    environment/flood and sources. Demo values carry their basis; source evidence is kept apart."""
    e = _engine()
    r = e.resolve(code)
    if r is None:
        return None
    demo = r.get("demoPresentation") or {}
    flood = r.get("floodDisplay") or {}
    fe = r.get("floodEvidence") or {}
    kind = ("GULAND_PARCEL" if r.get("importedParcel") else "PROJECT_LOT_UNLOCATED" if r.get("unlocatedProjectLot")
            else "PROJECT_LOT" if r.get("sourceLot") else "PLANNING_CELL")
    prices = []
    if r.get("roadPriceEvidence"):
        p = r["roadPriceEvidence"]
        prices.append({"type": "ROAD_ASKING_ESTIMATE", "label": "Ước tính từ giá rao tuyến đường lân cận (không phải giá thị trường hay giá giao dịch)", "valueVnd": p["estimatedReferenceVnd"],
                       "unitPriceMillionPerSqm": p["unitMillionPerSqm"], "date": None, "sampleCount": p["sampleCount"],
                       "confidence": p["confidence"], "sources": p.get("listingUrls") or [p["sourceUrl"]], "warnings": p.get("warnings", [])})
    if r.get("demoPriceVnd"):
        prices.append({"type": "SIMULATED_DEMO", "label": "Giá giả lập demo (không phải giá thị trường hay giá giao dịch)", "valueVnd": r["demoPriceVnd"],
                       "unitPriceVndPerSqm": r.get("demoUnitPriceVndPerSqm"), "date": None, "sources": []})
    if kind.startswith("PROJECT_LOT") and r.get("referencePriceVnd"):
        lot = r.get("sourceLotEvidence") or e.imported.EXTRAS.get(code) or {}
        prices.append({"type": "HISTORICAL_ASKING", "label": "Giá chào lịch sử theo tin nguồn (không phải giá thị trường hiện tại hay giá giao dịch)", "valueVnd": r["referencePriceVnd"],
                       "date": lot.get("sourceDate"), "sources": [lot.get("sourceUrl")] if lot.get("sourceUrl") else []})
    if kind == "GULAND_PARCEL" and r.get("priceVnd"):
        prices.append({"type": "SOURCE_ASKING", "label": "Giá chào theo tin nguồn (không phải giá thị trường hay giá giao dịch)", "valueVnd": r["priceVnd"], "date": None, "sources": [r.get("sourceUrl")]})
    sources = []
    for url in [r.get("sourceUrl"), *(x.get("sourceUrl") for x in r.get("planningEvidence", []) if isinstance(x, dict))]:
        if url and url not in sources:
            sources.append(url)
    return {
        "landId": e.land_id(code), "sourceCode": code, "kind": kind, "dataVersion": "HX-LAND-DEMO-20261126", "demoOnly": True,
        "governance": {"containsSyntheticData": True, "publicApproved": False, "officialCadastralParcel": False,
                       "marketOrTransactionValue": False, "excludedFrom": ["VALUATION", "COMPARABLE", "MARKET"]},
        "displayName": r.get("displayName") or code, "location": (r.get("addressEvidence") or {}).get("location") or "Hòa Xuân, Đà Nẵng",
        "located": kind != "PROJECT_LOT_UNLOCATED",
        "pointOnSurface": r.get("pointOnSurface") if kind != "PROJECT_LOT_UNLOCATED" else None,
        "cadastral": {"areaSqm": r.get("computedAreaSqm"), "areaBasis": "SOURCE_PARCEL" if kind == "GULAND_PARCEL" else "LISTING" if kind.startswith("PROJECT") else "COMPUTED_FROM_PLANNING_CELL",
                      "sheet": r.get("sheet"), "parcel": r.get("parcel"), "block": (r.get("sourceLotEvidence") or {}).get("block") or r.get("block"),
                      "lotNumbers": (r.get("sourceLotEvidence") or {}).get("lotNumbers") or r.get("lotNumbers"),
                      "planningCellId": r.get("planningCellId") or (code if kind == "PLANNING_CELL" else None),
                      "planningCandidates": r.get("planningCandidates", []),
                      "projectName": demo.get("projectName"), "widthMeters": None, "lengthMeters": None, "direction": None,
                      "geometryBasis": "SOURCE_PLANNING_CELL_NOT_CADASTRAL" if kind == "PLANNING_CELL" else "SOURCE_REPORTED_UNVERIFIED" if kind != "PROJECT_LOT_UNLOCATED" else "UNLOCATED"},
        "price": {"display": r.get("priceDescription"), "evidence": prices},
        "documents": {"demo": bool(demo), "landType": demo.get("landType") or r.get("landLabel") or r.get("planningLabel"),
                      "ownershipDocument": demo.get("ownershipDocument") or "Chưa xác minh", "recovery": demo.get("recovery") or "Chưa xác minh",
                      "dispute": demo.get("dispute") or "Chưa xác minh", "mortgage": demo.get("mortgage") or "Chưa xác minh",
                      "compensation": demo.get("compensation") or "Chưa xác minh",
                      "basis": "USER_APPROVED_DEMO_SCENARIO" if demo else "SOURCE", "verifiedForThisParcel": False,
                      "sourceLegalStatus": r.get("legalStatus", "UNKNOWN"), "owner": None,
                      "transferRestrictions": None, "financialObligations": None},
        "planning": {"sourceLabel": r.get("planningLabel") or r.get("landLabel"), "code": r.get("planningCode"), "text": r.get("planningText"),
                     "plans": [{"id": x.get("id"), "name": x.get("name")} for x in r.get("planningEvidence", []) if isinstance(x, dict)][:12],
                     "codeSpatialConflict": r.get("codeSpatialConflict"), "roadExpansion": None, "affectedAreaSqm": None,
                     "buildingDensity": None, "floors": None, "heightMeters": None, "setbackMeters": None, "buildingLine": None},
        "flood": {"display": flood.get("display"), "relation": flood.get("relation") or flood.get("basis"), "detail": flood.get("detail") or fe.get("message"),
                  "isDemoAssumption": flood.get("isDemoAssumption", False), "verifiedForThisParcel": False,
                  "records": [{k: i.get(k) for k in ("id", "relation", "location_text", "street", "referenceRoad", "distanceMeters", "source_title", "publication_date", "source_url", "source_page")}
                              for i in fe.get("items", [])][:8]},
        "environment": {"elevationMeters": None, "slopeDegrees": None, "drainage": None, "landslideRisk": None},
        "sources": sources,
    }


def create_land_router(expected_demo_key: str | None = None):
    def require_demo_access(request: Request):
        key = expected_demo_key if expected_demo_key is not None else None
        if land_runtime_mode(demo_key=key) != "SYNTHETIC_DEMO":
            raise HTTPException(404, "Không tìm thấy hồ sơ đất.")
        client_host = request.client.host if request.client else None
        if not authorize_land_demo_request(request.headers, client_host, key):
            raise HTTPException(403, "Hồ sơ đất demo chỉ dành cho môi trường trình diễn nội bộ được cấp phép trên loopback.")

    router = APIRouter(prefix="/land", dependencies=[Depends(require_demo_access)])

    def code_or_404(value):
        code = _engine().code_for(value) if isinstance(value, str) and CODE.match(value) else None
        if code is None:
            raise HTTPException(404, "Không tìm thấy hồ sơ đất.")
        return code

    @router.get("/health")
    def health():
        return _engine().health()

    @router.get("/records/{record_id}")
    def record(record_id: str, request: Request):
        return _json(record_view(code_or_404(record_id)), request)

    @router.get("/records/{record_id}/overview")
    def overview(record_id: str, request: Request):
        from .overview import service
        return _json(service.get(record_view(code_or_404(record_id))), request)

    @router.get("/neighbors")
    def neighbors(request: Request, id: str = Query(..., max_length=80)):
        data = _engine().neighbors(code_or_404(id))
        if data is None:
            raise HTTPException(404, "Hồ sơ chưa có vị trí trên bản đồ.")
        for f in data["features"]:
            p = f["properties"]
            f["properties"] = {k: v for k, v in p.items() if k not in RECORD_KEYS_DROP and not isinstance(v, (dict, list)) or k in ("color", "floodDisplay")}
            f["properties"]["landId"] = _engine().land_id(p["id"]) if _engine().resolve(p["id"]) else None
        return _json(data, request)

    @router.get("/planning-cells")
    def planning_cells(request: Request):
        raw, packed = _planning_cells_gzip()
        if "gzip" in request.headers.get("accept-encoding", ""):
            return Response(packed, media_type="application/json", headers={"Content-Encoding": "gzip", "Cache-Control": "public, max-age=3600", "Vary": "Accept-Encoding"})
        return Response(raw, media_type="application/json", headers={"Cache-Control": "public, max-age=3600"})

    @router.get("/flood-map")
    def flood_map(request: Request, ids: str | None = Query(None, max_length=12000)):
        chosen = None if ids is None else [x for x in ids.split(",") if re.fullmatch(r"[A-Za-z0-9-]{1,40}", x)]
        if chosen is not None and len(chosen) > 200:
            raise HTTPException(400, "Tối đa 200 hồ sơ mỗi lần.")
        return _json(_engine().flood_map(chosen), request)

    @router.get("/flood-catalog")
    def flood_catalog(request: Request):
        return _json(_engine().flood_catalog(), request)

    @router.get("/project-boundaries")
    def project_boundaries(request: Request):
        return _json(_engine().project_boundaries(), request)

    return router
