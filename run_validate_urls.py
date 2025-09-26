import sys
import os
import json
import datetime

# add src to import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from validator import probe_task

def unique_sections(tasks):
    seen = set()
    result = []
    for t in tasks:
        key = (t.poet, t.book_or_style)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result

def main():
    """
    Usage:
      python run_validate_urls.py <poet_slug> <excel_path> [sh_numbers...]
    Example:
      python run_validate_urls.py hafez inputs\\excels\\hafez.xlsx 1 2 10 30
    """
    if len(sys.argv) < 3:
        print("Usage: python run_validate_urls.py <poet_slug> <excel_path> [sh_numbers...]")
        sys.exit(1)

    poet = sys.argv[1]
    excel_path = sys.argv[2]
    sh_numbers = [int(x) for x in sys.argv[3:]] if len(sys.argv) > 3 else [1, 2, 5, 10, 30]

    tasks = read_excel_tasks(poet, excel_path)
    # Collapse to unique sections per book/style
    sections = unique_sections(tasks)

    os.makedirs(os.path.join("data", "metadata", "validators"), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join("data", "metadata", "validators", f"{poet}-{ts}.jsonl")

    print(f"Poet={poet} sections={len(sections)} -> report: {out_path}")
    with open(out_path, "w", encoding="utf-8") as f:
        for (p, section) in sections:
            res = probe_task(p, section, sh_numbers)
            line = json.dumps(res.__dict__, ensure_ascii=False)
            f.write(line + "\n")
            # Console summary
            print(f"- {section}: has_sh_pages={res.has_sh_pages}, section_exists={res.section_page_exists}")
            for url, code in list(res.status_by_url.items())[:5]:
                print(f"  {code}  {url}")

    print("Done. Open the JSONL report and mark sections with has_sh_pages=false as no-sh sections.")
    print("Later we will create a mapping file to handle these cases automatically.")

if __name__ == "__main__":
    main()
