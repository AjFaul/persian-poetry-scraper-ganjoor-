import os
import sys
import json
import time
import re
import csv

# Import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")
EXCEL_PATH = os.path.join("inputs", "excels", "attar.xlsx")

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

def unique_sections_from_excel(poet: str, excel_path: str):
    tasks = read_excel_tasks(poet, excel_path)
    seen = set()
    sections = []
    for t in tasks:
        sec = (t.book_or_style or "").strip()
        if not sec:
            continue
        if sec not in seen:
            seen.add(sec)
            sections.append(sec)
    return sections

def probe_section_mode(poet: str, section: str, sh_sample: int = 1):
    """
    Try to detect if section has sh pages.
    Returns one of: "sh_pages", "no_sh", "unknown"
    """
    # Check section landing
    try:
        s_url = build_section_url(poet, section)
        s_html = fetch_html(s_url)
        section_ok = s_html is not None
    except Exception:
        section_ok = False

    if section_ok:
        # Try one poem sh page
        try:
            p_url = build_poem_url(poet, sh_sample, section)
        except Exception:
            p_url = None
        if p_url:
            p_html = fetch_html(p_url)
            if p_html:
                text, _audio = parse_poem_page(p_html)
                if text:
                    return "sh_pages"
        return "no_sh"
    return "unknown"

def extract_one(poet: str, section: str, sh_num: int):
    """
    Extract exactly one poem; save only if both text and audio exist.
    """
    base_dir = "data"
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
    if not os.path.exists(failed_csv):
        with open(failed_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section", "sh", "reason", "url"])

    url = build_poem_url(poet, sh_num, section)
    html = fetch_html(url)
    if not html:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section, sh_num, "html_not_200", url])
        print(f"[skip] {url} -> no HTML")
        return False

    text, audio = parse_poem_page(html)
    if not text or not audio:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section, sh_num, "missing_text_or_audio", url])
        print(f"[skip] {url} -> missing text/audio")
        return False

    ok = store_pair(base_dir, poet, section, sh_num, text, audio)
    if ok:
        print(f"[saved] {poet}/{section}/sh{sh_num}")
        return True
    else:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section, sh_num, "audio_download_failed", url])
        print(f"[skip] {url} -> audio download failed")
        return False

def main():
    """
    Usage:
      python run_attar_one.py
    Reads sections from inputs/excels/attar.xlsx, decides mode per section using 1 sample (sh1),
    updates inputs/config/url_modes.json, and extracts exactly one poem for the first section
    that is detected as sh_pages.
    """
    poet = "attar"
    if not os.path.exists(EXCEL_PATH):
        print("[HALT] Missing Excel:", EXCEL_PATH)
        sys.exit(1)

    # Load/prepare mapping
    modes = load_json_safe(MODES_PATH)
    if poet not in modes:
        modes[poet] = {}

    # Read sections from Attar Excel
    sections = unique_sections_from_excel(poet, EXCEL_PATH)
    if not sections:
        print("[HALT] No sections found in Excel headers for attar.")
        sys.exit(2)

    print(f"[INFO] sections from Excel for {poet}:", sections)

    # Decide mode per section with one sample sh (sh1)
    sh_sample = 1
    first_ok_section = None
    for sec in sections:
        mode = probe_section_mode(poet, sec, sh_sample=sh_sample)
        modes[poet][sec] = {"mode": mode}
        print(f"[MAP] {poet}/{sec} -> {mode}")
        if first_ok_section is None and mode == "sh_pages":
            first_ok_section = sec

    # Save mapping
    save_json(MODES_PATH, modes)
    print("[INFO] mapping saved ->", MODES_PATH)

    # If we found a sh_pages section, extract exactly one poem (sh1)
    if first_ok_section:
        print(f"[RUN] extracting one poem: {poet}/{first_ok_section}/sh{sh_sample}")
        ok = extract_one(poet, first_ok_section, sh_sample)
        print("[DONE] result:", "saved" if ok else "skipped")
    else:
        print("[DONE] No section detected as sh_pages. Consider validator for attar or manual mapping.")

if __name__ == "__main__":
    main()
