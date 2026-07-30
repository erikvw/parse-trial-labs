from __future__ import annotations

import contextlib
import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pdfplumber

from .constants import (
    DATETIME_FORMAT,
    HEADER_PATTERN,
    KNOWN_INVESTIGATIONS,
    RESULT_NO_FLAG_PATTERN,
    RESULT_PATTERN,
)

logger = logging.getLogger(__name__)


def _parse_header_field(text: str, pattern: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _parse_datetime_field(
    text: str, label: str, *, tz: ZoneInfo | None = None
) -> datetime | None:
    m = re.search(rf"{label}\s+(\d{{2}}/\d{{2}}/\d{{4}})\s+Time\s+(\S+)", text)
    if m:
        raw = f"{m.group(1)} {m.group(2)}"
        try:
            dt = datetime.strptime(raw, DATETIME_FORMAT)  # noqa: DTZ007
        except ValueError:
            return None
        if tz:
            dt = dt.replace(tzinfo=tz)
        return dt
    return None


def _parse_result_line(line: str) -> dict | None:
    """Try to parse an source_utestid result line.

    Handles two layouts seen in MNH PDFs:
      1) INVESTIGATION  result units  Flag  ref_low - ref_high
      2) INVESTIGATION  result units       ref_low - ref_high   (no flag)
    """
    for regex in [RESULT_PATTERN, RESULT_NO_FLAG_PATTERN]:
        m = regex.match(line)
        if m:
            groups = m.groupdict()
            source_utestid = groups["source_utestid"].strip()
            if source_utestid.startswith("PANEL"):
                return None
            if source_utestid in KNOWN_INVESTIGATIONS or _fuzzy_match_source_utestid(
                source_utestid
            ):
                flag = groups.get("flag", "") or ""
                ref_lower, ref_upper = _split_reference_range(groups["ref_range"].strip())
                return {
                    "source_utestid": source_utestid,
                    "result": groups["result"],
                    "source_units": groups["source_units"],
                    "flag": flag,
                    "reference_range_lower": ref_lower,
                    "reference_range_upper": ref_upper,
                }
    return None


def _split_reference_range(ref_range: str) -> tuple[str, str]:
    parts = ref_range.split("-")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return ref_range, ""


def _fuzzy_match_source_utestid(name: str) -> bool:
    return any(name.upper() == k.upper() for k in KNOWN_INVESTIGATIONS)


_DUPLICATE_COMPARE_FIELDS = (
    "result",
    "source_units",
    "flag",
    "reference_range_lower",
    "reference_range_upper",
)


def _dedupe_result_rows(rows: list[dict], filepath: Path) -> list[dict]:
    """Collapse repeated result lines for the same order/investigation.

    Some MNH PDFs render each result line twice (a text-extraction artifact
    of the report layout). If the repeated lines agree, keep one copy; if
    they disagree, the source data is ambiguous and we refuse to guess.
    """
    seen: dict[tuple, dict] = {}
    deduped: list[dict] = []
    for row in rows:
        key = (row["order_no"], row["result_no"], row["sample_no"], row["source_utestid"])
        existing = seen.get(key)
        if existing is None:
            seen[key] = row
            deduped.append(row)
            continue
        mismatches = {
            field: (existing[field], row[field])
            for field in _DUPLICATE_COMPARE_FIELDS
            if existing[field] != row[field]
        }
        if mismatches:
            raise ValueError(
                f"Conflicting duplicate result within PDF. See {row['source_utestid']!r} in "
                f"{filepath.name} (order_no={row['order_no']!r}): {mismatches}"
            )
        logger.warning(
            "Duplicate result collapsed: %s in %s (order_no=%s)",
            row["source_utestid"],
            filepath.name,
            row["order_no"],
            extra={"source_file": filepath.name, "source_utestid": row["source_utestid"]},
        )
    return deduped


def parse(
    filepath: str | Path,
    *,
    tz: ZoneInfo | None = None,
    is_valid_identifier_func: Callable | None = None,
) -> list[dict]:
    filepath = Path(filepath)
    rows = []

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            full_text = text

            report_type = ""
            result_status = ""
            for line in lines:
                m = HEADER_PATTERN.match(line.strip())
                if m:
                    report_type = m.group("report_type").strip()
                    result_status = m.group("result_status").strip()
                    break

            name_id = _parse_header_field(full_text, r"Name\s+(\S+)")
            age = _parse_header_field(full_text, r"Age\s+(\d+)")
            sex = _parse_header_field(full_text, r"Sex\s+(\w+)")
            ordered_by = _parse_header_field(full_text, r"Ordered By\s+(.+?)(?:\s+Contact)")
            clinic_ward = _parse_header_field(full_text, r"Clinic / Ward\s+(.+?)(?:\n|$)")
            order_no = _parse_header_field(full_text, r"Order No\s+(\S+)")
            order_datetime = _parse_datetime_field(full_text, r"Order No\s+\S+\s+Date", tz=tz)
            result_no = _parse_header_field(full_text, r"Result No\s+(\S+)")
            result_datetime = _parse_datetime_field(
                full_text, r"Result No\s+\S+\s+Date", tz=tz
            )
            specimen_collected_by = _parse_header_field(
                full_text, r"Specimen Collected By\s+(.+?)\s+Date"
            )
            specimen_collected_datetime = _parse_datetime_field(
                full_text, r"Specimen Collected By\s+.+?\s+Date", tz=tz
            )
            specimen_received_by = _parse_header_field(
                full_text, r"Specimen Recieved By\s+(.+?)\s+Date"
            )
            specimen_received_datetime = _parse_datetime_field(
                full_text, r"Specimen Recieved By\s+.+?\s+Date", tz=tz
            )
            sample_type = _parse_header_field(full_text, r"Sample Type\s+(\S+)")
            sample_condition = _parse_header_field(
                full_text, r"Condition when Received\s+(\w+)"
            )
            sample_no = _parse_header_field(full_text, r"Sample No\s+(\S+)")
            priority = _parse_header_field(full_text, r"Priority\s+(\w+)")
            reported_by = _parse_header_field(full_text, r"Reported By\s+(.+?)\s+Date")
            reported_datetime = _parse_datetime_field(
                full_text, r"Reported By\s+.+?\s+Date", tz=tz
            )
            verified_by = _parse_header_field(full_text, r"Verified By\s+(.+?)\s+Date")
            verified_datetime = _parse_datetime_field(
                full_text, r"Verified By\s+.+?\s+Date", tz=tz
            )

            # parse name_id
            subject_identifier, screening_identifier = parse_name_id(
                name_id,
                is_valid_identifier_func,
            )

            header = {
                "source_file": filepath.name,
                "report_type": report_type,
                "result_status": result_status,
                "name_id": name_id,
                "subject_identifier": subject_identifier,
                "screening_identifier": screening_identifier,
                "age": age,
                "sex": sex,
                "ordered_by": ordered_by,
                "clinic_ward": clinic_ward,
                "order_no": order_no,
                "order_datetime": order_datetime,
                "result_no": result_no,
                "result_datetime": result_datetime,
                "specimen_collected_by": specimen_collected_by,
                "specimen_collected_datetime": specimen_collected_datetime,
                "specimen_received_by": specimen_received_by,
                "specimen_received_datetime": specimen_received_datetime,
                "sample_type": sample_type,
                "sample_condition": sample_condition,
                "sample_no": sample_no,
                "priority": priority,
                "reported_by": reported_by,
                "reported_datetime": reported_datetime,
                "verified_by": verified_by,
                "verified_datetime": verified_datetime,
            }

            in_results = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("Investigation"):
                    in_results = True
                    continue
                if in_results:
                    if stripped.startswith("Reported By"):
                        break
                    result_body = _parse_result_line(stripped)
                    if result_body:
                        rows.append({**header, **result_body})

    return _dedupe_result_rows(rows, filepath)


def extract_identifier_from_name_id(name_id: str) -> str:
    if "/" in name_id:
        name_id = name_id.replace("//", "/")
        return name_id.split("/", 1)[1]
    return name_id


def parse_name_id(
    name_id: str,
    is_valid_identifier_func: Callable | None,
):
    subject_identifier = ""
    screening_identifier = ""
    if name_id:
        identifier = extract_identifier_from_name_id(name_id)
        screening_identifier = "".join(re.findall(r"[0-9A-Z]", identifier))
        if len(screening_identifier) != 8:
            screening_identifier = ""
            with contextlib.suppress(ValueError):
                if is_valid_identifier_func(identifier):
                    subject_identifier = identifier
    return subject_identifier, screening_identifier
