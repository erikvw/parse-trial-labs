from __future__ import annotations

import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

import pdfplumber

try:
    from django.utils.timezone import now as get_now
except ImportError:
    from datetime import UTC, datetime

    def get_now() -> datetime:
        return datetime.now(tz=UTC)

    def get_default_tz() -> ZoneInfo:
        return ZoneInfo("UTC")

else:
    from django.conf import settings

    def get_default_tz() -> ZoneInfo:
        """Read TIME_ZONE on use, not on import, so importing this
        module never requires configured Django settings.
        """
        return ZoneInfo(settings.TIME_ZONE)


def hash_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
