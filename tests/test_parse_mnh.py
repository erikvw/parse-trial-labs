from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from parse_labs import parse_folder
from parse_labs.parsers import parse_mnh
from parse_labs.parsers.parse_mnh.parser import (
    _parse_datetime_field,
    _parse_header_field,
    _parse_result_line,
)

from .fake_pdf import (
    generate_fake_chemistry,
    generate_fake_folder,
    generate_fake_haematology,
    generate_fake_immunology,
)

# --- Unit tests: _parse_result_line ---


class TestParseResultLine:
    def test_with_flag(self):
        line = "CHOLESTEROL 6.10 mmol/L High 0 - 5.53"
        result = _parse_result_line(line)
        assert result is not None
        assert result["investigation"] == "CHOLESTEROL"
        assert result["result"] == "6.10"
        assert result["units"] == "mmol/L"
        assert result["flag"] == "High"
        assert result["reference_range_lower"] == "0"
        assert result["reference_range_upper"] == "5.53"

    def test_without_flag(self):
        line = "CREATININE 75.0 umol/L 50.4 - 98.1"
        result = _parse_result_line(line)
        assert result is not None
        assert result["investigation"] == "CREATININE"
        assert result["result"] == "75.0"
        assert result["units"] == "umol/L"
        assert result["flag"] == ""
        assert result["reference_range_lower"] == "50.4"
        assert result["reference_range_upper"] == "98.1"

    def test_leading_dot_result(self):
        line = "ABS MONOCYTES .4500 K/uL Normal 0 - 0.9"
        result = _parse_result_line(line)
        assert result is not None
        assert result["investigation"] == "ABS MONOCYTES"
        assert result["result"] == ".4500"
        assert result["units"] == "K/uL"

    def test_leading_dot_ref_range(self):
        line = "BASOPHILS 2.308 % High 0.02 - 0.1"
        result = _parse_result_line(line)
        assert result is not None
        assert result["reference_range_lower"] == "0.02"
        assert result["reference_range_upper"] == "0.1"

    def test_panel_header_skipped(self):
        line = "PANEL FULL BLOOD COUNT WITH DIFFERENTIAL"
        result = _parse_result_line(line)
        assert result is None

    def test_unknown_investigation_rejected(self):
        line = "BOGUS TEST 1.23 mg/dL 0 - 5"
        result = _parse_result_line(line)
        assert result is None

    def test_integer_result(self):
        line = "ALBUMIN 42 g/L Normal 35.6 - 50.4"
        result = _parse_result_line(line)
        assert result is not None
        assert result["result"] == "42"

    def test_low_flag(self):
        line = "UREA NITROGEN 1.8 mmol/L Low 2.5 - 6.7"
        result = _parse_result_line(line)
        assert result is not None
        assert result["flag"] == "Low"

    def test_normal_flag(self):
        line = "AMYLASE 100.00 U/L Normal 42.8 - 164.4"
        result = _parse_result_line(line)
        assert result is not None
        assert result["flag"] == "Normal"

    def test_parentheses_in_name(self):
        line = "ALT(SGPT) 22.50 U/L Normal 0 - 55"
        result = _parse_result_line(line)
        assert result is not None
        assert result["investigation"] == "ALT(SGPT)"

    def test_calc_in_name(self):
        line = "LDL CHOL (CALC) 3.50 mmol/L High 0 - 3.34"
        result = _parse_result_line(line)
        assert result is not None
        assert result["investigation"] == "LDL CHOL (CALC)"


# --- Unit tests: _parse_header_field / _parse_datetime_field ---


class TestParseHeaderFields:
    SAMPLE_HEADER = (
        "Name FKP/999-00-1234-5 Age 35 Years Sex Male\n"
        "Ordered By DOCTOR JANE DOE Contact No Clinic / Ward OTHERS\n"
        "Order No DG-25-999001 Date 01/01/2026 Time 10:00:00 Patient Contact No.\n"
        "Result No LB-250100001 Date 01/01/2026 Time 14:30:00\n"
        "Specimen Collected By NURSE JOHN SMITH Date 01/01/2026 Time 10:05:00\n"
        "Specimen Recieved By NURSE JOHN SMITH Date 01/01/2026 Time 10:15:00\n"
        "Sample Type BLOOD Condition when Received Good\n"
        "Sample No 0199990001/0 Priority Regular\n"
        "Reported By LAB TECH ALICE Date 01/01/2026 Time 14:30:05\n"
        "Verified By SENIOR TECH BOB Date 01/01/2026 Time 15:00:00\n"
    )

    def test_name_id(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Name\s+(\S+)") == "FKP/999-00-1234-5"

    def test_age(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Age\s+(\d+)") == "35"

    def test_sex(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Sex\s+(\w+)") == "Male"

    def test_ordered_by(self):
        val = _parse_header_field(self.SAMPLE_HEADER, r"Ordered By\s+(.+?)(?:\s+Contact)")
        assert val == "DOCTOR JANE DOE"

    def test_clinic_ward(self):
        val = _parse_header_field(self.SAMPLE_HEADER, r"Clinic / Ward\s+(.+?)(?:\n|$)")
        assert val == "OTHERS"

    def test_order_no(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Order No\s+(\S+)") == "DG-25-999001"

    def test_sample_type(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Sample Type\s+(\S+)") == "BLOOD"

    def test_sample_condition(self):
        val = _parse_header_field(self.SAMPLE_HEADER, r"Condition when Received\s+(\w+)")
        assert val == "Good"

    def test_priority(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"Priority\s+(\w+)") == "Regular"

    def test_missing_field_returns_empty(self):
        assert _parse_header_field(self.SAMPLE_HEADER, r"IP Number\s+(\S+)") == ""

    def test_datetime_naive_without_tz(self):
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Order No\s+\S+\s+Date")
        assert val == datetime(2026, 1, 1, 10, 0, 0)  # noqa: DTZ001
        assert val.tzinfo is None

    def test_datetime_aware_with_tz(self):
        tz = ZoneInfo("Africa/Dar_es_Salaam")
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Order No\s+\S+\s+Date", tz=tz)
        assert val == datetime(2026, 1, 1, 10, 0, 0, tzinfo=tz)
        assert val.tzinfo is tz

    def test_result_datetime(self):
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Result No\s+\S+\s+Date")
        assert val == datetime(2026, 1, 1, 14, 30, 0)  # noqa: DTZ001

    def test_specimen_collected_datetime(self):
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Specimen Collected By\s+.+?\s+Date")
        assert val == datetime(2026, 1, 1, 10, 5, 0)  # noqa: DTZ001

    def test_specimen_received_datetime(self):
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Specimen Recieved By\s+.+?\s+Date")
        assert val == datetime(2026, 1, 1, 10, 15, 0)  # noqa: DTZ001

    def test_verified_datetime(self):
        val = _parse_datetime_field(self.SAMPLE_HEADER, r"Verified By\s+.+?\s+Date")
        assert val == datetime(2026, 1, 1, 15, 0, 0)  # noqa: DTZ001

    def test_datetime_returns_none_when_missing(self):
        text = "Verified By Date Time\n"
        val = _parse_datetime_field(text, r"Verified By\s+.+?\s+Date")
        assert val is None

    def test_verified_by_empty_when_missing(self):
        text = "Verified By Date Time\n"
        val = _parse_header_field(text, r"Verified By\s+(.+?)\s+Date")
        assert val == ""


# --- Integration tests: parse_mnh with fake PDFs ---


class TestParsePdfChemistry:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.pdf_path = tmp_path / "chemistry.pdf"
        generate_fake_chemistry(self.pdf_path)
        self.rows = parse_mnh(self.pdf_path)

    def test_row_count(self):
        assert len(self.rows) == 13

    def test_report_type(self):
        assert self.rows[0]["report_type"] == "CLINICAL CHEMISTRY"

    def test_result_status(self):
        assert self.rows[0]["result_status"] == "Provisional Result"

    def test_patient_id(self):
        assert self.rows[0]["name_id"] == "FKP/999-00-1234-5"

    def test_age_sex(self):
        assert self.rows[0]["age"] == "35"
        assert self.rows[0]["sex"] == "Male"

    def test_ordered_by(self):
        assert self.rows[0]["ordered_by"] == "DOCTOR JANE DOE"

    def test_specimen_collected(self):
        assert self.rows[0]["specimen_collected_by"] == "NURSE JOHN SMITH"
        assert self.rows[0]["specimen_collected_datetime"] == datetime(2026, 1, 1, 10, 5, 0)  # noqa: DTZ001

    def test_investigations_present(self):
        names = [r["investigation"] for r in self.rows]
        assert "UREA NITROGEN" in names
        assert "CREATININE" in names
        assert "LDL CHOL (CALC)" in names

    def test_flagged_result(self):
        cholesterol = next(r for r in self.rows if r["investigation"] == "CHOLESTEROL")
        assert cholesterol["flag"] == "High"
        assert cholesterol["result"] == "6.10"

    def test_unflagged_result(self):
        urea = next(r for r in self.rows if r["investigation"] == "UREA NITROGEN")
        assert urea["flag"] == ""

    def test_verified_by(self):
        assert self.rows[0]["verified_by"] == "SENIOR TECH BOB"
        assert self.rows[0]["verified_datetime"] == datetime(2026, 1, 1, 15, 0, 0)  # noqa: DTZ001

    def test_datetimes_naive_without_tz(self):
        assert self.rows[0]["order_datetime"].tzinfo is None

    def test_datetimes_aware_with_tz(self, tmp_path):
        tz = ZoneInfo("Africa/Dar_es_Salaam")
        rows = parse_mnh(tmp_path / "chemistry.pdf", tz=tz)
        assert rows[0]["order_datetime"].tzinfo is tz


class TestParsePdfHaematology:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.pdf_path = tmp_path / "haematology.pdf"
        generate_fake_haematology(self.pdf_path)
        self.rows = parse_mnh(self.pdf_path)

    def test_row_count(self):
        assert len(self.rows) == 19

    def test_report_type(self):
        assert self.rows[0]["report_type"] == "HAEMOTOLOGY"

    def test_result_status(self):
        assert self.rows[0]["result_status"] == "Final Result"

    def test_panel_header_excluded(self):
        names = [r["investigation"] for r in self.rows]
        assert "PANEL FULL BLOOD COUNT WITH DIFFERENTIAL" not in names

    def test_leading_dot_result_parsed(self):
        mono = next(r for r in self.rows if r["investigation"] == "ABS MONOCYTES")
        assert mono["result"] == ".4500"

    def test_all_haem_investigations(self):
        names = {r["investigation"] for r in self.rows}
        expected = {
            "WBC",
            "ABS NEUTROPHIL",
            "NEUTROPHILS",
            "LYMPHOCYTES (ABSOLUTE)",
            "LYMPHOCYTES",
            "ABS MONOCYTES",
            "MONOCYTES",
            "ABS EOSINOPHILS",
            "EOSINOPHILS",
            "ABS BASOPHILS",
            "BASOPHILS",
            "RBC",
            "HGB",
            "HCT",
            "MCV",
            "MCH",
            "MCHC",
            "RDW",
            "PLATELETS",
        }
        assert names == expected


class TestParsePdfImmunology:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.pdf_path = tmp_path / "immunology.pdf"
        generate_fake_immunology(self.pdf_path)
        self.rows = parse_mnh(self.pdf_path)

    def test_row_count(self):
        assert len(self.rows) == 1

    def test_report_type(self):
        assert self.rows[0]["report_type"] == "IMMUNOLOGY"

    def test_insulin_result(self):
        assert self.rows[0]["investigation"] == "INSULIN"
        assert self.rows[0]["result"] == "8.50"
        assert self.rows[0]["units"] == "uIU/mL"
        assert self.rows[0]["flag"] == "Normal"
        assert self.rows[0]["reference_range_lower"] == "4.03"
        assert self.rows[0]["reference_range_upper"] == "23.46"


# --- Integration test: parse_folder ---


class TestParseFolder:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.folder = tmp_path / "labs"
        generate_fake_folder(self.folder)
        self.df = parse_folder(self.folder, parse_mnh, verbose=False)

    def test_total_rows(self):
        assert len(self.df) == 33  # 13 + 19 + 1

    def test_files_parsed(self):
        assert self.df["source_file"].nunique() == 3

    def test_result_column_numeric(self):
        assert self.df["result"].dtype.kind == "f"

    def test_all_columns_present(self):
        expected_cols = {
            "source_file",
            "report_type",
            "result_status",
            "name_id",
            "age",
            "sex",
            "ordered_by",
            "clinic_ward",
            "order_no",
            "order_datetime",
            "result_no",
            "result_datetime",
            "specimen_collected_by",
            "specimen_collected_datetime",
            "specimen_received_by",
            "specimen_received_datetime",
            "sample_type",
            "sample_condition",
            "sample_no",
            "priority",
            "reported_by",
            "reported_datetime",
            "verified_by",
            "verified_datetime",
            "investigation",
            "result",
            "units",
            "flag",
            "reference_range_lower",
            "reference_range_upper",
        }
        assert expected_cols == set(self.df.columns)

    def test_datetime_columns_are_datetime(self):
        for col in [
            "order_datetime",
            "result_datetime",
            "specimen_collected_datetime",
            "specimen_received_datetime",
            "reported_datetime",
            "verified_datetime",
        ]:
            assert self.df[col].dtype.kind == "M", f"{col} not datetime"

    def test_datetime_aware_with_tz(self, tmp_path):
        folder = tmp_path / "labs_tz"
        generate_fake_folder(folder)
        tz = ZoneInfo("Africa/Dar_es_Salaam")
        df = parse_folder(folder, parse_mnh, tz=tz, verbose=False)
        val = df["order_datetime"].iloc[0]
        assert val.tzinfo is not None

    def test_empty_folder(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        df = parse_folder(empty, parse_mnh, verbose=False)
        assert len(df) == 0
