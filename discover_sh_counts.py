import os
import sys
import json
import glob
import re
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

def load_json_safe(path: str):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def has_text(poet: str, section_path: str, sh_num: int) -> bool:
    try:
        url = build_poem_url(poet, sh_num, section_path)
    except Exception:
        return False
    html = fetch_html(url)
    if not html:
        return False
    text, _audio = parse_poem_page(html)
    return bool(text)

def find_last_sh(poet: str, section_path: str, start_guess: int = 1, sleep_s: float = 0.15) -> int:
    """
    Find the largest sh number that returns HTML with parseable text.
    Strategy:
      1) Exponential search to bracket [lo, hi] such that lo exists and hi doesn't.
      2) Binary search inside [lo, hi).
    Returns the last sh >= 1 with text, or 0 if none found.
    """
    # If even sh1 has no text => early out
    if not has_text(poet, section_path, 1):
        return 0

    lo = 1
    hi = max(start_guess, 2)
    # Step 1: exponential grow until miss
    while has_text(poet, section_path, hi):
        lo = hi
        hi = hi * 2
        time.sleep(sleep_s)

    # Step 2: binary search in (lo, hi]
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if has_text(poet, section_path, mid):
            lo = mid
        else:
            hi = mid
        time.sleep(sleep_s)

    return lo

def sections_from_excel(poet: str, excel_path: str):
    tasks = read_excel_tasks(poet, excel_path)
    seen = set()
    out = []
    for t in tasks:
        sec = (t.book_or_style or "").strip()
        if sec and sec not in seen:
            seen.add(sec)
            out.append(sec)
    return out

def main():
    """
    Usage:
      python discover_sh_counts.py
    Behavior:
      - Scans inputs/excels/*.xlsx
      - For each poet:
          * Read level-1 sections from its Excel.
          * For each section path present in url_modes.json with mode='sh_pages':
              - Discover last sh and write 'count' field under that mapping.
          * For sections with mode='no_sh': skip count (no sh pages).
          * For sections missing from mapping: first probe landing+sh1 to decide mode minimally,
            and if sh_pages, compute count; else record as no_sh/unknown.
      - No downloads; only HTML checks. All updates are merged into inputs/config/url_modes.json
        as:
          "poet": {
             "section_or_nested": { "mode": "sh_pages", "count": 495 },
             ...
          }
    """
    modes = load_json_safe(MODES_PATH)
    excels = sorted(glob.glob(os.path.join("inputs", "excels", "*.xlsx")))
    if not excels:
        print("[HALT] No excels in inputs/excels")
        sys.exit(1)

    for xlsx in excels:
        poet = os.path.splitext(os.path.basename(xlsx))[0].lower()
        print("\n" + "="*70)
        print(f"[POET] {poet}")

        if poet not in modes:
            modes[poet] = {}

        # Level-1 sections from Excel
        l1_sections = sections_from_excel(poet, xlsx)
        print("[INFO] L1 from Excel:", l1_sections)

        # Ensure at least minimal mapping for L1 sections (probe sh1 quickly)
        for l1 in l1_sections:
            if l1 not in modes[poet]:
                # minimal probe to assign mode quickly
                landing = build_section_url(poet, l1)
                print("[CHECK] landing:", landing)
                html = fetch_html(landing)
                if not html:
                    modes[poet][l1] = {"mode": "unknown"}
                    continue
                if has_text(poet, l1, 1):
                    modes[poet][l1] = {"mode": "sh_pages"}
                else:
                    modes[poet][l1] = {"mode": "no_sh"}

        # For every mapping entry of this poet that is sh_pages, compute count
        for section_path, cfg in list(modes[poet].items()):
            if cfg.get("mode") != "sh_pages":
                continue
            print(f"[COUNT] discovering last sh for {poet}/{section_path} ...")
            last_sh = find_last_sh(poet, section_path, start_guess=64)
            modes[poet][section_path]["count"] = last_sh
            print(f"[COUNT] {poet}/{section_path} -> {last_sh}")

        # Persist after each poet
        save_json(MODES_PATH, modes)
        print("[WRITE] mapping updated:", MODES_PATH)

    print("\n[DONE] counts discovered and written to url_modes.json")

if __name__ == "__main__":
    main()
