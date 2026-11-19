"""YOLOv8 object detection for property images.

This package is deliberately separate from ``app.imagecheck``: duplicate-image
detection answers "has this photo been used before?", while this module answers
"what furniture and fixtures are visible in this photo?". They share no state,
no model and no index, so a failure in one cannot degrade the other.

Third-party component
---------------------
Detection is performed by Ultralytics YOLOv8 (``ultralytics`` 8.4.212) using the
stock COCO-pretrained ``yolov8n.pt`` checkpoint. No retraining or fine-tuning is
involved; the model is used exactly as published.

License: **AGPL-3.0** — https://github.com/ultralytics/ultralytics

SmartProp uses this component for a graduation project (study, research, and
demonstration to an academic panel). That scope does not remove the AGPL
obligations; it only means they are not currently triggered, because the system
is not distributed and not offered as a public network service. See
``ai-services/docs/YOLOV8_LICENSE_NOTICE.md`` for the full record, including what
would trigger compliance and which parts of this repository would form the
Corresponding Source.
"""
