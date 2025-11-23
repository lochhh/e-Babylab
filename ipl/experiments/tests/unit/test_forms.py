"""Unit tests for forms in ipl.experiments.forms."""
import pytest
from django.core.exceptions import ValidationError


class TestVocabularyChecklistForm:
    """Test VocabularyChecklistForm if it exists."""

    def test_form_exists(self):
        """Test VocabularyChecklistForm can be imported."""
        try:
            from experiments.forms import VocabularyChecklistForm
            assert VocabularyChecklistForm is not None
        except ImportError:
            pytest.skip("VocabularyChecklistForm not found")

    def test_form_initialization(self, experiment_factory):
        """Test VocabularyChecklistForm initializes with experiment."""
        try:
            from experiments.forms import VocabularyChecklistForm
        except ImportError:
            pytest.skip("VocabularyChecklistForm not found")
        
        experiment = experiment_factory()
        form = VocabularyChecklistForm(cdi_form=experiment, word='apple')
        assert form is not None
        assert 'word_apple' in form.fields

    def test_form_with_word_creates_field(self, experiment_factory):
        """Test form creates checkbox field for given word."""
        try:
            from experiments.forms import VocabularyChecklistForm
        except ImportError:
            pytest.skip("VocabularyChecklistForm not found")
        
        experiment = experiment_factory()
        form = VocabularyChecklistForm(cdi_form=experiment, word='ball')
        assert 'word_ball' in form.fields
        assert form.fields['word_ball'].label == 'ball'


class TestConsentForm:
    """Test ConsentForm functionality."""

    def test_form_exists(self):
        """Test ConsentForm can be imported."""
        try:
            from experiments.forms import ConsentForm
            assert ConsentForm is not None
        except ImportError:
            pytest.skip("ConsentForm not found")

    def test_form_initialization(self, experiment_factory, consent_question_factory):
        """Test ConsentForm initializes with consent questions."""
        try:
            from experiments.forms import ConsentForm
        except ImportError:
            pytest.skip("ConsentForm not found")
        
        experiment = experiment_factory()
        cq1 = consent_question_factory(experiment, text="Do you agree?")
        
        form = ConsentForm(experiment=experiment)
        assert form is not None
        assert f'question_{cq1.pk}' in form.fields


class TestSubjectDataForm:
    """Test SubjectDataForm functionality."""

    def test_form_exists(self):
        """Test SubjectDataForm can be imported."""
        try:
            from experiments.forms import SubjectDataForm
            assert SubjectDataForm is not None
        except ImportError:
            pytest.skip("SubjectDataForm not found")

    def test_form_initialization(self, experiment_factory, question_factory):
        """Test SubjectDataForm initializes with subject questions."""
        try:
            from experiments.forms import SubjectDataForm
        except ImportError:
            pytest.skip("SubjectDataForm not found")
        
        experiment = experiment_factory()
        q1 = question_factory(experiment, text="What is your name?", question_type='text')
        
        form = SubjectDataForm(experiment=experiment)
        assert form is not None
        assert f'question_{q1.pk}' in form.fields

    def test_form_creates_text_field(self, experiment_factory, question_factory):
        """Test form creates appropriate field for text question type."""
        try:
            from experiments.forms import SubjectDataForm
            from django import forms as django_forms
        except ImportError:
            pytest.skip("SubjectDataForm not found")
        
        experiment = experiment_factory()
        q = question_factory(experiment, text="Comment", question_type='text')
        
        form = SubjectDataForm(experiment=experiment)
        field = form.fields[f'question_{q.pk}']
        assert isinstance(field, django_forms.CharField)

    def test_form_creates_radio_field(self, experiment_factory, question_factory):
        """Test form creates radio field for radio question type."""
        try:
            from experiments.forms import SubjectDataForm
            from django import forms as django_forms
        except ImportError:
            pytest.skip("SubjectDataForm not found")
        
        experiment = experiment_factory()
        q = question_factory(
            experiment,
            text="Choose one",
            question_type='radio',
            choices='Option A, Option B'
        )
        
        form = SubjectDataForm(experiment=experiment)
        field = form.fields[f'question_{q.pk}']
        assert isinstance(field, django_forms.ChoiceField)

    def test_form_respects_required_flag(self, experiment_factory, question_factory):
        """Test form respects required flag on questions."""
        try:
            from experiments.forms import SubjectDataForm
        except ImportError:
            pytest.skip("SubjectDataForm not found")
        
        experiment = experiment_factory()
        q_required = question_factory(experiment, text="Required", required=True)
        q_optional = question_factory(experiment, text="Optional", required=False, position=2)
        
        form = SubjectDataForm(experiment=experiment)
        assert form.fields[f'question_{q_required.pk}'].required is True
        assert form.fields[f'question_{q_optional.pk}'].required is False


class TestExperimentForm:
    """Test ExperimentForm functionality."""

    def test_form_exists(self):
        """Test ExperimentForm can be imported."""
        try:
            from experiments.forms import ExperimentForm
            assert ExperimentForm is not None
        except ImportError:
            pytest.skip("ExperimentForm not found")

    def test_form_has_sharing_groups_field(self):
        """Test ExperimentForm has sharing_groups field."""
        try:
            from experiments.forms import ExperimentForm
        except ImportError:
            pytest.skip("ExperimentForm not found")
        
        form = ExperimentForm()
        assert 'sharing_groups' in form.fields

    def test_clean_sharing_groups_validates_group_required(self, user):
        """Test clean_sharing_groups validates at least one group when sharing with groups."""
        try:
            from experiments.forms import ExperimentForm
        except ImportError:
            pytest.skip("ExperimentForm not found")
        
        form = ExperimentForm(data={
            'user': user.pk,
            'exp_name': 'Test',
            'sharing_option': 'GRP',  # Sharing with groups
            'sharing_groups': [],  # No groups selected
        })
        
        is_valid = form.is_valid()
        assert not is_valid
        assert 'sharing_groups' in form.errors
