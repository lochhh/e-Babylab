"""Unit tests for ipl/experiments/forms.py"""
import pytest
from experiments.forms import VocabularyChecklistForm


class TestVocabularyChecklistForm:
    """Test VocabularyChecklistForm."""
    
    def test_vocabulary_checklist_form_init(self, experiment_factory):
        """Test VocabularyChecklistForm initialization."""
        experiment = experiment_factory()
        
        form = VocabularyChecklistForm(cdi_form=experiment, word='apple')
        
        # Should create field for word
        assert 'word_apple' in form.fields
        assert form.fields['word_apple'].label == 'apple'
    
    def test_vocabulary_checklist_form_no_word(self, experiment_factory):
        """Test VocabularyChecklistForm with no word."""
        experiment = experiment_factory()
        
        form = VocabularyChecklistForm(cdi_form=experiment)
        
        # Should have no fields
        assert len(form.fields) == 0
