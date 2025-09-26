import sys
import os

# add src to sys.path so imports work when running this file directly
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from url_builder import BASE_URL, build_poet_url, build_section_url, build_poem_url

def show(title, value):
    print(f"{title}: {value}")

def main():
    print("=== Poet root URLs ===")
    show("hafez", build_poet_url("hafez"))
    show("saadi", build_poet_url("saadi"))
    show("ferdousi", build_poet_url("ferdousi"))

    print("\n=== Section URLs ===")
    show("hafez/ghazal", build_section_url("hafez", "ghazal"))
    show("saadi/ghazal", build_section_url("saadi", "ghazal"))
    show("ferdousi/shahnameh", build_section_url("ferdousi", "shahnameh"))

    print("\n=== Poem URLs without section ===")
    show("hafez sh1", build_poem_url("hafez", 1))
    show("saadi sh5", build_poem_url("saadi", 5))
    show("khayyam sh12", build_poem_url("khayyam", 12))

    print("\n=== Poem URLs with section ===")
    show("hafez/ghazal sh2", build_poem_url("hafez", 2, "ghazal"))
    show("ferdousi/shahnameh sh10", build_poem_url("ferdousi", 10, "shahnameh"))
    show("saadi/ghazal sh30", build_poem_url("saadi", 30, "ghazal"))

    print("\n=== Trim and cleanup demo ===")
    show("trimmed poet", build_poet_url("  /hafez/  "))
    show("trimmed poem with section", build_poem_url(" /hafez/ ", 30, " /ghazal/ "))

if __name__ == "__main__":
    main()
