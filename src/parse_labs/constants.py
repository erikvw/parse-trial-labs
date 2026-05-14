from __future__ import annotations

import re

KNOWN_INVESTIGATIONS: set[str] = {
    "UREA NITROGEN",
    "CREATININE",
    "URIC ACID",
    "CHOLESTEROL",
    "HDL CHOLESTEROL",
    "ALT(SGPT)",
    "AST(SGOT)",
    "ALKALINE PHOSPHATASE",
    "GAMMA GT",
    "AMYLASE",
    "TRIGLYCERIDES",
    "ALBUMIN",
    "LDL CHOL (CALC)",
    "INSULIN",
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

HEADER_RE = re.compile(
    r"^(?P<report_type>[\w\s]+?)\s+REPORT\s+\[(?P<result_status>[^\]]+)\]"
)

RESULT_RE = re.compile(
    r"^(?P<investigation>.+?)\s+"
    r"(?P<result>[<>]?\.?\d+\.?\d*)\s+"
    r"(?P<units>\S+)\s+"
    r"(?P<flag>Low|High|Normal|Critical)?\s*"
    r"(?P<ref_range>\.?\d+\.?\d*\s*-\s*\.?\d+\.?\d*)"
)

RESULT_NO_FLAG_RE = re.compile(
    r"^(?P<investigation>.+?)\s+"
    r"(?P<result>[<>]?\.?\d+\.?\d*)\s+"
    r"(?P<units>\S+)\s+"
    r"(?P<ref_range>\.?\d+\.?\d*\s*-\s*\.?\d+\.?\d*)"
)
