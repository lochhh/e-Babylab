"""
Tests for experiments app forms.

This module tests:
- Form validation
- Clean methods
- Form field generation
- Error handling
"""
from django.test import TestCase
from django.contrib.auth.models import User
from experiments.forms import (
    ConsentForm, SubjectDataForm, ExperimentForm, VocabularyChecklistForm, ImportForm
)
from experiments.models import Question, SubjectData, Experiment
from tests.helpers import (
    ExperimentFactory, QuestionFactory, ConsentQuestionFactory, UserFactory
)
import datetime


class ConsentFormTest(TestCase):
    """Test the ConsentForm."""
    
    def test_consent_form_no_questions(self):
        """Test form with no consent questions."""
        experiment = ExperimentFactory()
        form = ConsentForm(experiment=experiment)
        self.assertEqual(len(form.fields), 0)
    
    def test_consent_form_single_question(self):
        """Test form with single consent question."""
        experiment = ExperimentFactory()
        consent_q = ConsentQuestionFactory(
            experiment=experiment,
            text='Do you agree?',
            response_yes='Yes',
            response_no='No'
        )
        
        form = ConsentForm(experiment=experiment)
        field_name = f'question_{consent_q.pk}'
        
        self.assertIn(field_name, form.fields)
        self.assertEqual(form.fields[field_name].label, 'Do you agree?')
        choices = form.fields[field_name].choices
        self.assertEqual(len(choices), 2)
        self.assertIn(('yes', 'Yes'), choices)
        self.assertIn(('no', 'No'), choices)
    
    def test_consent_form_multiple_questions(self):
        """Test form with multiple consent questions."""
        experiment = ExperimentFactory()
        cq1 = ConsentQuestionFactory(experiment=experiment, position=0)
        cq2 = ConsentQuestionFactory(experiment=experiment, position=1)
        cq3 = ConsentQuestionFactory(experiment=experiment, position=2)
        
        form = ConsentForm(experiment=experiment)
        self.assertEqual(len(form.fields), 3)
        self.assertIn(f'question_{cq1.pk}', form.fields)
        self.assertIn(f'question_{cq2.pk}', form.fields)
        self.assertIn(f'question_{cq3.pk}', form.fields)
    
    def test_consent_form_valid_submission(self):
        """Test valid form submission."""
        experiment = ExperimentFactory()
        cq1 = ConsentQuestionFactory(experiment=experiment)
        
        form_data = {f'question_{cq1.pk}': 'yes'}
        form = ConsentForm(data=form_data, experiment=experiment)
        
        self.assertTrue(form.is_valid())
    
    def test_consent_form_field_has_required_class(self):
        """Test that consent question fields have required class."""
        experiment = ExperimentFactory()
        consent_q = ConsentQuestionFactory(experiment=experiment)
        
        form = ConsentForm(experiment=experiment)
        field_name = f'question_{consent_q.pk}'
        
        self.assertIn('required', form.fields[field_name].widget.attrs.get('class', ''))


class SubjectDataFormTest(TestCase):
    """Test the SubjectDataForm."""
    
    def test_subject_data_form_hidden_fields(self):
        """Test that resolution fields are hidden."""
        experiment = ExperimentFactory()
        form = SubjectDataForm(experiment=experiment)
        
        self.assertIn('resolution_w', form.fields)
        self.assertIn('resolution_h', form.fields)
        self.assertEqual(form.fields['resolution_w'].widget.__class__.__name__, 'HiddenInput')
        self.assertEqual(form.fields['resolution_h'].widget.__class__.__name__, 'HiddenInput')
    
    def test_subject_data_form_text_question(self):
        """Test form with text question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='What is your name?',
            question_type=Question.TEXT,
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        self.assertTrue(form.fields[field_name].required)
        self.assertEqual(form.fields[field_name].label, 'What is your name?')
    
    def test_subject_data_form_radio_question(self):
        """Test form with radio question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Choose one',
            question_type=Question.RADIO,
            choices='Option A, Option B, Option C',
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        choices = [choice[0] for choice in form.fields[field_name].choices]
        self.assertIn('Option A', choices)
        self.assertIn('Option B', choices)
        self.assertIn('Option C', choices)
    
    def test_subject_data_form_select_question(self):
        """Test form with select question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Select one',
            question_type=Question.SELECT,
            choices='Choice 1, Choice 2',
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        # Should have empty option plus the choices
        choices = form.fields[field_name].choices
        self.assertEqual(choices[0], ('', '-------------'))
    
    def test_subject_data_form_integer_question(self):
        """Test form with integer question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='How many?',
            question_type=Question.INTEGER,
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        self.assertEqual(form.fields[field_name].__class__.__name__, 'IntegerField')
    
    def test_subject_data_form_num_range_question(self):
        """Test form with number range question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Age',
            question_type=Question.NUM_RANGE,
            choices='1, 100',
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        field = form.fields[field_name]
        self.assertEqual(field.min_value, 1)
        self.assertEqual(field.max_value, 100)
    
    def test_subject_data_form_age_question(self):
        """Test form with age question."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Date of birth',
            question_type=Question.AGE,
            choices='12, 36',  # 12-36 months
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertIn(field_name, form.fields)
        self.assertEqual(form.fields[field_name].__class__.__name__, 'DateField')
    
    def test_subject_data_form_required_field(self):
        """Test that required questions are marked required."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Required question',
            question_type=Question.TEXT,
            required=True
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertTrue(form.fields[field_name].required)
        self.assertIn('required', form.fields[field_name].widget.attrs.get('class', ''))
    
    def test_subject_data_form_optional_field(self):
        """Test that optional questions are not marked required."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Optional question',
            question_type=Question.TEXT,
            required=False
        )
        
        form = SubjectDataForm(experiment=experiment)
        field_name = f'question_{question.pk}'
        
        self.assertFalse(form.fields[field_name].required)
    
    def test_subject_data_form_clean_age_validation_too_young(self):
        """Test age validation rejects too young participants."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Date of birth',
            question_type=Question.AGE,
            choices='24, 36',  # 24-36 months
            required=True
        )
        
        # Birth date that makes child 12 months old (too young)
        birth_date = datetime.date.today() - datetime.timedelta(days=365)
        
        form_data = {
            f'question_{question.pk}': birth_date,
            'resolution_w': 1920,
            'resolution_h': 1080
        }
        
        form = SubjectDataForm(data=form_data, experiment=experiment)
        self.assertFalse(form.is_valid())
        self.assertIn(f'question_{question.pk}', form.errors)
    
    def test_subject_data_form_clean_age_validation_too_old(self):
        """Test age validation rejects too old participants."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Date of birth',
            question_type=Question.AGE,
            choices='12, 24',  # 12-24 months
            required=True
        )
        
        # Birth date that makes child 36 months old (too old)
        birth_date = datetime.date.today() - datetime.timedelta(days=365*3)
        
        form_data = {
            f'question_{question.pk}': birth_date,
            'resolution_w': 1920,
            'resolution_h': 1080
        }
        
        form = SubjectDataForm(data=form_data, experiment=experiment)
        self.assertFalse(form.is_valid())
        self.assertIn(f'question_{question.pk}', form.errors)
    
    def test_subject_data_form_save_creates_subject(self):
        """Test that saving form creates SubjectData instance."""
        experiment = ExperimentFactory()
        question = QuestionFactory(
            experiment=experiment,
            text='Name',
            question_type=Question.TEXT,
            required=True
        )
        
        form_data = {
            f'question_{question.pk}': 'John Doe',
            'resolution_w': 1920,
            'resolution_h': 1080
        }
        
        form = SubjectDataForm(data=form_data, experiment=experiment)
        self.assertTrue(form.is_valid())
        
        subject = form.save()
        self.assertIsNotNone(subject.pk)
        self.assertEqual(subject.experiment, experiment)
        self.assertEqual(subject.participant_id, 1)  # First participant
    
    def test_subject_data_form_save_increments_participant_id(self):
        """Test that participant_id increments correctly."""
        experiment = ExperimentFactory()
        
        # Create first subject
        form_data = {
            'resolution_w': 1920,
            'resolution_h': 1080
        }
        
        form1 = SubjectDataForm(data=form_data, experiment=experiment)
        subject1 = form1.save()
        self.assertEqual(subject1.participant_id, 1)
        
        # Create second subject
        form2 = SubjectDataForm(data=form_data, experiment=experiment)
        subject2 = form2.save()
        self.assertEqual(subject2.participant_id, 2)
    
    def test_subject_data_form_uuid_generated(self):
        """Test that form generates UUID for subject."""
        experiment = ExperimentFactory()
        form = SubjectDataForm(experiment=experiment)
        
        self.assertIsNotNone(form.uuid)
        self.assertEqual(len(form.uuid), 32)  # UUID hex is 32 characters


class ImportFormTest(TestCase):
    """Test the ImportForm."""
    
    def test_import_form_has_file_field(self):
        """Test that ImportForm has a file field."""
        form = ImportForm()
        self.assertIn('file', form.fields)
    
    def test_import_form_file_required(self):
        """Test that file field is required."""
        form = ImportForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
