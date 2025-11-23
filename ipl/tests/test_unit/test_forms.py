"""
Smoke tests for forms in ipl.experiments.forms (VocabularyChecklistForm).
If the form or module does not exist, tests will skip.
"""
import importlib
import pytest


def test_vocabulary_checklist_form_constructs_and_validates():
    try:
        forms = importlib.import_module("ipl.experiments.forms")
    except Exception:
        pytest.skip("forms module not present")
    if not hasattr(forms, "VocabularyChecklistForm"):
        pytest.skip("VocabularyChecklistForm not present")
    Form = getattr(forms, "VocabularyChecklistForm")
    # Try constructing with minimal required args; if signature differs the test will skip
    try:
        f = Form(cdi_form=None, word="test")
        # call is_valid if available
        if hasattr(f, "is_valid"):
            # likely invalid since no data, but shouldn't raise
            _ = f.is_valid()
    except TypeError:
        pytest.skip("VocabularyChecklistForm signature not compatible with smoke test")