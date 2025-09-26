from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict
import time
import os
import sys
import requests

# Make sure we can import url_builder when running scripts directly
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from url_builder import build_section_url, build_poem_url  # absolute import

REQUEST_TIMEOUT = 10
HEADERS = {
    "User-Agent": "GanjoorScraper/1.0 (+research; contact@example.com)"
}

@dataclass
class ProbeResult:
    poet: str
    book_or_style: str
    subsection: Optional[str]
    checked_sh: List[int]
    status_by_url: Dict[str, int]
    has_sh_pages: bool
    section_page_exists: Optional[bool]
    notes: Optional[str] = None

def http_status(url: str) -> int:
    try:
        r = requests.head(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if r.status_code == 405:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return r.status_code
    except requests.RequestException:
        return 0

def probe_task(poet: str, section: Optional[str], sh_numbers: List[int]) -> ProbeResult:
    status_by_url: Dict[str, int] = {}

    has_sh = False
    if section is not None:
        for sh in sh_numbers:
            try:
                url = build_poem_url(poet, sh, section)
            except Exception:
                status_by_url[f"build_poem_url_error(sh{sh})"] = -1
                continue
            code = http_status(url)
            status_by_url[url] = code
            if code == 200:
                has_sh = True
                break
            time.sleep(0.2)

        # Test section landing page
        try:
            s_url = build_section_url(poet, section)
            code = http_status(s_url)
            status_by_url[s_url] = code
            section_exists = (code == 200)
        except Exception:
            section_exists = None
    else:
        # No section provided: probe poet root only for completeness
        from url_builder import build_poet_url
        s_url = build_poet_url(poet)
        code = http_status(s_url)
        status_by_url[s_url] = code
        section_exists = (code == 200)

    return ProbeResult(
        poet=poet,
        book_or_style=section or "__root__",
        subsection=None,
        checked_sh=sh_numbers,
        status_by_url=status_by_url,
        has_sh_pages=has_sh,
        section_page_exists=section_exists,
        notes=None
    )
