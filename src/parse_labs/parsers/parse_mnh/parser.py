from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pdfplumber

from .constants import (
    DATETIME_FORMAT,
    HEADER_RE,
    KNOWN_INVESTIGATIONS,
    RESULT_NO_FLAG_RE,
    RESULT_RE,
)


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
    """Try to parse an investigation result line.

    Handles two layouts seen in MNH PDFs:
      1) INVESTIGATION  result units  Flag  ref_low - ref_high
      2) INVESTIGATION  result units       ref_low - ref_high   (no flag)
    """
    for regex in [RESULT_RE, RESULT_NO_FLAG_RE]:
        m = regex.match(line)
        if m:
            groups = m.groupdict()
            inv = groups["investigation"].strip()
            if inv.startswith("PANEL"):
                return None
            if inv in KNOWN_INVESTIGATIONS or _fuzzy_match_investigation(inv):
                flag = groups.get("flag", "") or ""
                ref_lower, ref_upper = _split_reference_range(
                    groups["ref_range"].strip()
                )
                return {
                    "investigation": inv,
                    "result": groups["result"],
                    "units": groups["units"],
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


def _fuzzy_match_investigation(name: str) -> bool:
    return any(name.upper() == k.upper() for k in KNOWN_INVESTIGATIONS)


def parse(
    filepath: str | Path, *, tz: ZoneInfo | None = None
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
                m = HEADER_RE.match(line.strip())
                if m:
                    report_type = m.group("report_type").strip()
                    result_status = m.group("result_status").strip()
                    break

            name_id = _parse_header_field(full_text, r"Name\s+(\S+)")
            age = _parse_header_field(full_text, r"Age\s+(\d+)")
            sex = _parse_header_field(full_text, r"Sex\s+(\w+)")
            ordered_by = _parse_header_field(
                full_text, r"Ordered By\s+(.+?)(?:\s+Contact)"
            )
            clinic_ward = _parse_header_field(
                full_text, r"Clinic / Ward\s+(.+?)(?:\n|$)"
            )
            order_no = _parse_header_field(full_text, r"Order No\s+(\S+)")
            order_datetime = _parse_datetime_field(
                full_text, r"Order No\s+\S+\s+Date", tz=tz
            )
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
            reported_by = _parse_header_field(
                full_text, r"Reported By\s+(.+?)\s+Date"
            )
            reported_datetime = _parse_datetime_field(
                full_text, r"Reported By\s+.+?\s+Date", tz=tz
            )
            verified_by = _parse_header_field(
                full_text, r"Verified By\s+(.+?)\s+Date"
            )
            verified_datetime = _parse_datetime_field(
                full_text, r"Verified By\s+.+?\s+Date", tz=tz
            )

            header = {
                "source_file": filepath.name,
                "report_type": report_type,
                "result_status": result_status,
                "name_id": name_id,
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
                    parsed = _parse_result_line(stripped)
                    if parsed:
                        rows.append({**header, **parsed})

    return rows


