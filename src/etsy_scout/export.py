"""Write ListingRows to Excel (sheet `competitor_listing`) and CSV."""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

from .models import COLUMNS, ListingRow

SHEET_NAME = "competitor_listing"


def to_dataframe(rows: list[ListingRow]) -> pd.DataFrame:
    return pd.DataFrame([r.to_record() for r in rows], columns=COLUMNS)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "search"


def excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        ws = writer.sheets[SHEET_NAME]
        ws.freeze_panes = "A2"
        for i, col in enumerate(df.columns, start=1):
            width = 60 if col == "listing_link" else max(12, min(40, len(col) + 2))
            ws.column_dimensions[get_column_letter(i)].width = width
        link_col = df.columns.get_loc("listing_link") + 1
        for r in range(2, len(df) + 2):
            cell = ws.cell(row=r, column=link_col)
            if cell.value:
                cell.hyperlink = cell.value
                cell.style = "Hyperlink"
    return buf.getvalue()


def write_outputs(rows: list[ListingRow], keyword: str, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify(keyword)}_{datetime.now():%Y%m%d_%H%M%S}"
    df = to_dataframe(rows)
    xlsx = out_dir / f"{stem}.xlsx"
    csv = out_dir / f"{stem}.csv"
    xlsx.write_bytes(excel_bytes(df))
    df.to_csv(csv, index=False)
    return xlsx, csv
