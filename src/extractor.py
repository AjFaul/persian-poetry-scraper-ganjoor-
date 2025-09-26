import re
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 15
HEADERS = {"User-Agent": "GanjoorScraper/1.0 (+research; contact@example.com)"}

def fetch_html(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return r.text
        return None
    except requests.RequestException:
        return None

def parse_poem_page(html: str):
    """
    Extract (poem_text, audio_url) precisely:
    - Walk couplets/hemistich containers instead of generic page text.
    - Return None for missing pieces.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove global noise
    for tag in soup.find_all(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # Heuristic: locate poem container
    candidates = []
    candidates += soup.select("div.poem, article .poem, main .poem")
    candidates += soup.select("div#poem, article #poem, main #poem")
    if not candidates:
        candidates = soup.select("div[class*='beyt'], div[class*='couplet'], div[class*='verse']")
    poem_root = candidates[0] if candidates else soup

    # Find couplet rows
    rows = []
    rows += poem_root.select("div[class*='beyt'], div[class*='couplet'], p[class*='beyt'], p[class*='couplet']")
    if not rows:
        rows = poem_root.select("li[class*='beyt'], li[class*='verse']")
    if not rows:
        rows = poem_root.find_all("p")

    verses = []
    for r in rows:
        # remove nested scripts/styles
        for bad in r.find_all(["script", "style", "noscript"]):
            bad.decompose()

        right = r.select_one(".misra,.m1,.hemistich-right,.right")
        left  = r.select_one(".misra2,.m2,.hemistich-left,.left")
        if right or left:
            rt = (right.get_text(" ", strip=True) if right else "").strip()
            lt = (left.get_text(" ", strip=True) if left else "").strip()
            line = f"{rt} | {lt}".strip(" |")
            if line.strip():
                verses.append(line)
                continue

        # fallback: both hemistichs inline
        text_inline = r.get_text(" ", strip=True)
        if " / " in text_inline:
            parts = [p.strip() for p in text_inline.split(" / ", 1)]
            line = " | ".join([p for p in parts if p])
            if line:
                verses.append(line)
        else:
            if text_inline:
                verses.append(text_inline)

    poem_text = "\n".join(v for v in verses if v.strip()) if verses else None

    # Audio: prefer audio under poem container
    audio_url = None
    for src in poem_root.select("audio source[src], audio[src]"):
        url = src.get("src")
        if url and re.search(r"\.(mp3|ogg|wav)(\?|$)", url, re.I):
            audio_url = url
            break
    if audio_url is None:
        for a in poem_root.select("a[href]"):
            href = a.get("href")
            if href and re.search(r"\.(mp3|ogg|wav)(\?|$)", href, re.I):
                audio_url = href
                break

    return poem_text, audio_url
