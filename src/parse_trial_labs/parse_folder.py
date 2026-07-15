from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from tqdm import tqdm


class _DuplicateTrackingHandler(logging.Handler):
    """Collects source files/tests flagged by parsers as having collapsed duplicates."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.duplicates: dict[str, set[str]] = {}

    def emit(self, record: logging.LogRecord) -> None:
        source_file = getattr(record, "source_file", None)
        source_utestid = getattr(record, "source_utestid", None)
        if source_file and source_utestid:
            self.duplicates.setdefault(source_file, set()).add(source_utestid)


def parse_folder(
    folder: str | Path,
    parser_func: Callable[str | Path, ZoneInfo | None],
    *,
    tz: ZoneInfo | None = None,
    is_valid_identifier_func: Callable | None = None,
    verbose: bool = True,
    log_path: str | Path | None = None,
) -> pd.DataFrame:
    folder = Path(folder)
    pdf_file_paths = sorted(folder.glob("*.pdf"))
    all_rows: list[dict] = []

    log_path = (
        Path(log_path)
        if log_path
        else folder / f"parse_session_{datetime.now():%Y%m%d_%H%M%S}.log"  # noqa: DTZ005
    )
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    dup_handler = _DuplicateTrackingHandler()
    parsers_logger = logging.getLogger("parse_trial_labs.parsers")
    parsers_logger.addHandler(file_handler)
    parsers_logger.addHandler(dup_handler)

    iterator = (
        tqdm(pdf_file_paths, desc="Parsing PDFs", unit="file") if verbose else pdf_file_paths
    )
    try:
        for pdf_file_path in iterator:
            try:
                all_rows.extend(
                    parser_func(
                        pdf_file_path,
                        tz=tz,
                        is_valid_identifier_func=is_valid_identifier_func,
                    )
                )
            except Exception as exc:
                sys.stdout.write(f"WARNING: failed to parse {pdf_file_path.name}: {exc}\n")
    finally:
        parsers_logger.removeHandler(file_handler)
        parsers_logger.removeHandler(dup_handler)
        file_handler.close()

    if dup_handler.duplicates:
        with log_path.open("a") as fh:
            fh.write("\nFiles with duplicate results collapsed:\n")
            for source_file, source_utestids in sorted(dup_handler.duplicates.items()):
                fh.write(f"  {source_file}: {', '.join(sorted(source_utestids))}\n")
        if verbose:
            sys.stdout.write(
                f"\n{len(dup_handler.duplicates)} file(s) had duplicate results collapsed "
                f"(see {log_path})\n"
            )

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df["result"] = pd.to_numeric(df["result"], errors="coerce")
    return df
