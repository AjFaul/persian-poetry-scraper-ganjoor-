import os
import pandas as pd
import tempfile
from src.parser_excel import read_excel_tasks, ExcelTask

def _make_excel(tmp_dir, data):
    path = os.path.join(tmp_dir, "sample.xlsx")
    pd.DataFrame(data).to_excel(path, header=False, index=False)
    return path

def test_read_excel_tasks_with_subsections():
    with tempfile.TemporaryDirectory() as d:
        # Two columns (books), each with two subsections
        data = [
            ["ghazal", "rubai"],
            ["sh-range-1-10", "set-a"],
            ["sh-range-11-20", "set-b"],
        ]
        path = _make_excel(d, data)
        tasks = read_excel_tasks("hafez", path)
        assert len(tasks) == 4
        assert tasks[0] == ExcelTask("hafez", "ghazal", "sh-range-1-10")
        assert tasks[1] == ExcelTask("hafez", "ghazal", "sh-range-11-20")
        assert tasks[2] == ExcelTask("hafez", "rubai", "set-a")
        assert tasks[3] == ExcelTask("hafez", "rubai", "set-b")

def test_read_excel_tasks_without_subsections():
    with tempfile.TemporaryDirectory() as d:
        # One column with no subsections under it
        data = [
            ["divan"],
            [None],
            [None],
        ]
        path = _make_excel(d, data)
        tasks = read_excel_tasks("saadi", path)
        assert len(tasks) == 1
        assert tasks[0].poet == "saadi"
        assert tasks[0].book_or_style == "divan"
        assert tasks[0].subsection is None
