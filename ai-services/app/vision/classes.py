"""Property-relevant COCO classes that YOLOv8n can actually detect.

The pretrained ``yolov8n.pt`` checkpoint is trained on COCO's 80 classes. Only a
subset of those is meaningful for a real-estate photo, so this module is the
single allowlist the detector filters against.

Two rules matter here:

1. **Never invent a class.** COCO has no ``bathtub``, ``wardrobe``, ``shower``,
   ``air conditioner`` or ``balcony`` class. A property photo containing those
   objects will simply not report them. Adding a label here without a matching
   COCO id would produce detections the model cannot support.
2. **Never relabel silently.** ``microwave`` and ``oven`` are distinct COCO
   classes; they share a display group but keep their own names so a reviewer
   can tell which one the model actually saw.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyClass:
    """One COCO class that is meaningful in a property photo."""

    coco_id: int
    coco_name: str
    label_vi: str
    group: str


# Ordered by how often the object appears in a listing photo, not by COCO id.
PROPERTY_CLASSES: tuple[PropertyClass, ...] = (
    PropertyClass(59, "bed", "Giường", "bedroom"),
    PropertyClass(57, "couch", "Ghế sofa", "living"),
    PropertyClass(56, "chair", "Ghế", "living"),
    PropertyClass(60, "dining table", "Bàn ăn", "living"),
    PropertyClass(62, "tv", "Tivi", "living"),
    PropertyClass(72, "refrigerator", "Tủ lạnh", "kitchen"),
    PropertyClass(68, "microwave", "Lò vi sóng", "kitchen"),
    PropertyClass(69, "oven", "Lò nướng", "kitchen"),
    PropertyClass(71, "sink", "Bồn rửa", "kitchen"),
    PropertyClass(61, "toilet", "Bồn cầu", "bathroom"),
    PropertyClass(58, "potted plant", "Cây cảnh", "decor"),
    PropertyClass(74, "clock", "Đồng hồ", "decor"),
    PropertyClass(75, "vase", "Bình hoa", "decor"),
)

BY_COCO_ID: dict[int, PropertyClass] = {item.coco_id: item for item in PROPERTY_CLASSES}
BY_COCO_NAME: dict[str, PropertyClass] = {item.coco_name: item for item in PROPERTY_CLASSES}

# COCO classes that exist but are deliberately excluded from property analysis.
# Kept explicit so a reviewer can see the decision rather than guess at it.
EXCLUDED_COCO_NAMES: tuple[str, ...] = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "toaster", "book", "scissors", "teddy bear",
    "hair drier", "toothbrush",
)

# Objects a property reviewer will look for that COCO simply cannot report.
# Surfaced in the API response so the UI never implies a silent "not found".
UNSUPPORTED_PROPERTY_OBJECTS: tuple[str, ...] = (
    "Bồn tắm", "Vòi sen", "Tủ quần áo", "Điều hoà", "Ban công", "Cầu thang",
    "Cửa sổ", "Sàn nhà", "Trần nhà", "Mái nhà", "Hồ bơi", "Sân vườn",
)


def class_names() -> list[str]:
    """COCO names this service can report, in allowlist order."""
    return [item.coco_name for item in PROPERTY_CLASSES]


def label_for(coco_name: str) -> str:
    """Vietnamese label for an allowlisted COCO name, else the raw name."""
    item = BY_COCO_NAME.get(coco_name)
    return item.label_vi if item else coco_name


def group_for(coco_name: str) -> str:
    item = BY_COCO_NAME.get(coco_name)
    return item.group if item else "other"
