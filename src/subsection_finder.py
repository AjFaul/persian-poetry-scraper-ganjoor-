import re
from urllib.parse import urljoin

BASE = "https://ganjoor.net"

def find_subsection_links(html: str, poet: str, section: str):
    """
    Extract immediate subsection links from a section landing page.
    Returns list of absolute URLs under /<poet>/<section>/...
    """
    if not html:
        return []
    links = re.findall(r'href="([^"]+)"', html)
    out = []
    prefix = f"/{poet}/{section}/"
    for href in links:
        if href.startswith(prefix):
            out.append(urljoin(BASE, href))
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq
