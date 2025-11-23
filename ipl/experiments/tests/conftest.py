"""
Pytest configuration and fixtures for the experiments app tests.

This module provides reusable fixtures for creating test data using Django ORM.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import User, Group
from django.utils import timezone


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123"
    )


@pytest.fixture
def group(db):
    """Create a test group."""
    return Group.objects.create(name="Test Group")


@pytest.fixture
def experiment(db, user):
    """Create a basic experiment."""
    from experiments.models import Experiment
    
    return Experiment.objects.create(
        user=user,
        exp_name="Test Experiment",
        sharing_option=Experiment.PRIVATE,
        list_selection_strategy=Experiment.LEASTPLAYED,
        recording_option=Experiment.NONE,
        general_onset=0
    )


@pytest.fixture
def experiment_with_group(db, user, group):
    """Create an experiment shared with a group."""
    from experiments.models import Experiment
    
    exp = Experiment.objects.create(
        user=user,
        exp_name="Shared Experiment",
        sharing_option=Experiment.MEMBERSONLY,
        list_selection_strategy=Experiment.SEQUENTIAL,
        recording_option=Experiment.VIDEO,
        general_onset=100
    )
    exp.sharing_groups.add(group)
    return exp


@pytest.fixture
def list_item(db, experiment):
    """Create a list item for an experiment."""
    from experiments.models import ListItem
    
    return ListItem.objects.create(
        experiment=experiment,
        list_name="List 1",
        global_timeout=300000,
        exclude_list=False
    )


@pytest.fixture
def outer_block_item(db, list_item):
    """Create an outer block item."""
    from experiments.models import OuterBlockItem
    
    return OuterBlockItem.objects.create(
        listitem=list_item,
        outer_block_name="Outer Block 1",
        position=1,
        randomise_inner_blocks=False
    )


@pytest.fixture
def block_item(db, outer_block_item):
    """Create a block item."""
    from experiments.models import BlockItem
    
    return BlockItem.objects.create(
        outerblockitem=outer_block_item,
        label="Block 1",
        comment="Test block",
        background_colour="#FFFFFF",
        randomise_trials=False,
        position=1
    )


@pytest.fixture
def trial_item(db, block_item):
    """Create a trial item."""
    from experiments.models import TrialItem
    
    return TrialItem.objects.create(
        blockitem=block_item,
        label="Trial 1",
        code="T1",
        visual_onset=0,
        audio_onset=0,
        user_input=TrialItem.NO,
        max_duration=5000,
        record_media=True,
        record_gaze=False,
        is_calibration=False,
        grid_row=1,
        grid_col=1,
        position=1
    )


@pytest.fixture
def subject_data(db, experiment, list_item):
    """Create subject data."""
    from experiments.models import SubjectData
    
    subject_id = str(uuid.uuid4())
    return SubjectData.objects.create(
        id=subject_id,
        participant_id=1,
        experiment=experiment,
        listitem=list_item,
        resolution_w=1920,
        resolution_h=1080
    )


@pytest.fixture
def trial_result(db, subject_data, trial_item):
    """Create a trial result."""
    from experiments.models import TrialResult
    
    return TrialResult.objects.create(
        subject=subject_data,
        trialitem=trial_item,
        start_time=1000.0,
        end_time=2000.0,
        key_pressed="click",
        trial_number=1,
        resolution_w=1920,
        resolution_h=1080,
        webgazer_data=[]
    )


@pytest.fixture
def question(db, experiment):
    """Create a text question for demographic data."""
    from experiments.models import Question
    
    return Question.objects.create(
        experiment=experiment,
        text="What is your age?",
        question_type=Question.INTEGER,
        position=1,
        required=True
    )


@pytest.fixture
def consent_question(db, experiment):
    """Create a consent question."""
    from experiments.models import ConsentQuestion
    
    return ConsentQuestion.objects.create(
        experiment=experiment,
        text="Do you consent to participate?",
        response_yes="Yes, I consent",
        response_no="No, I do not consent",
        position=1
    )


@pytest.fixture
def instrument(db):
    """Create a CDI instrument."""
    from experiments.models import Instrument
    
    return Instrument.objects.create(
        instr_name="Test Instrument"
    )
