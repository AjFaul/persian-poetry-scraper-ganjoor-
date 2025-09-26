import os
import sys
import json
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

def load_modes():
    if not os.path.exists(MODES_PATH):
        return {}
    with open(MODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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

def to_int_safe(s: str) -> int:
    m = re.search(r"(\d+)", s)
    if not m:
        raise ValueError("invalid number")
    return int(m.group(1))

def discover_count(poet: str, section_path: str) -> int:
    # lightweight count discovery like before (exponential + binary)
    def has_text(sh: int) -> bool:
        try:
            url = build_poem_url(poet, sh, section_path)
        except Exception:
            return False
        html = fetch_html(url)
        if not html: return False
        text, _ = parse_poem_page(html)
        return bool(text)

    if not has_text(1):
        return 0
    lo, hi = 1, 64
    while has_text(hi):
        lo, hi = hi, hi * 2
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if has_text(mid): lo = mid
        else: hi = mid
    return lo

def pick(items: list[str], title: str) -> str:
    if not items:
        return ""
    print(f"\n== {title} ==")
    for i, it in enumerate(items, 1):
        print(f"{i}. {it}")
    while True:
        sel = input("Enter number: ").strip()
        try:
            idx = to_int_safe(sel)
            if 1 <= idx <= len(items):
                return items[idx-1]
        except Exception:
            pass
        print("Invalid choice, try again.")

def list_nested_from_modes(poet: str, modes: dict) -> list[str]:
    # nested paths are those containing '/'
    if poet not in modes: return []
    keys = [k for k in modes[poet].keys() if "/" in k]
    return sorted(keys)

def main():
    """
    Interactive CLI to browse poets -> sections -> nested sections using url_modes.json.
    Operations:
      - Only prints/validates URLs; does not download.
      - Shows mode and count if available.
      - Can compute count on-demand for sh_pages without count.
    """
    modes = load_modes()
    poets = sorted(modes.keys())
    if not poets:
        # fallback to excels list
        excels = sorted(os.listdir(os.path.join("inputs", "excels")))
        poets = [os.path.splitext(x)[0] for x in excels if x.lower().endswith(".xlsx")]
    if not poets:
        print("No poets found in mapping or excels.")
        return

    poet = pick(poets, "Choose a poet")
    if not poet:
        print("No poet chosen.")
        return

    # level-1 sections from Excel (preferred) or from mapping keys without '/'
    l1 = sections_from_excel(poet)
    if not l1 and poet in modes:
        l1 = sorted([k for k in modes[poet].keys() if "/" not in k])

    section = pick(l1, f"Choose a level-1 section for {poet}")
    if not section:
        print("No section chosen.")
        return

    # Show info for level-1
    m = modes.get(poet, {}).get(section, {})
    print(f"\n[INFO] {poet}/{section} -> mode={m.get('mode','-')}, count={m.get('count','-')}")
    print("[URL] landing:", build_section_url(poet, section))
    print("[URL] sample sh1:", build_poem_url(poet, 1, section))

    # If mode=no_sh, show nested list derived from mapping or by probing landing quickly
    nested_options = [k for k in list_nested_from_modes(poet, modes) if k.startswith(section + "/")]
    if m.get("mode") == "no_sh" and not nested_options:
        # quick derive from landing
        from subsection_finder import find_subsection_links
        html = fetch_html(build_section_url(poet, section))
        subs = find_subsection_links(html, poet, section)
        for u in subs:
            rel = u.replace("https://ganjoor.net","").strip("/").split("/",1)[1]
            nested_options.append(rel)

    nested_options = sorted(set(nested_options))
    if nested_options:
        nested = pick(nested_options, f"Choose nested under {section}")
        if nested:
            mm = modes.get(poet, {}).get(nested, {})
            print(f"\n[INFO] {poet}/{nested} -> mode={mm.get('mode','-')}, count={mm.get('count','-')}")
            print("[URL] landing:", build_section_url(poet, nested))
            print("[URL] sample sh1:", build_poem_url(poet, 1, nested))
            if mm.get("mode") == "sh_pages" and "count" not in mm:
                ans = input("Compute count now? (y/n): ").strip().lower()
                if ans.startswith("y"):
                    cnt = discover_count(poet, nested)
                    print(f"[COUNT] {poet}/{nested} -> {cnt}")
                    modes.setdefault(poet,{}).setdefault(nested,{})["mode"]="sh_pages"
                    modes[poet][nested]["count"] = cnt
                    with open(MODES_PATH,"w",encoding="utf-8") as f:
                        json.dump(modes,f,ensure_ascii=False,indent=2)
                    print("[WRITE] url_modes.json updated.")

    print("\nTip: to actually extract later, run your batch/extractor using the shown paths and counts.")
    print("Exit.")

if __name__ == "__main__":
    main()
