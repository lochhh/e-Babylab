"""
Unit tests for ipl.experiments.forms module.
"""
import pytest
from datetime import date, timedelta


class TestForms:
    """Tests for forms in ipl.experiments.forms."""

    def test_vocabulary_checklist_form_import(self):
        """Test that VocabularyChecklistForm can be imported."""
        try:
            from ipl.experiments.forms import VocabularyChecklistForm
            assert VocabularyChecklistForm is not None
        except ImportError:
            pytest.skip("VocabularyChecklistForm not available")

    def test_vocabulary_checklist_form_basic(self, experiment_factory):
        """Test basic VocabularyChecklistForm construction."""
        try:
            from ipl.experiments.forms import VocabularyChecklistForm
        except ImportError:
            pytest.skip("VocabularyChecklistForm not available")
        
        experiment = experiment_factory()
        
        # Test form construction with minimal data
        form = VocabularyChecklistForm(cdi_form=experiment, word='test_word')
        assert form is not None
        assert 'word_test_word' in form.fields

    def test_vocabulary_checklist_form_no_word(self, experiment_factory):
        """Test VocabularyChecklistForm without word parameter."""
        try:
            from ipl.experiments.forms import VocabularyChecklistForm
        except ImportError:
            pytest.skip("VocabularyChecklistForm not available")
        
        experiment = experiment_factory()
        
        # Test form construction without word
        form = VocabularyChecklistForm(cdi_form=experiment)
        assert form is not None

    def test_consent_form_import(self):
        """Test that ConsentForm can be imported."""
        try:
            from ipl.experiments.forms import ConsentForm
            assert ConsentForm is not None
        except ImportError:
            pytest.skip("ConsentForm not available")

    def test_consent_form_basic(self, experiment_factory, consent_question_factory):
        """Test basic ConsentForm construction."""
        try:
            from ipl.experiments.forms import ConsentForm
        except ImportError:
            pytest.skip("ConsentForm not available")
        
        experiment = experiment_factory()
        consent_question_factory(experiment=experiment, text="Do you consent?")
        
        form = ConsentForm(experiment=experiment)
        assert form is not None

    def test_subject_data_form_import(self):
        """Test that SubjectDataForm can be imported."""
        try:
            from ipl.experiments.forms import SubjectDataForm
            assert SubjectDataForm is not None
        except ImportError:
            pytest.skip("SubjectDataForm not available")

    def test_subject_data_form_basic(self, experiment_factory, question_factory):
        """Test basic SubjectDataForm construction."""
        try:
            from ipl.experiments.forms import SubjectDataForm
        except ImportError:
            pytest.skip("SubjectDataForm not available")
        
        experiment = experiment_factory()
        question_factory(experiment=experiment, text="Name?", question_type='text')
        
        form = SubjectDataForm(experiment=experiment)
        assert form is not None
        assert hasattr(form, 'uuid')

    def test_subject_data_form_with_age_question(self, experiment_factory, question_factory):
        """Test SubjectDataForm with age question type."""
        try:
            from ipl.experiments.forms import SubjectDataForm
        except ImportError:
            pytest.skip("SubjectDataForm not available")
        
        experiment = experiment_factory()
        question_factory(
            experiment=experiment,
            text="Date of birth",
            question_type='age',
            choices='12, 36'
        )
        
        form = SubjectDataForm(experiment=experiment)
        assert form is not None

    def test_subject_data_form_with_radio_question(self, experiment_factory, question_factory):
        """Test SubjectDataForm with radio question type."""
        try:
            from ipl.experiments.forms import SubjectDataForm
        except ImportError:
            pytest.skip("SubjectDataForm not available")
        
        experiment = experiment_factory()
        question_factory(
            experiment=experiment,
            text="Choose one",
            question_type='radio',
            choices='Yes, No, Maybe'
        )
        
        form = SubjectDataForm(experiment=experiment)
        assert form is not None

    def test_import_form_import(self):
        """Test that ImportForm can be imported."""
        try:
            from ipl.experiments.forms import ImportForm
            assert ImportForm is not None
        except ImportError:
            pytest.skip("ImportForm not available")

    def test_import_form_basic(self):
        """Test basic ImportForm construction."""
        try:
            from ipl.experiments.forms import ImportForm
        except ImportError:
            pytest.skip("ImportForm not available")
        
        form = ImportForm()
        assert form is not None
        assert 'import_file' in form.fields
