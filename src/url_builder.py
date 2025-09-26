from typing import Optional

BASE_URL = "https://ganjoor.net"

def _sanitize_slug(value: str) -> str:
    if value is None:
        raise ValueError("value must not be None")
    v = value.strip()
    v = v.strip("/")
    v = " ".join(v.split())
    if not v:
        raise ValueError("value must not be empty or only slashes")
    return v

def build_poet_url(poet: str) -> str:
    poet_slug = _sanitize_slug(poet)
    return f"{BASE_URL}/{poet_slug}"

def build_section_url(poet: str, section: str) -> str:
    poet_slug = _sanitize_slug(poet)
    section_slug = _sanitize_slug(section)
    return f"{BASE_URL}/{poet_slug}/{section_slug}"

def build_poem_url(poet: str, sh_number: int, section: Optional[str] = None) -> str:
    if not isinstance(sh_number, int) or sh_number <= 0:
        raise ValueError("sh_number must be a positive integer")
    poet_slug = _sanitize_slug(poet)
    # If section parameter is provided (even empty/whitespace), enforce sanitization
    if section is not None:
        section_slug = _sanitize_slug(section)
        return f"{BASE_URL}/{poet_slug}/{section_slug}/sh{sh_number}"
    # Only when section is truly None, build without section
    return f"{BASE_URL}/{poet_slug}/sh{sh_number}"
