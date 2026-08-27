from __future__ import annotations

import logging


class DuplicateTrackingHandler(logging.Handler):
    """Collects source files/tests flagged by parsers as having
    collapsed duplicates.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.duplicates: dict[str, set[str]] = {}

    def emit(self, record: logging.LogRecord) -> None:
        source_file = getattr(record, "source_file", None)
        source_utestid = getattr(record, "source_utestid", None)
        if source_file and source_utestid:
            self.duplicates.setdefault(source_file, set()).add(source_utestid)
