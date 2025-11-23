"""Unit tests for experiments models."""
import pytest
from django.contrib.auth.models import User

from ipl.experiments.models import Experiment, Question


@pytest.mark.django_db
class TestQuestionModel:
    """Test cases for the Question model."""
    
    def test_question_str(self, question_factory):
        """Test the __str__ method returns the question text."""
        question = question_factory(text='What is your name?')
        assert str(question) == 'What is your name?'
    
    def test_question_creation(self, question_factory):
        """Test basic question creation."""
        question = question_factory(
            text='Sample question',
            question_type=Question.TEXT,
            required=True,
            position=1
        )
        assert question.text == 'Sample question'
        assert question.question_type == Question.TEXT
        assert question.required is True
        assert question.position == 1
    
    def test_question_types(self, question_factory):
        """Test that all question types can be created."""
        types = [
            Question.TEXT,
            Question.RADIO,
            Question.SELECT,
            Question.SELECT_MULTIPLE,
            Question.INTEGER,
            Question.NUM_RANGE,
            Question.AGE,
            Question.SEX
        ]
        
        for i, qtype in enumerate(types):
            question = question_factory(
                text=f'Question {i}',
                question_type=qtype,
                position=i
            )
            assert question.question_type == qtype
    
    def test_question_ordering(self, question_factory):
        """Test that questions are ordered by position."""
        q3 = question_factory(text='Third', position=3)
        q1 = question_factory(text='First', position=1)
        q2 = question_factory(text='Second', position=2)
        
        questions = Question.objects.all()
        assert list(questions) == [q1, q2, q3]
    
    def test_get_choices_radio(self, question_factory):
        """Test get_choices method for radio type questions."""
        question = question_factory(
            text='Choose one',
            question_type=Question.RADIO
        )
        question.choices = 'option1, option2, option3'
        question.save()
        
        expected = (('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3'))
        assert question.get_choices() == expected
    
    def test_get_choices_with_spaces(self, question_factory):
        """Test get_choices handles extra spaces correctly."""
        question = question_factory(
            text='Choose one',
            question_type=Question.SELECT
        )
        question.choices = '  option1  ,  option2  ,  option3  '
        question.save()
        
        expected = (('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3'))
        assert question.get_choices() == expected
    
    def test_get_choices_empty_string(self, question_factory):
        """Test get_choices handles empty strings in choices."""
        question = question_factory(text='Choose one')
        question.choices = 'option1,,option2'
        question.save()
        
        expected = (('option1', 'option1'), ('option2', 'option2'))
        assert question.get_choices() == expected


@pytest.mark.django_db
class TestExperimentModel:
    """Test cases for the Experiment model."""
    
    def test_experiment_creation(self, user):
        """Test basic experiment creation."""
        experiment = Experiment.objects.create(
            user=user,
            exp_name='My Test Experiment',
            sharing_option=Experiment.PRIVATE,
            recording_option=Experiment.NONE
        )
        assert experiment.exp_name == 'My Test Experiment'
        assert experiment.user == user
        assert experiment.sharing_option == Experiment.PRIVATE
    
    def test_experiment_default_values(self, user):
        """Test experiment default field values."""
        experiment = Experiment.objects.create(
            user=user,
            exp_name='Test Exp'
        )
        assert experiment.sharing_option == Experiment.PRIVATE
        assert experiment.list_selection_strategy == Experiment.LEASTPLAYED
        assert experiment.recording_option == Experiment.NONE
        assert experiment.include_pause_page is True
        assert experiment.show_gaze_estimations is False
        assert experiment.general_onset == 0
    
    def test_experiment_uuid_primary_key(self, user):
        """Test that experiment uses UUID as primary key."""
        experiment = Experiment.objects.create(
            user=user,
            exp_name='UUID Test'
        )
        assert experiment.id is not None
        # UUID should be a string representation of UUID
        assert len(str(experiment.id)) == 36  # Standard UUID string length
