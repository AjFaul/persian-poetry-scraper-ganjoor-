# Persian Poetry Scraper for Ganjoor

Command-line tool for interactively browsing and downloading poems + audio from Ganjoor (with structure auto-detection).

---

## Quick Start

1. **Clone and install:**
    ```
    git clone https://github.com/AjFaul/persian-poetry-scraper-ganjoor-.git
    cd persian-poetry-scraper-ganjoor-
    pip install -r requirements.txt
    ```

2. **(Optional) Prepare mapping (url_modes, poem counts):**
    ```
    python discover_sh_counts.py
    ```

3. **Run the main tool:**
    ```
    python cli_downloader.py
    ```
    - Select a poet ("All" = all poets).
    - Set delay (ms, eg. 300).
    - Choose: Browse, Download all, Download specific section.

4. **Result files:**
    - Downloaded poems go to `data/text/...`
    - Downloaded audio goes to `data/audio/...`
    - Only poems with both text and audio are saved.

---

## FAQ

**How do I just see the available poets/sections?**  
Run the tool → select "Browse sections".

**How do I download everything for one poet?**  
Select a poet, pick "Download ALL..." and confirm. (Beware: this is heavy!)

**How do I download a range of poems?**  
Select "Download a specific section", then the section/subsection, then set the range.

**What if a poem doesn't have both text + audio?**  
It is skipped and not saved.

**Where do I get the .xlsx files?**  
Excel files should be in `inputs/excels/` (see provided samples or documentation).

---

## Technical Notes

- Python 3.10 or later required.
- Supports automatic and Excel-driven structure.
- Conservative to avoid server overload – configure delay as needed.

---

## License

MIT – source code only. Downloaded data is subject to ganjoor.net's terms.

---

