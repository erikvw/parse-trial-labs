from __future__ import annotations

import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from tqdm import tqdm

from .duplicate_tracking_handler import DuplicateTrackingHandler
from .utils import get_default_tz, get_now, hash_bytes, hash_text

logger = logging.getLogger(__name__)


class FilesToDataFrame:
    def __init__(  # noqa: PLR0913
        self,
        folder: Path,
        parser_func: Callable[str | Path, ZoneInfo | None],
        *,
        tz: ZoneInfo | None = None,
        is_valid_identifier_func: Callable | None = None,
        duplicates_json_path: str | Path | None = None,
        log_path: str | Path | None = None,
        verbose: bool = True,
    ):
        self._file_handler = None
        self._pkg_logger = None
        self._dataframe = pd.DataFrame()
        self.duplicates_mapping: dict[Path, Path] = {}
        self.ts = get_now().strftime("%Y%m%d_%H%M%S")
        self.byte_digests: dict[Path, str] = {}
        self.app_name = "parse_trial_labs"
        self.verbose = verbose
        self.folder = Path(folder)
        self.parser_func = parser_func
        self.is_valid_identifier_func = is_valid_identifier_func
        self.pdf_file_paths: list[Path] = sorted(self.folder.glob("*.pdf"))
        self.duplicates_json_path = (
            Path(duplicates_json_path)
            if duplicates_json_path
            else self.folder / f"parse_session_{self.ts}.duplicates.json"
        )
        self.tz = tz or get_default_tz()
        self.log_path = (
            Path(log_path) if log_path else self.folder / f"parse_session_{self.ts}.log"
        )
        self.dup_handler = DuplicateTrackingHandler()

        self.add_log_handlers()
        self.load_duplicates_mapping()
        self.load_bytes_digests()

    @property
    def dataframe(self) -> pd.DataFrame:
        if self._dataframe.empty:
            all_rows: list[dict] = []
            iterator = (
                tqdm(self.files_to_parse, desc="Parsing PDFs", unit="file")
                if self.verbose
                else self.files_to_parse
            )
            try:
                for pdf_file_path in iterator:
                    try:
                        rows = self.parser_func(
                            pdf_file_path,
                            tz=self.tz,
                            is_valid_identifier_func=self.is_valid_identifier_func,
                        )
                        source_file_sha256 = self.byte_digests.get(pdf_file_path, "")
                        for row in rows:
                            row["source_file_sha256"] = source_file_sha256
                        all_rows.extend(rows)
                    except Exception as exc:
                        sys.stdout.write(
                            f"WARNING: failed to parse {pdf_file_path.name}: {exc}\n"
                        )
            finally:
                self.remove_log_handlers()
            self._dataframe = pd.DataFrame(all_rows)
            if not self._dataframe.empty:
                self._dataframe["result"] = pd.to_numeric(
                    self._dataframe["result"], errors="coerce"
                )
            self.write_duplicates()
            self.log_duplicates()
        return self._dataframe

    def load_duplicates_mapping(self):
        if self.duplicates_json_path and self.duplicates_json_path.exists():
            data: dict[str, str] = json.loads(self.duplicates_json_path.read_text())
            self.duplicates_mapping = {
                Path(dup): Path(original) for dup, original in data.items()
            }

        else:
            self.find_duplicate_files()
            self.write_duplicate_mapping()

    def load_bytes_digests(self):
        # already populated unless the duplicates mapping was read from json
        for pdf_file_path in self.files_to_parse:
            if pdf_file_path not in self.byte_digests:
                try:
                    self.byte_digests[pdf_file_path] = hash_bytes(pdf_file_path)
                except OSError as exc:
                    logger.warning("Could not hash %s: %s", pdf_file_path.name, exc)
        for dup_path, original_path in sorted(self.duplicates_mapping.items()):
            logger.warning(
                "Duplicate file skipped: %s is a duplicate of %s",
                dup_path.name,
                original_path.name,
            )

    @property
    def files_to_parse(self) -> list[Path]:
        return [p for p in self.pdf_file_paths if p not in self.duplicates_mapping]

    def write_duplicate_mapping(self) -> None:
        data = {str(dup): str(original) for dup, original in self.duplicates_mapping.items()}
        self.duplicates_json_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    @property
    def file_handler(self) -> logging.FileHandler:
        if not self._file_handler:
            self._file_handler = logging.FileHandler(self.log_path)
            self._file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
        return self._file_handler

    @property
    def pkg_logger(self) -> logging.Logger:
        if not self._pkg_logger:
            self._pkg_logger = logging.getLogger(self.app_name)
        return self._pkg_logger

    def add_log_handlers(self) -> None:
        """Attach handlers before anything logs.

        Parsers emit warnings while `dataframe` runs and duplicate
        files are reported from `load_bytes_digests`. Attaching here
        means both reach the session log, and `dup_handler` collects
        during parsing rather than after it.
        """
        self.pkg_logger.addHandler(self.file_handler)
        self.pkg_logger.addHandler(self.dup_handler)

    def remove_log_handlers(self) -> None:
        self.pkg_logger.removeHandler(self.file_handler)
        self.pkg_logger.removeHandler(self.dup_handler)
        self.file_handler.close()

    def find_duplicate_files(self):
        """Map each duplicate file to the first-seen file it duplicates.

        Checks exact byte content first (cheap), then falls back to the
        extracted text so a re-saved/re-printed copy (different bytes,
        identical visible content) is still caught. Files that can't be
        hashed are left alone and surface through the normal per-file
        parse error handling instead.

        Populates `byte_digests` with the sha256 of each file's bytes
        while reading it, so callers need not read every file a second
        time to get it.
        """
        seen_by_bytes: dict[str, Path] = {}
        seen_by_text: dict[str, Path] = {}
        iterator = (
            tqdm(self.pdf_file_paths, desc="Scanning for duplicates", unit="file")
            if self.verbose
            else self.pdf_file_paths
        )
        for path in iterator:
            try:
                byte_digest = hash_bytes(path)
            except OSError:
                continue
            self.byte_digests[path] = byte_digest
            original = seen_by_bytes.get(byte_digest)
            if original is not None:
                self.duplicates_mapping[path] = original
                continue
            seen_by_bytes[byte_digest] = path

            try:
                text_digest = hash_text(path)
            except Exception as exc:
                logger.warning("Could not extract text from %s: %s", path.name, exc)
                continue
            original = seen_by_text.get(text_digest)
            if original is not None:
                self.duplicates_mapping[path] = original
                continue
            seen_by_text[text_digest] = path

    def write_duplicates(self):
        if self.duplicates_mapping:
            with self.log_path.open("a") as fh:
                fh.write("\nDuplicate files skipped (same file under a different name):\n")
                for dup_path, original_path in sorted(self.duplicates_mapping.items()):
                    fh.write(f"  {dup_path.name} == {original_path.name}\n")
            if self.verbose:
                sys.stdout.write(
                    f"\n{len(self.duplicates_mapping)} duplicate file(s) "
                    f"skipped (see {self.log_path})\n"
                )

    def log_duplicates(self):
        if self.dup_handler.duplicates:
            with self.log_path.open("a") as fh:
                fh.write("\nFiles with duplicate results collapsed:\n")
                for source_file, source_utestids in sorted(
                    self.dup_handler.duplicates.items()
                ):
                    fh.write(f"  {source_file}: {', '.join(sorted(source_utestids))}\n")
            if self.verbose:
                sys.stdout.write(
                    f"\n{len(self.dup_handler.duplicates)} file(s) had duplicate "
                    f"results collapsed (see {self.log_path})\n"
                )
