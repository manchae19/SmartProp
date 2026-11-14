"""Standalone, read-only Location Resolution & Address Confidence Audit for TiniX representatives (Step 19.4.1A).

Strictly adheres to SmartProp Step 19.4.1A constraints:
- Processes ONLY the 55,816 eligible TiniX SALE representatives in MySQL (`smartprop.tinix_dataset_records`).
- 100% READ-ONLY on MySQL (`SET SESSION TRANSACTION READ ONLY` + SQL statement guard).
- Preserves all original TiniX fields, `internal_id`, `quality_status`, and `quality_rule_version`.
- Never fabricates GPS coordinates (`resolvedLatitude = None`, `resolvedLongitude = None` when unverified).
- Never makes bulk external geocoding API calls.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
import time
import tracemalloc
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymysql

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
ADMIN_MAPPING_PATH = SCRIPT_DIR / "danang_admin_mapping_v1.json"
STREET_PROJECT_CATALOG_PATH = SCRIPT_DIR / "danang_street_project_catalog_v1.json"
DEFAULT_OUTPUT_DIR = ROOT / ".scratch/tinix-integration/step19-4-1a"
EXPECTED_REVISION = "ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f"
EXPECTED_REPRESENTATIVE_COUNT = 55816

PRECISION_ORDER = ("EXACT", "HIGH", "STREET", "WARD", "DISTRICT", "UNKNOWN")

# Confidence weights (documented explicitly per Section 8; never used to upgrade LocationPrecision)
CONFIDENCE_WEIGHTS = {
    "STRUCTURED_PROVINCE_VALID": 0.10,
    "STRUCTURED_DISTRICT_VALID": 0.20,
    "STRUCTURED_WARD_VALID": 0.20,
    "STRUCTURED_STREET_VALID": 0.15,
    "STREET_ATTESTED_IN_DISTRICT": 0.10,
    "TITLE_CATEGORY_A_CORROBORATED": 0.10,
    "DESC_CATEGORY_A_CORROBORATED": 0.08,
    "EXPLICIT_HOUSE_NUMBER": 0.07,
    "ALLEY_OR_PLOT_DETAIL": 0.03,
    "VERIFIED_PROJECT_MATCH": 0.05,
    "TEXT_RECOVERED_WARD": 0.12,
    "TEXT_RECOVERED_STREET": 0.12,
    "PENALTY_NEEDS_MAPPING": -0.05,
    "PENALTY_LOCATION_FROM_MARKETING": -0.15,
    "PENALTY_SOURCE_INCONSISTENT": -0.25,
    "PENALTY_AMBIGUOUS_LOCATION": -0.15,
    "PENALTY_ADDRESS_CONFLICT": -0.35,
    "MAX_WITHOUT_VERIFIED_GPS": 0.95,
}

SYLLABLE_HOA_RE = re.compile(r"\b([HhTtXxLl])oà\b")

ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\ufeff\u00ad]")
MULTISPACE_RE = re.compile(r"[ \t\r\f\v]+")
PHONE_REDACT_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]*\d){8,10}(?!\d)")
EMAIL_REDACT_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Clause splitting keeps dash-separated address chains ("Khuê Trung - Cẩm Lệ - Đà Nẵng") intact
CLAUSE_SPLIT_RE = re.compile(r"(?:\r?\n|[.;|•●▪♦✅👉📍🏠🏡💥🌟🔥📌]+)")
SUBCLAUSE_SPLIT_RE = re.compile(r"\s*,\s*")

BROKER_CONTACT_RE = re.compile(
    r"(?:\b(?:"
    r"liên\s+hệ\s*(?:văn\s+phòng|vp|công\s+ty|cty|sàn|ngay|em|anh|chị|sđt|call|:)|"
    r"lh\s*(?:văn\s+phòng|vp|ngay|sđt|zalo|em|:|\d|\[)|"
    r"văn\s+phòng\s*(?:giao\s+dịch|công\s+ty|bđs|nhà\s+đất|tại|ở|:)|"
    r"địa\s+chỉ\s+(?:văn\s+phòng|công\s+ty|liên\s+hệ)|"
    r"trụ\s+sở\s*(?:chính|công\s+ty|tại|:)|"
    r"chi\s+nhánh\s*(?:công\s+ty|tại|:)|"
    r"pkd\s*\d*\s*:|vp\s*\d+\s*:|"
    r"công\s+ty\s+(?:cp\s+|cổ\s+phần\s+|tnhh\s+)?(?:bđs|bất\s+động\s+sản)|"
    r"đại\s+lý\s+phân\s+phối|"
    r"sàn\s+giao\s+dịch\s+bđs|"
    r"chuyên\s+(?:nhà\s+đất|mua\s+bán\s+ký\s+gửi)|"
    r"làm\s+việc\s+tại\s+văn\s+phòng"
    r")\b|\[phone_number\])",
    re.IGNORECASE,
)

# Trailing footer block trigger (everything after this in the tail of description is broker signature Category C)
BROKER_FOOTER_START_RE = re.compile(
    r"(?:---+|\bchi\s+tiết\s+liên\s+hệ\b|\bliên\s+hệ\s*(?:ngay|:|\s+sđt|\s+xem)|\blh\s*:|"
    r"\bcông\s+ty\s+(?:cp\s+|tnhh\s+)?(?:bđs|bất\s+động\s+sản)\b|\bđại\s+lý\s+phân\s+phối\b|"
    r"\btrụ\s+sở\s*:|\bpkd\s*\d*\s*:)",
    re.IGNORECASE,
)

# Nearby / marketing / directional prepositions immediately preceding a location mention
NEARBY_PREFIX_RE = re.compile(
    r"(?:"
    r"\bgần|\bsát|\bngay\s+sát|\bkề|\bliền\s+kề|\bcạnh|\bbên\s+cạnh|"
    r"\bđối\s+diện|\bsau\s+lưng|\bphía\s+sau|\bphía\s+trước|"
    r"\bcách|\bchỉ\s+cách|\bkhoảng\s+cách|"
    r"\bđi\s+bộ\s+ra|\bra\s+biển|\bra\s+đường|\bra\s+chợ|\bra\s+cầu|\bra\s+sông|\bra\s+sân\s+bay|"
    r"\bthông\s+ra|\bthông\s+thẳng(?:\s+ra)?|\bnối\s+thông|\bnối\s+ra|\băn\s+thông|"
    r"\bsong\s+song(?:\s+với|\s+đường)?|"
    r"(?<!\blake\s)(?<!\bocean\s)(?<!\briver\s)(?<!\bsea\s)(?<!\bpark\s)(?<!\bsky\s)(?<!\bgolf\s)(?<!\bcity\s)\bview|"
    r"\bnhìn\s+ra|\bhướng\s+nhìn|\bhướng\s+ra|"
    r"\bgiáp(?:\s+ranh)?|\btiếp\s+giáp|"
    r"\bkết\s+nối|\bdi\s+chuyển(?:\s+đến|\s+ra|\s+về|\s+qua)?|\bthuận\s+tiện\s+đi|"
    r"\bbán\s+kính(?:\s+\d+\s*(?:m|km))?"
    r")\s*(?:với\s+|đến\s+|tới\s+|nhanh\s+chóng\s*)?(?:biển\s+|bãi\s+tắm\s+|cầu\s+|chợ\s+|sông\s+|công\s+viên\s+|trường\s+|bệnh\s+viện\s+|sân\s+bay\s+|đường\s+|phố\s+|trục\s+|kđt\s+|khu\s+đô\s+thị\s+|dự\s+án\s+|phường\s+|quận\s+)?$",
    re.IGNORECASE,
)

# Clause-wide connectivity/proximity list cue (e.g. "dễ dàng kết nối Liên Chiểu, Hải Châu, sân bay")
CLAUSE_CONNECTIVITY_LIST_RE = re.compile(
    r"\b(?:kết\s+nối|di\s+chuyển\s+(?:qua|đến|về|đi)|thuận\s+tiện\s+đi(?:\s+lại)?|giáp\s+ranh)\b",
    re.IGNORECASE,
)

# Anchored right after mention: e.g. "cầu Rồng 1 km", "biển Mỹ Khê 200m", "chợ Hàn 3 phút"
DISTANCE_SUFFIX_RE = re.compile(
    r"^\s*(?:chỉ\s+|khoảng\s+|tầm\s+|chưa\s+tới\s+|chưa\s+đầy\s+|hơn\s+)?\d+(?:[.,]\d+)?\s*(?:m|km|mét|phút|p|bước(?:\s+chân)?)\b",
    re.IGNORECASE,
)

PROPERTY_CUE_PREFIX_RE = re.compile(
    r"(?:"
    r"\bmặt\s+tiền|\bmt|\bkiệt|\bkiet|\bhẻm|\bhem|\bngõ|\bngo|"
    r"\bđịa\s+chỉ\s*:?|\btọa\s+lạc(?:\s+tại|\s+trên)?|\bnằm\s+(?:tại|trên)|"
    r"\btại|\bthuộc|"
    r"\bbán\s+(?:nhà|đất|căn\s+hộ|biệt\s+thự|villa|khách\s+sạn|tòa\s+nhà|lô\s+đất|nhà\s+phố|shophouse)"
    r")[^,;.\n]{0,30}$",
    re.IGNORECASE,
)

STREET_EXPLICIT_CUE_RE = re.compile(
    r"(?:"
    r"\bđường|\bphố|\bmặt\s+tiền(?:\s+đường)?|\bmt(?:\s+đường)?|"
    r"\bkiệt\s+\d+[A-Za-z0-9/]*\s*(?:đường\s+)?|\bhẻm\s+\d+[A-Za-z0-9/]*\s*(?:đường\s+)?|"
    r"\bk\d+[A-Za-z0-9/]*\s*(?:đường\s+)?|\bsố\s+\d+[A-Za-z0-9/]*\s+(?:đường\s+)?|"
    r"\btại\s+\d+[A-Za-z0-9/]*\s+(?:đường\s+)?|"
    r"\bbán\s+(?:nhà|đất|lô\s+đất)\s+(?:đẹp\s+|mặt\s+tiền\s+)?\d+[A-Za-z0-9/]*\s+(?:đường\s+)?|"
    r"\btđc|\btdc|\bkhu\s+tái\s+định\s+cư|"
    r"\bquốc\s+lộ|\bql|\btỉnh\s+lộ|\bđt|\bđh|\btrục(?:\s+đường)?"
    r")\s*$",
    re.IGNORECASE,
)

CORNER_INTERSECTION_RE = re.compile(
    r"\b(?:"
    r"2\s*mặt\s+tiền|hai\s+mặt\s+tiền|3\s*mặt\s+tiền|ba\s+mặt\s+tiền|"
    r"2\s*mt|3\s*mt|lô\s+góc|nhà\s+góc|căn\s+góc|góc\s+2|"
    r"ngã\s+tư|ngã\s+ba|ngã\s+4|ngã\s+3|giao\s+(?:với|đường|nhau)|nút\s+giao|"
    r"mặt\s+tiền\s+[^,.\n]{2,35}\s+và\s+[^,.\n]{2,35}|"
    r"mặt\s+sau|hai\s+mặt\s+kiệt|2\s+mặt\s+kiệt"
    r")\b",
    re.IGNORECASE,
)

PLOT_CODE_RE = re.compile(
    r"\b(?:lô|block|phân\s+khu)\s+([A-Z]{1,3}\d{1,3}[A-Z]?(?:\s*[-.]\s*\d{1,4}[A-Z]?)?|\d{1,3}\s*-\s*[A-Z]\d{1,3})\b",
    re.IGNORECASE,
)

OUT_OF_DANANG_MAINLAND_RE = re.compile(
    r"\b(?:"
    r"biển\s+thuận\s+an|bãi\s+tắm\s+thuận\s+an|phường\s+thuận\s+an|"
    r"thừa\s+thiên\s+huế|tp\.?\s*huế|thành\s+phố\s+huế|vịnh\s+lăng\s+cô|thị\s+trấn\s+lăng\s+cô"
    r")\b",
    re.IGNORECASE,
)

# Require explicit administrative prefix so Đà Nẵng streets ("Đường Núi Thành", "Cẩm Nam 1") never collide with Quảng Nam towns!
QUANG_NAM_EXPANDED_CATEGORY_A_RE = re.compile(
    r"\b(?:"
    r"(?:thị\s+xã|tx\.?)\s+điện\s+bàn|"
    r"(?:phường|xã)\s+(?:điện\s+ngọc|điện\s+dương|điện\s+nam(?:\s+bắc|\s+trung|\s+đông)?|điện\s+thắng|cẩm\s+châu|cẩm\s+an|cẩm\s+hà|cẩm\s+nam)|"
    r"(?:thành\s+phố|tp\.?)\s+(?:hội\s+an|tam\s+kỳ)|"
    r"(?:huyện|thị\s+trấn)\s+(?:núi\s+thành|đại\s+lộc|duy\s+xuyên|thăng\s+bình)"
    r")\b(?!\s*\d)",
    re.IGNORECASE,
)

DATE_STREETS = {"2/9", "29/3", "30/4", "3/2"}

INVALID_HOUSE_FOLLOWERS = {
    "tầng", "tang", "mê", "me", "lầu", "lau", "phòng", "phong", "pn", "wc",
    "m", "m2", "m²", "mét", "met", "km", "tỷ", "ty", "triệu", "trieu",
    "mặt", "mat", "mt", "kiệt", "kiet", "lô", "lo", "thửa", "thua", "phút", "phut",
}


def normalize_nfc(value: str | None) -> str:
    if not value:
        return ""
    s = unicodedata.normalize("NFC", value)
    s = ZERO_WIDTH_RE.sub("", s)
    s = SYLLABLE_HOA_RE.sub(lambda m: m.group(1) + "òa", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s


def fold_ascii(value: str | None) -> str:
    if not value:
        return ""
    nfd = unicodedata.normalize("NFD", value)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"\s+", " ", stripped).strip()


def redact_pii(text: str | None) -> str:
    if not text:
        return ""
    s = PHONE_REDACT_RE.sub("[REDACTED_PHONE]", text)
    s = EMAIL_REDACT_RE.sub("[REDACTED_EMAIL]", s)
    return s


def assert_readonly_sql(sql: str) -> None:
    cleaned = sql.strip().upper()
    if cleaned == "SET SESSION TRANSACTION READ ONLY":
        return
    if not cleaned.startswith("SELECT"):
        raise PermissionError(f"Write/DDL SQL is strictly forbidden in Step 19.4.1A: {sql[:80]}")
    forbidden = ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "DROP ", "TRUNCATE ", "REPLACE ", "CREATE ")
    if any(tok in cleaned for tok in forbidden):
        raise PermissionError(f"Mutating SQL keyword rejected in Step 19.4.1A: {sql[:80]}")


@dataclass(frozen=True)
class TextMention:
    kind: str  # DISTRICT | WARD | POST2025_UNIT | STREET | PROJECT
    canonical: str
    category: str  # A | B | C | D
    source_field: str  # TITLE | DESCRIPTION
    raw_match: str
    explicit_cue: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class TinixLocationResolver:
    """Deterministic, auditable Location Resolution engine for TiniX Đà Nẵng listings."""

    def __init__(
        self,
        admin_mapping_path: Path = ADMIN_MAPPING_PATH,
        street_project_catalog_path: Path = STREET_PROJECT_CATALOG_PATH,
    ) -> None:
        self.admin_data = json.loads(admin_mapping_path.read_text(encoding="utf-8"))
        self.catalog_data = json.loads(street_project_catalog_path.read_text(encoding="utf-8"))
        self.mapping_version: str = self.admin_data["mappingVersion"]
        self.catalog_version: str = self.catalog_data["catalogVersion"]

        self.districts_meta: dict[str, dict[str, Any]] = self.admin_data["historicalDistricts"]
        self.district_lookup: dict[str, str] = {}
        for dist_name, meta in self.districts_meta.items():
            self.district_lookup[fold_ascii(dist_name)] = dist_name
            for alias in meta.get("aliases", []):
                if len(alias) >= 4:  # Avoid matching 2-letter abbreviations in free text
                    self.district_lookup[fold_ascii(alias)] = dist_name

        # Ward lookups: (district, ward_folded) and standalone ward_folded
        self.ward_by_dist_and_fold: dict[tuple[str, str], dict[str, Any]] = {}
        self.wards_by_fold: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for w_entry in self.admin_data["historicalWards"]:
            w_canon = normalize_nfc(w_entry["ward"])
            d_canon = normalize_nfc(w_entry["district"])
            enriched = {**w_entry, "ward": w_canon, "district": d_canon}
            keys = {fold_ascii(w_canon)}
            for al in w_entry.get("aliases", []):
                keys.add(fold_ascii(al))
            for k in keys:
                self.ward_by_dist_and_fold[(d_canon, k)] = enriched
                if enriched not in self.wards_by_fold[k]:
                    self.wards_by_fold[k].append(enriched)

        # Post-01/07/2025 NQ 1659 2-tier core units
        self.post2025_units: dict[str, dict[str, Any]] = self.admin_data["post2025CoreUnits"]
        self.post2025_by_fold: dict[str, str] = {}
        for unit_name in self.post2025_units:
            self.post2025_by_fold[fold_ascii(unit_name)] = unit_name

        # Street & Project catalogs
        self.rejected_bare_streets = set(self.catalog_data["rejectedBareStreets"])
        self.ward_homonyms_not_streets = {
            fold_ascii(x) for x in self.catalog_data["wardHomonymsNotStandaloneStreets"]
        }
        self.canonical_street_overrides = {
            normalize_nfc(k).lower(): normalize_nfc(v)
            for k, v in self.catalog_data["canonicalStreetOverrides"].items()
        }
        self.streets_meta: dict[str, dict[str, Any]] = self.catalog_data["streets"]
        self.street_by_fold: dict[str, str] = {}
        self.street_ngram_index: dict[tuple[str, ...], str] = {}
        self.numbered_street_stems: dict[tuple[str, ...], tuple[str, dict[str, int]]] = {}
        self.max_street_tokens = 1

        for supp_stem, supp_dists in self.catalog_data.get("supplementalNumberedStreetStems", {}).items():
            s_nfc = normalize_nfc(supp_stem)
            s_toks = tuple(self._tokenize_words(s_nfc.lower()))
            if len(s_toks) >= 2:
                self.numbered_street_stems[s_toks] = (s_nfc, dict(supp_dists))
                self.max_street_tokens = max(self.max_street_tokens, len(s_toks))

        for canon_s, s_meta in self.streets_meta.items():
            m_stem = re.match(r"^(.+?)\s+(\d{1,2})$", canon_s)
            if m_stem:
                stem_name = m_stem.group(1).strip()
                stem_toks = tuple(self._tokenize_words(stem_name.lower()))
                if len(stem_toks) >= 2:
                    prev_name, prev_dists = self.numbered_street_stems.get(stem_toks, (stem_name, {}))
                    merged_d = dict(prev_dists)
                    for dk, dv in s_meta.get("districts", {}).items():
                        merged_d[dk] = merged_d.get(dk, 0) + dv
                    self.numbered_street_stems[stem_toks] = (prev_name, merged_d)
                    self.max_street_tokens = max(self.max_street_tokens, len(stem_toks))

            all_forms = {canon_s, *s_meta.get("aliases", [])}
            for form in all_forms:
                f_low = normalize_nfc(form).lower()
                f_ascii = fold_ascii(form)
                self.street_by_fold[f_low] = canon_s
                self.street_by_fold[f_ascii] = canon_s
                toks = tuple(self._tokenize_words(f_low))
                if toks:
                    self.street_ngram_index[toks] = canon_s
                    if len(toks) > self.max_street_tokens:
                        self.max_street_tokens = len(toks)
                toks_ascii = tuple(self._tokenize_words(f_ascii))
                if toks_ascii and toks_ascii not in self.street_ngram_index:
                    self.street_ngram_index[toks_ascii] = canon_s

        # Also add common date-street textual forms ("2 tháng 9", "30 tháng 4", "29 tháng 3", "3 tháng 2", "cmt8")
        extra_street_aliases = {
            ("2", "tháng", "9"): "2/9",
            ("2", "thang", "9"): "2/9",
            ("đường", "2/9"): "2/9",
            ("30", "tháng", "4"): "30/4",
            ("30", "thang", "4"): "30/4",
            ("29", "tháng", "3"): "29/3",
            ("29", "thang", "3"): "29/3",
            ("3", "tháng", "2"): "3/2",
            ("3", "thang", "2"): "3/2",
            ("cmt8",): "Cách Mạng Tháng Tám",
            ("cách", "mạng", "tháng", "8"): "Cách Mạng Tháng Tám",
            ("cach", "mang", "thang", "8"): "Cách Mạng Tháng Tám",
            ("đường", "số", "5"): "Số 5",
            ("duong", "so", "5"): "Số 5",
            ("đường", "số", "4"): "Số 4",
            ("đường", "số", "2"): "Số 2",
        }
        for k_toks, target in extra_street_aliases.items():
            if target in self.streets_meta:
                self.street_ngram_index[k_toks] = target

        # Projects index
        self.projects_meta: dict[str, dict[str, Any]] = self.catalog_data["projects"]
        self.project_by_fold: dict[str, str] = {}
        self.project_ngram_index: dict[tuple[str, ...], str] = {}
        self.max_project_tokens = 1
        for canon_p, p_meta in self.projects_meta.items():
            forms = {canon_p, *p_meta.get("aliases", [])}
            for form in forms:
                f_low = normalize_nfc(form).lower()
                f_ascii = fold_ascii(form)
                self.project_by_fold[f_low] = canon_p
                self.project_by_fold[f_ascii] = canon_p
                toks = tuple(self._tokenize_words(f_low))
                if len(toks) >= 2 or (len(toks) == 1 and len(toks[0]) >= 5):
                    self.project_ngram_index[toks] = canon_p
                    self.max_project_tokens = max(self.max_project_tokens, len(toks))

        # Regex for administrative mentions in text (districts, wards, post-2025 units)
        self._compile_admin_patterns()

    def _compile_admin_patterns(self) -> None:
        dist_names = sorted(
            ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu", "Cẩm Lệ", "Hòa Vang", "Hoàng Sa"],
            key=len,
            reverse=True,
        )
        dist_alt = "|".join(re.escape(d) for d in dist_names)
        self.prefixed_district_re = re.compile(
            rf"\b(?P<prefix>quận|q\.?|huyện(?:\s+đảo)?|h\.?|đặc\s+khu)\s*(?P<name>{dist_alt})\b",
            re.IGNORECASE,
        )
        self.bare_district_re = re.compile(
            rf"(?:,\s*|\s*[-–]\s*|\btại\s+|\bthuộc\s+|\bở\s+|\bkhu\s+vực\s+)(?P<name>{dist_alt})(?=\s*(?:,|\.|-|–|\n|$|\bđà\s+nẵng|\btp|\bngay|\bgần))",
            re.IGNORECASE,
        )

        # Prefixed ward / commune mentions (handles pre-2025, NQ 1251, and NQ 1659 names!)
        ward_terms: set[str] = set()
        for w in self.admin_data["historicalWards"]:
            ward_terms.add(normalize_nfc(w["ward"]))
            for al in w.get("aliases", []):
                ward_terms.add(normalize_nfc(al))
        for u in self.post2025_units:
            stripped = re.sub(r"^(?:Phường|Xã|Đặc khu)\s+", "", u, flags=re.IGNORECASE).strip()
            if stripped:
                ward_terms.add(stripped)
        ward_alt = "|".join(re.escape(x) for x in sorted(ward_terms, key=len, reverse=True))
        self.prefixed_ward_re = re.compile(
            rf"\b(?P<prefix>phường|p\.?|xã|x\.?)\s*(?P<name>{ward_alt})\b",
            re.IGNORECASE,
        )

    @staticmethod
    def _tokenize_words(text: str) -> list[str]:
        return re.findall(r"\d{1,2}/\d{1,2}|[0-9a-zA-ZÀ-ỹĐđ]+", text)

    @staticmethod
    def _tokenize_with_spans(text: str) -> list[tuple[str, int, int]]:
        return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\d{1,2}/\d{1,2}|[0-9a-zA-ZÀ-ỹĐđ]+", text)]

    def _classify_span_context(
        self,
        clause_text: str,
        start: int,
        end: int,
        entity_kind: str,
        canonical_name: str,
        is_broker_clause: bool,
    ) -> tuple[str, bool]:
        if is_broker_clause:
            return ("C", False)

        # Restrict prefix/suffix to the nearest comma sub-clause so adjacent phrases don't bleed
        left_comma = clause_text.rfind(",", 0, start)
        sub_start = left_comma + 1 if left_comma != -1 else 0
        right_comma = clause_text.find(",", end)
        sub_end = right_comma if right_comma != -1 else len(clause_text)

        prefix = clause_text[max(sub_start, start - 48) : start]
        suffix = clause_text[end : min(sub_end, end + 24)]

        explicit_cue = bool(STREET_EXPLICIT_CUE_RE.search(prefix) or PROPERTY_CUE_PREFIX_RE.search(prefix))

        # Check if earlier in this same clause a connectivity/proximity list began ("kết nối Liên Chiểu, Hải Châu")
        if CLAUSE_CONNECTIVITY_LIST_RE.search(clause_text[:start]):
            return ("D" if entity_kind == "PROJECT" else "B", explicit_cue)

        # Protect "Cách Mạng Tháng Tám" from "cách" preposition false positive
        if NEARBY_PREFIX_RE.search(prefix) or DISTANCE_SUFFIX_RE.search(suffix):
            if entity_kind == "PROJECT":
                return ("D", explicit_cue)
            return ("B", explicit_cue)

        # Also catch "gần/sát/cách ... <mention>" when separated by a short noun like "gần biển Mỹ Khê" or "cách cầu Rồng"
        wider_prefix = clause_text[max(sub_start, start - 32) : start].lower()
        if re.search(
            r"(?:\bgần|\bsát|\bcạnh|\bliền\s+kề|\bđối\s+diện|\bsau\s+lưng|\bcách|\bthông\s+ra|\bsong\s+song|"
            r"(?<!\blake\s)(?<!\bocean\s)(?<!\briver\s)(?<!\bsea\s)(?<!\bpark\s)(?<!\bsky\s)(?<!\bgolf\s)(?<!\bcity\s)\bview|"
            r"\bnhìn\s+ra|\bra\s+biển|\bra\s+đường)\b",
            wider_prefix,
        ):
            # Make sure "Cách" isn't part of another street before this one
            if not re.search(r"cách\s+mạng\s+tháng", wider_prefix):
                return ("D" if entity_kind == "PROJECT" else "B", explicit_cue)

        return ("A", explicit_cue)

    def _extract_text_mentions(self, text: str, source_field: str) -> list[TextMention]:
        if not text:
            return []
        norm_text = normalize_nfc(text)
        mentions: list[TextMention] = []
        raw_clauses = CLAUSE_SPLIT_RE.split(norm_text)
        total_clauses = len(raw_clauses)
        in_broker_footer = False

        for clause_idx, raw_clause in enumerate(raw_clauses):
            clause = raw_clause.strip()
            if not clause:
                continue
            if (
                source_field == "DESCRIPTION"
                and clause_idx >= max(1, total_clauses // 2)
                and (BROKER_FOOTER_START_RE.search(clause) or "[phone_number]" in clause.lower())
            ):
                in_broker_footer = True
            is_broker = in_broker_footer or bool(BROKER_CONTACT_RE.search(clause))

            # 1. Prefixed ward / post-2025 unit mentions
            ward_spans: list[tuple[int, int]] = []
            for m in self.prefixed_ward_re.finditer(clause):
                w_raw = normalize_nfc(m.group("name"))
                p_raw = m.group("prefix").lower().rstrip(".")
                cat, exp = self._classify_span_context(clause, m.start(), m.end(), "WARD", w_raw, is_broker)
                ward_spans.append((m.start(), m.end()))

                # Check if this is an NQ 1659 post-07/2025 operational unit (e.g. "Phường Hòa Cường", "Phường An Hải", "Xã Hòa Vang", "Xã Bà Nà")
                full_unit_key = fold_ascii(f"{'Xã' if p_raw.startswith('x') else 'Phường'} {w_raw}")
                w_fold = fold_ascii(w_raw)

                if w_fold in self.wards_by_fold:
                    # Exact match in historical / NQ 1251 wards
                    # Note: some names like "Hải Châu", "Thanh Khê", "An Khê", "Hòa Xuân" exist in BOTH NQ 1251 and NQ 1659!
                    mentions.append(
                        TextMention(
                            kind="WARD",
                            canonical=self.wards_by_fold[w_fold][0]["ward"],
                            category=cat,
                            source_field=source_field,
                            raw_match=m.group(0),
                            explicit_cue=True,
                            extra={"post2025Unit": self.post2025_by_fold.get(full_unit_key)},
                        )
                    )
                elif full_unit_key in self.post2025_by_fold:
                    mentions.append(
                        TextMention(
                            kind="POST2025_UNIT",
                            canonical=self.post2025_by_fold[full_unit_key],
                            category=cat,
                            source_field=source_field,
                            raw_match=m.group(0),
                            explicit_cue=True,
                        )
                    )

            # 2. Prefixed & bare district mentions (excluding spans already matched as prefixed wards, e.g. "Phường Ngũ Hành Sơn", "Xã Hòa Vang")
            dist_spans: list[tuple[int, int]] = []
            for is_prefixed_dist, regex in ((True, self.prefixed_district_re), (False, self.bare_district_re)):
                for m in regex.finditer(clause):
                    s_pos, e_pos = m.start("name"), m.end("name")
                    if any(not (e_pos <= ws or s_pos >= we) for ws, we in ward_spans + dist_spans):
                        continue
                    # Make sure "Đường Hoàng Sa" or "Đường Ngũ Hành Sơn" is NOT parsed as a bare district!
                    before_name = clause[max(0, s_pos - 20) : s_pos]
                    if re.search(r"\b(?:đường|phố|mặt\s+tiền|mt|kiệt|hẻm)\s*$", before_name, re.IGNORECASE):
                        continue
                    d_canon = self.district_lookup.get(fold_ascii(m.group("name")))
                    if d_canon:
                        cat, exp = self._classify_span_context(clause, m.start(), m.end(), "DISTRICT", d_canon, is_broker)
                        dist_spans.append((m.start(), m.end()))
                        mentions.append(
                            TextMention(
                                kind="DISTRICT",
                                canonical=d_canon,
                                category=cat,
                                source_field=source_field,
                                raw_match=m.group(0).strip(" ,"),
                                explicit_cue=True,
                                extra={"prefixedDistrict": is_prefixed_dist},
                            )
                        )

            # 3. Token n-gram scan for Projects and Streets (longest-match first, non-overlapping)
            tok_spans = self._tokenize_with_spans(clause)
            n_toks = len(tok_spans)
            if not n_toks:
                continue
            low_words = [t[0].lower() for t in tok_spans]
            ascii_words = [fold_ascii(t[0]) for t in tok_spans]

            # 3a. Projects
            occupied = [False] * n_toks
            max_p = min(self.max_project_tokens, n_toks)
            for i in range(n_toks):
                if occupied[i]:
                    continue
                for length in range(max_p, 0, -1):
                    if i + length > n_toks or any(occupied[i : i + length]):
                        continue
                    seq_low = tuple(low_words[i : i + length])
                    canon_p = self.project_ngram_index.get(seq_low)
                    if not canon_p and length >= 2:
                        canon_p = self.project_ngram_index.get(tuple(ascii_words[i : i + length]))
                    if canon_p:
                        char_s, char_e = tok_spans[i][1], tok_spans[i + length - 1][2]
                        # Single-word project like "Azura" requires apartment/building/project context
                        if length == 1:
                            ctx = clause[max(0, char_s - 25) : min(len(clause), char_e + 25)].lower()
                            if not re.search(r"\b(?:căn\s+hộ|chung\s+cư|tòa|dự\s+án|tower|azura)\b", ctx):
                                continue
                        cat, exp = self._classify_span_context(clause, char_s, char_e, "PROJECT", canon_p, is_broker)
                        for k in range(i, i + length):
                            occupied[k] = True
                        mentions.append(
                            TextMention(
                                kind="PROJECT",
                                canonical=canon_p,
                                category=cat,
                                source_field=source_field,
                                raw_match=clause[char_s:char_e],
                                explicit_cue=exp,
                            )
                        )
                        break

            # 3b. Streets
            occupied_st = [False] * n_toks
            # Mark ward & district spans as occupied unless preceded by explicit street cue ("đường ...")
            for ws, we in ward_spans + dist_spans:
                for idx_t, (_, ts, te) in enumerate(tok_spans):
                    if ts >= ws and te <= we:
                        occupied_st[idx_t] = True

            max_s = min(self.max_street_tokens, n_toks)
            for i in range(n_toks):
                if occupied_st[i]:
                    continue
                for length in range(max_s, 0, -1):
                    if i + length > n_toks or any(occupied_st[i : i + length]):
                        continue
                    seq_low = tuple(low_words[i : i + length])
                    canon_s = self.street_ngram_index.get(seq_low)
                    used_ascii_fallback = False
                    # Support numbered street stems (e.g. "Giáng Hương 6", "Hói Kiểng 26") when followed by a street integer
                    if (
                        not canon_s
                        and length >= 2
                        and i + length < n_toks
                        and low_words[i + length].isdigit()
                        and 1 <= int(low_words[i + length]) <= 60
                        and seq_low in self.numbered_street_stems
                    ):
                        next_after_num = low_words[i + length + 1] if (i + length + 1) < n_toks else ""
                        if next_after_num not in INVALID_HOUSE_FOLLOWERS:
                            char_s_stem = tok_spans[i][1]
                            if STREET_EXPLICIT_CUE_RE.search(clause[max(0, char_s_stem - 30) : char_s_stem]):
                                stem_canon, _ = self.numbered_street_stems[seq_low]
                                canon_s = f"{stem_canon} {low_words[i + length]}"
                                length = length + 1

                    if not canon_s and length >= 2:
                        # Only allow ASCII fallback if at least 2 tokens and preceded by road cue to avoid Vietnamese minimal-pair collisions
                        char_s_probe = tok_spans[i][1]
                        if STREET_EXPLICIT_CUE_RE.search(clause[max(0, char_s_probe - 30) : char_s_probe]):
                            canon_s = self.street_ngram_index.get(tuple(ascii_words[i : i + length]))
                            used_ascii_fallback = canon_s is not None
                    if not canon_s:
                        continue

                    char_s, char_e = tok_spans[i][1], tok_spans[i + length - 1][2]
                    # Reject date-like fractions if part of面积/ratio/24/7 or preceded by kiệt slash
                    if canon_s in DATE_STREETS:
                        before_ch = clause[max(0, char_s - 20) : char_s]
                        if not re.search(r"\b(?:đường|phố|mặt\s+tiền|mt|kiệt|hẻm|k\d+|số\s+\d+)\s*$", before_ch, re.IGNORECASE):
                            continue

                    s_meta = self.streets_meta.get(canon_s, {})
                    cat, exp = self._classify_span_context(clause, char_s, char_e, "STREET", canon_s, is_broker)

                    # Require explicit road cue for 1-token or homonym streets (e.g. "Hoàng Sa", "Ngũ Hành Sơn", "K20", "Vành Đai", "Số 5")
                    if s_meta.get("requiresExplicitCue") or fold_ascii(canon_s) in self.ward_homonyms_not_streets:
                        before_st = clause[max(0, char_s - 32) : char_s]
                        if not STREET_EXPLICIT_CUE_RE.search(before_st):
                            continue

                    # Prevent matching a person/common phrase when "Khuê Mỹ" is part of ward "Phường Khuê Mỹ"
                    after_st = clause[char_e : min(len(clause), char_e + 12)]
                    # Check if text actually continues with a street number (e.g. matched "Hói Kiểng" when text says "Hói Kiểng 10" not in catalog)
                    num_ext = re.match(r"^\s+(\d{1,2})\b(?!\s*(?:m|m2|m²|km|tầng|pn|tỷ|triệu|phút|%))", after_st, re.IGNORECASE)
                    final_street = canon_s
                    extra_tok = 0
                    if num_ext and not re.search(r"\d+$", canon_s):
                        candidate_numbered = f"{canon_s} {num_ext.group(1)}"
                        stem_toks_check = tuple(self._tokenize_words(canon_s.lower()))
                        if candidate_numbered in self.streets_meta or (
                            stem_toks_check in self.numbered_street_stems and 1 <= int(num_ext.group(1)) <= 60
                        ):
                            final_street = candidate_numbered
                            char_e += num_ext.end()
                            if i + length < n_toks and low_words[i + length] == num_ext.group(1):
                                extra_tok = 1

                    for k in range(i, i + length + extra_tok):
                        occupied_st[k] = True
                    mentions.append(
                        TextMention(
                            kind="STREET",
                            canonical=final_street,
                            category=cat,
                            source_field=source_field,
                            raw_match=clause[char_s:char_e],
                            explicit_cue=exp,
                            extra={"asciiFallback": used_ascii_fallback},
                        )
                    )
                    break

        return mentions

    def _extract_house_and_alley(
        self,
        title: str,
        description: str,
        resolved_street: str | None,
        floor_count: float | None,
    ) -> tuple[str | None, str | None, str | None, list[str]]:
        """Extract verified Category A houseNumber, alleyNumber, and plotCode without false positives."""
        evidence: list[str] = []
        house_number: str | None = None
        alley_number: str | None = None
        plot_code: str | None = None

        combined_sources = [("TITLE", normalize_nfc(title)), ("DESC", normalize_nfc(description))]

        # Extract subdivision plotCode if present (e.g. "lô B2-12")
        for _, txt in combined_sources:
            if not txt:
                continue
            pm = PLOT_CODE_RE.search(txt)
            if pm:
                cand_plot = re.sub(r"\s+", "", pm.group(1)).upper()
                # Ignore generic "lô góc", "lô đôi"
                if any(ch.isdigit() for ch in cand_plot):
                    plot_code = cand_plot
                    evidence.append("TEXT_PLOT_CODE")
                    break

        if not resolved_street:
            return (None, None, plot_code, evidence)

        # Build safe regex variants for the resolved street
        st_variants = {resolved_street}
        st_meta = self.streets_meta.get(resolved_street)
        if st_meta:
            st_variants.update(st_meta.get("aliases", []))
        if resolved_street == "Cách Mạng Tháng Tám":
            st_variants.update({"CMT8", "Cách Mạng Tháng 8"})
        st_alt = "|".join(re.escape(v) for v in sorted(st_variants, key=len, reverse=True) if len(v) >= 2)
        if not st_alt:
            return (None, None, plot_code, evidence)

        # Pattern 1: Alley + slash house number before street, e.g. "K146/12 Lê Đình Dương", "kiệt 325/18 Hùng Vương"
        alley_house_re = re.compile(
            rf"\b(?:kiệt|kiet|hẻm|hem|ngõ|ngo|k)\s*(?P<alley>\d{{1,4}}[A-LN-Za-ln-z]?)\s*/\s*(?P<subhouse>\d{{1,4}}[A-LN-Za-ln-z]?(?:/\d{{1,3}}[A-LN-Za-ln-z]?)?)"
            rf"\s+(?:đường\s+|phố\s+)?(?:{st_alt})\b",
            re.IGNORECASE,
        )
        # Pattern 2: Alley WITHOUT house number slash, e.g. "kiệt 146 Lê Đình Dương", "K354 Trưng Nữ Vương" (excluding alley widths like "kiệt 3m", "kiệt 5m")
        alley_only_re = re.compile(
            rf"\b(?:kiệt|kiet|hẻm|hem|ngõ|ngo|k)\s*(?P<alley>\d{{1,4}}[A-LN-Za-ln-z]?)(?![.,]?\d*\s*(?:m|mét)\b)\s+(?:đường\s+|phố\s+)?(?:{st_alt})\b",
            re.IGNORECASE,
        )
        # Pattern 3: Explicit "số <N> [đường] <Street>" (excluding "đường số <N>" and "lô số <N>")
        explicit_so_re = re.compile(
            rf"(?<!đường\s)(?<!lô\s)(?<!thửa\s)(?<!tầng\s)(?<!căn\s)\b(?:nhà\s+số|số\s+nhà|địa\s+chỉ\s*:?\s*(?:số\s+)?|tại\s+số|số)\s*"
            rf"(?P<hnum>\d{{1,4}}[A-LN-Za-ln-z]?(?:/\d{{1,3}}[A-LN-Za-ln-z]?)?)\s+(?:đường\s+|phố\s+)?(?:{st_alt})\b",
            re.IGNORECASE,
        )
        # Pattern 4: Direct street address "<Cue> <N> <Street>", e.g. "Bán nhà 72 Hàm Nghi", "Lake View 72 Hàm Nghi", "Địa chỉ: 300 Dũng Sĩ Thanh Khê"
        direct_house_re = re.compile(
            rf"\b(?:địa\s+chỉ\s*:?|tại|mặt\s+tiền|mt|bán\s+nhà|nhà\s+phố|nhà|tòa\s+nhà|khách\s+sạn|lake\s+view|tower|chung\s+cư)\s+"
            rf"(?P<hnum>\d{{1,4}}[A-LN-Za-ln-z]?)\s+(?:{st_alt})\b",
            re.IGNORECASE,
        )

        for src_label, txt in combined_sources:
            if not txt:
                continue
            raw_clauses = CLAUSE_SPLIT_RE.split(txt)
            total_clauses = len(raw_clauses)
            for clause_idx, raw_clause in enumerate(raw_clauses):
                clause = raw_clause.strip()
                if not clause:
                    continue
                if (
                    src_label == "DESC"
                    and clause_idx >= max(1, total_clauses // 2)
                    and (BROKER_FOOTER_START_RE.search(clause) or "[phone_number]" in clause.lower())
                ):
                    break
                if BROKER_CONTACT_RE.search(clause):
                    continue

                m1 = alley_house_re.search(clause)
                if m1:
                    cat, _ = self._classify_span_context(clause, m1.start(), m1.end(), "STREET", resolved_street, False)
                    if cat == "A":
                        alley_val = m1.group("alley").upper()
                        sub_val = m1.group("subhouse").upper()
                        alley_number = f"K{alley_val}"
                        house_number = f"K{alley_val}/{sub_val}"
                        evidence.append(f"TEXT_{src_label}_ALLEY_HOUSE_NUMBER")
                        return (house_number, alley_number, plot_code, evidence)

                m3 = explicit_so_re.search(clause)
                if m3:
                    h_cand = m3.group("hnum").upper()
                    if h_cand not in DATE_STREETS and resolved_street != f"Số {h_cand}":
                        cat, _ = self._classify_span_context(clause, m3.start(), m3.end(), "STREET", resolved_street, False)
                        if cat == "A":
                            house_number = h_cand
                            evidence.append(f"TEXT_{src_label}_HOUSE_NUMBER")
                            return (house_number, alley_number, plot_code, evidence)

                m4 = direct_house_re.search(clause)
                if m4:
                    h_cand = m4.group("hnum").upper()
                    # Guard against "nhà 3 [tầng] <Street>" or "2 [mặt tiền]" typos on tiny integers 1..5
                    cue_low = m4.group(0).lower()
                    is_tiny_int = h_cand.isdigit() and int(h_cand) <= 5
                    if is_tiny_int and not cue_low.startswith(("địa chỉ", "tại")):
                        if floor_count is not None and abs(float(floor_count) - int(h_cand)) < 0.01:
                            pass
                        elif int(h_cand) in (2, 3) and ("nhà" in cue_low or "mặt tiền" in cue_low):
                            pass
                        else:
                            cat, _ = self._classify_span_context(clause, m4.start(), m4.end(), "STREET", resolved_street, False)
                            if cat == "A":
                                house_number = h_cand
                                evidence.append(f"TEXT_{src_label}_HOUSE_NUMBER")
                                return (house_number, alley_number, plot_code, evidence)
                    elif h_cand not in DATE_STREETS:
                        cat, _ = self._classify_span_context(clause, m4.start(), m4.end(), "STREET", resolved_street, False)
                        if cat == "A":
                            house_number = h_cand
                            evidence.append(f"TEXT_{src_label}_HOUSE_NUMBER")
                            return (house_number, alley_number, plot_code, evidence)

                if alley_number is None:
                    m2 = alley_only_re.search(clause)
                    if m2:
                        cat, _ = self._classify_span_context(clause, m2.start(), m2.end(), "STREET", resolved_street, False)
                        if cat == "A" and resolved_street != "K20":
                            alley_number = f"K{m2.group('alley').upper()}"
                            evidence.append(f"TEXT_{src_label}_ALLEY_NUMBER")

        return (house_number, alley_number, plot_code, evidence)

    def resolve_record(self, row: dict[str, Any]) -> dict[str, Any]:
        """Resolve location precision, administrative mapping, confidence, and amenity capability for 1 TiniX row."""
        internal_id = row["internal_id"]
        orig_province = row.get("province_name")
        orig_district = row.get("district_name")
        orig_ward = row.get("ward_name")
        orig_street = row.get("street_name")
        orig_project = row.get("project_name")
        title = row.get("name") or ""
        description = row.get("description") or ""
        prop_type = row.get("normalized_type") or ""
        quality_status = row.get("quality_status") or "HYBRID_ELIGIBLE_RESEARCH"
        quality_rule_version = row.get("quality_rule_version") or "TINIX_RESEARCH_V1"
        floor_count = row.get("floor_count")

        # Verified GPS support (0 in TiniX, supported for schema completeness & unit testing)
        verified_lat = row.get("verified_latitude")
        verified_lng = row.get("verified_longitude")
        verified_geocode_level = row.get("verified_geocode_level")  # None | 'EXACT_PIN' | 'ROOFTOP_VERIFIED' | 'UNVERIFIED_GEOCODE'

        evidence: list[str] = []
        issues: set[str] = set()
        reasons: list[str] = []

        norm_prov = normalize_nfc(orig_province)
        norm_dist_raw = normalize_nfc(orig_district)
        norm_ward_raw = normalize_nfc(orig_ward)
        norm_street_raw = normalize_nfc(orig_street)
        norm_proj_raw = normalize_nfc(orig_project)

        title_mentions = self._extract_text_mentions(title, "TITLE")
        desc_mentions = self._extract_text_mentions(description, "DESCRIPTION")
        all_mentions = title_mentions + desc_mentions
        has_corner_cue = bool(CORNER_INTERSECTION_RE.search(f"{title}\n{description}"))

        # 1. Province & Special Territory / Out-of-Scope check
        province_valid = fold_ascii(norm_prov) in {"da nang", "thanh pho da nang", "tp da nang"}
        if province_valid:
            evidence.append("STRUCTURED_PROVINCE")
        elif norm_prov:
            issues.add("SOURCE_LOCATION_INCONSISTENT")

        combined_norm_text = f"{normalize_nfc(title)}\n{normalize_nfc(description)}"
        if OUT_OF_DANANG_MAINLAND_RE.search(combined_norm_text):
            # Check if it's Hoàng Sa + Thuận An or explicit out-of-province property
            if fold_ascii(norm_dist_raw) == "hoang sa" or re.search(
                r"\b(?:tại|thuộc|xã|phường)\s+thuận\s+an\b", combined_norm_text, re.IGNORECASE
            ):
                issues.add("SOURCE_LOCATION_INCONSISTENT")
                reasons.append("Văn bản mô tả địa danh ngoài Đà Nẵng (Thuận An / Thừa Thiên Huế).")

        if QUANG_NAM_EXPANDED_CATEGORY_A_RE.search(combined_norm_text):
            issues.add("ADDRESS_CONFLICT")
            issues.add("NEEDS_MAPPING")
            reasons.append("Văn bản vị trí tài sản nhắc địa bàn Quảng Nam mở rộng sau 07/2025 mâu thuẫn quận lịch sử.")

        # 2. Historical District Resolution
        struct_dist = self.district_lookup.get(fold_ascii(norm_dist_raw)) if norm_dist_raw else None
        if struct_dist == "Hoàng Sa":
            issues.add("NON_RESIDENTIAL_SPECIAL_TERRITORY")
            issues.add("SOURCE_LOCATION_INCONSISTENT")
            reasons.append(
                "Bản ghi gắn quận/huyện 'Hoàng Sa' (Huyện đảo/Đặc khu không có khu dân cư thương mại phục vụ LIVING; nhầm với 'đường Hoàng Sa' hoặc địa phương khác)."
            )

        is_hoa_lien_split_context = (
            struct_dist == "Hòa Vang" and fold_ascii(norm_ward_raw) == "hoa lien"
        )
        cat_a_districts = []
        hoa_lien_post2025_lien_chieu = False
        for m in all_mentions:
            if m.kind == "DISTRICT" and m.category == "A" and m.canonical != "Hoàng Sa":
                # Under NQ 1659 (01/07/2025), southern Xã Hòa Liên (Hòa Vang) merged into Phường Liên Chiểu;
                # listings writing "Hòa Liên - Liên Chiểu - Đà Nẵng" (without "Quận Liên Chiểu") refer to post-2025 Phường Liên Chiểu!
                if (
                    is_hoa_lien_split_context
                    and m.canonical == "Liên Chiểu"
                    and not m.extra.get("prefixedDistrict")
                ):
                    hoa_lien_post2025_lien_chieu = True
                    continue
                if m.canonical not in cat_a_districts:
                    cat_a_districts.append(m.canonical)

        resolved_district: str | None = None
        district_conflict = False

        if struct_dist and struct_dist != "Hoàng Sa":
            evidence.append("STRUCTURED_DISTRICT")
            if cat_a_districts:
                if struct_dist in cat_a_districts:
                    evidence.append("TEXT_CORROBORATED_DISTRICT")
                    # Check if a SECOND incompatible Category A district was also claimed as property location
                    other_dists = [d for d in cat_a_districts if d != struct_dist]
                    if other_dists and not has_corner_cue:
                        # Only flag conflict if title itself contradicts structured district, or multiple distinct districts compete without street border justification
                        title_a_dists = {
                            m.canonical for m in title_mentions if m.kind == "DISTRICT" and m.category == "A" and m.canonical != "Hoàng Sa"
                        }
                        if title_a_dists and struct_dist not in title_a_dists:
                            district_conflict = True
                else:
                    # Category A text only names a DIFFERENT district than structured district!
                    district_conflict = True
                    issues.add("ADDRESS_CONFLICT")
                    issues.add("AMBIGUOUS_LOCATION")
                    reasons.append(
                        f"Mâu thuẫn quận/huyện giữa trường cấu trúc ('{struct_dist}') và địa chỉ tài sản trong văn bản ({cat_a_districts})."
                    )
            if not district_conflict and "ADDRESS_CONFLICT" not in issues:
                resolved_district = struct_dist
        elif struct_dist is None and cat_a_districts:
            if len(cat_a_districts) == 1 and "ADDRESS_CONFLICT" not in issues:
                resolved_district = cat_a_districts[0]
                evidence.append("TEXT_RECOVERED_DISTRICT")
            elif len(cat_a_districts) > 1:
                district_conflict = True
                issues.add("ADDRESS_CONFLICT")
                issues.add("AMBIGUOUS_LOCATION")
                reasons.append(f"Nhiều quận/huyện mâu thuẫn trong văn bản: {cat_a_districts}.")

        # Check if structured district came SOLELY from a broker office clause (Category C)
        if struct_dist and not cat_a_districts:
            cat_c_dists = {m.canonical for m in all_mentions if m.kind == "DISTRICT" and m.category == "C"}
            if struct_dist in cat_c_dists and not orig_ward and not orig_street:
                issues.add("SOURCE_LOCATION_INCONSISTENT")
                issues.add("AMBIGUOUS_LOCATION")
                resolved_district = None
                reasons.append(f"Quận '{struct_dist}' chỉ xuất hiện trong địa chỉ liên hệ văn phòng môi giới (Category C).")

        # 3. Historical & 2025 Ward Resolution
        resolved_ward_historical: str | None = None
        resolved_ward_nq1251: str | None = None
        resolved_unit_nq1659: str | None = None
        ward_conflict = False

        struct_ward_entry: dict[str, Any] | None = None
        if norm_ward_raw and resolved_district:
            w_fold = fold_ascii(norm_ward_raw)
            struct_ward_entry = self.ward_by_dist_and_fold.get((resolved_district, w_fold))
            if struct_ward_entry is None and w_fold in self.wards_by_fold:
                # Structured ward belongs to a DIFFERENT district!
                actual_dists = sorted({e["district"] for e in self.wards_by_fold[w_fold]})
                issues.add("SOURCE_LOCATION_INCONSISTENT")
                issues.add("ADDRESS_CONFLICT")
                ward_conflict = True
                reasons.append(
                    f"Phường/xã cấu trúc '{norm_ward_raw}' thuộc {actual_dists}, không thuộc '{resolved_district}'."
                )

        cat_a_ward_mentions = [m for m in all_mentions if m.kind == "WARD" and m.category == "A"]
        cat_a_post2025_mentions = [m for m in all_mentions if m.kind == "POST2025_UNIT" and m.category == "A"]

        if struct_ward_entry and not ward_conflict and not district_conflict:
            evidence.append("STRUCTURED_WARD")
            resolved_ward_nq1251 = struct_ward_entry["nq1251Ward"]
            resolved_unit_nq1659 = struct_ward_entry["nq1659Unit"]

            # Determine pre-2025 historical ward
            if struct_ward_entry["stage"] == "NQ_1251":
                # e.g. "Hải Châu" (Hải Châu I + II) or "An Hải Nam" (An Hải Đông + Tây)
                pre_members = set(struct_ward_entry.get("pre2025Members", []))
                matched_pre = [
                    m.canonical for m in cat_a_ward_mentions if m.canonical in pre_members
                ]
                if len(set(matched_pre)) == 1:
                    resolved_ward_historical = matched_pre[0]
                    evidence.append("TEXT_DISAMBIGUATED_PRE2025_WARD")
                else:
                    # Keep NQ 1251 official ward, note 2-to-1 pre-2025 boundary merge
                    resolved_ward_historical = struct_ward_entry["ward"]
                    issues.add("NEEDS_MAPPING")
            else:
                resolved_ward_historical = struct_ward_entry["ward"]

            if struct_ward_entry.get("mappingCertainty") == "SPLIT_BOUNDARY_NEEDS_MAPPING":
                # Xã Hòa Liên -> split between Phường Liên Chiểu & Phường Hải Vân from 01/07/2025
                if hoa_lien_post2025_lien_chieu:
                    resolved_unit_nq1659 = "Phường Liên Chiểu"
                    evidence.append("TEXT_POST2025_UNIT_CONSISTENT")
                else:
                    issues.add("NEEDS_MAPPING")
                    resolved_unit_nq1659 = None

            # Cross-check against Category A ward mentions in text (accounting for legal 2025 merges!)
            for wm in cat_a_ward_mentions:
                wm_fold = fold_ascii(wm.canonical)
                wm_entries = self.wards_by_fold.get(wm_fold, [])
                # Check if wm is compatible with struct_ward_entry via NQ 1251 or NQ 1659!
                compatible = False
                for we in wm_entries:
                    if (
                        we["ward"] == struct_ward_entry["ward"]
                        or we["nq1251Ward"] == struct_ward_entry["nq1251Ward"]
                        or (
                            wm.extra.get("post2025Unit")
                            and wm.extra.get("post2025Unit") == struct_ward_entry.get("nq1659Unit")
                        )
                    ):
                        compatible = True
                        break
                # Special case: "Phường Hải Châu", "Phường Thanh Khê", "Phường An Khê", "Phường Hòa Xuân", "Phường Sơn Trà", "Phường Cẩm Lệ", "Phường Liên Chiểu"
                # are NQ 1659 merged wards whose short names collide with historical wards/districts!
                if not compatible:
                    post_unit_candidate = wm.extra.get("post2025Unit")
                    if post_unit_candidate and post_unit_candidate == struct_ward_entry.get("nq1659Unit"):
                        compatible = True
                if compatible:
                    if "TEXT_CORROBORATED_WARD" not in evidence:
                        evidence.append("TEXT_CORROBORATED_WARD")
                else:
                    # Only flag conflict if not a cross-ward corner cue
                    if not has_corner_cue:
                        ward_conflict = True
                        issues.add("ADDRESS_CONFLICT")
                        issues.add("AMBIGUOUS_LOCATION")
                        reasons.append(
                            f"Mâu thuẫn phường/xã: cấu trúc '{struct_ward_entry['ward']}' nhưng văn bản ghi '{wm.raw_match}'."
                        )
                        resolved_ward_historical = None
                        resolved_ward_nq1251 = None
                        resolved_unit_nq1659 = None
                        break

            # Cross-check against explicit NQ 1659 post-2025 units in text (e.g. "Phường Hòa Cường", "Xã Bà Nà")
            if not ward_conflict:
                for pm in cat_a_post2025_mentions:
                    unit_meta = self.post2025_units.get(pm.canonical, {})
                    if struct_ward_entry["ward"] in unit_meta.get("memberWards", []) or struct_ward_entry["nq1251Ward"] in unit_meta.get("memberWards", []):
                        if "TEXT_POST2025_UNIT_CONSISTENT" not in evidence:
                            evidence.append("TEXT_POST2025_UNIT_CONSISTENT")
                    elif not has_corner_cue:
                        ward_conflict = True
                        issues.add("ADDRESS_CONFLICT")
                        issues.add("AMBIGUOUS_LOCATION")
                        reasons.append(
                            f"Mâu thuẫn ĐVHC 2025: phường cấu trúc '{struct_ward_entry['ward']}' không thuộc '{pm.canonical}'."
                        )
                        resolved_ward_historical = None
                        resolved_ward_nq1251 = None
                        resolved_unit_nq1659 = None
                        break

        elif not norm_ward_raw and resolved_district and not district_conflict:
            # Structured ward is missing -> check if Category A text explicitly names a historical ward or post-2025 unit!
            valid_text_wards: list[dict[str, Any]] = []
            for wm in cat_a_ward_mentions:
                w_entry = self.ward_by_dist_and_fold.get((resolved_district, fold_ascii(wm.canonical)))
                if w_entry and w_entry not in valid_text_wards:
                    valid_text_wards.append(w_entry)

            if len(valid_text_wards) == 1:
                we = valid_text_wards[0]
                # Watch out: if text says "Phường Hải Châu" or "Phường Thanh Khê" (which is BOTH an NQ 1251 ward AND a larger NQ 1659 ward!),
                # check if the text says ", TP Đà Nẵng" without "Quận" (post-07/2025 2-tier format!)
                post_u = f"Phường {we['ward']}"
                is_2tier_format = (
                    post_u in self.post2025_units
                    and len(self.post2025_units[post_u]["memberWards"]) > 2
                    and not any(m.kind == "DISTRICT" and m.category == "A" for m in all_mentions)
                )
                if is_2tier_format:
                    resolved_unit_nq1659 = post_u
                    issues.add("NEEDS_MAPPING")
                    evidence.append("TEXT_POST2025_UNIT_ONLY")
                else:
                    resolved_ward_historical = we["ward"]
                    resolved_ward_nq1251 = we["nq1251Ward"]
                    resolved_unit_nq1659 = we["nq1659Unit"]
                    evidence.append("TEXT_RECOVERED_WARD")
                    if we["stage"] == "NQ_1251" or we.get("mappingCertainty") == "SPLIT_BOUNDARY_NEEDS_MAPPING":
                        issues.add("NEEDS_MAPPING")
            elif len(valid_text_wards) > 1 and not has_corner_cue:
                issues.add("AMBIGUOUS_LOCATION")
                reasons.append(
                    f"Thiếu phường cấu trúc và văn bản nhắc nhiều phường ({[w['ward'] for w in valid_text_wards]})."
                )
            elif cat_a_post2025_mentions:
                matching_units = [
                    pm.canonical
                    for pm in cat_a_post2025_mentions
                    if resolved_district in self.post2025_units.get(pm.canonical, {}).get("historicalDistricts", [])
                ]
                uniq_units = list(dict.fromkeys(matching_units))
                if len(uniq_units) == 1:
                    resolved_unit_nq1659 = uniq_units[0]
                    issues.add("NEEDS_MAPPING")  # Cannot guess single historical ward from merged NQ 1659 unit!
                    evidence.append("TEXT_POST2025_UNIT_ONLY")
            elif resolved_district == "Ngũ Hành Sơn":
                # Entire Ngũ Hành Sơn district (all 4 wards) deterministically became Phường Ngũ Hành Sơn under NQ 1659!
                resolved_unit_nq1659 = "Phường Ngũ Hành Sơn"

        # 4. Project / Building Resolution (separating Category A property project vs Category D marketing reference)
        matched_project: str | None = None
        cat_a_projects = list(dict.fromkeys(m.canonical for m in all_mentions if m.kind == "PROJECT" and m.category == "A"))
        cat_d_projects = list(dict.fromkeys(m.canonical for m in all_mentions if m.kind == "PROJECT" and m.category == "D"))

        if norm_proj_raw and resolved_district and not district_conflict:
            canon_struct_proj = (
                self.project_by_fold.get(norm_proj_raw.lower())
                or self.project_by_fold.get(fold_ascii(norm_proj_raw))
                or norm_proj_raw
            )
            # Check if structured project was contaminated from a Category D marketing comparison ("gần FPT City", "sát Sun Cosmo")
            if canon_struct_proj in cat_d_projects and canon_struct_proj not in cat_a_projects:
                issues.add("LOCATION_FROM_MARKETING_TEXT")
                reasons.append(f"Dự án cấu trúc '{orig_project}' chỉ xuất hiện ở ngữ cảnh quảng cáo lân cận (Category D).")
            else:
                p_meta = self.projects_meta.get(canon_struct_proj)
                if p_meta and resolved_district not in p_meta["districts"]:
                    issues.add("SOURCE_LOCATION_INCONSISTENT")
                    reasons.append(
                        f"Dự án '{canon_struct_proj}' thuộc {list(p_meta['districts'].keys())}, không khớp quận '{resolved_district}'."
                    )
                else:
                    matched_project = canon_struct_proj
                    evidence.append("STRUCTURED_PROJECT")
                    if canon_struct_proj in cat_a_projects:
                        evidence.append("TEXT_CORROBORATED_PROJECT")
        elif not norm_proj_raw and resolved_district and not district_conflict and len(cat_a_projects) == 1:
            cand_p = cat_a_projects[0]
            p_meta = self.projects_meta.get(cand_p, {})
            if resolved_district in p_meta.get("districts", {}):
                matched_project = cand_p
                evidence.append("TEXT_RECOVERED_PROJECT")

        # 5. Street Resolution (validating structured `street_name` against corrupted bare numbers, ward homonyms, marketing Category B & broker Category C)
        normalized_street: str | None = None
        street_conflict = False

        cat_a_streets = list(dict.fromkeys(m.canonical for m in all_mentions if m.kind == "STREET" and m.category == "A"))
        cat_b_streets = list(dict.fromkeys(m.canonical for m in all_mentions if m.kind == "STREET" and m.category == "B"))
        cat_c_streets = list(dict.fromkeys(m.canonical for m in all_mentions if m.kind == "STREET" and m.category == "C"))

        if norm_street_raw and resolved_district and not district_conflict and not ward_conflict:
            s_low = norm_street_raw.lower()
            s_fold = fold_ascii(norm_street_raw)

            # Case 5a: Bare corrupted integer/code (e.g. "5" from "đường 5,5m" or truncated "Hói Kiểng 10" -> "10")
            if norm_street_raw in self.rejected_bare_streets:
                # Check if Category A text actually says "Đường số N" or a numbered street ending in N (e.g. "Hói Kiểng 10")
                recovered = None
                for cs in cat_a_streets:
                    if cs == f"Số {norm_street_raw}" or cs.endswith(f" {norm_street_raw}"):
                        recovered = cs
                        break
                if recovered:
                    normalized_street = recovered
                    evidence.append("TEXT_RECOVERED_TRUNCATED_STREET")
                else:
                    issues.add("SOURCE_LOCATION_INCONSISTENT")
                    reasons.append(
                        f"Loại bỏ street_name cấu trúc '{orig_street}' (số cụt từ độ rộng đường 'đường 5,5m/7,5m' hoặc mã nội bộ chưa đủ tên đường)."
                    )

            # Case 5b: Structured street is actually a ward homonym ("Hòa Thọ Đông", "Mỹ An", "Nại Hiên Đông", "Hòa Liên", "Hòa Khánh")
            elif s_fold in self.ward_homonyms_not_streets:
                # Check if Category A text has a numbered variant like "Mỹ An 7" or explicit "đường ..."
                recovered = None
                for cs in cat_a_streets:
                    if fold_ascii(cs).startswith(s_fold + " "):
                        recovered = cs
                        break
                if recovered:
                    normalized_street = recovered
                    evidence.append("TEXT_RECOVERED_TRUNCATED_STREET")
                elif re.search(rf"\b(?:đường|phố)\s+{re.escape(norm_street_raw)}\b(?!\s*\d)", combined_norm_text, re.IGNORECASE):
                    normalized_street = norm_street_raw
                    evidence.append("STRUCTURED_STREET")
                else:
                    issues.add("SOURCE_LOCATION_INCONSISTENT")
                    reasons.append(
                        f"Loại bỏ street_name '{orig_street}' trùng tên phường/xã mà không có bằng chứng tên đường độc lập."
                    )

            else:
                canon_struct_street = (
                    self.canonical_street_overrides.get(s_low)
                    or self.street_by_fold.get(s_low)
                    or self.street_by_fold.get(s_fold)
                    or norm_street_raw
                )

                # Case 5c: Check if structured street appears ONLY in Category B (nearby landmark/marketing) or Category C (broker office)!
                if canon_struct_street in cat_b_streets and canon_struct_street not in cat_a_streets:
                    issues.add("LOCATION_FROM_MARKETING_TEXT")
                    reasons.append(
                        f"Loại bỏ street_name '{orig_street}' vì trong văn bản chỉ xuất hiện ở ngữ cảnh lân cận/quảng cáo (Category B: gần/cách/thông ra/đối diện)."
                    )
                    # If text ALSO explicitly states the real Category A street, use that real Category A street!
                    if len(cat_a_streets) == 1:
                        cand_a = cat_a_streets[0]
                        if self._is_street_compatible_with_district(cand_a, resolved_district):
                            normalized_street = cand_a
                            evidence.append("TEXT_RECOVERED_STREET")
                elif canon_struct_street in cat_c_streets and canon_struct_street not in cat_a_streets:
                    issues.add("SOURCE_LOCATION_INCONSISTENT")
                    reasons.append(
                        f"Loại bỏ street_name '{orig_street}' vì chỉ xuất hiện trong địa chỉ văn phòng môi giới (Category C)."
                    )
                else:
                    # Case 5d: Check district consistency & conflict with Category A text streets
                    if not self._is_street_compatible_with_district(canon_struct_street, resolved_district):
                        issues.add("SOURCE_LOCATION_INCONSISTENT")
                        issues.add("AMBIGUOUS_LOCATION")
                        reasons.append(
                            f"Tên đường '{canon_struct_street}' không khớp thực nghiệm với quận/huyện '{resolved_district}'."
                        )
                    elif cat_a_streets and canon_struct_street not in cat_a_streets and not has_corner_cue:
                        # Check if structured street is a prefix/variant of cat_a_street (e.g. "Khuê Mỹ Đông" vs "Khuê Mỹ Đông 14")
                        refined = next(
                            (cs for cs in cat_a_streets if fold_ascii(cs).startswith(fold_ascii(canon_struct_street) + " ")),
                            None,
                        )
                        if refined:
                            normalized_street = refined
                            evidence.append("STRUCTURED_STREET")
                            evidence.append("TEXT_REFINED_NUMBERED_STREET")
                        else:
                            # Check if the Category A street in TITLE directly contradicts structured street
                            title_a_streets = [
                                m.canonical for m in title_mentions if m.kind == "STREET" and m.category == "A"
                            ]
                            if title_a_streets and canon_struct_street not in title_a_streets:
                                street_conflict = True
                                issues.add("ADDRESS_CONFLICT")
                                issues.add("AMBIGUOUS_LOCATION")
                                reasons.append(
                                    f"Mâu thuẫn tên đường giữa trường cấu trúc ('{canon_struct_street}') và tiêu đề tài sản ({title_a_streets})."
                                )
                            else:
                                # Structured street kept, note text mentions secondary street (e.g. internal road / connecting alley)
                                normalized_street = canon_struct_street
                                evidence.append("STRUCTURED_STREET")
                    else:
                        normalized_street = canon_struct_street
                        evidence.append("STRUCTURED_STREET")
                        if canon_struct_street in cat_a_streets:
                            if any(m.kind == "STREET" and m.category == "A" and m.canonical == canon_struct_street for m in title_mentions):
                                evidence.append("TEXT_TITLE_STREET")
                            if any(m.kind == "STREET" and m.category == "A" and m.canonical == canon_struct_street for m in desc_mentions):
                                evidence.append("TEXT_DESC_STREET")

        elif not norm_street_raw and resolved_district and not district_conflict and not ward_conflict:
            # Structured street_name is empty -> check Category A explicit street mentions in title/description
            explicit_a_streets = list(
                dict.fromkeys(
                    m.canonical
                    for m in all_mentions
                    if m.kind == "STREET"
                    and m.category == "A"
                    and m.explicit_cue
                    and self._is_street_compatible_with_district(m.canonical, resolved_district)
                )
            )
            if len(explicit_a_streets) == 1:
                normalized_street = explicit_a_streets[0]
                evidence.append("TEXT_RECOVERED_STREET")
            elif len(explicit_a_streets) > 1:
                if has_corner_cue:
                    normalized_street = explicit_a_streets[0]
                    evidence.append("TEXT_RECOVERED_CORNER_STREET")
                else:
                    # Prefer title street only if description street is not competing; otherwise mark AMBIGUOUS_LOCATION!
                    issues.add("AMBIGUOUS_LOCATION")
                    reasons.append(
                        f"Thiếu street_name cấu trúc và văn bản nêu nhiều tên đường khác nhau không có dấu hiệu lô góc: {explicit_a_streets}."
                    )
            elif not explicit_a_streets and cat_b_streets:
                # Listing ONLY mentions nearby landmarks/streets ("Bán nhà gần biển Mỹ Khê", "Nhà cách cầu Rồng 1km")
                issues.add("LOCATION_FROM_MARKETING_TEXT")

        # 6. House Number, Alley Number & Plot Code Extraction
        house_number, alley_number, plot_code, detail_ev = self._extract_house_and_alley(
            title=title,
            description=description,
            resolved_street=normalized_street,
            floor_count=floor_count,
        )
        evidence.extend(detail_ev)

        # 7. Verified Coordinates & Geocode Handling (Section 7 & 10)
        resolved_lat: float | None = None
        resolved_lng: float | None = None
        if verified_lat is not None and verified_lng is not None:
            if verified_geocode_level in ("EXACT_PIN", "ROOFTOP_VERIFIED"):
                resolved_lat = float(verified_lat)
                resolved_lng = float(verified_lng)
                evidence.append(f"VERIFIED_{verified_geocode_level}")
            else:
                issues.add("UNVERIFIED_GEOCODE")

        # 8. Mutually Exclusive LocationPrecision Classification (Section 7)
        has_subdistrict_ward = bool(
            resolved_ward_historical
            or resolved_ward_nq1251
            or ("TEXT_POST2025_UNIT_ONLY" in evidence and resolved_unit_nq1659 != "Phường Ngũ Hành Sơn")
        )
        if resolved_district is None or district_conflict or "NON_RESIDENTIAL_SPECIAL_TERRITORY" in issues:
            precision = "UNKNOWN"
            if not reasons:
                reasons.append("Không xác định được quận/huyện cư trú hợp lệ tại Đà Nẵng.")
        elif resolved_lat is not None and resolved_lng is not None and verified_geocode_level == "EXACT_PIN":
            precision = "EXACT"
            reasons.append("Có tọa độ GPS bất động sản xác thực từ nguồn tin cậy.")
        elif resolved_lat is not None and resolved_lng is not None and verified_geocode_level == "ROOFTOP_VERIFIED":
            precision = "HIGH"
            reasons.append("Có địa chỉ chi tiết và tọa độ geocoding cấp tòa nhà/số nhà đã đối chiếu.")
        elif normalized_street and not street_conflict:
            precision = "STREET"
            if house_number:
                reasons.append(
                    f"Xác định được số nhà/ngách '{house_number}' trên đường '{normalized_street}' ({resolved_district}), nhưng chưa có tọa độ GPS xác thực."
                )
            elif alley_number:
                reasons.append(
                    f"Xác định được kiệt/hẻm '{alley_number}' đường '{normalized_street}' ({resolved_district}), chưa xác định tọa độ căn nhà."
                )
            else:
                reasons.append(
                    f"Xác định được tên đường '{normalized_street}' ({resolved_district}), thiếu số nhà/tọa độ chính xác."
                )
        elif has_subdistrict_ward and not ward_conflict:
            precision = "WARD"
            w_label = resolved_ward_historical or resolved_ward_nq1251 or resolved_unit_nq1659
            reasons.append(f"Chỉ xác định tin cậy đến cấp phường/xã '{w_label}' ({resolved_district}), thiếu tên đường/số nhà.")
        else:
            precision = "DISTRICT"
            reasons.append(f"Chỉ xác định tin cậy đến cấp quận/huyện '{resolved_district}', thiếu phường/xã và tên đường.")

        # 9. Address-Level Geocoding Potential (`isAddressGeocodeCandidate` — Section 12 #14)
        # Strict definition: ONLY records with specific houseNumber+street+district OR verified building-scale apartment/tower project!
        is_building_project = bool(
            matched_project
            and self.projects_meta.get(matched_project, {}).get("isBuildingScale", False)
            and prop_type == "APARTMENT"
        )
        is_address_geocode_candidate = bool(
            precision in ("EXACT", "HIGH")
            or (precision == "STREET" and house_number is not None)
            or (precision in ("STREET", "WARD") and is_building_project)
        )
        geocode_candidate_tier = (
            "HOUSE_NUMBER_ON_STREET"
            if (precision == "STREET" and house_number is not None)
            else ("BUILDING_TOWER_PROJECT" if (precision in ("STREET", "WARD") and is_building_project) else "NONE")
        )

        # 10. Location Intelligence & Distance/Amenity Capability (Section 11 & 13)
        can_calculate_property_distance = precision in ("EXACT", "HIGH") and resolved_lat is not None and resolved_lng is not None
        can_analyze_area_amenities = precision in ("EXACT", "HIGH", "STREET", "WARD", "DISTRICT")
        if can_calculate_property_distance:
            amenity_capability = "PROPERTY_LEVEL"
            amenity_granularity = "EXACT_RADIUS_METERS"
        elif precision in ("STREET", "WARD"):
            amenity_capability = "AREA_LEVEL"
            amenity_granularity = "WARD_OR_STREET_AREA"
        elif precision == "DISTRICT":
            amenity_capability = "AREA_LEVEL"
            amenity_granularity = "DISTRICT_MACRO_ONLY"
        else:
            amenity_capability = "INSUFFICIENT_DATA"
            amenity_granularity = "NONE"

        # 11. Independent Location Confidence Score (`[0.00, 1.00]`, Section 8)
        confidence = self._compute_confidence(
            precision=precision,
            province_valid=province_valid,
            evidence=evidence,
            issues=issues,
            house_number=house_number,
            alley_number=alley_number,
            plot_code=plot_code,
            matched_project=matched_project,
            normalized_street=normalized_street,
            resolved_district=resolved_district,
            has_verified_gps=can_calculate_property_distance,
        )

        return {
            "internalId": internal_id,
            "propertyType": prop_type,
            "locationPrecision": precision,
            "locationConfidence": confidence,
            "originalProvince": orig_province,
            "originalDistrict": orig_district,
            "originalWard": orig_ward,
            "originalStreet": orig_street,
            "originalProject": orig_project,
            "resolvedDistrictHistorical": resolved_district,
            "resolvedWardHistorical": resolved_ward_historical,
            "resolvedWardNq1251": resolved_ward_nq1251,
            "resolvedUnitNq1659": resolved_unit_nq1659,
            "adminMappingVersion": self.mapping_version,
            "normalizedStreet": normalized_street,
            "houseNumber": house_number,
            "alleyNumber": alley_number,
            "plotCode": plot_code,
            "matchedProject": matched_project,
            "resolvedLatitude": resolved_lat,
            "resolvedLongitude": resolved_lng,
            "isAddressGeocodeCandidate": is_address_geocode_candidate,
            "geocodeCandidateTier": geocode_candidate_tier,
            "canCalculatePropertyDistance": can_calculate_property_distance,
            "canAnalyzeAreaAmenities": can_analyze_area_amenities,
            "amenityCapability": amenity_capability,
            "amenityGranularity": amenity_granularity,
            "locationEvidence": evidence,
            "locationIssues": sorted(issues),
            "classificationReason": " ".join(reasons),
            "qualityStatus": quality_status,
            "qualityRuleVersion": quality_rule_version,
        }

    def _is_street_compatible_with_district(self, canonical_street: str, district: str) -> bool:
        s_meta = self.streets_meta.get(canonical_street)
        if not s_meta:
            m_stem = re.match(r"^(.+?)\s+(\d{1,2})$", canonical_street)
            if m_stem:
                stem_toks = tuple(self._tokenize_words(m_stem.group(1).lower()))
                if stem_toks in self.numbered_street_stems:
                    _, stem_dists = self.numbered_street_stems[stem_toks]
                    return (not stem_dists) or (district in stem_dists) or (sum(stem_dists.values()) < 5)
            return True  # Rare/unindexed street in structured column: do not reject without contrary evidence
        dist_counts = s_meta.get("districts", {})
        if not dist_counts or district in dist_counts:
            return True
        # Allow low-frequency border streets (<5 total occurrences), flag clear cross-city mismatches (>=5 in other districts, 0 here)
        total_other = sum(dist_counts.values())
        return total_other < 5

    def _compute_confidence(
        self,
        precision: str,
        province_valid: bool,
        evidence: list[str],
        issues: set[str],
        house_number: str | None,
        alley_number: str | None,
        plot_code: str | None,
        matched_project: str | None,
        normalized_street: str | None,
        resolved_district: str | None,
        has_verified_gps: bool,
    ) -> float:
        if "NON_RESIDENTIAL_SPECIAL_TERRITORY" in issues or precision == "UNKNOWN":
            return 0.05 if province_valid else 0.00

        score = 0.0
        ev_set = set(evidence)
        if province_valid:
            score += CONFIDENCE_WEIGHTS["STRUCTURED_PROVINCE_VALID"]
        if "STRUCTURED_DISTRICT" in ev_set:
            score += CONFIDENCE_WEIGHTS["STRUCTURED_DISTRICT_VALID"]
        elif "TEXT_RECOVERED_DISTRICT" in ev_set:
            score += 0.12

        if "STRUCTURED_WARD" in ev_set:
            score += CONFIDENCE_WEIGHTS["STRUCTURED_WARD_VALID"]
        elif "TEXT_RECOVERED_WARD" in ev_set:
            score += CONFIDENCE_WEIGHTS["TEXT_RECOVERED_WARD"]

        if normalized_street:
            if "STRUCTURED_STREET" in ev_set:
                score += CONFIDENCE_WEIGHTS["STRUCTURED_STREET_VALID"]
            else:
                score += CONFIDENCE_WEIGHTS["TEXT_RECOVERED_STREET"]
            if resolved_district and canonical_attested(self.streets_meta, normalized_street, resolved_district):
                score += CONFIDENCE_WEIGHTS["STREET_ATTESTED_IN_DISTRICT"]

        if any(e in ev_set for e in ("TEXT_TITLE_STREET", "TEXT_CORROBORATED_WARD", "TEXT_CORROBORATED_DISTRICT", "TEXT_CORROBORATED_PROJECT")):
            score += CONFIDENCE_WEIGHTS["TITLE_CATEGORY_A_CORROBORATED"]
        if "TEXT_DESC_STREET" in ev_set:
            score += CONFIDENCE_WEIGHTS["DESC_CATEGORY_A_CORROBORATED"]

        if house_number:
            score += CONFIDENCE_WEIGHTS["EXPLICIT_HOUSE_NUMBER"]
        elif alley_number or plot_code:
            score += CONFIDENCE_WEIGHTS["ALLEY_OR_PLOT_DETAIL"]

        if matched_project:
            score += CONFIDENCE_WEIGHTS["VERIFIED_PROJECT_MATCH"]

        if "NEEDS_MAPPING" in issues:
            score += CONFIDENCE_WEIGHTS["PENALTY_NEEDS_MAPPING"]
        if "LOCATION_FROM_MARKETING_TEXT" in issues:
            score += CONFIDENCE_WEIGHTS["PENALTY_LOCATION_FROM_MARKETING"]
        if "SOURCE_LOCATION_INCONSISTENT" in issues:
            score += CONFIDENCE_WEIGHTS["PENALTY_SOURCE_INCONSISTENT"]
        if "AMBIGUOUS_LOCATION" in issues:
            score += CONFIDENCE_WEIGHTS["PENALTY_AMBIGUOUS_LOCATION"]
        if "ADDRESS_CONFLICT" in issues:
            score += CONFIDENCE_WEIGHTS["PENALTY_ADDRESS_CONFLICT"]

        cap = 1.00 if has_verified_gps else CONFIDENCE_WEIGHTS["MAX_WITHOUT_VERIFIED_GPS"]
        return round(max(0.00, min(cap, score)), 2)


def canonical_attested(streets_meta: dict[str, dict[str, Any]], street: str, district: str) -> bool:
    meta = streets_meta.get(street)
    return bool(meta and meta.get("districts", {}).get(district, 0) > 0)


# ---------------------------------------------------------------------------
# Read-Only MySQL Batch Reader (zero raw_payload in RAM, zero N+1 queries)
# ---------------------------------------------------------------------------

def open_readonly_mysql_connection() -> pymysql.connections.Connection:
    spec = importlib.util.spec_from_file_location("rec", SCRIPT_DIR / "run-recommendation-local.py")
    rec = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(rec)
    priv = rec.private_environment()
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user=priv["DB_USER"],
        password=priv["DB_PASSWORD"],
        database="smartprop",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    for secret_k in ("DB_USER", "DB_PASSWORD", "JWT_SECRET"):
        priv.pop(secret_k, None)
    with conn.cursor() as cur:
        sql = "SET SESSION TRANSACTION READ ONLY"
        assert_readonly_sql(sql)
        cur.execute(sql)
    return conn


def fetch_tinix_probe_and_ids(conn: pymysql.connections.Connection) -> tuple[dict[str, Any], set[str], list[str]]:
    with conn.cursor() as cur:
        probe_sql = """
            SELECT COUNT(*) AS total_cnt,
                   COALESCE(BIT_XOR(CRC32(CONCAT_WS('|',internal_id,price_vnd))),0) AS fp
            FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)
            WHERE quality_status='HYBRID_ELIGIBLE_RESEARCH'
              AND is_duplicate_representative=1
              AND is_protected_holdout=0
              AND transaction_type='SALE'
              AND price_vnd>0
        """
        assert_readonly_sql(probe_sql)
        cur.execute(probe_sql)
        probe = cur.fetchone() or {}

        held_sql = """
            SELECT DISTINCT h.duplicate_group
            FROM tinix_dataset_records h FORCE INDEX (ix_tinix_hybrid)
            WHERE h.quality_status IN ('HYBRID_ELIGIBLE_RESEARCH','NEEDS_REVIEW','EXCLUDED')
              AND h.is_duplicate_representative IN (0,1)
              AND h.is_protected_holdout=1
        """
        assert_readonly_sql(held_sql)
        cur.execute(held_sql)
        held_groups = {r["duplicate_group"] for r in cur.fetchall()}

        ids_sql = """
            SELECT k.internal_id
            FROM tinix_dataset_records k FORCE INDEX (ix_tinix_hybrid)
            WHERE k.quality_status='HYBRID_ELIGIBLE_RESEARCH'
              AND k.is_duplicate_representative=1
              AND k.is_protected_holdout=0
              AND k.transaction_type='SALE'
              AND k.price_vnd>0
            ORDER BY k.internal_id
        """
        assert_readonly_sql(ids_sql)
        cur.execute(ids_sql)
        all_ids = [r["internal_id"] for r in cur.fetchall()]

    return (probe, held_groups, all_ids)


def iter_representative_batches(
    conn: pymysql.connections.Connection,
    target_ids: list[str],
    held_groups: set[str],
    batch_size: int = 2000,
):
    """Yield eligible representatives in contiguous PK batches without loading raw_payload."""
    with conn.cursor() as cur:
        for offset in range(0, len(target_ids), batch_size):
            chunk_ids = target_ids[offset : offset + batch_size]
            placeholders = ",".join(["%s"] * len(chunk_ids))
            batch_sql = f"""
                SELECT internal_id, name, description, province_name, district_name, ward_name,
                       street_name, project_name, normalized_type, district, ward,
                       floor_count, road_width, price_vnd, area_sqm,
                       quality_status, quality_rule_version, duplicate_group
                FROM tinix_dataset_records
                WHERE internal_id IN ({placeholders})
                  AND dataset_revision=%s
                  AND source_name='TINIX_AI'
                  AND quality_status='HYBRID_ELIGIBLE_RESEARCH'
                  AND JSON_LENGTH(quality_issues)=0
                  AND verification_status='UNVERIFIED'
                  AND research_only=1
                  AND listing_availability='UNKNOWN'
                  AND transaction_type='SALE'
                  AND transaction_basis='EXPLICIT_SALE_TEXT'
                  AND is_protected_holdout=0
                  AND is_duplicate_representative=1
                  AND price_vnd>0 AND area_sqm>0
                ORDER BY internal_id
            """
            assert_readonly_sql(batch_sql)
            cur.execute(batch_sql, [*chunk_ids, EXPECTED_REVISION])
            rows = [r for r in cur.fetchall() if r["duplicate_group"] not in held_groups]
            yield offset, rows


def run_pilot(output_dir: Path, sample_target: int = 1000) -> dict[str, Any]:
    """Run a stratified ~1,000-record pilot covering all property types, districts, and edge cases."""
    output_dir.mkdir(parents=True, exist_ok=True)
    resolver = TinixLocationResolver()
    conn = open_readonly_mysql_connection()
    t0 = time.perf_counter()
    try:
        _, held_groups, all_ids = fetch_tinix_probe_and_ids(conn)
        # Ensure Hoàng Sa record + contiguous diverse blocks across the PK space are included
        hoang_sa_id = "39d31d348d37ba9911f506dce085c896f687ecf1b93f1e61ad2904d7845a0cdf"
        selected_ids: list[str] = []
        # Pick 10 contiguous slices of 120 IDs across all_ids (~1,200 candidates) -> stratify down to `sample_target`
        step = max(1, len(all_ids) // 10)
        for i in range(10):
            start = min(i * step, max(0, len(all_ids) - 130))
            selected_ids.extend(all_ids[start : start + 125])
        if hoang_sa_id in set(all_ids) and hoang_sa_id not in selected_ids:
            selected_ids.append(hoang_sa_id)
        selected_ids = sorted(set(selected_ids))

        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for _, rows in iter_representative_batches(conn, selected_ids, held_groups, batch_size=500):
            for r in rows:
                res = resolver.resolve_record(r)
                candidates.append((r, res))

        # Ensure balanced coverage across HOUSE, LAND, APARTMENT, VILLA, all districts, conflicts, legacy names, ward-only, district-only
        picked: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        buckets = defaultdict(list)
        for r, res in candidates:
            buckets[f"type:{res['propertyType']}"].append((r, res))
            buckets[f"dist:{r.get('district_name') or 'NONE'}"].append((r, res))
            buckets[f"prec:{res['locationPrecision']}"].append((r, res))
            if res["houseNumber"]:
                buckets["feat:house"].append((r, res))
            if res["matchedProject"]:
                buckets["feat:project"].append((r, res))
            if res["locationIssues"]:
                buckets["feat:issues"].append((r, res))
            if "NEEDS_MAPPING" in res["locationIssues"] or "TEXT_DISAMBIGUATED_PRE2025_WARD" in res["locationEvidence"] or "TEXT_POST2025_UNIT_CONSISTENT" in res["locationEvidence"]:
                buckets["feat:mapping"].append((r, res))

        # Guarantee rare strata first
        for key, items in sorted(buckets.items(), key=lambda kv: len(kv[1])):
            for r, res in items[:45]:
                if len(picked) < sample_target:
                    picked[res["internalId"]] = (r, res)
        for r, res in candidates:
            if len(picked) >= sample_target:
                break
            picked[res["internalId"]] = (r, res)

        pilot_rows = list(picked.values())
    finally:
        conn.close()

    elapsed = time.perf_counter() - t0
    prec_counts = Counter(res["locationPrecision"] for _, res in pilot_rows)
    type_counts = Counter(res["propertyType"] for _, res in pilot_rows)
    dist_counts = Counter((r.get("district_name") or "NULL") for r, _ in pilot_rows)
    issue_counts = Counter(iss for _, res in pilot_rows for iss in res["locationIssues"])

    audit_samples = []
    seen_audit = set()
    audit_strata = [
        ("HOUSE_NUMBER", lambda r, res: res["houseNumber"] is not None),
        ("ALLEY_ONLY", lambda r, res: res["alleyNumber"] is not None and res["houseNumber"] is None),
        ("STREET_NO_HOUSE", lambda r, res: res["locationPrecision"] == "STREET" and not res["houseNumber"] and not res["alleyNumber"]),
        ("PROJECT_MATCHED", lambda r, res: res["matchedProject"] is not None),
        ("WARD_ONLY", lambda r, res: res["locationPrecision"] == "WARD"),
        ("DISTRICT_ONLY", lambda r, res: res["locationPrecision"] == "DISTRICT"),
        ("MARKETING_REJECTED", lambda r, res: "LOCATION_FROM_MARKETING_TEXT" in res["locationIssues"]),
        ("CONFLICT_OR_INCONSISTENT", lambda r, res: "ADDRESS_CONFLICT" in res["locationIssues"] or "SOURCE_LOCATION_INCONSISTENT" in res["locationIssues"]),
        ("NEEDS_MAPPING", lambda r, res: "NEEDS_MAPPING" in res["locationIssues"]),
        ("UNKNOWN", lambda r, res: res["locationPrecision"] == "UNKNOWN"),
    ]
    for label, pred in audit_strata:
        cnt = 0
        for r, res in pilot_rows:
            if res["internalId"] not in seen_audit and pred(r, res):
                seen_audit.add(res["internalId"])
                audit_samples.append({
                    "stratum": label,
                    "internalId": res["internalId"],
                    "title": redact_pii((r.get("name") or "")[:160]),
                    "descriptionSnippet": redact_pii((r.get("description") or "")[:220].replace("\n", " ")),
                    "origDistrict": r.get("district_name"),
                    "origWard": r.get("ward_name"),
                    "origStreet": r.get("street_name"),
                    "origProject": r.get("project_name"),
                    "precision": res["locationPrecision"],
                    "confidence": res["locationConfidence"],
                    "normalizedStreet": res["normalizedStreet"],
                    "houseNumber": res["houseNumber"],
                    "alleyNumber": res["alleyNumber"],
                    "matchedProject": res["matchedProject"],
                    "resolvedWardHistorical": res["resolvedWardHistorical"],
                    "resolvedUnitNq1659": res["resolvedUnitNq1659"],
                    "issues": res["locationIssues"],
                    "evidence": res["locationEvidence"],
                    "reason": redact_pii(res["classificationReason"]),
                })
                cnt += 1
                if cnt >= 6:
                    break

    pilot_summary = {
        "pilotCount": len(pilot_rows),
        "elapsedSeconds": round(elapsed, 3),
        "precisionCounts": dict(prec_counts),
        "propertyTypeCounts": dict(type_counts),
        "districtCounts": dict(dist_counts),
        "issueCounts": dict(issue_counts),
        "hasHouseNumber": sum(1 for _, res in pilot_rows if res["houseNumber"]),
        "hasNormalizedStreet": sum(1 for _, res in pilot_rows if res["normalizedStreet"]),
        "hasMatchedProject": sum(1 for _, res in pilot_rows if res["matchedProject"]),
        "auditSampleCount": len(audit_samples),
        "auditSamples": audit_samples,
    }
    (output_dir / "pilot_1000_summary.json").write_text(
        json.dumps(pilot_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[PILOT] Processed {len(pilot_rows)} stratified representatives in {elapsed:.2f}s | Precision: {dict(prec_counts)}",
        flush=True,
    )
    return pilot_summary


def run_full_dataset(output_dir: Path, batch_size: int = 2000) -> dict[str, Any]:
    """Process all 55,816 eligible TiniX representatives in read-only contiguous batches and write CSV/JSONL outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    t_start = time.perf_counter()

    resolver = TinixLocationResolver()
    conn = open_readonly_mysql_connection()

    jsonl_path = output_dir / "tinix_location_resolution_55816.jsonl"
    tmp_jsonl_path = output_dir / "tinix_location_resolution_55816.jsonl.tmp"

    precision_counts: Counter[str] = Counter()
    by_district: dict[str, Counter[str]] = defaultdict(Counter)
    by_prop_type: dict[str, Counter[str]] = defaultdict(Counter)
    by_dist_and_type: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    issue_counts: Counter[str] = Counter()
    conflict_combos: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()
    granularity_counts: Counter[str] = Counter()
    geocode_tier_counts: Counter[str] = Counter()
    nq1659_counts: Counter[str] = Counter()

    stats_counters = Counter()
    confidence_sum_by_prec: defaultdict[str, float] = defaultdict(float)
    samples_by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)

    try:
        probe_before, held_groups, all_ids = fetch_tinix_probe_and_ids(conn)
        print(
            f"[FULL-RUN] Starting read-only batch analysis on {len(all_ids)} index candidates "
            f"(excluding {len(held_groups)} held duplicate groups)...",
            flush=True,
        )

        total_processed = 0
        with tmp_jsonl_path.open("w", encoding="utf-8") as jf:
            for offset, rows in iter_representative_batches(conn, all_ids, held_groups, batch_size=batch_size):
                for r in rows:
                    res = resolver.resolve_record(r)
                    total_processed += 1

                    prec = res["locationPrecision"]
                    d_key = res["resolvedDistrictHistorical"] or f"UNRESOLVED({r.get('district_name') or 'NULL'})"
                    t_key = res["propertyType"] or "UNKNOWN"

                    precision_counts[prec] += 1
                    by_district[d_key][prec] += 1
                    by_district[d_key]["TOTAL"] += 1
                    by_prop_type[t_key][prec] += 1
                    by_prop_type[t_key]["TOTAL"] += 1
                    by_dist_and_type[(d_key, t_key)][prec] += 1
                    by_dist_and_type[(d_key, t_key)]["TOTAL"] += 1

                    confidence_sum_by_prec[prec] += res["locationConfidence"]
                    capability_counts[res["amenityCapability"]] += 1
                    granularity_counts[res["amenityGranularity"]] += 1
                    geocode_tier_counts[res["geocodeCandidateTier"]] += 1
                    nq1659_counts[res["resolvedUnitNq1659"] or "UNMAPPED_OR_SPLIT"] += 1

                    if res["originalStreet"]:
                        stats_counters["orig_has_street"] += 1
                    if res["originalProject"]:
                        stats_counters["orig_has_project"] += 1
                    if res["originalWard"]:
                        stats_counters["orig_has_ward"] += 1
                    if res["houseNumber"]:
                        stats_counters["has_house_number"] += 1
                        by_district[d_key]["HAS_HOUSE"] += 1
                        by_prop_type[t_key]["HAS_HOUSE"] += 1
                    if res["alleyNumber"]:
                        stats_counters["has_alley_number"] += 1
                    if res["plotCode"]:
                        stats_counters["has_plot_code"] += 1
                    if res["normalizedStreet"]:
                        stats_counters["has_normalized_street"] += 1
                        by_district[d_key]["HAS_STREET"] += 1
                        by_prop_type[t_key]["HAS_STREET"] += 1
                    if res["matchedProject"]:
                        stats_counters["has_matched_project"] += 1
                        by_district[d_key]["HAS_PROJECT"] += 1
                        by_prop_type[t_key]["HAS_PROJECT"] += 1
                    if prec in ("WARD", "DISTRICT"):
                        stats_counters["ward_or_district_only"] += 1
                    if res["isAddressGeocodeCandidate"]:
                        stats_counters["address_geocode_candidates"] += 1
                        by_district[d_key]["GEOCODE_CANDIDATE"] += 1
                        by_prop_type[t_key]["GEOCODE_CANDIDATE"] += 1
                    if res["canCalculatePropertyDistance"]:
                        stats_counters["can_calculate_property_distance"] += 1
                    if res["canAnalyzeAreaAmenities"]:
                        stats_counters["can_analyze_area_amenities"] += 1
                    else:
                        stats_counters["cannot_analyze_amenities"] += 1

                    for ev in res["locationEvidence"]:
                        evidence_counts[ev] += 1
                    for iss in res["locationIssues"]:
                        issue_counts[iss] += 1

                    conflict_flags = [
                        iss
                        for iss in res["locationIssues"]
                        if iss in ("ADDRESS_CONFLICT", "AMBIGUOUS_LOCATION", "SOURCE_LOCATION_INCONSISTENT", "LOCATION_FROM_MARKETING_TEXT", "NON_RESIDENTIAL_SPECIAL_TERRITORY")
                    ]
                    if conflict_flags:
                        stats_counters["any_conflict_or_inconsistency"] += 1
                        combo_key = "+".join(sorted(conflict_flags))
                        conflict_combos[f"{combo_key}|{prec}"] += 1
                    if "ADDRESS_CONFLICT" in res["locationIssues"]:
                        stats_counters["strict_address_conflict"] += 1
                        by_district[d_key]["ADDRESS_CONFLICT"] += 1
                    if "NEEDS_MAPPING" in res["locationIssues"]:
                        stats_counters["needs_mapping"] += 1
                        by_district[d_key]["NEEDS_MAPPING"] += 1

                    # Collect clean, PII-redacted samples across buckets for location_resolution_samples.csv
                    bucket_keys = [prec]
                    if res["houseNumber"]:
                        bucket_keys.append("HOUSE_NUMBER")
                    if "ADDRESS_CONFLICT" in res["locationIssues"]:
                        bucket_keys.append("ADDRESS_CONFLICT")
                    if "LOCATION_FROM_MARKETING_TEXT" in res["locationIssues"]:
                        bucket_keys.append("MARKETING_FILTERED")
                    if "NEEDS_MAPPING" in res["locationIssues"]:
                        bucket_keys.append("NEEDS_MAPPING")
                    for bk in bucket_keys:
                        if len(samples_by_bucket[bk]) < 12:
                            samples_by_bucket[bk].append({
                                "sampleCategory": bk,
                                "internalId": res["internalId"],
                                "propertyType": res["propertyType"],
                                "locationPrecision": res["locationPrecision"],
                                "locationConfidence": f"{res['locationConfidence']:.2f}",
                                "originalDistrict": res["originalDistrict"] or "",
                                "originalWard": res["originalWard"] or "",
                                "originalStreet": res["originalStreet"] or "",
                                "originalProject": res["originalProject"] or "",
                                "resolvedDistrictHistorical": res["resolvedDistrictHistorical"] or "",
                                "resolvedWardHistorical": res["resolvedWardHistorical"] or "",
                                "resolvedWardNq1251": res["resolvedWardNq1251"] or "",
                                "resolvedUnitNq1659": res["resolvedUnitNq1659"] or "",
                                "normalizedStreet": res["normalizedStreet"] or "",
                                "houseNumber": res["houseNumber"] or "",
                                "alleyNumber": res["alleyNumber"] or "",
                                "matchedProject": res["matchedProject"] or "",
                                "isAddressGeocodeCandidate": str(res["isAddressGeocodeCandidate"]).lower(),
                                "canCalculatePropertyDistance": str(res["canCalculatePropertyDistance"]).lower(),
                                "amenityCapability": res["amenityCapability"],
                                "locationIssues": ";".join(res["locationIssues"]),
                                "locationEvidence": ";".join(res["locationEvidence"]),
                                "sanitizedTitle": redact_pii((r.get("name") or "")[:140].replace("\n", " ")),
                                "classificationReason": redact_pii(res["classificationReason"]),
                            })

                    # Write sanitized per-record JSONL (no raw title/description/PII needed in bulk JSONL)
                    sanitized_res = {**res, "classificationReason": redact_pii(res["classificationReason"])}
                    jf.write(json.dumps(sanitized_res, ensure_ascii=False) + "\n")

                if total_processed % 10000 < batch_size or total_processed == EXPECTED_REPRESENTATIVE_COUNT:
                    dt = time.perf_counter() - t_start
                    print(
                        f"[FULL-RUN] Progress: {total_processed:,}/{EXPECTED_REPRESENTATIVE_COUNT:,} "
                        f"({100.0 * total_processed / EXPECTED_REPRESENTATIVE_COUNT:.1f}%) in {dt:.1f}s "
                        f"| Precision so far: {dict(precision_counts)}",
                        flush=True,
                    )

        # Verify MySQL replay fingerprint is 100% untouched after run!
        probe_after, _, _ = fetch_tinix_probe_and_ids(conn)
        assert probe_before == probe_after, f"MySQL probe changed unexpectedly: {probe_before} vs {probe_after}"
    finally:
        conn.close()

    # Atomic replace of JSONL file so reruns never duplicate data
    if jsonl_path.exists():
        jsonl_path.unlink()
    tmp_jsonl_path.replace(jsonl_path)

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total_seconds = time.perf_counter() - t_start

    precision_sum = sum(precision_counts[p] for p in PRECISION_ORDER)
    if total_processed != EXPECTED_REPRESENTATIVE_COUNT or precision_sum != total_processed:
        raise RuntimeError(
            f"Precision count invariant failed: processed={total_processed}, precision_sum={precision_sum}"
        )

    # Count per-precision geocode candidates directly from JSONL output
    geo_by_prec: Counter[str] = Counter()
    with jsonl_path.open("r", encoding="utf-8") as jf:
        for line in jf:
            obj = json.loads(line)
            if obj["isAddressGeocodeCandidate"]:
                geo_by_prec[obj["locationPrecision"]] += 1

    # Write CSV 1: location_precision_summary.csv
    with (output_dir / "location_precision_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "location_precision", "record_count", "percentage", "avg_confidence",
            "can_calculate_property_distance_count", "can_analyze_area_amenities_count",
            "amenity_capability", "address_geocode_candidate_count",
        ])
        for p in PRECISION_ORDER:
            cnt = precision_counts[p]
            pct = (100.0 * cnt / total_processed) if total_processed else 0.0
            avg_c = (confidence_sum_by_prec[p] / cnt) if cnt else 0.0
            dist_cnt = cnt if p in ("EXACT", "HIGH") else 0
            area_cnt = cnt if p in ("EXACT", "HIGH", "STREET", "WARD", "DISTRICT") else 0
            cap_label = (
                "PROPERTY_LEVEL" if p in ("EXACT", "HIGH")
                else ("AREA_LEVEL" if p in ("STREET", "WARD", "DISTRICT") else "INSUFFICIENT_DATA")
            )
            w.writerow([p, cnt, f"{pct:.4f}", f"{avg_c:.4f}", dist_cnt, area_cnt, cap_label, geo_by_prec[p]])
        w.writerow([
            "TOTAL", total_processed, "100.0000",
            f"{sum(confidence_sum_by_prec.values()) / total_processed:.4f}",
            stats_counters["can_calculate_property_distance"],
            stats_counters["can_analyze_area_amenities"],
            "ALL",
            stats_counters["address_geocode_candidates"],
        ])

    # Write CSV 2: location_precision_by_district.csv
    with (output_dir / "location_precision_by_district.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "district_historical", "total_records", "percentage_of_dataset",
            "EXACT", "HIGH", "STREET", "WARD", "DISTRICT", "UNKNOWN",
            "has_house_number", "has_normalized_street", "has_matched_project",
            "address_geocode_candidates", "address_conflict_count", "needs_mapping_count",
        ])
        for d_key, c in sorted(by_district.items(), key=lambda x: -x[1]["TOTAL"]):
            tot = c["TOTAL"]
            w.writerow([
                d_key, tot, f"{100.0 * tot / total_processed:.4f}",
                c["EXACT"], c["HIGH"], c["STREET"], c["WARD"], c["DISTRICT"], c["UNKNOWN"],
                c["HAS_HOUSE"], c["HAS_STREET"], c["HAS_PROJECT"],
                c["GEOCODE_CANDIDATE"], c["ADDRESS_CONFLICT"], c["NEEDS_MAPPING"],
            ])

    # Write CSV 3: location_precision_by_property_type.csv
    with (output_dir / "location_precision_by_property_type.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "property_type", "total_records", "percentage_of_dataset",
            "EXACT", "HIGH", "STREET", "WARD", "DISTRICT", "UNKNOWN",
            "has_house_number", "has_normalized_street", "has_matched_project",
            "address_geocode_candidates",
        ])
        for t_key, c in sorted(by_prop_type.items(), key=lambda x: -x[1]["TOTAL"]):
            tot = c["TOTAL"]
            w.writerow([
                t_key, tot, f"{100.0 * tot / total_processed:.4f}",
                c["EXACT"], c["HIGH"], c["STREET"], c["WARD"], c["DISTRICT"], c["UNKNOWN"],
                c["HAS_HOUSE"], c["HAS_STREET"], c["HAS_PROJECT"], c["GEOCODE_CANDIDATE"],
            ])

    # Write CSV 4: address_conflict_summary.csv
    with (output_dir / "address_conflict_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category_type", "issue_or_combination", "resulting_precision", "record_count", "percentage_of_dataset"])
        for iss_name, cnt in sorted(issue_counts.items(), key=lambda x: -x[1]):
            w.writerow(["SINGLE_ISSUE_FLAG", iss_name, "ALL", cnt, f"{100.0 * cnt / total_processed:.4f}"])
        for combo_prec, cnt in sorted(conflict_combos.items(), key=lambda x: -x[1]):
            combo, prec_val = combo_prec.split("|", 1)
            w.writerow(["CONFLICT_COMBINATION", combo, prec_val, cnt, f"{100.0 * cnt / total_processed:.4f}"])

    # Write CSV 5: location_resolution_samples.csv (deduplicated across buckets)
    seen_sample_ids: set[str] = set()
    sample_rows_out: list[dict[str, Any]] = []
    for bk in ["HOUSE_NUMBER", "STREET", "WARD", "DISTRICT", "UNKNOWN", "ADDRESS_CONFLICT", "MARKETING_FILTERED", "NEEDS_MAPPING"]:
        for item in samples_by_bucket.get(bk, []):
            if item["internalId"] not in seen_sample_ids:
                seen_sample_ids.add(item["internalId"])
                sample_rows_out.append(item)
    if sample_rows_out:
        fieldnames = list(sample_rows_out[0].keys())
        with (output_dir / "location_resolution_samples.csv").open("w", encoding="utf-8", newline="") as f:
            dw = csv.DictWriter(f, fieldnames=fieldnames)
            dw.writeheader()
            dw.writerows(sample_rows_out)

    metrics = {
        "totalProcessed": total_processed,
        "precisionCounts": {p: precision_counts[p] for p in PRECISION_ORDER},
        "precisionSumCheck": precision_sum == total_processed == EXPECTED_REPRESENTATIVE_COUNT,
        "avgConfidenceByPrecision": {
            p: round(confidence_sum_by_prec[p] / precision_counts[p], 4) if precision_counts[p] else None
            for p in PRECISION_ORDER
        },
        "overallAvgConfidence": round(sum(confidence_sum_by_prec.values()) / total_processed, 4),
        "featureCounts": dict(stats_counters),
        "geocodeByPrecision": dict(geo_by_prec),
        "geocodeCandidateTiers": dict(geocode_tier_counts),
        "amenityCapabilityCounts": dict(capability_counts),
        "amenityGranularityCounts": dict(granularity_counts),
        "issueCounts": dict(issue_counts),
        "evidenceCounts": dict(evidence_counts),
        "nq1659UnitCounts": dict(nq1659_counts.most_common()),
        "byDistrict": {k: dict(v) for k, v in by_district.items()},
        "byPropertyType": {k: dict(v) for k, v in by_prop_type.items()},
        "byDistrictAndPropertyType": {f"{d}|{t}": dict(v) for (d, t), v in by_dist_and_type.items()},
        "runtimeStats": {
            "wallClockSeconds": round(total_seconds, 3),
            "rowsPerSecond": round(total_processed / total_seconds, 1),
            "batchSize": batch_size,
            "sqlBatchCount": (len(all_ids) + batch_size - 1) // batch_size,
            "peakTracemallocMiB": round(peak_mem / (1024 * 1024), 2),
            "mysqlReplayProbeBefore": probe_before,
            "mysqlReplayProbeAfter": probe_after,
            "mysqlImmutableVerified": probe_before == probe_after,
        },
        "mappingVersion": resolver.mapping_version,
        "catalogVersion": resolver.catalog_version,
    }
    (output_dir / "full_run_metrics_55816.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(
        f"[FULL-RUN COMPLETE] {total_processed:,} rows in {total_seconds:.2f}s "
        f"({metrics['runtimeStats']['rowsPerSecond']} rows/s, peak heap {metrics['runtimeStats']['peakTracemallocMiB']} MiB) "
        f"| Precision: {metrics['precisionCounts']}",
        flush=True,
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pilot = sub.add_parser("pilot", help="Run stratified ~1,000-record pilot from MySQL (READ ONLY)")
    p_pilot.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p_pilot.add_argument("--sample-size", type=int, default=1000)

    p_full = sub.add_parser("run-full", help="Run full 55,816-representative Location Resolution (READ ONLY)")
    p_full.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p_full.add_argument("--batch-size", type=int, default=2000)

    args = parser.parse_args()
    if args.cmd == "pilot":
        run_pilot(args.output_dir, sample_target=args.sample_size)
    elif args.cmd == "run-full":
        run_full_dataset(args.output_dir, batch_size=args.batch_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
