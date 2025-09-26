import sys
import os
import json
import time
import csv

# import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from url_builder import build_poem_url, build_section_url
from extractor import fetch_html, parse_poem_page, store_pair, load_modes

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

def read_modes():
    if not os.path.exists(MODES_PATH):
        return {}
    return load_modes(MODES_PATH)

def write_modes(modes: dict):
    os.makedirs(os.path.dirname(MODES_PATH), exist_ok=True)
    with open(MODES_PATH, "w", encoding="utf-8") as f:
        json.dump(modes, f, ensure_ascii=False, indent=2)

def has_sh_pages_section(modes: dict, poet: str) -> bool:
    return poet in modes and any(cfg.get("mode") == "sh_pages" for cfg in modes[poet].values())

def pick_sh_section(modes: dict, poet: str):
    # Prefer an existing sh_pages section
    if poet in modes:
        for sec, cfg in modes[poet].items():
            if cfg.get("mode") == "sh_pages":
                return sec
    return None

def probe_section(poet: str, section: str, sh_samples=(1,2,5,10)):
    # Return True if any poem URL in samples returns HTML 200 and parseable text
    ok_any = False
    for sh in sh_samples:
        url = build_poem_url(poet, sh, section)
        html = fetch_html(url)
        if not html:
            continue
        text, audio = parse_poem_page(html)
        # موفقیت برای شناسایی الگو: وجود متن کافی است؛ الزام همزمان متن+خوانش را در ذخیره‌سازی رعایت می‌کنیم
        if text:
            ok_any = True
            break
    return ok_any

def ensure_sh_section(modes: dict, poet: str):
    # If poet not present, create empty
    if poet not in modes:
        modes[poet] = {}

    # 1) if already has sh_pages, return it
    sec = pick_sh_section(modes, poet)
    if sec:
        return sec, False  # no change

    # 2) try common sections heuristically
    candidates = ["ghazal", "ghazaliat", "rubai", "qaside", "masnavi", "ghaside"]
    for c in candidates:
        try:
            # quick probe: section landing 200?
            s_url = build_section_url(poet, c)
            html = fetch_html(s_url)
            if not html:
                continue
            # now probe a few sh pages
            if probe_section(poet, c):
                modes[poet][c] = {"mode": "sh_pages"}
                return c, True
        except Exception:
            continue

    # 3) fallback: no sh_pages found
    return None, False

def extract_range(poet: str, section: str, start_sh: int, end_sh: int):
    base_dir = "data"
    os.makedirs(base_dir, exist_ok=True)
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
    if not os.path.exists(failed_csv):
        with open(failed_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section", "sh", "reason", "url"])

    saved = 0
    skipped = 0
    for sh in range(start_sh, end_sh + 1):
        url = build_poem_url(poet, sh, section)
        html = fetch_html(url)
        if not html:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "html_not_200", url])
            print(f"[skip] {url} -> no HTML")
            skipped += 1
            time.sleep(0.3)
            continue
        text, audio = parse_poem_page(html)
        if not text or not audio:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "missing_text_or_audio", url])
            print(f"[skip] {url} -> missing text/audio")
            skipped += 1
            time.sleep(0.3)
            continue
        ok = store_pair(base_dir, poet, section, sh, text, audio)
        if ok:
            print(f"[saved] {poet}/{section}/sh{sh}")
            saved += 1
        else:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "audio_download_failed", url])
            print(f"[skip] {url} -> audio download failed")
            skipped += 1
        time.sleep(0.4)
    return saved, skipped

def main():
    """
    Usage:
      python run_autofix_and_extract.py <poet_slug> [start_sh end_sh]
    Example:
      python run_autofix_and_extract.py hafez 1 5
    """
    if len(sys.argv) < 2:
        print("Usage: python run_autofix_and_extract.py <poet_slug> [start_sh end_sh]")
        sys.exit(1)

    poet = sys.argv[1]
    start_sh = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end_sh = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    modes = read_modes()
    section = pick_sh_section(modes, poet)

    if section is None:
        print(f"No sh_pages section mapped for poet={poet}. Probing common sections...")
        section, changed = ensure_sh_section(modes, poet)
        if section is None:
            print("Could not auto-detect a sh_pages section. Please run validator again or add mapping manually.")
            sys.exit(2)
        if changed:
            write_modes(modes)
            print(f"Updated mapping: {poet}/{section} -> sh_pages written to {MODES_PATH}")

    print(f"Extracting poet={poet} section={section} sh{start_sh}-{end_sh}")
    saved, skipped = extract_range(poet, section, start_sh, end_sh)
    print
