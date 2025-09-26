import sys
import os
import json
import time
import csv

# Ensure src is importable
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

print("[INFO] CWD:", os.getcwd())
print("[INFO] SRC path:", SRC)

# Imports
try:
    from url_builder import build_poem_url, build_section_url
    from extractor import fetch_html, parse_poem_page, store_pair, load_modes
except Exception as e:
    print("[ERROR] Import failed:", e)
    sys.exit(2)

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

def read_modes():
    if not os.path.exists(MODES_PATH):
        print("[WARN] modes file not found ->", MODES_PATH)
        return {}
    try:
        return load_modes(MODES_PATH)
    except Exception as e:
        print("[WARN] failed to load modes:", e)
        return {}

def write_modes(modes: dict):
    os.makedirs(os.path.dirname(MODES_PATH), exist_ok=True)
    with open(MODES_PATH, "w", encoding="utf-8") as f:
        json.dump(modes, f, ensure_ascii=False, indent=2)
    print("[INFO] modes written ->", MODES_PATH)

def show_modes(modes: dict, poet: str):
    print("[INFO] modes keys:", list(modes.keys()))
    if poet in modes:
        print(f"[INFO] sections for {poet}:", json.dumps(modes[poet], ensure_ascii=False, indent=2))
    else:
        print(f"[INFO] poet {poet} not present in modes")

def pick_sh_section(modes: dict, poet: str):
    if poet in modes:
        for sec, cfg in modes[poet].items():
            if cfg.get("mode") == "sh_pages":
                return sec
    return None

def probe_section(poet: str, section: str, sh_samples=(1,2,5,10)):
    print(f"[PROBE] poet={poet} section={section} -> trying SH samples {sh_samples}")
    for sh in sh_samples:
        try:
            url = build_poem_url(poet, sh, section)
        except Exception as e:
            print(f"[PROBE] build_poem_url failed for sh{sh} ->", e)
            continue
        print("[PROBE] GET:", url)
        html = fetch_html(url)
        if not html:
            print("[PROBE] no HTML for", url)
            continue
        text, audio = parse_poem_page(html)
        print(f"[PROBE] parsed: text={'yes' if text else 'no'}, audio={'yes' if audio else 'no'}")
        if text:
            print("[PROBE] section looks valid for sh_pages")
            return True
        time.sleep(0.2)
    return False

def ensure_sh_section(modes: dict, poet: str):
    # Ensure poet key exists
    if poet not in modes:
        modes[poet] = {}
    # If exists
    sec = pick_sh_section(modes, poet)
    if sec:
        print(f"[INFO] found existing sh_pages section: {poet}/{sec}")
        return sec, False
    # Try common candidates
    candidates = ["ghazal", "ghazaliat", "rubai", "qaside", "masnavi", "ghaside"]
    print("[INFO] No sh_pages mapping -> probing candidates:", candidates)
    for c in candidates:
        try:
            s_url = build_section_url(poet, c)
            print("[PROBE] section landing:", s_url)
            html = fetch_html(s_url)
            if not html:
                print("[PROBE] section page not 200 for", c)
                continue
            if probe_section(poet, c):
                modes[poet][c] = {"mode": "sh_pages"}
                print(f"[INFO] autodetected sh_pages: {poet}/{c}")
                return c, True
        except Exception as e:
            print(f"[PROBE] error probing {c} ->", e)
            continue
    print("[INFO] could not auto-detect any sh_pages section")
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
    print(f"[RUN] Extracting {poet}/{section} sh{start_sh}-{end_sh}")
    for sh in range(start_sh, end_sh + 1):
        url = build_poem_url(poet, sh, section)
        print("[RUN] GET:", url)
        html = fetch_html(url)
        if not html:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "html_not_200", url])
            print("[skip]", url, "-> no HTML")
            skipped += 1
            time.sleep(0.3)
            continue
        text, audio = parse_poem_page(html)
        print(f"[RUN] parsed sh{sh}: text={'yes' if text else 'no'}, audio={'yes' if audio else 'no'}")
        if not text or not audio:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "missing_text_or_audio", url])
            print("[skip]", url, "-> missing text/audio")
            skipped += 1
            time.sleep(0.3)
            continue
        ok = store_pair(base_dir, poet, section, sh, text, audio)
        if ok:
            print("[saved]", f"{poet}/{section}/sh{sh}")
            saved += 1
        else:
            with open(failed_csv, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([poet, section, sh, "audio_download_failed", url])
            print("[skip]", url, "-> audio download failed")
            skipped += 1
        time.sleep(0.4)
    print(f"[DONE] saved={saved}, skipped={skipped}. Output under data/text and data/audio.")

def main():
    """
    Usage:
      python debug_and_run.py <poet_slug> [start_sh end_sh]
    """
    if len(sys.argv) < 2:
        print("Usage: python debug_and_run.py <poet_slug> [start_sh end_sh]")
        sys.exit(1)

    poet = sys.argv[1]
    start_sh = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end_sh = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print("[STEP] loading modes:", MODES_PATH)
    modes = read_modes()
    show_modes(modes, poet)

    print("[STEP] ensuring sh_pages section for", poet)
    section, changed = ensure_sh_section(modes, poet)
    if section is None:
        print("[HALT] no sh_pages section detected. Please run validator or add mapping manually.")
        sys.exit(2)
    if changed:
        write_modes(modes)

    print("[STEP] starting extraction…")
    extract_range(poet, section, start_sh, end_sh)

if __name__ == "__main__":
    main()
