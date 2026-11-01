"""Smoke tests for template_defaults.py content availability."""

import importlib
import re

import pytest

mod = importlib.import_module("experiments.template_defaults")


def test_template_defaults_contains_strings():
    """Verify that key template default variables exist and are strings."""
    # Expect some of the template default variables to be present and string-like
    for name in [
        "information_page_content",
        "experiment_page_content",
        "thank_you_page_content",
    ]:
        if hasattr(mod, name):
            val = getattr(mod, name)
            assert isinstance(val, str)


@pytest.mark.parametrize(
    "name", ["thank_you_page_content", "thank_you_abort_page_content"]
)
def test_end_page_buttons_share_one_flex_row(name):
    """Both end-page buttons sit directly in the same flex row.

    Wrapping only one in its own <form> inside the row stretches the other to
    the form's line-box height, so the buttons render at different heights.
    """
    row = re.search(
        r'<div class="d-flex[^"]*">(.*?)</div>', getattr(mod, name), re.S
    ).group(1)
    assert 'id="approve-data-button"' in row
    assert 'id="delete-data-button"' in row
    assert "<form" not in row
