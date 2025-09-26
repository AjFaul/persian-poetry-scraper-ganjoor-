import sys
import os
import json

def decide_mode(entry: dict) -> str:
    # If any sh URL worked -> sh_pages
    if entry.get("has_sh_pages") is True:
        return "sh_pages"
    # If sh URLs failed but section landing is 200 -> no_sh
    if entry.get("has_sh_pages") is False and entry.get("section_page_exists") is True:
        return "no_sh"
    # Otherwise unknown (needs manual review)
    return "unknown"

def main():
    """
    Usage:
      python build_url_modes.py <report_jsonl_path> <poet_slug>
    Example:
      python build_url_modes.py data\\metadata\\validators\\hafez-20250926-142911.jsonl hafez
    Output:
      inputs/config/url_modes.json (merged per poet)
    """
    if len(sys.argv) < 3:
        print("Usage: python build_url_modes.py <report_jsonl_path> <poet_slug>")
        sys.exit(1)

    report_path = sys.argv[1]
    poet = sys.argv[2]

    if not os.path.exists(report_path):
        print(f"Report not found: {report_path}")
        sys.exit(2)

    os.makedirs(os.path.join("inputs", "config"), exist_ok=True)
    modes_path = os.path.join("inputs", "config", "url_modes.json")

    # Load existing mapping if present
    mapping = {}
    if os.path.exists(modes_path):
        with open(modes_path, "r", encoding="utf-8") as f:
            try:
                mapping = json.load(f)
            except Exception:
                mapping = {}

    if poet not in mapping:
        mapping[poet] = {}

    count = 0
    with open(report_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            section = entry.get("book_or_style") or "__root__"
            mode = decide_mode(entry)
            mapping[poet][section] = {"mode": mode}
            count += 1

    with open(modes_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"Wrote/updated: {modes_path} (sections processed: {count})")

if __name__ == "__main__":
    main()
