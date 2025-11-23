"""Unit tests for ipl.experiments.forms"""
import pytest
from unittest.mock import Mock, patch

try:
    from ipl.experiments.forms import VocabularyChecklistForm
    FORMS_AVAILABLE = True
except ImportError:
    FORMS_AVAILABLE = False


@pytest.mark.skipif(not FORMS_AVAILABLE, reason="Forms module not available")
def test_vocabulary_checklist_form_creation(experiment_factory):
    """Test VocabularyChecklistForm can be instantiated."""
    experiment = experiment_factory()
    
    # Create form with a word
    form = VocabularyChecklistForm(cdi_form=experiment, word='apple')
    
    # Check that form has the expected field
    assert 'word_apple' in form.fields


@pytest.mark.skipif(not FORMS_AVAILABLE, reason="Forms module not available")
def test_vocabulary_checklist_form_no_word(experiment_factory):
    """Test VocabularyChecklistForm without a word."""
    experiment = experiment_factory()
    
    # Create form without a word
    form = VocabularyChecklistForm(cdi_form=experiment)
    
    # Should have no fields
    assert len(form.fields) == 0


@pytest.mark.skipif(not FORMS_AVAILABLE, reason="Forms module not available")
def test_vocabulary_checklist_form_valid(experiment_factory):
    """Test VocabularyChecklistForm validation."""
    experiment = experiment_factory()
    
    # Create form with data
    form = VocabularyChecklistForm(
        data={'word_test': True},
        cdi_form=experiment,
        word='test'
    )
    
    # Form should be valid
    assert form.is_valid()


@pytest.mark.skipif(not FORMS_AVAILABLE, reason="Forms module not available")
def test_vocabulary_checklist_form_clean(experiment_factory):
    """Test VocabularyChecklistForm clean behavior."""
    experiment = experiment_factory()
    
    form = VocabularyChecklistForm(
        data={'word_banana': False},
        cdi_form=experiment,
        word='banana'
    )
    
    # Should be valid even if unchecked (boolean field)
    assert form.is_valid()
