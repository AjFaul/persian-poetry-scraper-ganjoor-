import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from extractor import fetch_html, parse_poem_page
from url_builder import build_poem_url

def check(poet, section_path, sh):
    url = build_poem_url(poet, sh, section_path)
    print("\nURL:", url)
    html = fetch_html(url)
    if not html:
        print("HTML: NO (status != 200)")
        return
    text, audio = parse_poem_page(html)
    print("TEXT lines:", 0 if not text else len(text.splitlines()))
    print("AUDIO:", "YES" if audio else "NO")
    if text:
        print("--- Preview ---")
        for ln in text.splitlines()[:6]:
            print(ln)
        print("---------------")

def main():
    samples = [
        ("hafez", "ghazal", 1),
        ("hafez", "ghazal", 2),
        ("attar", "divana/ghazal-attar", 1),
        ("attar", "khosroname", 1),
    ]
    for s in samples:
        check(*s)

if __name__ == "__main__":
    main()
