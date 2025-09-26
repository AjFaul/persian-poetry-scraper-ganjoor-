from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os
import pandas as pd  # requires: pip install pandas openpyxl

@dataclass
class ExcelTask:
    poet: str
    book_or_style: str
    subsection: Optional[str]  # can be None if no subsection layer

def read_excel_tasks(poet: str, excel_path: str) -> List[ExcelTask]:
    """
    Read an Excel file where:
      - first row contains one or more book/style names (columns)
      - subsequent rows contain subsections under each column
    It returns one ExcelTask per (book/style, subsection) pair.
    If a column has no subsections (all NaN after first row) we produce a task with subsection=None.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path, header=None, dtype=str)
    if df.empty:
        return []

    # First row are column headers (book/style names)
    headers = df.iloc[0].tolist()
    tasks: List[ExcelTask] = []

    # For each column, scan the below rows as subsections
    for col_idx, header in enumerate(headers):
        if header is None:
            continue
        book = str(header).strip()
        if not book:
            continue

        col_series = df.iloc[1:, col_idx]  # below first row
        # Collect non-empty subsections
        subsections = []
        for v in col_series.tolist():
            if v is None:
                continue
            s = str(v).strip()
            if s:
                subsections.append(s)

        if subsections:
            for sub in subsections:
                tasks.append(ExcelTask(poet=poet, book_or_style=book, subsection=sub))
        else:
            # No subsection rows under this book/style
            tasks.append(ExcelTask(poet=poet, book_or_style=book, subsection=None))

    return tasks
