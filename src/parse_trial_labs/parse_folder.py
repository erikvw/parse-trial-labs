from __future__ import annotations

import hashlib
import logging
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pdfplumber
from tqdm import tqdm

logger = logging.getLogger(__name__)


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


def _hash_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _find_duplicate_files(pdf_file_paths: list[Path]) -> dict[Path, Path]:
    """Map each duplicate file to the first-seen file it duplicates.

    Checks exact byte content first (cheap), then falls back to the
    extracted text so a re-saved/re-printed copy (different bytes,
    identical visible content) is still caught. Files that can't be
    hashed are left alone and surface through the normal per-file
    parse error handling instead.
    """
    seen_by_bytes: dict[str, Path] = {}
    seen_by_text: dict[str, Path] = {}
    duplicate_of: dict[Path, Path] = {}
    for path in pdf_file_paths:
        try:
            byte_digest = _hash_bytes(path)
        except OSError:
            continue
        original = seen_by_bytes.get(byte_digest)
        if original is not None:
            duplicate_of[path] = original
            continue
        seen_by_bytes[byte_digest] = path

        try:
            text_digest = _hash_text(path)
        except Exception as exc:
            logger.warning("Could not extract text from %s: %s", path.name, exc)
            continue
        original = seen_by_text.get(text_digest)
        if original is not None:
            duplicate_of[path] = original
            continue
        seen_by_text[text_digest] = path
    return duplicate_of


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
    pkg_logger = logging.getLogger("parse_trial_labs")
    pkg_logger.addHandler(file_handler)
    pkg_logger.addHandler(dup_handler)

    duplicate_of = _find_duplicate_files(pdf_file_paths)
    for dup_path, original_path in sorted(duplicate_of.items()):
        logger.warning(
            "Duplicate file skipped: %s is a duplicate of %s",
            dup_path.name,
            original_path.name,
        )
    files_to_parse = [p for p in pdf_file_paths if p not in duplicate_of]

    iterator = (
        tqdm(files_to_parse, desc="Parsing PDFs", unit="file") if verbose else files_to_parse
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
        pkg_logger.removeHandler(file_handler)
        pkg_logger.removeHandler(dup_handler)
        file_handler.close()

    if duplicate_of:
        with log_path.open("a") as fh:
            fh.write("\nDuplicate files skipped (same file under a different name):\n")
            for dup_path, original_path in sorted(duplicate_of.items()):
                fh.write(f"  {dup_path.name} == {original_path.name}\n")
        if verbose:
            sys.stdout.write(
                f"\n{len(duplicate_of)} duplicate file(s) skipped (see {log_path})\n"
            )

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
