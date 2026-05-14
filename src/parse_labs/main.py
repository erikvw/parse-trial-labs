from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .parsers import parse_folder, parse_pdf


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_file_or_folder>", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    if target.is_dir():
        df = parse_folder(target)
    elif target.is_file() and target.suffix.lower() == ".pdf":
        rows = parse_pdf(target)
        df = pd.DataFrame(rows)
        if not df.empty:
            df["result"] = pd.to_numeric(df["result"], errors="coerce")
    else:
        print(f"Error: {target} is not a PDF file or directory", file=sys.stderr)
        sys.exit(1)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 30)
    print(f"\n{len(df)} results from {df['source_file'].nunique()} files\n")
    print(df.to_string(index=False))

    csv_out = (
        target / "lab_results.csv" if target.is_dir() else target.with_suffix(".csv")
    )
    df.to_csv(csv_out, index=False)
    print(f"\nSaved to {csv_out}")
