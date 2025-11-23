"""
Test fixtures for ipl/experiments tests.

This module provides pytest-django fixtures using Django ORM directly.
"""
import pytest
from django.contrib.auth.models import User, Group
from experiments.models import (
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
    def _create_instrument(instr_name='Test Instrument', **kwargs):
        return Instrument.objects.create(
            instr_name=instr_name,
            **kwargs
        )
    return _create_instrument


@pytest.fixture
def experiment_factory(db, user):
    """Factory for creating Experiment instances."""
    def _create_experiment(exp_name='Test Experiment', **kwargs):
        defaults = {
            'user': user,
            'exp_name': exp_name,
        }
        defaults.update(kwargs)
        return Experiment.objects.create(**defaults)
    return _create_experiment


@pytest.fixture
def listitem_factory(db):
    """Factory for creating ListItem instances."""
    def _create_listitem(experiment, list_name='Test List', **kwargs):
        defaults = {
            'experiment': experiment,
            'list_name': list_name,
        }
        defaults.update(kwargs)
        return ListItem.objects.create(**defaults)
    return _create_listitem


@pytest.fixture
def outerblock_factory(db):
    """Factory for creating OuterBlockItem instances."""
    def _create_outerblock(listitem, outer_block_name='Outer Block', **kwargs):
        defaults = {
            'listitem': listitem,
            'outer_block_name': outer_block_name,
        }
        defaults.update(kwargs)
        return OuterBlockItem.objects.create(**defaults)
    return _create_outerblock


@pytest.fixture
def blockitem_factory(db):
    """Factory for creating BlockItem instances."""
    def _create_blockitem(outerblockitem, label='Block', **kwargs):
        defaults = {
            'outerblockitem': outerblockitem,
            'label': label,
        }
        defaults.update(kwargs)
        return BlockItem.objects.create(**defaults)
    return _create_blockitem


@pytest.fixture
def trialitem_factory(db):
    """Factory for creating TrialItem instances."""
    def _create_trialitem(blockitem, label='Trial', code='T1', max_duration=1000, **kwargs):
        defaults = {
            'blockitem': blockitem,
            'label': label,
            'code': code,
            'max_duration': max_duration,
        }
        defaults.update(kwargs)
        return TrialItem.objects.create(**defaults)
    return _create_trialitem


@pytest.fixture
def subjectdata_factory(db):
    """Factory for creating SubjectData instances."""
    def _create_subjectdata(experiment, subject_id='test-subject-1', **kwargs):
        defaults = {
            'id': subject_id,
            'experiment': experiment,
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
    def _create_question(experiment, text='Test Question', **kwargs):
        defaults = {
            'experiment': experiment,
            'text': text,
            'required': False,
        }
        defaults.update(kwargs)
        return Question.objects.create(**defaults)
    return _create_question


@pytest.fixture
def consent_question_factory(db):
    """Factory for creating ConsentQuestion instances."""
    def _create_consent_question(experiment, text='Consent Question', **kwargs):
        defaults = {
            'experiment': experiment,
            'text': text,
        }
        defaults.update(kwargs)
        return ConsentQuestion.objects.create(**defaults)
    return _create_consent_question
