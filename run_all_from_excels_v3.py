import os
import sys
import json
import time
import csv
import glob
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair
from subsection_finder import find_subsection_links

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

def probe_mode_sh(poet: str, section_path: str, sh_sample: int = 1) -> str:
    """
    Probe a section or nested section path (e.g., 'divana/ghazal-attar'):
    - If landing 200 and sh_sample has text => sh_pages
    - If landing 200 but sh_sample not textual => no_sh
    - Else unknown
    """
    # landing
    sec_url = build_section_url(poet, section_path)
    print("[CHECK] landing:", sec_url)
    html = fetch_html(sec_url)
    if not html:
        print("[RESULT] landing HTML=NO -> unknown")
        return "unknown"

    # sh sample
    try:
        p_url = build_poem_url(poet, sh_sample, section_path)
    except Exception:
        p_url = None
    if p_url:
        print("[CHECK] sample poem:", p_url)
        html2 = fetch_html(p_url)
        if html2:
            text, _audio = parse_poem_page(html2)
            print("[RESULT] sh text? ->", "YES" if text else "NO")
            if text:
                return "sh_pages"
    print("[RESULT] treat as no_sh")
    return "no_sh"

def extract_one(poet: str, section_path: str, sh_num: int, failed_csv: str) -> tuple[bool, str]:
    url = build_poem_url(poet, sh_num, section_path)
    print("[RUN] GET:", url)
    html = fetch_html(url)
    if not html:
        reason = "html_not_200"
        print("[skip]", reason)
        return False, reason
    text, audio = parse_poem_page(html)
    print(f"[PARSE] text={'YES' if text else 'NO'}, audio={'YES' if audio else 'NO'}")
    if not text or not audio:
        reason = "missing_text_or_audio"
        print("[skip]", reason)
        return False, reason
    ok = store_pair("data", poet, section_path, sh_num, text, audio)
    if not ok:
        reason = "audio_download_failed"
        print("[skip]", reason)
        return False, reason
    print("[saved]")
    return True, "saved"

def main():
    """
    Usage:
      python run_all_from_excels_v3.py <poet_slug> [sh_sample]
    Example:
      python run_all_from_excels_v3.py attar 1
    Behavior:
      - Reads first-row sections (level-1) from poet's Excel.
      - For each level-1 section:
          * Probe its mode (sh_pages / no_sh / unknown).
          * If no_sh: fetch landing, parse immediate subsections, and for each nested section:
              - Probe nested mode using one sh sample.
              - If nested sh_pages: attempt to extract exactly one poem and stop.
      - Updates inputs/config/url_modes.json with discovered modes for both level-1 and nested sections.
      - Prints every URL it checks for full transparency.
    """
    if len(sys.argv) < 2:
        print("Usage: python run_all_from_excels_v3.py <poet_slug> [sh_sample]")
        sys.exit(1)

    poet = sys.argv[1].strip().lower()
    sh_sample = to_int_safe(sys.argv[2]) if len(sys.argv) > 2 else 1

    excel_path = os.path.join("inputs", "excels", f"{poet}.xlsx")
    if not os.path.exists(excel_path):
        print("[HALT] Excel not found:", excel_path)
        sys.exit(2)

    modes = load_json_safe(MODES_PATH)
    if poet not in modes:
        modes[poet] = {}

    # Summary files
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
    if not os.path.exists(failed_csv):
        with open(failed_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section_path", "sh", "reason", "url"])

    tasks = read_excel_tasks(poet, excel_path)
    # Unique level-1 sections
    lvl1_sections = []
    seen = set()
    for t in tasks:
        sec = (t.book_or_style or "").strip()
        if sec and sec not in seen:
            seen.add(sec)
            lvl1_sections.append(sec)

    print(f"[INFO] L1 sections from Excel for {poet}:", lvl1_sections)

    for l1 in lvl1_sections:
        print("\n" + "-"*60)
        print(f"[L1] probing {poet}/{l1}")
        mode_l1 = probe_mode_sh(poet, l1, sh_sample=sh_sample)
        modes[poet][l1] = {"mode": mode_l1}

        if mode_l1 == "sh_pages":
            print(f"[L1] extracting one poem {poet}/{l1}/sh{sh_sample}")
            ok, reason = extract_one(poet, l1, sh_sample, failed_csv)
            # if saved or skipped, continue to next L1
            continue

        if mode_l1 == "no_sh":
            # Explore nested subsections under landing
            l1_url = build_section_url(poet, l1)
            print("[FETCH] landing for nested scan:", l1_url)
            l1_html = fetch_html(l1_url)
            subs = find_subsection_links(l1_html, poet, l1)
            print(f"[INFO] found {len(subs)} nested under {l1} (show up to 15):")
            for u in subs[:15]:
                print("  *", u)

            # Probe a few nested subsections
            for sub in subs[:10]:
                rel = sub.replace("https://ganjoor.net", "").strip("/")
                # rel looks like "attar/divana/ghazal-attar"
                parts = rel.split("/")
                if len(parts) < 3:
                    continue
                nested_path = "/".join(parts[1:])  # "divana/ghazal-attar"
                print(f"[L2] probing nested {poet}/{nested_path}")
                mode_l2 = probe_mode_sh(poet, nested_path, sh_sample=sh_sample)
                # Store nested mapping as "divana/ghazal-attar": {mode: ...}
                modes[poet][nested_path] = {"mode": mode_l2}
                if mode_l2 == "sh_pages":
                    print(f"[L2] extracting one poem {poet}/{nested_path}/sh{sh_sample}")
                    ok, reason = extract_one(poet, nested_path, sh_sample, failed_csv)
                    # Stop after first success attempt at L2 to keep it short
                    break

        # unknown: nothing to extract, just record

        # Persist mapping after each L1 iteration
        save_json(MODES_PATH, modes)

    print("\n[FINAL] mapping saved to:", MODES_PATH)
    print("[DONE] run completed.")

if __name__ == "__main__":
    main()
