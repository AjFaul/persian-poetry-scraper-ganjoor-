import os
import sys
import json
import re
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

# ---------- helpers ----------
def load_modes():
    if not os.path.exists(MODES_PATH):
        return {}
    with open(MODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_modes(modes: dict):
    os.makedirs(os.path.dirname(MODES_PATH), exist_ok=True)
    with open(MODES_PATH, "w", encoding="utf-8") as f:
        json.dump(modes, f, ensure_ascii=False, indent=2)

def sections_from_excel(poet: str) -> list[str]:
    excel_path = os.path.join("inputs", "excels", f"{poet}.xlsx")
    if not os.path.exists(excel_path):
        return []
    tasks = read_excel_tasks(poet, excel_path)
    seen, out = set(), []
    for t in tasks:
        sec = (t.book_or_style or "").strip()
        if sec and sec not in seen:
            seen.add(sec)
            out.append(sec)
    return out

def list_nested_from_modes(poet: str, modes: dict, parent: str) -> list[str]:
    if poet not in modes: return []
    return sorted([k for k in modes[poet].keys() if "/" in k and k.startswith(parent + "/")])

def to_int_safe(s: str, default: int | None = None) -> int:
    m = re.search(r"(\d+)", str(s))
    if not m:
        if default is not None: return default
        raise ValueError("invalid number")
    return int(m.group(1))

def prompt_choice(items: list[str], title: str, extras: list[str] = None) -> str:
    if extras is None: extras = []
    opts = items + extras
    print(f"\n== {title} ==")
    for i, it in enumerate(opts, 1):
        print(f"{i}. {it}")
    while True:
        ans = input("Enter number: ").strip()
        try:
            idx = to_int_safe(ans)
            if 1 <= idx <= len(opts):
                return opts[idx-1]
        except Exception:
            pass
        print("Invalid choice.")

def discover_count(poet: str, section_path: str) -> int:
    def has_text(sh: int) -> bool:
        try:
            url = build_poem_url(poet, sh, section_path)
        except Exception:
            return False
        html = fetch_html(url)
        if not html: return False
        text, _ = parse_poem_page(html)
        return bool(text)
    if not has_text(1): return 0
    lo, hi = 1, 64
    while has_text(hi):
        lo, hi = hi, hi * 2
        time.sleep(0.1)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if has_text(mid): lo = mid
        else: hi = mid
        time.sleep(0.05)
    return lo

def extract_range(poet: str, section_path: str, start_sh: int, end_sh: int, sleep_s: float):
    base_dir = "data"
    os.makedirs(base_dir, exist_ok=True)
    failed_csv = os.path.join("data", "metadata", "failed.csv")
    os.makedirs(os.path.dirname(failed_csv), exist_ok=True)
    if not os.path.exists(failed_csv):
        with open(failed_csv, "w", encoding="utf-8") as f:
            f.write("poet,section,sh,reason,url\n")

    saved, skipped = 0, 0
    for sh in range(start_sh, end_sh + 1):
        url = build_poem_url(poet, sh, section_path)
        html = fetch_html(url)
        if not html:
            with open(failed_csv, "a", encoding="utf-8") as f:
                f.write(f"{poet},{section_path},{sh},html_not_200,{url}\n")
            print(f"[skip] {url} -> no HTML")
            skipped += 1
            time.sleep(sleep_s)
            continue
        text, audio = parse_poem_page(html)
        if not text or not audio:
            with open(failed_csv, "a", encoding="utf-8") as f:
                f.write(f"{poet},{section_path},{sh},missing_text_or_audio,{url}\n")
            print(f"[skip] {url} -> missing text/audio")
            skipped += 1
            time.sleep(sleep_s)
            continue
        ok = store_pair(base_dir, poet, section_path, sh, text, audio)
        if ok:
            print(f"[saved] {poet}/{section_path}/sh{sh}")
            saved += 1
        else:
            with open(failed_csv, "a", encoding="utf-8") as f:
                f.write(f"{poet},{section_path},{sh},audio_download_failed,{url}\n")
            print(f"[skip] {url} -> audio download failed")
            skipped += 1
        time.sleep(sleep_s)
    return saved, skipped

def download_poet(poet: str, modes: dict, rate_ms: int):
    if poet not in modes:
        print(f"[WARN] Poet '{poet}' not in mapping; skipping.")
        return
    sleep_s = max(rate_ms, 0) / 1000.0
    total_saved, total_skipped = 0, 0
    for section_path, cfg in modes[poet].items():
        if cfg.get("mode") != "sh_pages": 
            continue
        cnt = cfg.get("count")
        if not cnt:
            print(f"[INFO] discovering count for {poet}/{section_path} ...")
            cnt = discover_count(poet, section_path)
            modes[poet][section_path]["count"] = cnt
            save_modes(modes)
        if cnt <= 0:
            print(f"[INFO] no poems for {poet}/{section_path}")
            continue
        print(f"[RUN] {poet}/{section_path}: sh1..sh{cnt}")
        s, k = extract_range(poet, section_path, 1, cnt, sleep_s)
        total_saved += s
        total_skipped += k
    print(f"[POET DONE] {poet}: saved={total_saved}, skipped={total_skipped}")

# ---------- CLI ----------
def main():
    """
    Interactive downloader/browser:
    - Step 1: choose poet (includes 'All' option).
    - Step 2: choose action:
        * Browse sections (no download)
        * Download all sh_pages for this poet
    - Nested navigation: option to pick a specific section_path and download partial range.
    - Rate limit: user can set delay between requests (ms).
    """
    modes = load_modes()
    poets = sorted(modes.keys())
    if not poets:
        print("No poets in mapping. Build url_modes.json first.")
        return

    choice_poet = prompt_choice(poets, "Choose a poet (or All at end)", extras=["All"])
    rate_ms = to_int_safe(input("Delay between requests in milliseconds (e.g., 300): ").strip() or "300", 300)

    if choice_poet == "All":
        print("WARNING: downloading ALL poets can be heavy and long. Proceed? (y/n)")
        if input().strip().lower().startswith("y"):
            for p in poets:
                download_poet(p, modes, rate_ms)
        else:
            print("Cancelled.")
        return

    poet = choice_poet
    print(f"\nSelected: {poet}")
    action = prompt_choice(
        ["Browse sections", "Download ALL sections of this poet", "Download a specific section path"],
        "Choose action"
    )

    if action == "Download ALL sections of this poet":
        print("WARNING: full download for this poet can be heavy. Proceed? (y/n)")
        if input().strip().lower().startswith("y"):
            download_poet(poet, modes, rate_ms)
        else:
            print("Cancelled.")
        return

    # Build L1 sections and nested options
    l1 = sections_from_excel(poet)
    if not l1 and poet in modes:
        l1 = sorted([k for k in modes[poet].keys() if "/" not in k])

    if action == "Browse sections":
        sec = prompt_choice(l1, f"{poet}: choose a level-1 section")
        if not sec:
            print("No section chosen.")
            return
        info = modes.get(poet, {}).get(sec, {})
        print(f"[INFO] {poet}/{sec} -> mode={info.get('mode','-')}, count={info.get('count','-')}")
        print("[URL] landing:", build_section_url(poet, sec))
        print("[URL] sample sh1:", build_poem_url(poet, 1, sec))
        nested = list_nested_from_modes(poet, modes, sec)
        if nested:
            sub = prompt_choice(nested, f"{poet}/{sec}: choose nested (or back)", extras=["Back"])
            if sub != "Back":
                mm = modes.get(poet, {}).get(sub, {})
                print(f"[INFO] {poet}/{sub} -> mode={mm.get('mode','-')}, count={mm.get('count','-')}")
                print("[URL] landing:", build_section_url(poet, sub))
                print("[URL] sample sh1:", build_poem_url(poet, 1, sub))
        return

    if action == "Download a specific section path":
        print("\nPick a level-1 section first.")
        sec = prompt_choice(l1, f"{poet}: choose level-1")
        if not sec:
            print("No section chosen.")
            return
        nested = list_nested_from_modes(poet, modes, sec)
        target = sec
        if nested:
            sub = prompt_choice(nested, f"{poet}/{sec}: choose nested (or choose '{sec}' to stay on L1)", extras=[sec])
            target = sub
        cfg = modes.get(poet, {}).get(target, {})
        if cfg.get("mode") != "sh_pages":
            print(f"[INFO] {poet}/{target} is not marked sh_pages (mode={cfg.get('mode')}). Aborting.")
            return
        cnt = cfg.get("count")
        if not cnt:
            print("[INFO] discovering count...")
            cnt = discover_count(poet, target)
            modes[poet][target] = modes.get(poet, {}).get(target, {})
            modes[poet][target]["mode"] = "sh_pages"
            modes[poet][target]["count"] = cnt
            save_modes(modes)
        print(f"Range available: 1..{cnt}")
        start = to_int_safe(input("Start sh (default 1): ").strip() or "1", 1)
        end = to_int_safe(input(f"End sh (default {cnt}): ").strip() or str(cnt), cnt)
        end = min(end, cnt)
        print(f"[RUN] downloading {poet}/{target} sh{start}..sh{end}")
        saved, skipped = extract_range(poet, target, start, end, rate_ms/1000.0)
        print(f"[DONE] saved={saved}, skipped={skipped}")
        return

if __name__ == "__main__":
    main()
