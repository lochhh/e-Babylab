"""Shared fixtures for integration tests."""

import pytest

TPL_FIELDS = [
    "information_page_tpl",
    "browser_check_page_tpl",
    "introduction_page_tpl",
    "consent_fail_page_tpl",
    "demographic_data_page_tpl",
    "cdi_page_tpl",
    "webcam_check_page_tpl",
    "microphone_check_page_tpl",
    "experiment_page_tpl",
    "pause_page_tpl",
    "thank_you_page_tpl",
    "thank_you_abort_page_tpl",
    "error_page_tpl",
]


@pytest.fixture
def simple_experiment(experiment_factory):
    """Experiment with all template fields set to 'OK' to avoid rendering errors."""
    exp = experiment_factory()
    for field in TPL_FIELDS:
        setattr(exp, field, "OK")
    exp.save()
    return exp


@pytest.fixture
def experiment_with_trials(
    simple_experiment,
    listitem_factory,
    outerblock_factory,
    blockitem_factory,
    trialitem_factory,
):
    """Experiment with a complete trial hierarchy: list → outer block → block → trial."""
    listitem = listitem_factory(experiment=simple_experiment)
    outerblock = outerblock_factory(listitem=listitem)
    block = blockitem_factory(outerblock=outerblock)
    trial = trialitem_factory(blockitem=block)
    return simple_experiment, listitem, trial
