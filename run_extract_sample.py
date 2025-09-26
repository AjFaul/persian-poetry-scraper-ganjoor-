import sys
import os
import csv
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from url_builder import build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair, load_modes

def pick_first_sh_pages_section(modes: dict, poet: str) -> str:
    if poet not in modes:
        raise ValueError(f"No modes for poet: {poet}")
    for section, cfg in modes[poet].items():
        if cfg.get("mode") == "sh_pages":
            return section
    raise ValueError(f"No sh_pages section found for poet: {poet}")

def main():
    """
    Usage:
      python run_extract_sample.py <poet_slug> [start_sh end_sh]
    Example:
      python run_extract_sample.py hafez 1 5
    """
    if len(sys.argv) < 2:
        print("Usage: python run_extract_sample.py <poet_slug> [start_sh end_sh]")
        sys.exit(1)

    poet = sys.argv[1]
    start_sh = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end_sh = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    # Load modes
    modes_path = os.path.join("inputs", "config", "url_modes.json")
    if not os.path.exists(modes_path):
        print(f"Missing modes file: {modes_path}")
        sys.exit(2)
    modes = load_modes(modes_path)

    # Choose first sh_pages section
    section = pick_first_sh_pages_section(modes, poet)
    print(f"Poet={poet} | Section={section} | Range sh{start_sh}..sh{end_sh}")

    # Prepare failed log
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
    if not os.path.exists(failed_csv):
        with open(failed_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["poet", "section", "sh", "reason", "url"])

    # Iterate and extract
    base_dir = os.path.join("data")
    os.makedirs(base_dir, exist_ok=True)

    for sh in range(start_sh, end_sh + 1):
        url = build_poem_url(poet, sh, section)
        html = fetch_html(url)
        if not html:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "html_not_200", url])
            print(f"[skip] {url} -> no HTML")
            time.sleep(0.3)
            continue

        text, audio = parse_poem_page(html)
        if not text or not audio:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "missing_text_or_audio", url])
            print(f"[skip] {url} -> missing text/audio")
            time.sleep(0.3)
            continue

        ok = store_pair(base_dir, poet, section, sh, text, audio)
        if ok:
            print(f"[saved] sh{sh}")
        else:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "audio_download_failed", url])
            print(f"[skip] {url} -> audio download failed")
        time.sleep(0.4)

    print("Done sample extraction.")

if __name__ == "__main__":
    main()
