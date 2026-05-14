from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

from .constants import (
    HEADER_RE,
    KNOWN_INVESTIGATIONS,
    RESULT_NO_FLAG_RE,
    RESULT_RE,
)


def _parse_header_field(text: str, pattern: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _parse_datetime_field(text: str, label: str) -> str:
    m = re.search(rf"{label}\s+(\d{{2}}/\d{{2}}/\d{{4}})\s+Time\s+(\S+)", text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return ""


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
                return {
                    "investigation": inv,
                    "result": groups["result"],
                    "units": groups["units"],
                    "flag": flag,
                    "reference_range": groups["ref_range"].strip(),
                }
    return None


def _fuzzy_match_investigation(name: str) -> bool:
    return any(name.upper() == k.upper() for k in KNOWN_INVESTIGATIONS)


def parse_pdf(filepath: str | Path) -> list[dict]:
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
                full_text, r"Order No\s+\S+\s+Date"
            )
            result_no = _parse_header_field(full_text, r"Result No\s+(\S+)")
            result_datetime = _parse_datetime_field(
                full_text, r"Result No\s+\S+\s+Date"
            )
            specimen_collected_by = _parse_header_field(
                full_text, r"Specimen Collected By\s+(.+?)\s+Date"
            )
            specimen_collected_datetime = _parse_datetime_field(
                full_text, r"Specimen Collected By\s+.+?\s+Date"
            )
            specimen_received_by = _parse_header_field(
                full_text, r"Specimen Recieved By\s+(.+?)\s+Date"
            )
            specimen_received_datetime = _parse_datetime_field(
                full_text, r"Specimen Recieved By\s+.+?\s+Date"
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
                full_text, r"Reported By\s+.+?\s+Date"
            )
            verified_by = _parse_header_field(
                full_text, r"Verified By\s+(.+?)\s+Date"
            )
            verified_datetime = _parse_datetime_field(
                full_text, r"Verified By\s+.+?\s+Date"
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


def parse_folder(folder: str | Path) -> pd.DataFrame:
    folder = Path(folder)
    all_rows: list[dict] = []
    for pdf_file in sorted(folder.glob("*.pdf")):
        try:
            all_rows.extend(parse_pdf(pdf_file))
        except Exception as exc:
            print(
                f"WARNING: failed to parse {pdf_file.name}: {exc}", file=sys.stderr
            )
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df["result"] = pd.to_numeric(df["result"], errors="coerce")
    return df
