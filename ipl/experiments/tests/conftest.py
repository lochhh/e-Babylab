"""Pytest fixtures for experiments app tests."""
import pytest
import uuid
from django.contrib.auth.models import User, Group
from ipl.experiments.models import (
    Instrument,
    Experiment,
    ListItem,
    OuterBlockItem,
    BlockItem,
    TrialItem,
    SubjectData,
    TrialResult,
    Question,
    ConsentQuestion,
)


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def group(db):
    """Create a test group."""
    return Group.objects.create(name='testgroup')


@pytest.fixture
def instrument_factory(db):
    """Factory for creating Instrument instances."""
    def _create_instrument(**kwargs):
        defaults = {
            'instr_name': 'Test Instrument',
        }
        defaults.update(kwargs)
        return Instrument.objects.create(**defaults)
    return _create_instrument


@pytest.fixture
def experiment_factory(db, user):
    """Factory for creating Experiment instances."""
    def _create_experiment(**kwargs):
        defaults = {
            'user': user,
            'exp_name': 'Test Experiment',
        }
        defaults.update(kwargs)
        return Experiment.objects.create(**defaults)
    return _create_experiment


@pytest.fixture
def listitem_factory(db):
    """Factory for creating ListItem instances."""
    def _create_listitem(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'list_name': 'Test List',
            'global_timeout': 300000,
        }
        defaults.update(kwargs)
        return ListItem.objects.create(**defaults)
    return _create_listitem


@pytest.fixture
def outerblock_factory(db):
    """Factory for creating OuterBlockItem instances."""
    def _create_outerblock(listitem, **kwargs):
        defaults = {
            'listitem': listitem,
            'outer_block_name': 'Test Outer Block',
            'position': 1,
        }
        defaults.update(kwargs)
        return OuterBlockItem.objects.create(**defaults)
    return _create_outerblock


@pytest.fixture
def blockitem_factory(db):
    """Factory for creating BlockItem instances."""
    def _create_blockitem(outerblockitem, **kwargs):
        defaults = {
            'outerblockitem': outerblockitem,
            'label': 'Test Block',
            'position': 1,
        }
        defaults.update(kwargs)
        return BlockItem.objects.create(**defaults)
    return _create_blockitem


@pytest.fixture
def trialitem_factory(db):
    """Factory for creating TrialItem instances."""
    def _create_trialitem(blockitem, **kwargs):
        defaults = {
            'blockitem': blockitem,
            'label': 'Test Trial',
            'code': 'TEST',
            'max_duration': 5000,
            'position': 1,
        }
        defaults.update(kwargs)
        return TrialItem.objects.create(**defaults)
    return _create_trialitem


@pytest.fixture
def subjectdata_factory(db):
    """Factory for creating SubjectData instances."""
    def _create_subjectdata(experiment, **kwargs):
        defaults = {
            'id': uuid.uuid4().hex,
            'experiment': experiment,
            'participant_id': 1,
        }
        defaults.update(kwargs)
        return SubjectData.objects.create(**defaults)
    return _create_subjectdata


@pytest.fixture
def trialresult_factory(db):
    """Factory for creating TrialResult instances."""
    def _create_trialresult(subject, trialitem, **kwargs):
        defaults = {
            'subject': subject,
            'trialitem': trialitem,
        }
        defaults.update(kwargs)
        return TrialResult.objects.create(**defaults)
    return _create_trialresult


@pytest.fixture
def question_factory(db):
    """Factory for creating Question instances."""
    def _create_question(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'text': 'Test question?',
            'required': True,
            'question_type': Question.TEXT,
            'position': 1,
        }
        defaults.update(kwargs)
        return Question.objects.create(**defaults)
    return _create_question


@pytest.fixture
def consent_question_factory(db):
    """Factory for creating ConsentQuestion instances."""
    def _create_consent_question(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'text': 'Do you consent?',
            'position': 1,
        }
        defaults.update(kwargs)
        return ConsentQuestion.objects.create(**defaults)
    return _create_consent_question
