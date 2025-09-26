import os
import sys
import json
import time
import csv
import glob
import re

# Import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_poem_url, build_section_url
from extractor import fetch_html, parse_poem_page, store_pair, load_modes

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
    # e.g., D:\...\inputs\excels\hafez.xlsx -> "hafez"
    base = os.path.basename(fname)
    name, _ = os.path.splitext(base)
    return name.strip().lower()

def pick_sh_section(modes: dict, poet: str) -> str | None:
    if poet in modes:
        for sec, cfg in modes[poet].items():
            if cfg.get("mode") == "sh_pages":
                return sec
    return None

def probe_section(poet: str, section: str, sh_samples=(1, 2, 5, 10)) -> bool:
    # Validate that some sh page returns HTML and has parseable text
    for sh in sh_samples:
        try:
            url = build_poem_url(poet, sh, section)
        except Exception:
            continue
        html = fetch_html(url)
        if not html:
            continue
        text, _audio = parse_poem_page(html)
        if text:
            return True
        time.sleep(0.2)
    return False

def ensure_sh_section(modes: dict, poet: str) -> tuple[str | None, bool]:
    # Ensure poet key
    if poet not in modes:
        modes[poet] = {}
    # Already present?
    sec = pick_sh_section(modes, poet)
    if sec:
        return sec, False
    # Try common candidates
    candidates = ["ghazal", "ghazaliat", "rubai", "qaside", "masnavi", "ghaside"]
    for c in candidates:
        try:
            s_url = build_section_url(poet, c)
            html = fetch_html(s_url)
            if not html:
                continue
            if probe_section(poet, c):
                modes[poet][c] = {"mode": "sh_pages"}
                return c, True
        except Exception:
            continue
    return None, False

def to_int_safe(token: str) -> int:
    m = re.search(r"(\d+)", str(token))
    if not m:
        raise ValueError(f"Invalid int token: {token!r}")
    return int(m.group(1))

def extract_range(poet: str, section: str, start_sh: int, end_sh: int, failed_csv: str) -> tuple[int, int]:
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
      python run_all_from_excels.py [start_sh end_sh]
    Default range: 1 5
    It scans inputs/excels/*.xlsx, builds or fixes url_modes.json per poet,
    then extracts sample range for each poet's sh_pages section.
    """
    start_sh = to_int_safe(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_sh = to_int_safe(sys.argv[2]) if len(sys.argv) > 2 else 5

    excels_dir = os.path.join("inputs", "excels")
    files = sorted(glob.glob(os.path.join(excels_dir, "*.xlsx")))
    if not files:
        print("[HALT] No Excel files found under inputs/excels")
        sys.exit(1)

    modes = load_json_safe(MODES_PATH)

    # Summary CSV
    summary_csv = os.path.join("data", "metadata", "summary.csv")
    os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
    if not os.path.exists(summary_csv):
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["poet", "section", "range", "saved", "skipped", "mapping_changed"])

    failed_csv = os.path.join("data", "metadata", "failed.csv")

    for xlsx in files:
        poet = normalize_poet_from_filename(xlsx)
        print("\n" + "="*70)
        print(f"[POET] {poet} | excel={os.path.basename(xlsx)}")

        # Ensure/auto-detect a sh_pages section
        section, changed = ensure_sh_section(modes, poet)
        if section is None:
            # If cannot detect sh_pages, we still keep modes as-is for manual review
            print(f"[WARN] Could not auto-detect sh_pages for {poet}. Please validate and edit mapping.")
            # Write unknown/no_sh hint if poet missing
            if poet not in modes:
                modes[poet] = {}
            if "__hint__" not in modes[poet]:
                modes[poet]["__hint__"] = {"mode": "unknown"}
            save_json(MODES_PATH, modes)
            with open(summary_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, "-", f"sh{start_sh}-{end_sh}", 0, 0, False])
            continue

        # Persist mapping if changed
        if changed:
            save_json(MODES_PATH, modes)
            print(f"[INFO] mapping updated -> {poet}/{section} set to sh_pages")

        # Extract sample range
        print(f"[RUN] extracting {poet}/{section} sh{start_sh}-{end_sh}")
        saved, skipped = extract_range(poet, section, start_sh, end_sh, failed_csv)

        with open(summary_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section, f"sh{start_sh}-{end_sh}", saved, skipped, changed])

    print("\n[DONE] Batch finished. See:")
    print(" - data/metadata/summary.csv (per-poet results)")
    print(" - data/metadata/failed.csv (skipped reasons)")
    print(" - inputs/config/url_modes.json (final mapping)")
    print("="*70)

if __name__ == "__main__":
    main()
