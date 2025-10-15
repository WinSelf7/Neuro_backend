from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, List
import pandas as pd
from bs4 import BeautifulSoup

def iter_table_htmls(obj) -> Iterable[str]:
    """Recursively yield any obj['html'] strings that look like <table> HTML."""
    if isinstance(obj, dict):
        # If this dict has an 'html' field with a table, yield it
        html = obj.get("html")
        if isinstance(html, str) and "<table" in html.lower():
            yield html
        # Recurse
        for v in obj.values():
            yield from iter_table_htmls(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_table_htmls(item)

def read_tables_from_html(html: str) -> List[pd.DataFrame]:
    """Extract all <table> elements from a string into DataFrames."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    dfs: List[pd.DataFrame] = []
    for t in tables:
        dfs.extend(pd.read_html(str(t)))  # may return multiple per table, keep all
    return dfs

def clean_header(df: pd.DataFrame) -> pd.DataFrame:
    """Promote first row as header and tidy the first column header."""
    df = df.copy()
    # promote first row to header
    header = df.iloc[0].astype(str).fillna("")
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = header
    if "" in df.columns:
        df = df.rename(columns={"": "Label"})
    return df

def combine_side_by_side(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Horizontally stitch multiple cleaned scorecard halves."""
    if not dfs:
        raise ValueError("No DataFrames to combine.")
    cleaned = [clean_header(x) for x in dfs]
    out = cleaned[0]
    for nxt in cleaned[1:]:
        if "Label" in nxt.columns:
            nxt = nxt.drop(columns=["Label"])
        out = pd.concat([out, nxt], axis=1)
    return out

def htmljson_to_excel(json_path: str, excel_path: str = "output.xlsx", try_combine: bool = True):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    # 1) collect ALL table-html snippets from the nested JSON
    table_htmls = list(iter_table_htmls(data))
    if not table_htmls:
        raise ValueError("No <table> HTML found inside JSON.")

    # 2) convert each HTML snippet into one or more DataFrames
    all_tables: List[pd.DataFrame] = []
    for h in table_htmls:
        all_tables.extend(read_tables_from_html(h))

    if not all_tables:
        raise ValueError("Found HTML but could not parse any tables with pandas.read_html.")

    # 3) write to Excel: Table1..N (cleaned), plus Combined if 2+ tables
    with pd.ExcelWriter(excel_path, engine="openpyxl") as xw:
        cleaned = []
        for i, df in enumerate(all_tables, start=1):
            cdf = clean_header(df)
            cdf.to_excel(xw, index=False, sheet_name=f"Table{i}")
            cleaned.append(cdf)

        if try_combine and len(all_tables) >= 2:
            combined = combine_side_by_side(all_tables)
            combined.to_excel(xw, index=False, sheet_name="Combined")

    return excel_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python html_to_excel.py <path_to_json> [output.xlsx]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) >= 3 else "output.xlsx"
    p = htmljson_to_excel(src, out, try_combine=True)
    print("Wrote:", Path(p).resolve())
