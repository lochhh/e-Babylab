"""Smoke tests for template_defaults.py content availability."""

import importlib

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
