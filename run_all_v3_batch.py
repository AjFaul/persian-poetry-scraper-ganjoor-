import os
import sys
import json
import time
import glob
import csv
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair
from subsection_finder import find_subsection_links  # create src/subsection_finder.py as provided earlier

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

def to_int_safe(token: str) -> int:
    m = re.search(r"(\d+)", str(token))
    if not m:
        raise ValueError(f"Invalid int token: {token!r}")
    return int(m.group(1))

def normalize_poet_from_filename(fname: str) -> str:
    base = os.path.basename(fname)
    name, _ = os.path.splitext(base)
    return name.strip().lower()

def probe_mode_for_path(poet: str, section_path: str, sh_sample: int = 1) -> str:
    # landing
    try:
        landing = build_section_url(poet, section_path)
    except Exception:
        print(f"[ERR] build_section_url failed for {poet}/{section_path}")
        return "unknown"
    print("[CHECK] landing:", landing)
    html = fetch_html(landing)
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

def extract_one(poet: str, section_path: str, sh_num: int, failed_csv: str):
    url = build_poem_url(poet, sh_num, section_path)
    print("[RUN] GET:", url)
    html = fetch_html(url)
    if not html:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section_path, sh_num, "html_not_200", url])
        print("[skip] no HTML")
        return False
    text, audio = parse_poem_page(html)
    print(f"[PARSE] text={'YES' if text else 'NO'}, audio={'YES' if audio else 'NO'}")
    if not text or not audio:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section_path, sh_num, "missing_text_or_audio", url])
        print("[skip] missing text/audio")
        return False
    ok = store_pair("data", poet, section_path, sh_num, text, audio)
    if not ok:
        with open(failed_csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([poet, section_path, sh_num, "audio_download_failed", url])
        print("[skip] audio download failed")
        return False
    print("[saved]")
    return True

def main():
    """
    Usage:
      python run_all_v3_batch.py [sh_sample]
    Behavior:
      - Scans inputs/excels/*.xlsx and processes every poet automatically.
      - Level-1 sections from Excel header are probed:
          * sh_pages: extract exactly one poem (sh_sample).
          * no_sh: parse landing to find immediate nested subsections; for each nested:
              - decide mode; if sh_pages -> extract one poem and move on.
          * unknown: record only.
      - All probed URLs are printed; modes are written to inputs/config/url_modes.json cumulatively.
      - Results go to data/text, data/audio, and data/metadata/{summary.csv,failed.csv}.
    """
    sh_sample = to_int_safe(sys.argv[1]) if len(sys.argv) > 1 else 1

    excels = sorted(glob.glob(os.path.join("inputs", "excels", "*.xlsx")))
    if not excels:
        print("[HALT] No Excel files found in inputs/excels")
        sys.exit(1)

    modes = load_json_safe(MODES_PATH)
    summary_csv = os.path.join("data", "metadata", "summary.csv")
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
    if not os.path.exists(summary_csv):
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section_path", "mode", "saved_one", "note"])

    if not os.path.exists(failed_csv):
        os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
        with open(failed_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["poet", "section_path", "sh", "reason", "url"])

    for xlsx in excels:
        poet = normalize_poet_from_filename(xlsx)
        print("\n" + "="*80)
        print(f"[POET] {poet} | excel={os.path.basename(xlsx)}")

        if poet not in modes:
            modes[poet] = {}

        try:
            tasks = read_excel_tasks(poet, xlsx)
        except Exception as e:
            print(f"[WARN] cannot read {xlsx}: {e}")
            continue

        # L1 sections from Excel headers
        lvl1_sections = []
        seen = set()
        for t in tasks:
            sec = (t.book_or_style or "").strip()
            if sec and sec not in seen:
                seen.add(sec)
                lvl1_sections.append(sec)

        print(f"[INFO] L1 sections:", lvl1_sections)

        for l1 in lvl1_sections:
            print("-"*60)
            print(f"[L1] {poet}/{l1}")
            mode_l1 = probe_mode_for_path(poet, l1, sh_sample=sh_sample)
            modes[poet][l1] = {"mode": mode_l1}
            saved_flag = False

            if mode_l1 == "sh_pages":
                saved_flag = extract_one(poet, l1, sh_sample, failed_csv)

            elif mode_l1 == "no_sh":
                # Explore nested subsections
                landing_url = build_section_url(poet, l1)
                print("[FETCH] landing for nested:", landing_url)
                html = fetch_html(landing_url)
                subs = find_subsection_links(html, poet, l1)
                print(f"[INFO] nested count={len(subs)} (up to 15):")
                for u in subs[:15]:
                    print("   *", u)
                # Probe nested
                for sub in subs:
                    rel = sub.replace("https://ganjoor.net", "").strip("/")
                    parts = rel.split("/")
                    if len(parts) < 3:
                        continue
                    nested_path = "/".join(parts[1:])  # keep nested slug
                    print(f"[L2] {poet}/{nested_path}")
                    mode_l2 = probe_mode_for_path(poet, nested_path, sh_sample=sh_sample)
                    modes[poet][nested_path] = {"mode": mode_l2}
                    if mode_l2 == "sh_pages" and not saved_flag:
                        saved_flag = extract_one(poet, nested_path, sh_sample, failed_csv)
                        # Keep scanning others for mapping, but only save one sample per L1

            # unknown -> nothing to extract, just record

            with open(summary_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, l1, mode_l1, "yes" if saved_flag else "no", ""])

            # Persist after each L1 to keep progress
            save_json(MODES_PATH, modes)

    print("\n[FINAL] url_modes.json updated at:", MODES_PATH)
    print("See data/metadata/summary.csv and failed.csv for results.")
    print("="*80)

if __name__ == "__main__":
    main()
