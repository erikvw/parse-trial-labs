"""Generate fake MNH-format lab PDFs for testing."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

CHEMISTRY_TEXT = """Muhimbili National Hospital
Dar Es Salaam, Tanzania
Phone No. 255-22-2151367-9, Fax No.
255-22-2150534, P.O.Box 65002
CLINICAL CHEMISTRY REPORT [Provisional Result]
IP Number Name FKP/999-00-1234-5 Age 35 Years Sex Male
MR Number Address
Ordered By DOCTOR JANE DOE Contact No Clinic / Ward OTHERS
Clinical Note
Order No DG-25-999001 Date 01/01/2026 Time 10:00:00 Patient Contact No.
Result No LB-250100001 Date 01/01/2026 Time 14:30:00
Specimen Collected By NURSE JOHN SMITH Date 01/01/2026 Time 10:05:00
Specimen Recieved By NURSE JOHN SMITH Date 01/01/2026 Time 10:15:00
Sample Type BLOOD Condition when Received Good
Sample No 0199990001/0 Priority Regular
Investigation Result Flag Reference Range
UREA NITROGEN 4.2 mmol/L 2.5 - 6.7
CREATININE 75.0 umol/L 50.4 - 98.1
URIC ACID 0.25 mmol/L 0.15 - 0.36
CHOLESTEROL 6.10 mmol/L High 0 - 5.53
HDL CHOLESTEROL 1.30 mmol/L Normal 1.04 - 1.55
ALT(SGPT) 22.50 U/L Normal 0 - 55
AST(SGOT) 31.00 U/L Normal 0 - 48.1
ALKALINE PHOSPHATASE 90.00 U/L 45.3 - 155
GAMMA GT 35.00 U/L 7.3 - 51.8
AMYLASE 100.00 U/L Normal 42.8 - 164.4
TRIGLYCERIDES 2.90 mmol/L High 0 - 2.88
ALBUMIN 42 g/L Normal 35.6 - 50.4
LDL CHOL (CALC) 3.50 mmol/L High 0 - 3.34
Reported By LAB TECH ALICE Date 01/01/2026 Time 14:30:05
Verified By SENIOR TECH BOB Date 01/01/2026 Time 15:00:00
Printed By PRINT OPERATOR Print Date 02/01/2026 Print Time 8:00:00 AM"""

HAEMATOLOGY_TEXT = """Muhimbili National Hospital
Dar Es Salaam, Tanzania
Phone No. 255-22-2151367-9, Fax No.
255-22-2150534, P.O.Box 65002
HAEMOTOLOGY REPORT [Final Result]
IP Number Name FKP/999-00-1234-5 Age 35 Years Sex Male
MR Number Address
Ordered By DOCTOR JANE DOE Contact No Clinic / Ward OTHERS
Clinical Note
Order No DG-25-999001 Date 01/01/2026 Time 10:00:00 Patient Contact No.
Result No LB-250100002 Date 01/01/2026 Time 12:00:00
Specimen Collected By NURSE JOHN SMITH Date 01/01/2026 Time 10:05:00
Specimen Recieved By NURSE JOHN SMITH Date 01/01/2026 Time 10:15:00
Sample Type BLOOD Condition when Received Good
Sample No 1199990001/0 Priority Regular
Investigation Result Flag Reference Range
PANEL FULL BLOOD COUNT WITH DIFFERENTIAL
WBC 6.500 K/uL 4 - 10
ABS NEUTROPHIL 3.200 K/uL Normal 2 - 6.9
NEUTROPHILS 49.23 % 40 - 80
LYMPHOCYTES (ABSOLUTE) 2.100 K/uL Normal 0.6 - 3.4
LYMPHOCYTES 32.31 % Normal 20 - 40
ABS MONOCYTES .4500 K/uL Normal 0 - 0.9
MONOCYTES 6.923 % Normal 2 - 10
ABS EOSINOPHILS .6000 K/uL Normal 0 - 0.7
EOSINOPHILS 9.231 % High 1 - 6
ABS BASOPHILS .1500 K/uL Normal 0 - 2
BASOPHILS 2.308 % High 0.02 - 0.1
RBC 4.800 M/uL 3.8 - 4.8
HGB 14.00 g/dL 12 - 15
HCT 42.00 % 36 - 46
MCV 87.50 fL 83 - 99
MCH 29.17 pg 27 - 32
MCHC 33.33 g/dL 31.5 - 34.5
RDW 13.00 % Normal 11.6 - 14.8
PLATELETS 250.0 K/uL 150 - 410
Reported By HAEM TECH CAROL Date 01/01/2026 Time 12:00:05
Verified By SENIOR TECH DAN Date 01/01/2026 Time 12:30:00
Printed By PRINT OPERATOR Print Date 02/01/2026 Print Time 8:00:00 AM"""

IMMUNOLOGY_TEXT = """Muhimbili National Hospital
Dar Es Salaam, Tanzania
Phone No. 255-22-2151367-9, Fax No.
255-22-2150534, P.O.Box 65002
IMMUNOLOGY REPORT [Final Result]
IP Number Name FKP/999-00-1234-5 Age 35 Years Sex Male
MR Number Address
Ordered By DOCTOR JANE DOE Contact No Clinic / Ward OTHERS
Clinical Note
Order No DG-25-999001 Date 01/01/2026 Time 10:00:00 Patient Contact No.
Result No LB-250100003 Date 01/01/2026 Time 16:00:00
Specimen Collected By NURSE JOHN SMITH Date 01/01/2026 Time 10:05:00
Specimen Recieved By NURSE JOHN SMITH Date 01/01/2026 Time 10:15:00
Sample Type BLOOD Condition when Received Good
Sample No 0199990002/0 Priority Regular
Investigation Result Flag Reference Range
INSULIN 8.50 uIU/mL Normal 4.03 - 23.46
Reported By IMMUNO TECH EVE Date 01/01/2026 Time 16:00:05
Verified By SENIOR TECH FRANK Date 01/01/2026 Time 16:30:00
Printed By PRINT OPERATOR Print Date 02/01/2026 Print Time 8:00:00 AM"""


def _text_to_pdf(text: str, path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    for line in text.strip().split("\n"):
        pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def generate_fake_chemistry(path: Path) -> None:
    _text_to_pdf(CHEMISTRY_TEXT, path)


def generate_fake_haematology(path: Path) -> None:
    _text_to_pdf(HAEMATOLOGY_TEXT, path)


def generate_fake_immunology(path: Path) -> None:
    _text_to_pdf(IMMUNOLOGY_TEXT, path)


def generate_fake_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    generate_fake_chemistry(folder / "FKP_chemistry.pdf")
    generate_fake_haematology(folder / "FKP_haematology.pdf")
    generate_fake_immunology(folder / "FKP_immunology.pdf")
