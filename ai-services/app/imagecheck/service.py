"""Image duplicate comparison and evidence-only classification."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .hashing import Fingerprint, cosine, fingerprint, hamming
from .index import ImageIndexUnavailable, IndexedImage, PublicImageIndex


MAX_RESULTS = 10


@dataclass(frozen=True)
class Match:
    image: IndexedImage
    similarity: float
    method: str
    classification: str
    dhash_distance: int
    phash_distance: int
    histogram_similarity: float
    layout_similarity: float


def _compare(query: Fingerprint, reference: IndexedImage, *, intra=False) -> Match | None:
    target = reference.fingerprint
    classification_prefix = "INTRA_" if intra else ""
    if query.sha256 == target.sha256:
        return Match(reference, 1.0, "SHA256",
                     classification_prefix + "EXACT_DUPLICATE", 0, 0, 1.0, 1.0)
    dh = hamming(query.dhash, target.dhash)
    ph = hamming(query.phash, target.phash)
    histogram = cosine(query.histogram, target.histogram)
    layout = cosine(query.layout, target.layout)
    if dh <= 6 or ph <= 8:
        classification, method = classification_prefix + "NEAR_DUPLICATE", "DHASH+PHASH"
    elif dh <= 12 or ph <= 16 or histogram >= 0.93 or layout >= 0.96:
        classification, method = classification_prefix + "SIMILAR", "PERCEPTUAL+COLOR_LAYOUT"
    else:
        return None
    similarity = (1.0 - (dh + ph) / 128.0) if "NEAR_DUPLICATE" in classification else max(
        1.0 - min(dh, ph) / 64.0, histogram, layout)
    return Match(reference, round(similarity, 4), method, classification,
                 dh, ph, round(histogram, 4), round(layout, 4))


class DuplicateImageService:
    def __init__(self, index: PublicImageIndex):
        self.index = index

    def check(self, data: bytes) -> dict[str, Any]:
        query = fingerprint(data)
        matches = [match for image in self.index.get() if (match := _compare(query, image))]
        matches.sort(key=lambda item: (-item.similarity, item.image.property_id, item.image.image_id))
        matches = matches[:MAX_RESULTS]
        exact = any(item.classification == "EXACT_DUPLICATE" for item in matches)
        near = any(item.classification == "NEAR_DUPLICATE" for item in matches)
        similar = bool(matches)
        status = "EXACT_DUPLICATE" if exact else "NEAR_DUPLICATE" if near else "SIMILAR" if similar else "NO_MATCH"
        return {
            "status": status,
            "matches": [_match(item) for item in matches],
            "query": {"sha256": query.sha256, "width": query.width, "height": query.height,
                      "format": query.format},
            "index": self.index.status(),
            "limitations": _limitations(),
        }

    def scan(self, property_id: str, images: list[tuple[str, bytes]]) -> dict[str, Any]:
        """Scan all images of one listing; exclude that listing from public matches."""
        if not property_id or not images:
            raise ValueError("INVALID_SCAN_INPUT")
        if len(images) > 30:
            raise ValueError("TOO_MANY_IMAGES")
        queries = [(image_id, fingerprint(data)) for image_id, data in images]
        current = [IndexedImage(property_id, image_id, None, None, None, None, "",
                                query) for image_id, query in queries]
        public = self.index.get(exclude_property_id=property_id)
        results = []
        for index, (image_id, query) in enumerate(queries):
            inter = [match for image in public if (match := _compare(query, image))]
            intra = []
            for other_index, other in enumerate(current):
                if other_index == index:
                    continue
                match = _compare(query, other, intra=True)
                if match:
                    intra.append(match)
            inter.sort(key=lambda item: (-item.similarity, item.image.property_id, item.image.image_id))
            intra.sort(key=lambda item: -item.similarity)
            matches = inter[:MAX_RESULTS]
            all_matches = matches + intra
            exact = any(item.classification.endswith("EXACT_DUPLICATE") for item in all_matches)
            near = any(item.classification.endswith("NEAR_DUPLICATE") for item in all_matches)
            if any(item.classification.startswith("INTRA_") for item in all_matches) and not matches:
                classification = "INTRA_DUPLICATE"
            else:
                classification = "EXACT_DUPLICATE" if exact else "NEAR_DUPLICATE" if near else "SIMILAR" if all_matches else "NONE"
            best = all_matches[0] if all_matches else None
            results.append({
                "imageId": image_id,
                "sha256": query.sha256,
                "width": query.width,
                "height": query.height,
                "format": query.format,
                "classification": classification,
                "similarity": best.similarity if best else None,
                "method": best.method if best else None,
                "matches": [_match(item) for item in matches],
                "intraMatches": [_match(item) for item in intra],
            })
        return {
            "status": "COMPLETED",
            "propertyId": property_id,
            "algorithmVersion": "imagecheck-v1",
            "images": results,
            "index": self.index.status(),
            "limitations": _limitations(),
        }


def _limitations():
    return [
        "Đây là so khớp ảnh nội bộ SmartProp, không phải kết luận ảnh bị đánh cắp.",
        "Chưa có reverse image search Internet; không tuyên bố đã quét toàn bộ web.",
        "Tier 3 dùng đặc trưng màu/bố cục, chưa dùng model ảnh pretrained do runtime không có torch/torchvision.",
    ]


def _match(item: Match) -> dict[str, Any]:
    image = item.image
    return {
        "propertyId": image.property_id,
        "listingCode": image.listing_code,
        "title": image.title,
        "location": " · ".join(value for value in (image.ward, image.district) if value),
        "imageId": image.image_id,
        "imageUrl": image.url,
        "listingUrl": f"/listing/{image.property_id}",
        "similarity": item.similarity,
        "classification": item.classification,
        "method": item.method,
        "evidence": {
            "dhashDistance": item.dhash_distance,
            "phashDistance": item.phash_distance,
            "histogramSimilarity": item.histogram_similarity,
            "layoutSimilarity": item.layout_similarity,
        },
    }
