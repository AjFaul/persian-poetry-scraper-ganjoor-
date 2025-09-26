import sys
import os

# Ensure src is importable when running directly
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from url_builder import BASE_URL, build_poet_url, build_section_url, build_poem_url

def ok(msg):
    print(f"[OK] {msg}")

def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)

def expect_raises(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        return True
    return False

def main():
    # Basic cases
    assert build_poet_url("hafez") == f"{BASE_URL}/hafez"
    ok("build_poet_url basic")

    assert build_section_url("hafez", "ghazal") == f"{BASE_URL}/hafez/ghazal"
    ok("build_section_url basic")

    assert build_poem_url("hafez", 2, "ghazal") == f"{BASE_URL}/hafez/ghazal/sh2"
    ok("build_poem_url with section")

    assert build_poem_url("hafez", 1) == f"{BASE_URL}/hafez/sh1"
    ok("build_poem_url without section")

    # Trimming
    assert build_poet_url("  /hafez/  ") == f"{BASE_URL}/hafez"
    ok("build_poet_url trimming")

    assert build_poem_url(" /hafez/ ", 30, " /ghazal/ ") == f"{BASE_URL}/hafez/ghazal/sh30"
    ok("build_poem_url trimming")

    # Invalid inputs that must raise
    if not expect_raises(build_poet_url, " / / "):
        fail("build_poet_url should raise on blank")

    if not expect_raises(build_poem_url, "hafez", 0, "ghazal"):
        fail("build_poem_url should raise on zero sh_number")

    if not expect_raises(build_poem_url, "hafez", -5, "ghazal"):
        fail("build_poem_url should raise on negative sh_number")

    if not expect_raises(build_poem_url, "   ", 2, "ghazal"):
        fail("build_poem_url should raise on blank poet")

    if not expect_raises(build_poem_url, "hafez", 2, "   "):
        fail("build_poem_url should raise on blank section")

    ok("All assertions passed")
    print("All url_builder checks passed.")

if __name__ == "__main__":
    main()
