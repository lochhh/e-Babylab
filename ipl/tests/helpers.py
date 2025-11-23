"""
Test helper utilities and factories for creating test data.

This module provides reusable test data creation helpers using factory_boy
to ensure consistent and maintainable test data across all test modules.
"""
import factory
import uuid
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User, Group
from experiments.models import (
    Instrument, Experiment, ListItem, OuterBlockItem, BlockItem, TrialItem,
    SubjectData, TrialResult, Question, AnswerText, AnswerRadio, AnswerSelect,
    AnswerSelectMultiple, AnswerInteger, ConsentQuestion, CdiResult
)


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""
    class Meta:
        model = User
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f'testuser{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False


class GroupFactory(DjangoModelFactory):
    """Factory for creating test groups."""
    class Meta:
        model = Group
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'testgroup{n}')


class InstrumentFactory(DjangoModelFactory):
    """Factory for creating test instruments."""
    class Meta:
        model = Instrument
    
    instr_name = factory.Sequence(lambda n: f'Instrument {n}')


class ExperimentFactory(DjangoModelFactory):
    """Factory for creating test experiments."""
    class Meta:
        model = Experiment
    
    user = factory.SubFactory(UserFactory)
    exp_name = factory.Sequence(lambda n: f'Test Experiment {n}')
    sharing_option = Experiment.PRIVATE
    list_selection_strategy = Experiment.LEASTPLAYED
    include_pause_page = True
    show_gaze_estimations = False
    recording_option = Experiment.NONE
    general_onset = 0
    assess_type = Experiment.COMP
    num_words = 25
    typical_dev = True


class ListItemFactory(DjangoModelFactory):
    """Factory for creating test list items."""
    class Meta:
        model = ListItem
    
    experiment = factory.SubFactory(ExperimentFactory)
    list_name = factory.Sequence(lambda n: f'List {n}')
    global_timeout = 300000
    exclude_list = False


class OuterBlockItemFactory(DjangoModelFactory):
    """Factory for creating test outer block items."""
    class Meta:
        model = OuterBlockItem
    
    listitem = factory.SubFactory(ListItemFactory)
    outer_block_name = factory.Sequence(lambda n: f'Outer Block {n}')
    randomise_inner_blocks = False
    position = factory.Sequence(lambda n: n)


class BlockItemFactory(DjangoModelFactory):
    """Factory for creating test block items."""
    class Meta:
        model = BlockItem
    
    outerblockitem = factory.SubFactory(OuterBlockItemFactory)
    label = factory.Sequence(lambda n: f'Block {n}')
    randomise_trials = False
    position = factory.Sequence(lambda n: n)


class TrialItemFactory(DjangoModelFactory):
    """Factory for creating test trial items."""
    class Meta:
        model = TrialItem
    
    blockitem = factory.SubFactory(BlockItemFactory)
    label = factory.Sequence(lambda n: f'Trial {n}')
    code = factory.Sequence(lambda n: f'T{n}')
    position = factory.Sequence(lambda n: n)
    visual_onset = 0
    audio_onset = 0
    visual_file = 'test_visual.jpg'  # Required field
    max_duration = 5000


class SubjectDataFactory(DjangoModelFactory):
    """Factory for creating test subject data."""
    class Meta:
        model = SubjectData
    
    id = factory.LazyFunction(lambda: uuid.uuid4().hex)
    experiment = factory.SubFactory(ExperimentFactory)
    listitem = factory.SubFactory(ListItemFactory)
    participant_id = factory.Sequence(lambda n: n + 1)
    resolution_w = 1920
    resolution_h = 1080


class TrialResultFactory(DjangoModelFactory):
    """Factory for creating test trial results."""
    class Meta:
        model = TrialResult
    
    subjectdata = factory.SubFactory(SubjectDataFactory)
    trialitem = factory.SubFactory(TrialItemFactory)
    response = 'test_response'
    response_time = 1000


class QuestionFactory(DjangoModelFactory):
    """Factory for creating test questions."""
    class Meta:
        model = Question
    
    experiment = factory.SubFactory(ExperimentFactory)
    text = factory.Sequence(lambda n: f'Question {n}')
    position = factory.Sequence(lambda n: n)
    required = True


class AnswerTextFactory(DjangoModelFactory):
    """Factory for creating text answers."""
    class Meta:
        model = AnswerText
    
    question = factory.SubFactory(QuestionFactory)
    subjectdata = factory.SubFactory(SubjectDataFactory)
    body = 'Test answer text'


class AnswerRadioFactory(DjangoModelFactory):
    """Factory for creating radio answers."""
    class Meta:
        model = AnswerRadio
    
    question = factory.SubFactory(QuestionFactory)
    subjectdata = factory.SubFactory(SubjectDataFactory)
    body = 'Option 1'


class AnswerSelectFactory(DjangoModelFactory):
    """Factory for creating select answers."""
    class Meta:
        model = AnswerSelect
    
    question = factory.SubFactory(QuestionFactory)
    subjectdata = factory.SubFactory(SubjectDataFactory)
    body = 'Option A'


class AnswerSelectMultipleFactory(DjangoModelFactory):
    """Factory for creating select multiple answers."""
    class Meta:
        model = AnswerSelectMultiple
    
    question = factory.SubFactory(QuestionFactory)
    subjectdata = factory.SubFactory(SubjectDataFactory)
    body = 'Option 1, Option 2'


class AnswerIntegerFactory(DjangoModelFactory):
    """Factory for creating integer answers."""
    class Meta:
        model = AnswerInteger
    
    question = factory.SubFactory(QuestionFactory)
    subjectdata = factory.SubFactory(SubjectDataFactory)
    body = 42


class ConsentQuestionFactory(DjangoModelFactory):
    """Factory for creating consent questions."""
    class Meta:
        model = ConsentQuestion
    
    experiment = factory.SubFactory(ExperimentFactory)
    text = factory.Sequence(lambda n: f'Consent Question {n}')
    position = factory.Sequence(lambda n: n)
    response_yes = 'I agree'
    response_no = 'I do not agree'


class CdiResultFactory(DjangoModelFactory):
    """Factory for creating CDI results."""
    class Meta:
        model = CdiResult
    
    subjectdata = factory.SubFactory(SubjectDataFactory)
    vocab_data = '[]'
    ability_estimate = 0.5
