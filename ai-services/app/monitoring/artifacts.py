"""Read-only, bounded checks of release pins. The prediction loader stays separate."""

from enum import Enum
from hashlib import sha256
from pathlib import Path

from .schema import InvalidTelemetry, integer


class Integrity(str, Enum):
    VERIFIED = "verified"
    MISSING = "missing_file"
    MODEL_HASH = "hash_mismatch"
    FEATURE_SCHEMA = "schema_mismatch"
    CALIBRATION = "calibration_mismatch"
    MANIFEST = "manifest_mismatch"
    UNAVAILABLE = "unavailable"


FILES = (
    ("model.json", Integrity.MODEL_HASH),
    ("feature_schema.json", Integrity.FEATURE_SCHEMA),
    ("calibration.json", Integrity.CALIBRATION),
    ("artifact_manifest.json", Integrity.MANIFEST),
)
V13_PINS = (
    (28512676, "3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03"),
    (24257, "84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea"),
    (547, "17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645"),
    (1078, "419599ecbefbe24bbbc1754a0224a7c25747ac3a08827d4e14ea62a5e41f2dce"),
)


def verify_artifacts(directory, *, pins=V13_PINS):
    """For trusted release directories or disposable fixtures. Never runs on a request."""
    if (type(pins) is not tuple or len(pins) != len(FILES)
            or any(type(pin) is not tuple or len(pin) != 2 or not integer(pin[0], 32 * 1024 * 1024)
                   or not pin[0] or type(pin[1]) is not str or len(pin[1]) != 64
                   or any(c not in "0123456789abcdef" for c in pin[1]) for pin in pins)):
        raise InvalidTelemetry("invalid_artifact_pins")
    root = Path(directory)
    for (name, mismatch), (size, expected) in zip(FILES, pins):
        file = root / name
        try:
            if file.is_symlink() or not file.is_file():
                return Integrity.MISSING if not file.exists() else Integrity.UNAVAILABLE
            if file.stat().st_size != size:
                return mismatch
            digest = sha256()
            remaining = size
            with file.open("rb") as stream:
                while remaining:
                    chunk = stream.read(min(remaining, 64 * 1024))
                    if not chunk:
                        return mismatch
                    remaining -= len(chunk)
                    digest.update(chunk)
                if stream.read(1):
                    return mismatch
            if digest.hexdigest() != expected:
                return mismatch
        except FileNotFoundError:
            return Integrity.MISSING
        except OSError:
            return Integrity.UNAVAILABLE
    return Integrity.VERIFIED
