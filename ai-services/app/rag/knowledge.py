"""Versioned PUBLIC corpus built only from the existing public Amenity Evidence API."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from .config import GroundingError, RagUnavailable


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def document(source_id, text, url, version, kind, metadata, scope="PUBLIC"):
    body = {"sourceId": source_id, "text": text, "url": url, "catalogVersion": version,
            "scope": scope, "kind": kind, "metadata": metadata}
    body["contentHash"] = digest(body)
    body["version"] = version + ":" + body["contentHash"][:16]
    return body


def build_corpus(backend, path):
    summary = backend.amenity_summary()
    areas = backend.amenity_areas()
    if len(areas) > 200 or len(areas) != summary["totalAreasAnalyzed"]:
        raise GroundingError("INVALID_CATALOG_COVERAGE")
    docs = []
    version = summary["catalogVersion"]
    for area in areas:
        profile = backend.amenity_profile(area["areaId"])
        meta = {k: profile.get(k) for k in ["areaId", "areaName", "areaLevel", "parentDistrict", "livingScore", "categoryScores", "confidence", "poiCounts", "sources"]}
        meta["district"] = profile["parentDistrict"]
        url = backend.settings.backend_url + "/api/v1/amenities/" + profile["areaId"]
        text = (f"Khu vực {profile['areaName']} ({profile['areaLevel']}); điểm tiện ích {profile['livingScore']}/100. "
                f"Số POI trong hồ sơ khu vực: {profile['poiCounts']['total']}. Đây là bằng chứng cấp khu vực, không phải khoảng cách từ từng bất động sản.")
        docs.append(document("amenity:" + profile["areaId"], text, url, version, "AREA_AMENITY", meta))
        for poi in profile.get("poiEvidence", []):
            key = digest({"areaId": profile["areaId"], **poi})[:16]
            metadata = {"areaId": profile["areaId"], "district": profile["parentDistrict"], **poi}
            docs.append(document("poi-evidence:" + key,
                        f"Bằng chứng tiện ích {poi['name']}, loại {poi['category']}, trong hồ sơ {profile['areaName']}; nguồn gán {poi['attributionBasis']}. Không có khoảng cách tới căn nhà.",
                        url, version, "POI_EVIDENCE", metadata))
    unique = {}
    for d in docs:
        if d["sourceId"] in unique and unique[d["sourceId"]] != d:
            raise GroundingError("CORPUS_SOURCE_ID_COLLISION")
        unique[d["sourceId"]] = d
    corpus = {"format": "SMARTPROP_RAG_PUBLIC_V1", "builtAt": datetime.now(timezone.utc).isoformat(),
              "summary": summary, "duplicateEvidenceCollapsed": len(docs) - len(unique), "documents": list(unique.values())}
    corpus["contentHash"] = digest(corpus)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)
    KnowledgeStore(path).load()
    return corpus


class KnowledgeStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        try:
            if self.path.stat().st_size > 8 * 1024 * 1024:
                raise GroundingError("CORPUS_TOO_LARGE")
            corpus = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise RagUnavailable("PUBLIC_CORPUS_UNAVAILABLE") from e
        fingerprint = corpus.get("contentHash")
        if digest({k: v for k, v in corpus.items() if k != "contentHash"}) != fingerprint or corpus.get("format") != "SMARTPROP_RAG_PUBLIC_V1":
            raise GroundingError("CORPUS_HASH_MISMATCH")
        if (datetime.now(timezone.utc) - datetime.fromisoformat(corpus["builtAt"])).total_seconds() > 86400:
            raise RagUnavailable("PUBLIC_CORPUS_SNAPSHOT_EXPIRED")
        seen = set()
        for d in corpus["documents"]:
            if d["scope"] != "PUBLIC" or d["kind"] not in ("AREA_AMENITY", "POI_EVIDENCE") or d["sourceId"] in seen:
                raise GroundingError("INVALID_CORPUS_PERMISSIONS")
            if d["contentHash"] != digest({k: v for k, v in d.items() if k not in ("contentHash", "version")}):
                raise GroundingError("CORPUS_DOCUMENT_HASH_MISMATCH")
            if "sampleListingCount" in json.dumps(d, ensure_ascii=False):
                raise GroundingError("RESTRICTED_AMENITY_METADATA")
            seen.add(d["sourceId"])
        return corpus
