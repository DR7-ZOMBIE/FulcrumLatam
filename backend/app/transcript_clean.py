"""Normalize raw transcript files (e.g. copy-paste from email) into dialogue text."""

import re

MARKER = "Synthetic Transcript"


def extract_transcript_text(raw: str) -> str:
    """Drop email/UI noise when present; keep from meeting marker or first timestamp."""
    if MARKER in raw:
        idx = raw.index(MARKER)
        raw = raw[idx:]
    # Fallback: first [MM:SS] or [HH:MM:SS] line
    m = re.search(r"\[\d{1,2}:\d{2}\]", raw)
    if m and m.start() > 0:
        raw = raw[m.start() :]
    return raw.strip()


def looks_like_timestamped_transcript(text: str) -> bool:
    return bool(re.search(r"\[\d{1,2}:\d{2}\]\s*\w+:", text[:5000]))
