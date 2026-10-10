"""
UI Hygiene & Production Hardening Regression Tests.
Verifies:
1. Backend URL resolution across local vs Render environments.
2. clean_html removes indentation and avoids CommonMark code block conversion.
3. No orphaned unclosed rt-card divs in any page modules.
4. All 10 pages and routing structures remain intact.
"""

import os
import re
from pathlib import Path
import pytest

from ui.routing import get_navigation_structure
from passenger_app import clean_html, resolve_backend_url


def test_resolve_backend_url_local():
    """Verify default local backend URL when no env vars are set."""
    env_backup = dict(os.environ)
    try:
        os.environ.pop("BACKEND_URL", None)
        os.environ.pop("RENDER", None)
        os.environ.pop("PORT", None)
        assert resolve_backend_url() == "http://127.0.0.1:8000"
    finally:
        os.environ.clear()
        os.environ.update(env_backup)


def test_resolve_backend_url_render_default():
    """Verify that on Render, backend URL defaults to deployed cloud backend."""
    env_backup = dict(os.environ)
    try:
        os.environ.pop("BACKEND_URL", None)
        os.environ["RENDER"] = "true"
        os.environ["PORT"] = "10000"
        assert resolve_backend_url() == "https://sih26028-railway-backend.onrender.com"
    finally:
        os.environ.clear()
        os.environ.update(env_backup)


def test_resolve_backend_url_render_with_localhost_override():
    """Verify that if BACKEND_URL was accidentally set to 127.0.0.1:8000 on Render, it repairs to cloud backend."""
    env_backup = dict(os.environ)
    try:
        os.environ["BACKEND_URL"] = "http://127.0.0.1:8000"
        os.environ["RENDER"] = "true"
        assert resolve_backend_url() == "https://sih26028-railway-backend.onrender.com"
    finally:
        os.environ.clear()
        os.environ.update(env_backup)


def test_resolve_backend_url_explicit_custom():
    """Verify explicit custom backend URL is respected."""
    env_backup = dict(os.environ)
    try:
        os.environ["BACKEND_URL"] = "https://custom-rail-backend.internal:8443/"
        assert resolve_backend_url() == "https://custom-rail-backend.internal:8443"
    finally:
        os.environ.clear()
        os.environ.update(env_backup)


def test_clean_html_dedents_and_strips_comments():
    """Verify clean_html removes comments and 4-space indents."""
    sample_indented_html = """
        <!-- Comment to remove -->
        <div class="test-card">
            <span>Hello World</span>
        </div>
    """
    cleaned = clean_html(sample_indented_html)
    assert "<!--" not in cleaned
    assert "Comment" not in cleaned
    assert cleaned.startswith('<div class="test-card">')
    assert "<span>Hello World</span>" in cleaned
    # Ensure no leading whitespace on lines
    for line in cleaned.splitlines():
        assert not line.startswith("    ")


def test_all_pages_have_balanced_rt_card_divs():
    """Verify that no page in ui/pages/ has unclosed or unbalanced rt-card divs."""
    pages_dir = Path(__file__).parent.parent / "ui" / "pages"
    for py_file in pages_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        # Find every st.markdown('<div class="rt-card"...>', unsafe_allow_html=True)
        # that is not closed in the same string
        calls = re.findall(r'st\.markdown\(\s*[\'"]<div class=[\'"]rt-card[\'"][^>]*>[\'"]', content)
        assert len(calls) == 0, f"Found unclosed opening <div class='rt-card'> in {py_file.name}: {calls}"


def test_navigation_has_all_10_pages():
    """Verify all 10 pages are registered in get_navigation_structure()."""
    nav = get_navigation_structure()
    assert "Passenger Services" in nav
    assert "User & System" in nav
    passenger_pages = nav["Passenger Services"]
    system_pages = nav["User & System"]
    assert len(passenger_pages) == 8
    assert len(system_pages) == 2
    for p in passenger_pages + system_pages:
        assert hasattr(p, "run")
        assert callable(p.run)


def test_apptest_zero_exceptions():
    """Verify that launching passenger_app via AppTest produces zero unhandled exceptions."""
    from streamlit.testing.v1 import AppTest
    root_dir = Path(__file__).parent.parent
    entrypoint = str(root_dir / "passenger_app.py")
    at = AppTest.from_file(entrypoint, default_timeout=15)
    at.run()
    assert len(at.exception) == 0, f"AppTest threw exceptions: {[e.message for e in at.exception]}"

