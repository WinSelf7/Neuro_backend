#!/usr/bin/env python3
import os, sys, json, re
from pathlib import Path
import pandas as pd

# --- OpenAI 1.88.0 style ---
from openai import OpenAI
# ⚠️ Hardcoding a key is not recommended; prefer env vars in production.
client = OpenAI(api_key="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")

# ======= Settings =======
APPLY_NDB_CAP = True       # set False to disable Net Double Bogey capping
DEFAULT_PLAYER_CH = 0      # default Course Handicap if not provided per player

# Canonical sheet header after the label column
HOLE_HEADER = [
    "1","2","3","4","5","6","7","8","9","OUT","",
    "10","11","12","13","14","15","16","17","18","IN","TOT","Hcp","NET"
]

# =========================
# Prompt: force the model to split packed runs in-extraction
# =========================
PROMPT_INSTRUCTIONS = r"""
You are given OCR text from a golf scorecard screenshot.

Return STRICT JSON **only** with this schema:
{
  "tee": ["<array of tee types from: BLACK, BLACK/BLUE, BLUE, BLUE/WHITE, WHITE, WHITE/GOLD, GOLD, GOLD/GREEN, GREEN>"],
  "gender": "<MEN|WOMEN|UNKNOWN>",
  "players": [
    {
      "name": "<player name>",
      "front9": [h1,h2,h3,h4,h5,h6,h7,h8,h9],
      "back9":  [h10,h11,h12,h13,h14,h15,h16,h17,h18]
    }
  ]
}

Normalization rules (MANDATORY):

A) Scope
- Do NOT return yardages, PAR rows, or HCP/Stroke Index rows in the JSON. Extract only: tee, gender, players[], and each player's hole-by-hole scores.

B) Tee Information
- The scorecard may contain one or multiple tee types (e.g., BLACK, BLUE, WHITE, etc.).
- Return tee types as an array. If only one tee is present, return a single-item array.
- If multiple tees are present, extract and return all tee types found.
- Example: ["BLACK", "BLUE"] or ["WHITE"] or ["GOLD", "GREEN"]

C) Split scorecards (two-table images) and row alignment
- The input may contain a LEFT table (front 9) with row labels (tee, Par, Stroke Index, players) and a RIGHT table (back 9) often WITHOUT row labels.
- When the RIGHT table lacks labels, map its rows to the LEFT table by **row order**:
  1) Right row 1 = tee yardages (ignore)
  2) Right row 2 = Par (ignore)
  3) Right row 3 = Stroke Index (ignore)
  4+) Right rows = Players, in the same order as the LEFT table’s player rows
- If only one side is present, extract whatever holes are present from that side and leave the other side as [].
- If multiple players are present, keep player order consistent across left/right when pairing front and back.

D) Recognizing back-nine–only cards
- If you see a header like **"10 11 12 13 14 15 16 17 18 In Total"**, treat this as the back-nine header.
- The numeric row directly under that header is the tee yardage (ignore), then Par (ignore), then Stroke Index (ignore),
  then player rows for the back nine.
- In this case, **front9 must be []**, and **back9** is extracted from the corresponding player row beneath.
- Example (back-nine only):
  Header:  "10 11 12 13 14 15 16 17 18 In Total"
  Tee:     "511 153 395 481 165 402 413 162 528 3210 6536"   (ignore)
  Par:     "5 3 4 5 3 4 4 3 5 36 73"                        (ignore)
  Player:  "6 4 4 5 3 5 4 6 5 1 96"
  → Interpret the first 9 scores before the total, dropping any extra small token immediately before the total (often a stray field like PH):
    back9 = [6,4,4,5,3,5,4,6,5]
    front9 = []

E) Interpreting player scores
1) Packed digit run for a nine (≥ 6 digits):
   - Represents exactly 9 hole scores in order.
   - Split into 9 integers:
     * Treat “10” as a single value 10.
     * Ignore lone ‘0’ digits otherwise.
   - Clamp to 1..17 if OCR noise.
   - Example: "69684763756" → [6,9,6,8,4,7,6,3,7] (sum = 56).

2) Token list with ambiguous two-digit tokens:
   - Example tokens: ["64","13","6","4","6","6","3","7","55"]
   - If the **last token on the player row** is ≥ 20, treat it as that nine’s TOTAL (target sum).
   - Two-digit tokens may be:
     * One score if 10..17 (e.g., "13" → 13), OR
     * Two single digits (e.g., "13" → 1,3)
   - **Preference rule:** Prefer interpreting 10..17 as single scores. Only split a two-digit token (e.g., "13" → 1,3) if needed to achieve **exactly 9** scores and match the TOTAL.
   - Choose the expansion that yields EXACTLY 9 scores and matches the TOTAL when possible; otherwise choose the closest sum.
   - Examples (must match exactly):
     ["64","13","6","4","6","6","3","7","55"] → [6,4,13,6,4,6,6,3,7] (sum = 55)
     ["7","10","5","4","4","6","5","5","50"] → [7,10,5,4,4,6,5,5,4] (sum = 50)

3) Right-table player rows with an extra small token before the total:
   - If there are **>9** tokens <18 before the first ≥20 token (the total), **drop the last small token immediately before the total**, then take the preceding 9 as the hole scores.
   - Example: "6 4 4 5 3 5 4 6 5 1 96" → drop the "1", back9 = [6,4,4,5,3,5,4,6,5], total=96.

4) Mixed cases:
   - If both front and back for a player appear mixed together, take the first 9 resolved scores as front9 and the next 9 as back9.
   - If only a total (≥20) appears without per-hole numbers for a side, return [] for that side.

F) Names
- Normalize names to "First Last". Comma input like "Page, Emma" is acceptable.

G) Output
- Output JSON ONLY. No prose, no code fences.
H) Validity constraints for front9/back9
- Each entry in front9/back9 MUST be an integer in the range 1..17 (inclusive). Do NOT include totals, OUT/IN, or any aggregate numbers in these arrays.
- If a token is ≥ 20, treat it as a total/aggregate and EXCLUDE it from the per-hole arrays.
- If you see a token like “55” mid-row that is NOT a total, split it into two scores [5,5]. In general, when a token >17 is clearly not a total, split it into its digits, keeping 10..17 as single values when present.
- Return exactly 9 values per side when that side is present; otherwise return [].
"""


# =========================
# Strict schema for Responses API
# =========================
EXTRACTION_SCHEMA = {
    "name": "golf_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["tee", "gender", "players"],
        "properties": {
            "tee": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "BLACK",
                        "BLACK/BLUE",
                        "BLUE",
                        "BLUE/WHITE",
                        "WHITE",
                        "WHITE/GOLD",
                        "GOLD",
                        "GOLD/GREEN",
                        "GREEN"
                    ]
                },
                "minItems": 1,  # Ensure at least one tee is included
                "uniqueItems": True  # Prevent duplicate tees
            },
            "gender": {
                "type": "string",
                "enum": ["MEN", "WOMEN", "UNKNOWN"]
            },
            "players": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "front9", "back9"],
                    "properties": {
                        "name": {"type": "string"},
                        "front9": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 0,
                            "maxItems": 9
                        },
                        "back9": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 0,
                            "maxItems": 9
                        },
                        # Optional Course Handicap (if OCR sees it)
                        "hcp": {"type": "integer"}
                    }
                }
            }
        }
    },
    "strict": True
}


# =========================
# OpenAI helpers
# =========================
def _responses_extract(md_text: str, model: str) -> dict:
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You extract structured data from noisy OCR text and return strict JSON only."},
            {"role": "user", "content": PROMPT_INSTRUCTIONS + "\n\nMD TEXT:\n" + md_text},
        ],
        response_format={"type": "json_schema", "json_schema": EXTRACTION_SCHEMA},
        temperature=0,
    )
    return json.loads(resp.output_text.strip())

def _chat_fallback_extract(md_text: str, model: str) -> dict:
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You extract structured data from noisy OCR text and return strict JSON only."},
            {"role": "user", "content": PROMPT_INSTRUCTIONS + "\n\nMD TEXT:\n" + md_text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = chat.choices[0].message.content.strip()

    print("content======>", content)
    if content.startswith("```"):
        content = re.sub(r"^```(json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return json.loads(content)

def call_openai_extract(md_text: str, model: str = "gpt-4o-mini") -> dict:
    try:
        return _responses_extract(md_text, model)
    except Exception:
        return _chat_fallback_extract(md_text, model)

# =========================
# Course helpers
# =========================
def load_course_reference(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _extract_18_from_schema_row(row):
    """
    From a 23-length row with OUT/''/IN/TOT/etc, return holes 1..18 only.
    Layout: [1..9, OUT, "", 10..18, IN, TOT, Hcp, NET]
    """
    if not isinstance(row, list):
        return [None]*18
    front9 = row[0:9]
    back9  = row[11:20]
    return list(front9) + list(back9)

def get_pars_18(course: dict):
    return _extract_18_from_schema_row(course.get("PAR") or [])

def get_stroke_index_18(course: dict, gender: str):
    g = (gender or "").upper()
    if g == "WOMEN":
        row = course.get("HCP Women") or course.get("HCP WOMEN") or []
    else:
        row = course.get("HCP Men") or course.get("HCP MEN") or []
    return _extract_18_from_schema_row(row)

# =========================
# Name & formatting helpers
# =========================
def _invert_name(full: str) -> str:
    s = (full or "").strip()
    if not s:
        return "Player"
    parts = s.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return s

def _title_gender(g: str) -> str:
    g = (g or "").upper()
    if g == "MEN": return "Men"
    if g == "WOMEN": return "Women"
    return "Unknown"

def _title_tee(t: str) -> str:
    t = (t or "").upper()
    return "/".join(p.capitalize() for p in t.split("/")) if t else "Blue"

def _safe_sum(nums):
    try:
        return int(sum(int(x) for x in nums if isinstance(x, (int, float))))
    except Exception:
        return ""

def _pad_row(row, target_len):
    r = row[:]
    if len(r) < target_len:
        r += [""] * (target_len - len(r))
    return r[:target_len]

# =========================
# Scores → row & DataFrame builder
# =========================
def _scores_to_row(front9, back9):
    v1 = list(front9 or [])
    v2 = list(back9 or [])
    if len(v1) < 9: v1 += [""] * (9 - len(v1))
    if len(v2) < 9: v2 += [""] * (9 - len(v2))
    out9 = _safe_sum(v1) if v1.count("") == 0 else ""
    in9  = _safe_sum(v2) if v2.count("") == 0 else ""
    tot  = _safe_sum((front9 or []) + (back9 or [])) if (len(front9 or [])==9 and len(back9 or [])==9) else ""
    return v1 + [out9, ""] + v2 + [in9, tot, "", ""]

def build_three_row_dataframe(course: dict, extraction: dict) -> pd.DataFrame:
    """
    Uses extraction (tee/gender/players) as returned by the model.
    Optionally applies Net Double Bogey caps to player scores before writing.
    """
    target_len = 1 + len(HOLE_HEADER)

    # 1) HOLE header
    hole_row = _pad_row(["HOLE"] + course.get("HOLE", HOLE_HEADER), target_len)

       # 2) Tee row (yardages)
    tee_array = extraction.get("tee") or ["BLUE"]
    tee_key = tee_array[0].upper()  # Take the first tee
    gender  = (extraction.get("gender") or "UNKNOWN").upper()
    tee_label = f"{_title_tee(tee_key)} - {_title_gender(gender)}"
    tee_vals  = course.get(tee_key, [""] * len(HOLE_HEADER))
    tee_row   = _pad_row([tee_label] + tee_vals, target_len)

    # 3) Par row
    par_row = _pad_row(["Par"] + course.get("PAR", [""] * len(HOLE_HEADER)), target_len)

    # 4) Stroke Index row(s)
    hcp_rows = []
    if gender == "MEN":
        hcp_rows.append(_pad_row(["HCP Men"] + course.get("HCP Men", [""] * len(HOLE_HEADER)), target_len))
    elif gender == "WOMEN":
        hcp_rows.append(_pad_row(["HCP Women"] + course.get("HCP Women", [""] * len(HOLE_HEADER)), target_len))
    else:
        hcp_rows.append(_pad_row(["HCP Men"] + course.get("HCP Men", [""] * len(HOLE_HEADER)), target_len))
        hcp_rows.append(_pad_row(["HCP Women"] + course.get("HCP Women", [""] * len(HOLE_HEADER)), target_len))

    # Prepare NDB caps if enabled
    pars_18 = get_pars_18(course)
    si_18   = get_stroke_index_18(course, gender)

    # 5) Player rows (use model’s arrays directly, only optional NDB cap)
    player_rows = []
    for p in extraction.get("players", []):
        label = _invert_name(p.get("name"))

        f = list(p.get("front9", []))
        b = list(p.get("back9", []))

        values = _scores_to_row(f, b)
        player_rows.append(_pad_row([label] + values, target_len))

    rows = [hole_row, tee_row, par_row] + hcp_rows + player_rows
    return pd.DataFrame(rows)

def build_eleven_row_dataframe(course: dict, extraction: dict) -> pd.DataFrame:
    """
    Build the table with this exact row order:
      1-5)  BLACK, BLACK/BLUE, BLUE, BLUE/WHITE, WHITE
      6)    HCP Men
      7-10) 4 men players (scores)
      11)   HOLE
      12)   PAR
      13-16)4 women players (scores)
      17-20)WHITE/GOLD, GOLD, GOLD/GREEN, GREEN
      21)   HCP Women
    """
    target_len = 1 + len(HOLE_HEADER)

    def _tee_row(tee_key: str, label_override: str = None):
        key = (tee_key or "").upper()
        vals = course.get(key, [""] * len(HOLE_HEADER))
        label = label_override if label_override is not None else _title_tee(key)
        return _pad_row([label] + vals, target_len)

    def _hcp_row(which: str):
        # which = "Men" or "Women"
        key = f"HCP {which}"
        vals = course.get(key, [""] * len(HOLE_HEADER))
        return _pad_row([key] + vals, target_len)

    def _hole_row():
        return _pad_row(["HOLE"] + course.get("HOLE", HOLE_HEADER), target_len)

    def _par_row():
        return _pad_row(["Par"] + course.get("PAR", [""] * len(HOLE_HEADER)), target_len)

    def _player_row(p: dict | None, fallback_label: str):
        if not p:
            # empty row placeholder
            return _pad_row([fallback_label] + _scores_to_row([], []), target_len)
        label = _invert_name(p.get("name"))
        f = list(p.get("front9", []) or [])
        b = list(p.get("back9", []) or [])
        return _pad_row([label] + _scores_to_row(f, b), target_len)

    # Determine which block receives the extracted players
    gender = (extraction.get("gender") or "UNKNOWN").upper()
    players = list(extraction.get("players", []))
    men_players = players if gender in ("MEN", "UNKNOWN") else []
    women_players = players if gender == "WOMEN" else []

    # Cap / slice to 4 and pad to 4 for each group
    men_players = (men_players[:4] + [None] * 4)[:4]
    women_players = (women_players[:4] + [None] * 4)[:4]

    # Build rows in required order
    rows = []
    # 1-5: top tees
    for tee in ["BLACK", "BLACK/BLUE", "BLUE", "BLUE/WHITE", "WHITE"]:
        rows.append(_tee_row(tee))

    # 6: HCP Men
    rows.append(_hcp_row("Men"))

    # 7-10: 4 men players
    for i in range(4):
        rows.append(_player_row(men_players[i], f"Player {i+1} (Men)"))

    # 11: HOLE
    rows.append(_hole_row())
    # 12: PAR
    rows.append(_par_row())

    # 13-16: 4 women players
    for i in range(4):
        rows.append(_player_row(women_players[i], f"Player {i+1} (Women)"))

    # 17-20: bottom tees
    for tee in ["WHITE/GOLD", "GOLD", "GOLD/GREEN", "GREEN"]:
        rows.append(_tee_row(tee))

    # 21: HCP Women
    rows.append(_hcp_row("Women"))

    return pd.DataFrame(rows)


# =========================
# Excel writer
# =========================
def write_excel(df: pd.DataFrame, out_path: Path):
    out_path = Path(out_path)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, header=False, sheet_name="Scorecard")
        wb = writer.book
        ws = writer.sheets["Scorecard"]

        header_fmt = wb.add_format({"bold": True, "align": "center", "valign": "vcenter", "border":1})
        cell_fmt   = wb.add_format({"align": "center", "valign": "vcenter", "border":1})
        label_fmt  = wb.add_format({"bold": True, "align": "right", "valign": "vcenter", "border":1})
        shade_fmt  = wb.add_format({"align":"center","valign":"vcenter","border":1,"bg_color":"#D9E1F2","bold":True})
        shade_label_fmt = wb.add_format({"bold":True,"align":"right","valign":"vcenter","border":1,"bg_color":"#D9E1F2"})

        nrows, ncols = df.shape
        ws.set_column(0, 0, 18)
        ws.set_column(1, ncols-1, 6)

        for r in range(nrows):
            for c in range(ncols):
                v = df.iat[r, c]
                fmt = cell_fmt
                if c == 0:
                    fmt = label_fmt
                if r in (0, 1, 2):  # HOLE / Tee / Par shaded
                    fmt = shade_fmt if c != 0 else shade_label_fmt
                ws.write(r, c, v, fmt)

        ws.freeze_panes(3, 1)
ALL_TEES = ["BLACK","BLACK/BLUE","BLUE","BLUE/WHITE","WHITE","WHITE/GOLD","GOLD","GOLD/GREEN","GREEN"]
  
def _normalize_tee_list(tee_val):
    # tee_val can be a string or a list[str]
    if isinstance(tee_val, str):
        tees = [tee_val]
    elif isinstance(tee_val, list):
        tees = tee_val
    else:
        tees = []
    # normalize case + strip whitespace
    norm = []
    for t in tees:
        if isinstance(t, str):
            norm.append(t.strip().upper())
    # dedupe while preserving order
    seen = set()
    out = []
    for t in norm:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def _is_all_tees(extraction: dict) -> bool:
    tees = _normalize_tee_list(extraction.get("tee"))
    return set(tees) == set(ALL_TEES) and len(tees) == len(ALL_TEES)
# =========================
# CLI
# =========================
def main():
    if len(sys.argv) < 4:
        print("Usage: python make_scorecard_from_md_openai.py <input.md> <course_reference.json> <output.xlsx>")
        sys.exit(1)

    in_md = Path(sys.argv[1])
    course_json = Path(sys.argv[2])
    out_xlsx = Path(sys.argv[3])

    md_text = in_md.read_text(encoding="utf-8", errors="ignore")
    course   = load_course_reference(course_json)   # must include HOLE, PAR, tees, HCP Men/Women
    extract  = call_openai_extract(md_text)         # tee (str|list), gender, players (optionally "hcp")
    print("extract=====>", extract)

    # === choose layout ===
    if _is_all_tees(extract):
        # All nine tees present: write the 21-row layout you requested
        df = build_eleven_row_dataframe(course, extract)
    else:
        # Single tee (or partial tees): keep the original simple 3-row layout
        df = build_three_row_dataframe(course, extract)

    write_excel(df, out_xlsx)
    print(f"Wrote {out_xlsx}")

if __name__ == "__main__":
    main()