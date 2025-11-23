"""Unit tests for forms.py"""
import pytest
from ipl.experiments.forms import VocabularyChecklistForm


class TestVocabularyChecklistForm:
    """Test VocabularyChecklistForm."""
    
    def test_form_initialization(self, experiment_factory):
        """Test form can be initialized."""
        experiment = experiment_factory()
        
        form = VocabularyChecklistForm(cdi_form=experiment, word='apple')
        
        assert 'word_apple' in form.fields
    
    def test_form_with_no_word(self, experiment_factory):
        """Test form initialization without word."""
        experiment = experiment_factory()
        
        form = VocabularyChecklistForm(cdi_form=experiment)
        
        # Form should be created but have no word fields
        assert len(form.fields) == 0
