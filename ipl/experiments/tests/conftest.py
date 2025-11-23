"""Pytest fixtures for ipl.experiments tests."""
import pytest
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
    return User.objects.create_user(username='testuser', password='testpass123')


@pytest.fixture
def group(db):
    """Create a test group."""
    return Group.objects.create(name='testgroup')


@pytest.fixture
def instrument_factory(db):
    """Factory for creating Instrument instances."""
    def create_instrument(**kwargs):
        defaults = {
            'instr_name': 'Test Instrument',
        }
        defaults.update(kwargs)
        return Instrument.objects.create(**defaults)
    return create_instrument


@pytest.fixture
def experiment_factory(db, user):
    """Factory for creating Experiment instances."""
    def create_experiment(**kwargs):
        defaults = {
            'user': user,
            'exp_name': 'Test Experiment',
        }
        defaults.update(kwargs)
        return Experiment.objects.create(**defaults)
    return create_experiment


@pytest.fixture
def listitem_factory(db):
    """Factory for creating ListItem instances."""
    def create_listitem(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'list_name': 'Test List',
        }
        defaults.update(kwargs)
        return ListItem.objects.create(**defaults)
    return create_listitem


@pytest.fixture
def outerblock_factory(db):
    """Factory for creating OuterBlockItem instances."""
    def create_outerblock(listitem, **kwargs):
        defaults = {
            'listitem': listitem,
            'outer_block_name': 'Test Outer Block',
            'position': 1,
        }
        defaults.update(kwargs)
        return OuterBlockItem.objects.create(**defaults)
    return create_outerblock


@pytest.fixture
def blockitem_factory(db):
    """Factory for creating BlockItem instances."""
    def create_blockitem(outerblockitem, **kwargs):
        defaults = {
            'outerblockitem': outerblockitem,
            'label': 'Test Block',
            'position': 1,
        }
        defaults.update(kwargs)
        return BlockItem.objects.create(**defaults)
    return create_blockitem


@pytest.fixture
def trialitem_factory(db):
    """Factory for creating TrialItem instances."""
    def create_trialitem(blockitem, **kwargs):
        defaults = {
            'blockitem': blockitem,
            'label': 'Test Trial',
            'code': 'TT',
            'max_duration': 1000,
            'position': 1,
        }
        defaults.update(kwargs)
        return TrialItem.objects.create(**defaults)
    return create_trialitem


@pytest.fixture
def subjectdata_factory(db):
    """Factory for creating SubjectData instances."""
    def create_subjectdata(experiment, **kwargs):
        defaults = {
            'id': 'test-subject-id',
            'experiment': experiment,
        }
        defaults.update(kwargs)
        return SubjectData.objects.create(**defaults)
    return create_subjectdata


@pytest.fixture
def trialresult_factory(db):
    """Factory for creating TrialResult instances."""
    def create_trialresult(subject, trialitem, **kwargs):
        defaults = {
            'subject': subject,
            'trialitem': trialitem,
        }
        defaults.update(kwargs)
        return TrialResult.objects.create(**defaults)
    return create_trialresult


@pytest.fixture
def question_factory(db):
    """Factory for creating Question instances."""
    def create_question(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'text': 'Test Question',
            'required': True,
            'position': 1,
        }
        defaults.update(kwargs)
        return Question.objects.create(**defaults)
    return create_question


@pytest.fixture
def consent_question_factory(db):
    """Factory for creating ConsentQuestion instances."""
    def create_consent_question(experiment, **kwargs):
        defaults = {
            'experiment': experiment,
            'text': 'Do you consent?',
            'position': 1,
        }
        defaults.update(kwargs)
        return ConsentQuestion.objects.create(**defaults)
    return create_consent_question
