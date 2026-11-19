"""Destination state for the commute question, kept in the conversation context.

Nothing here is written to the profile. The workplace string never reaches this module
for saved accounts (the backend resolves it internally); for typed addresses it lives in
temporary guest memory or the account-owned durable checkpoint/history. It is
never echoed into public shared fields, URLs or model prompts.
"""
import re

from .intent import fold

ASK_SOURCE = "ASK_SOURCE"
AWAIT_ADDRESS = "AWAIT_ADDRESS"
PICK_CANDIDATE = "PICK_CANDIDATE"

SAVED_HINTS = re.compile(r"\b(?:dung|su dung|lay)\b.*\b(?:noi lam viec|cho lam|van phong)\b|\b(?:noi lam viec|cho lam) da luu\b")
NEW_HINTS = re.compile(r"\b(?:nhap|go|dien)\b.*\b(?:dia diem|dia chi|cho lam|noi lam viec)\b|\bdia diem khac\b")
SKIP_HINTS = re.compile(r"\b(?:bo qua|thoi|khong can|de sau)\b")
CONSENT_YES = re.compile(r"^\s*(?:dong y|duoc|ok|okay|u+k?|vang)\s*[.!]?\s*$")
WALK = re.compile(r"\b(?:di bo|walk)\b")
DRIVE = re.compile(r"\b(?:o to|xe hoi|drive|oto)\b")
ORDINAL = re.compile(r"^\s*(?:so\s*)?(\d{1,2})\s*$")


def wants_skip(question):
    return bool(SKIP_HINTS.search(fold(question)))


def wants_saved(question):
    return bool(SAVED_HINTS.search(fold(question)))


def wants_new(question):
    return bool(NEW_HINTS.search(fold(question)))


def is_plain_consent(question):
    return bool(CONSENT_YES.match(fold(question)))


def mode_for(question, current="drive"):
    text = fold(question)
    if WALK.search(text):
        return "walk"
    if DRIVE.search(text):
        return "drive"
    return current or "drive"


def candidate_index(question, count):
    """1-based pick from a numbered candidate list, or None.

    Accepts a bare number, "số 2", or the whole quick-reply label ("2. Some address").
    """
    text = fold(question)
    match = re.match(r"^\s*(?:so\s*)?(\d{1,2})(?:\s*[.):]|\s|$)", text)
    if match:
        value = int(match.group(1))
        return value if 1 <= value <= count else None
    if re.search(r"\b(?:cai )?(?:dau tien|thu nhat)\b", text):
        return 1
    if re.search(r"\bthu hai\b", text) and count >= 2:
        return 2
    if re.search(r"\bthu ba\b", text) and count >= 3:
        return 3
    return None


def address_from(question):
    """The typed address, when the message is more than a bare consent word."""
    text = (question or "").strip()
    if len(text) < 3 or is_plain_consent(text):
        return None
    # A message that only chooses an option is not an address.
    if wants_saved(text) or wants_new(text) or wants_skip(text):
        return None
    return text[:300]


def stage_of(state):
    return state.get("commuteStage")


def destination_of(state):
    value = state.get("commuteDestination")
    return value if isinstance(value, dict) else None
