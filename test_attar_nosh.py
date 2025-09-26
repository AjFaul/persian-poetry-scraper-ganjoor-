import os
import sys
import json

# import path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from extractor import fetch_html, load_modes
from url_builder import build_section_url, build_poem_url

MODES_PATH = os.path.join("inputs", "config", "url_modes.json")

def main():
    """
    Usage:
      python test_attar_nosh.py [section_name]
    If section_name is omitted, the script auto-picks the first section of attar marked as no_sh
    in inputs/config/url_modes.json.
    For visibility, it prints the exact URLs it probes.
    """
    poet = "attar"

    if not os.path.exists(MODES_PATH):
        print("[HALT] Missing mapping file:", MODES_PATH)
        sys.exit(1)

    modes = load_modes(MODES_PATH)
    if poet not in modes:
        print(f"[HALT] Poet '{poet}' not found in mapping. Please run the mapper first.")
        sys.exit(2)

    # choose section
    section_arg = sys.argv[1].strip() if len(sys.argv) > 1 else None

    target_section = None
    if section_arg:
        # Use provided section
        target_section = section_arg
        mode = modes[poet].get(target_section, {}).get("mode")
        if not mode:
            print(f"[WARN] '{target_section}' not present in mapping for {poet}. Proceeding anyway…")
        else:
            print(f"[INFO] Mapping for {poet}/{target_section}: mode={mode}")
    else:
        # Auto-pick first no_sh section
        for sec, cfg in modes[poet].items():
            if cfg.get("mode") == "no_sh":
                target_section = sec
                print(f"[INFO] Auto-picked no_sh section: {poet}/{target_section}")
                break
        if not target_section:
            print(f"[HALT] No section with mode=no_sh found for {poet}.")
            sys.exit(3)

    # 1) Show and fetch the section landing URL (the page that should contain all text if no_sh)
    try:
        section_url = build_section_url(poet, target_section)
    except Exception as e:
        print(f"[ERROR] build_section_url failed: {e}")
        sys.exit(4)

    print("[CHECK] Section landing URL:", section_url)
    html = fetch_html(section_url)
    if html:
        print("[RESULT] Section landing returned HTML=YES (status assumed 200)")
        print("[NOTE] For mode=no_sh we do NOT expect sh pages like poet/section/shN to exist meaningfully.")
    else:
        print("[RESULT] Section landing returned HTML=NO (likely 404 or blocked)")
        print("[NOTE] If landing is not available, mapping to no_sh is probably incorrect.")
        sys.exit(0)

    # 2) For demonstration, also show what a sh URL WOULD look like and check it once
    #    This is only to illustrate why saving is skipped for no_sh.
    try:
        sample_sh_url = build_poem_url(poet, 1, target_section)
    except Exception as e:
        sample_sh_url = None
        print(f"[INFO] build_poem_url failed (as expected for no_sh): {e}")

    if sample_sh_url:
        print("[CHECK] Hypothetical sh URL (for illustration):", sample_sh_url)
        html2 = fetch_html(sample_sh_url)
        print("[RESULT] sh1 HTML present? ->", "YES" if html2 else "NO")
        print("[NOTE] Even if sh page returns HTML, for no_sh sections content is on the landing page;")
        print("       and because project requires both text+audio for saving, and landing usually lacks a single audio file,")
        print("       saving is intentionally skipped for no_sh.")
    else:
        print("[NOTE] No sh URL constructed (input validation stopped it), which is consistent with no_sh logic.")

    print("[DONE] no_sh check completed. If needed, we can implement separate extraction logic for no_sh pages later.")

if __name__ == "__main__":
    main()
