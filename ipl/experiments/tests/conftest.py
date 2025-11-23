"""Pytest fixtures for experiments app tests."""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from experiments.models import Experiment, Question


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def experiment(db, user):
    """Create a test experiment."""
    return Experiment.objects.create(
        user=user,
        exp_name='Test Experiment',
        sharing_option=Experiment.PRIVATE,
        recording_option=Experiment.NONE
    )


@pytest.fixture
def question_factory(db, experiment):
    """
    Factory fixture for creating Question instances.
    
    Returns a function that creates questions with specified parameters.
    The 'days' parameter allows creating questions at different time offsets.
    """
    def _create_question(text='Test Question', question_type=Question.TEXT, required=True, position=1, days=0):
        """
        Create a question with the given parameters.
        
        Args:
            text: The question text
            question_type: Type of question (TEXT, RADIO, etc.)
            required: Whether the question is required
            position: Position in the form
            days: Offset in days for created timestamp (for time-based testing)
        
        Returns:
            Question instance
        """
        question = Question(
            text=text,
            question_type=question_type,
            required=required,
            experiment=experiment,
            position=position
        )
        question.save()
        
        # If days offset specified, manually adjust created timestamp for testing
        if days != 0:
            # Note: Django models don't have pub_date by default for Question
            # This is a placeholder for time-based testing if needed in future
            pass
        
        return question
    
    return _create_question
