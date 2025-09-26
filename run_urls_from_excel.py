import sys
import os
import re

# Allow importing from src when running directly
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from parser_excel import read_excel_tasks
from url_builder import build_section_url, build_poem_url

def to_int_safe(token: str) -> int:
    """
    Convert a token to int by stripping non-digit chars at ends.
    Accepts forms like '30.', ' 12 ', 'sh15' -> tries to recover digits.
    """
    if token is None:
        raise ValueError("Empty token")
    s = str(token).strip()
    m = re.search(r"(\d+)", s)
    if not m:
        raise ValueError(f"Not a valid integer: {token!r}")
    return int(m.group(1))

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_urls_from_excel.py <poet_slug> <excel_path> [<sample_sh_numbers>...]")
        print("Example: python run_urls_from_excel.py hafez inputs\\excels\\hafez.xlsx 1 2 30")
        sys.exit(1)

    poet = sys.argv[1]
    excel_path = sys.argv[2]

    try:
        sh_numbers = [to_int_safe(x) for x in sys.argv[3:]] if len(sys.argv) > 3 else [1, 2, 3]
    except Exception as e:
        print(f"Invalid SH number argument(s): {e}")
        sys.exit(2)

    tasks = read_excel_tasks(poet, excel_path)

    print(f"Poet: {poet}")
    print(f"Tasks from Excel: {len(tasks)}")
    for i, t in enumerate(tasks[:10], start=1):
        print(f"[Task {i}] book/style='{t.book_or_style}', subsection='{t.subsection}'")
        try:
            section_url = build_section_url(poet, t.book_or_style)
            print(f"  Section URL: {section_url}")
        except Exception as e:
            print(f"  Section URL error: {e}")

        for sh in sh_numbers[:3]:
            try:
                poem_url = build_poem_url(poet, sh, t.book_or_style)
                print(f"  Poem URL (sh{sh}): {poem_url}")
            except Exception as e:
                print(f"  Poem URL error for sh{sh}: {e}")

if __name__ == "__main__":
    main()
