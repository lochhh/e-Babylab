"""
Pytest fixtures for ipl.experiments tests.
"""
import pytest
from django.contrib.auth.models import User
from ipl.experiments.models import (
    Experiment,
    Instrument,
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
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


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
            'sharing_option': 'OWN',
            'list_selection_strategy': 'LPF',
        }
        defaults.update(kwargs)
        return Experiment.objects.create(**defaults)
    return _create_experiment


@pytest.fixture
def listitem_factory(db):
    """Factory for creating ListItem instances."""
    def _create_listitem(experiment, **kwargs):
        defaults = {
            'list_name': 'Test List',
            'global_timeout': 300000,
            'exclude_list': False,
        }
        defaults.update(kwargs)
        return ListItem.objects.create(experiment=experiment, **defaults)
    return _create_listitem


@pytest.fixture
def outerblock_factory(db):
    """Factory for creating OuterBlockItem instances."""
    def _create_outerblock(listitem, **kwargs):
        defaults = {
            'outer_block_name': 'Test Outer Block',
            'position': 1,
            'randomise_inner_blocks': False,
        }
        defaults.update(kwargs)
        return OuterBlockItem.objects.create(listitem=listitem, **defaults)
    return _create_outerblock


@pytest.fixture
def blockitem_factory(db):
    """Factory for creating BlockItem instances."""
    def _create_blockitem(outerblockitem, **kwargs):
        defaults = {
            'label': 'Test Block',
            'background_colour': '#FFFFFF',
            'randomise_trials': False,
            'position': 1,
        }
        defaults.update(kwargs)
        return BlockItem.objects.create(outerblockitem=outerblockitem, **defaults)
    return _create_blockitem


@pytest.fixture
def trialitem_factory(db):
    """Factory for creating TrialItem instances."""
    def _create_trialitem(blockitem, **kwargs):
        defaults = {
            'label': 'Test Trial',
            'code': 'TEST',
            'visual_onset': 0,
            'audio_onset': 0,
            'user_input': 'NO',
            'max_duration': 5000,
            'position': 1,
        }
        defaults.update(kwargs)
        return TrialItem.objects.create(blockitem=blockitem, **defaults)
    return _create_trialitem


@pytest.fixture
def subjectdata_factory(db):
    """Factory for creating SubjectData instances."""
    def _create_subjectdata(experiment, **kwargs):
        import uuid
        defaults = {
            'id': uuid.uuid4().hex,
            'participant_id': 1,
            'experiment': experiment,
            'resolution_w': 1920,
            'resolution_h': 1080,
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
            'trial_number': 1,
        }
        defaults.update(kwargs)
        return TrialResult.objects.create(**defaults)
    return _create_trialresult


@pytest.fixture
def question_factory(db):
    """Factory for creating Question instances."""
    def _create_question(experiment, **kwargs):
        defaults = {
            'text': 'Test question?',
            'required': True,
            'experiment': experiment,
            'question_type': 'text',
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
            'text': 'Do you consent?',
            'experiment': experiment,
            'position': 1,
            'response_yes': 'Yes',
            'response_no': 'No',
        }
        defaults.update(kwargs)
        return ConsentQuestion.objects.create(**defaults)
    return _create_consent_question
