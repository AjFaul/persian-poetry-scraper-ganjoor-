import os
import sys
import re
from urllib.parse import urljoin

# import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from url_builder import build_section_url, build_poem_url
from extractor import fetch_html, parse_poem_page, store_pair

BASE = "https://ganjoor.net"

def find_subsection_links(html: str, poet: str, section: str):
    """
    Parse the section landing page and extract all links that look like
    immediate subsections under /<poet>/<section>/...
    Returns list of absolute URLs.
    """
    links = re.findall(r'href="([^"]+)"', html or "")
    out = []
    prefix = f"/{poet}/{section}/"
    for href in links:
        if href.startswith(prefix):
            out.append(urljoin(BASE, href))
    # Deduplicate while keeping order
    seen = set()
    uniq = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

def classify_subsection_url(url: str):
    """
    Given a subsection URL like https://ganjoor.net/attar/divana/ghazal-attar/,
    try sh1 and decide mode: sh_pages if sh1 has text, else no_sh if landing exists.
    """
    # landing
    print("[CHECK] subsection landing:", url)
    html = fetch_html(url)
    if not html:
        print("[RESULT] landing HTML=NO -> unknown")
        return "unknown"

    # try sh1 under the same path
    sh1 = url.rstrip("/") + "/sh1"
    print("[CHECK] sample poem URL:", sh1)
    html2 = fetch_html(sh1)
    if html2:
        text, _audio = parse_poem_page(html2)
        print("[RESULT] sh1 text? ->", "YES" if text else "NO")
        if text:
            return "sh_pages"
    # landing existed but sh1 not textual -> treat as no_sh
    return "no_sh"

def extract_one(poet: str, section: str, sh_num: int):
    url = build_poem_url(poet, sh_num, section)
    print("[RUN] GET:", url)
    html = fetch_html(url)
    if not html:
        print("[skip] no HTML")
        return False
    text, audio = parse_poem_page(html)
    print(f"[PARSE] text={'YES' if text else 'NO'}, audio={'YES' if audio else 'NO'}")
    if not text or not audio:
        print("[skip] missing text/audio (policy)")
        return False
    ok = store_pair("data", poet, section, sh_num, text, audio)
    print("[saved]" if ok else "[skip] audio download failed")
    return ok

def main():
    poet = "attar"
    section = "divana"  # top-level that is no_sh in your mapping
    # 1) landing of divana
    sec_url = build_section_url(poet, section)
    print("[CHECK] section landing:", sec_url)
    html = fetch_html(sec_url)
    print("[RESULT] landing HTML ->", "YES" if html else "NO")
    if not html:
        return

    # 2) extract subsection links from landing
    subs = find_subsection_links(html, poet, section)
    print("[INFO] found subsections (first 20 shown):")
    for u in subs[:20]:
        print("  -", u)
    if not subs:
        print("[NOTE] No subsections detected under divana; content likely inline on landing pages.")
        return

    # 3) classify first few subsections and show their modes
    tested = 0
    for sub_url in subs[:10]:
        mode = classify_subsection_url(sub_url)
        print(f"[MODE] {sub_url} -> {mode}")
        tested += 1
        # If a sh_pages is found, try to save one poem from it
        if mode == "sh_pages":
            # derive 'section/subsection' slug to hand over to build_poem_url
            rel = sub_url.replace(BASE, "").strip("/")
            # rel is like "attar/divana/ghazal-attar"
            parts = rel.split("/")
            if len(parts) >= 3:
                # section_for_poem is "divana/ghazal-attar"
                section_for_poem = "/".join(parts[1:])  # keep nested path
                print("[TRY] extracting one from:", section_for_poem)
                extract_one(poet, section_for_poem, 1)
            break

    print("[DONE] Probe finished.")

if __name__ == "__main__":
    main()
