from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from tqdm import tqdm


def parse_folder(
    folder: str | Path,
    parser_func: Callable[str | Path, ZoneInfo | None],
    *,
    tz: ZoneInfo | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    folder = Path(folder)
    pdf_file_paths = sorted(folder.glob("*.pdf"))
    all_rows: list[dict] = []
    iterator = (
        tqdm(pdf_file_paths, desc="Parsing PDFs", unit="file")
        if verbose
        else pdf_file_paths
    )
    for pdf_file_path in iterator:
        try:
            all_rows.extend(parser_func(pdf_file_path, tz=tz))
        except Exception as exc:
            sys.stdout.write(f"WARNING: failed to parse {pdf_file_path.name}: {exc}\n")
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df["result"] = pd.to_numeric(df["result"], errors="coerce")
    return df
