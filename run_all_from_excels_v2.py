import os
import sys
import json
import time
import csv
import glob
import re
from typing import Tuple, Optional

# Import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_poem_url, build_section_url
from extractor import fetch_html, parse_poem_page, store_pair

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

def normalize_poet_from_filename(fname: str) -> str:
    base = os.path.basename(fname)
    name, _ = os.path.splitext(base)
    return name.strip().lower()

def to_int_safe(token: str) -> int:
    m = re.search(r"(\d+)", str(token))
    if not m:
        raise ValueError(f"Invalid int token: {token!r}")
    return int(m.group(1))

def probe_section_mode(poet: str, section: str, sh_samples=(1, 2, 5, 10)) -> Tuple[str, dict]:
    """
    Return (mode, status_by_url). mode in {"sh_pages","no_sh","unknown"}.
    """
    status = {}

    # 1) Probe section landing
    try:
        s_url = build_section_url(poet, section)
        html = fetch_html(s_url)
        status[s_url] = 200 if html else 0
        section_ok = html is not None
    except Exception:
        section_ok = False

    # 2) If section landing ok, try sh pages
    has_sh = False
    if section_ok:
        for sh in sh_samples:
            try:
                p_url = build_poem_url(poet, sh, section)
            except Exception:
                continue
            html = fetch_html(p_url)
            status[p_url] = 200 if html else 0
            if not html:
                continue
            text, _audio = parse_poem_page(html)
            if text:
                has_sh = True
                break
            time.sleep(0.15)

    if has_sh:
        return "sh_pages", status
    if section_ok:
        return "no_sh", status
    return "unknown", status

def extract_sample(poet: str, section: str, start_sh: int, end_sh: int, failed_csv: str) -> Tuple[int, int]:
    base_dir = "data"
    os.makedirs(base_dir, exist_ok=True)
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
            print(f"[skip] {poet}/{section}/sh{sh} -> no HTML")
            skipped += 1
            time.sleep(0.25)
            continue
        text, audio = parse_poem_page(html)
        if not text or not audio:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "missing_text_or_audio", url])
            print(f"[skip] {poet}/{section}/sh{sh} -> missing text/audio")
            skipped += 1
            time.sleep(0.25)
            continue
        ok = store_pair(base_dir, poet, section, sh, text, audio)
        if ok:
            print(f"[saved] {poet}/{section}/sh{sh}")
            saved += 1
        else:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "audio_download_failed", url])
            print(f"[skip] {poet}/{section}/sh{sh} -> audio download failed")
            skipped += 1
        time.sleep(0.35)
    return saved, skipped

def main():
    """
    Usage:
      python run_all_from_excels_v2.py [start_sh end_sh]
    Reads each Excel to get its section names (first row headers),
    determines mode per section (sh_pages / no_sh / unknown),
    updates inputs/config/url_modes.json, and extracts sample range
    only for sections marked sh_pages.
    """
    start_sh = to_int_safe(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_sh = to_int_safe(sys.argv[2]) if len(sys.argv) > 2 else 5

    excels_dir = os.path.join("inputs", "excels")
    files = sorted(glob.glob(os.path.join(excels_dir, "*.xlsx")))
    if not files:
        print("[HALT] No Excel files found under inputs/excels")
        sys.exit(1)

    modes = load_json_safe(MODES_PATH)

    summary_csv = os.path.join("data", "metadata", "summary.csv")
    os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
    if not os.path.exists(summary_csv):
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section", "mode", "range", "saved", "skipped"])

    failed_csv = os.path.join("data", "metadata", "failed.csv")

    for xlsx in files:
        poet = normalize_poet_from_filename(xlsx)
        print("\n" + "="*70)
        print(f"[POET] {poet} | excel={os.path.basename(xlsx)}")

        # Read sections from Excel headers
        try:
            tasks = read_excel_tasks(poet, xlsx)
        except Exception as e:
            print(f"[WARN] cannot read {xlsx}: {e}")
            continue

        # Unique sections from headers
        sections = []
        seen = set()
        for t in tasks:
            sec = (t.book_or_style or "").strip()
            if not sec:
                continue
            if sec not in seen:
                seen.add(sec)
                sections.append(sec)

        if poet not in modes:
            modes[poet] = {}

        # Decide mode per section using real Excel headers
        for sec in sections:
            mode_prev = modes[poet].get(sec, {}).get("mode")
            mode, _status = probe_section_mode(poet, sec)
            modes[poet][sec] = {"mode": mode}
            print(f"[MAP] {poet}/{sec} -> {mode} (prev={mode_prev})")

        # Persist mapping after each poet
        save_json(MODES_PATH, modes)

        # Extract only for sh_pages sections
        for sec, cfg in modes[poet].items():
            if cfg.get("mode") != "sh_pages":
                continue
            print(f"[RUN] extracting {poet}/{sec} sh{start_sh}-{end_sh}")
            saved, skipped = extract_sample(poet, sec, start_sh, end_sh, failed_csv)
            with open(summary_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, sec, "sh_pages", f"sh{start_sh}-{end_sh}", saved, skipped])

    print("\n[DONE] See updated mapping at:", MODES_PATH)
    print(" - data/metadata/summary.csv (per-poet-section results)")
    print(" - data/metadata/failed.csv (skipped reasons)")

if __name__ == "__main__":
    main()
