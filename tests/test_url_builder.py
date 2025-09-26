import pytest
from src.url_builder import (
    BASE_URL,
    build_poet_url,
    build_section_url,
    build_poem_url,
)

def test_build_poet_url_basic():
    assert build_poet_url("hafez") == f"{BASE_URL}/hafez"

def test_build_poet_url_strips_slashes_and_spaces():
    assert build_poet_url("  /hafez/  ") == f"{BASE_URL}/hafez"

def test_build_poet_url_invalid_blank():
    with pytest.raises(ValueError):
        build_poet_url(" / / ")

def test_build_section_url_basic():
    assert build_section_url("hafez", "ghazal") == f"{BASE_URL}/hafez/ghazal"

def test_build_section_url_strips():
    assert build_section_url(" /hafez/ ", " /ghazal/ ") == f"{BASE_URL}/hafez/ghazal"

def test_build_section_url_invalid():
    import pytest
    with pytest.raises(ValueError):
        build_section_url("hafez", "   ")
    with pytest.raises(ValueError):
        build_section_url("   ", "ghazal")

def test_build_poem_url_with_section():
    assert build_poem_url("hafez", 2, "ghazal") == f"{BASE_URL}/hafez/ghazal/sh2"

def test_build_poem_url_without_section():
    assert build_poem_url("hafez", 1) == f"{BASE_URL}/hafez/sh1"

def test_build_poem_url_trim_inputs():
    assert build_poem_url(" /hafez/ ", 30, " /ghazal/ ") == f"{BASE_URL}/hafez/ghazal/sh30"

def test_build_poem_url_invalid_sh_number_zero():
    import pytest
    with pytest.raises(ValueError):
        build_poem_url("hafez", 0, "ghazal")

def test_build_poem_url_invalid_sh_number_negative():
    import pytest
    with pytest.raises(ValueError):
        build_poem_url("hafez", -5, "ghazal")

def test_build_poem_url_invalid_poet_slug():
    import pytest
    with pytest.raises(ValueError):
        build_poem_url("   ", 2, "ghazal")

def test_build_poem_url_invalid_section_slug():
    import pytest
    with pytest.raises(ValueError):
        build_poem_url("hafez", 2, "   ")
