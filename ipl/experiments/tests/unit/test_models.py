"""
Unit tests for the experiments app models.

Tests model behavior, __str__ representations, custom methods,
field validation, and constraints.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


class TestInstrument:
    """Tests for the Instrument model."""

    def test_str_representation(self, instrument):
        """Test the string representation of an Instrument."""
        assert str(instrument) == "Test Instrument"

    def test_instrument_creation(self, db):
        """Test creating an Instrument instance."""
        from experiments.models import Instrument
        
        instrument = Instrument.objects.create(instr_name="New Instrument")
        assert instrument.instr_name == "New Instrument"
        assert Instrument.objects.count() == 1


class TestExperiment:
    """Tests for the Experiment model."""

    def test_str_representation(self, experiment):
        """Test the string representation of an Experiment."""
        assert str(experiment) == "Test Experiment"

    def test_experiment_creation_defaults(self, user):
        """Test creating an experiment with default values."""
        from experiments.models import Experiment
        
        exp = Experiment.objects.create(
            user=user,
            exp_name="Default Experiment"
        )
        assert exp.sharing_option == Experiment.PRIVATE
        assert exp.list_selection_strategy == Experiment.LEASTPLAYED
        assert exp.recording_option == Experiment.NONE
        assert exp.general_onset == 0
        assert exp.include_pause_page is True
        assert exp.show_gaze_estimations is False

    def test_experiment_uuid_primary_key(self, experiment):
        """Test that experiment uses UUID as primary key."""
        assert isinstance(experiment.id, uuid.UUID)

    def test_subject_questions_method(self, experiment, question):
        """Test the subject_questions method returns correct queryset."""
        questions = experiment.subject_questions()
        assert questions.count() == 1
        assert questions.first() == question

    def test_subject_questions_method_no_pk(self, db):
        """Test subject_questions returns empty queryset when experiment is unsaved."""
        from experiments.models import Experiment
        
        exp = Experiment()
        # Unsaved experiment still has a UUID pk but returns empty queryset
        result = exp.subject_questions()
        assert result is None or (hasattr(result, 'count') and result.count() == 0)

    def test_consent_questions_method(self, experiment, consent_question):
        """Test the consent_questions method returns correct queryset."""
        questions = experiment.consent_questions()
        assert questions.count() == 1
        assert questions.first() == consent_question

    def test_consent_questions_method_no_pk(self, db):
        """Test consent_questions returns empty queryset when experiment is unsaved."""
        from experiments.models import Experiment
        
        exp = Experiment()
        # Unsaved experiment still has a UUID pk but returns empty queryset
        result = exp.consent_questions()
        assert result is None or (hasattr(result, 'count') and result.count() == 0)

    def test_get_list_item_least_played(self, experiment, list_item):
        """Test get_list_item with least played strategy."""
        from experiments.models import ListItem
        
        list_item2 = ListItem.objects.create(
            experiment=experiment,
            list_name="List 2",
            global_timeout=300000
        )
        
        # Set strategy to least played
        experiment.list_selection_strategy = experiment.LEASTPLAYED
        experiment.save()
        
        # Should return a list item
        result = experiment.get_list_item()
        assert result in [list_item, list_item2]

    def test_get_list_item_sequential(self, experiment, list_item):
        """Test get_list_item with sequential strategy."""
        from experiments.models import ListItem
        
        list_item2 = ListItem.objects.create(
            experiment=experiment,
            list_name="List 2",
            global_timeout=300000
        )
        
        experiment.list_selection_strategy = experiment.SEQUENTIAL
        experiment.save()
        
        result = experiment.get_list_item()
        # Should return first list item
        assert result == list_item

    def test_get_list_item_random(self, experiment, list_item):
        """Test get_list_item with random strategy."""
        experiment.list_selection_strategy = experiment.RANDOM
        experiment.save()
        
        result = experiment.get_list_item()
        assert result == list_item

    def test_get_list_item_no_lists(self, experiment):
        """Test get_list_item returns None when no lists exist."""
        result = experiment.get_list_item()
        assert result is None

    def test_get_list_item_excluded_lists(self, experiment, list_item):
        """Test get_list_item ignores excluded lists."""
        list_item.exclude_list = True
        list_item.save()
        
        result = experiment.get_list_item()
        assert result is None


class TestListItem:
    """Tests for the ListItem model."""

    def test_str_representation(self, list_item):
        """Test the string representation of a ListItem."""
        assert str(list_item) == "List 1"

    def test_list_item_creation(self, experiment):
        """Test creating a ListItem instance."""
        from experiments.models import ListItem
        
        list_item = ListItem.objects.create(
            experiment=experiment,
            list_name="New List",
            global_timeout=600000,
            exclude_list=False
        )
        assert list_item.list_name == "New List"
        assert list_item.global_timeout == 600000
        assert list_item.exclude_list is False


class TestOuterBlockItem:
    """Tests for the OuterBlockItem model."""

    def test_str_representation(self, outer_block_item):
        """Test the string representation of an OuterBlockItem."""
        assert str(outer_block_item) == "Outer Block 1"

    def test_ordering(self, list_item):
        """Test that outer blocks are ordered by position."""
        from experiments.models import OuterBlockItem
        
        block1 = OuterBlockItem.objects.create(
            listitem=list_item,
            outer_block_name="Block 1",
            position=2
        )
        block2 = OuterBlockItem.objects.create(
            listitem=list_item,
            outer_block_name="Block 2",
            position=1
        )
        
        blocks = OuterBlockItem.objects.all()
        assert list(blocks) == [block2, block1]


class TestBlockItem:
    """Tests for the BlockItem model."""

    def test_str_representation(self, block_item):
        """Test the string representation of a BlockItem."""
        assert str(block_item) == "Block 1"

    def test_default_background_colour(self, outer_block_item):
        """Test that default background colour is white."""
        from experiments.models import BlockItem
        
        block = BlockItem.objects.create(
            outerblockitem=outer_block_item,
            label="Test Block",
            position=1
        )
        assert block.background_colour == "#FFFFFF"

    def test_ordering(self, outer_block_item):
        """Test that blocks are ordered by position."""
        from experiments.models import BlockItem
        
        block1 = BlockItem.objects.create(
            outerblockitem=outer_block_item,
            label="Block A",
            position=2
        )
        block2 = BlockItem.objects.create(
            outerblockitem=outer_block_item,
            label="Block B",
            position=1
        )
        
        blocks = BlockItem.objects.all()
        assert list(blocks) == [block2, block1]


class TestTrialItem:
    """Tests for the TrialItem model."""

    def test_str_representation(self, trial_item):
        """Test the string representation of a TrialItem."""
        assert str(trial_item) == "Trial 1"

    def test_trial_item_defaults(self, block_item):
        """Test creating a TrialItem with default values."""
        from experiments.models import TrialItem
        
        trial = TrialItem.objects.create(
            blockitem=block_item,
            label="Default Trial",
            code="DT",
            max_duration=3000,
            position=1
        )
        assert trial.visual_onset == 0
        assert trial.audio_onset == 0
        assert trial.user_input == TrialItem.NO
        assert trial.record_media is True
        assert trial.record_gaze is True
        assert trial.is_calibration is False
        assert trial.grid_row == 1
        assert trial.grid_col == 1

    def test_calibration_points_default(self, trial_item):
        """Test that default calibration points are set correctly."""
        assert len(trial_item.calibration_points) == 9
        assert trial_item.calibration_points[0] == [50, 50]

    def test_ordering(self, block_item):
        """Test that trials are ordered by position."""
        from experiments.models import TrialItem
        
        trial1 = TrialItem.objects.create(
            blockitem=block_item,
            label="Trial A",
            code="TA",
            max_duration=3000,
            position=2
        )
        trial2 = TrialItem.objects.create(
            blockitem=block_item,
            label="Trial B",
            code="TB",
            max_duration=3000,
            position=1
        )
        
        trials = TrialItem.objects.all()
        assert list(trials) == [trial2, trial1]


class TestSubjectData:
    """Tests for the SubjectData model."""

    def test_str_representation(self, subject_data):
        """Test the string representation of SubjectData."""
        assert str(subject_data) == subject_data.id

    def test_subject_data_creation(self, experiment, list_item):
        """Test creating SubjectData instance."""
        from experiments.models import SubjectData
        
        subject_id = str(uuid.uuid4())
        subject = SubjectData.objects.create(
            id=subject_id,
            participant_id=5,
            experiment=experiment,
            listitem=list_item,
            resolution_w=1280,
            resolution_h=720
        )
        assert subject.participant_id == 5
        assert subject.experiment == experiment
        assert subject.listitem == list_item
        assert subject.resolution_w == 1280
        assert subject.resolution_h == 720

    def test_subject_data_timestamps(self, subject_data):
        """Test that created and updated timestamps are set."""
        assert subject_data.created is not None
        assert subject_data.updated is not None


class TestTrialResult:
    """Tests for the TrialResult model."""

    def test_trial_result_creation(self, subject_data, trial_item):
        """Test creating a TrialResult instance."""
        from experiments.models import TrialResult
        
        result = TrialResult.objects.create(
            subject=subject_data,
            trialitem=trial_item,
            start_time=500.0,
            end_time=1500.0,
            key_pressed="space",
            trial_number=3,
            resolution_w=1920,
            resolution_h=1080
        )
        assert result.subject == subject_data
        assert result.trialitem == trial_item
        assert result.start_time == 500.0
        assert result.end_time == 1500.0
        assert result.key_pressed == "space"
        assert result.trial_number == 3

    def test_webgazer_data_default(self, trial_result):
        """Test that webgazer_data has a default empty list."""
        assert trial_result.webgazer_data == []


class TestQuestion:
    """Tests for the Question model."""

    def test_question_creation(self, experiment):
        """Test creating a Question instance."""
        from experiments.models import Question
        
        question = Question.objects.create(
            experiment=experiment,
            text="What is your name?",
            question_type=Question.TEXT,
            position=2,
            required=False
        )
        assert question.text == "What is your name?"
        assert question.question_type == Question.TEXT
        assert question.position == 2
        assert question.required is False


class TestConsentQuestion:
    """Tests for the ConsentQuestion model."""

    def test_consent_question_creation(self, experiment):
        """Test creating a ConsentQuestion instance."""
        from experiments.models import ConsentQuestion
        
        question = ConsentQuestion.objects.create(
            experiment=experiment,
            text="I agree to the terms",
            response_yes="I agree",
            response_no="I disagree",
            position=1
        )
        assert question.text == "I agree to the terms"
        assert question.response_yes == "I agree"
        assert question.response_no == "I disagree"


class TestValidators:
    """Tests for model validators."""

    def test_validate_list_valid(self):
        """Test validate_list with valid input."""
        from experiments.models import validate_list
        
        # Should not raise an exception
        validate_list("option1, option2, option3")

    def test_validate_list_invalid_single_item(self):
        """Test validate_list with single item raises ValidationError."""
        from experiments.models import validate_list
        
        with pytest.raises(ValidationError):
            validate_list("single_option")

    def test_validate_range_valid(self):
        """Test validate_range with valid input."""
        from experiments.models import validate_range
        
        # Should not raise an exception
        validate_range("1, 10")

    def test_validate_range_invalid_count(self):
        """Test validate_range with wrong number of values."""
        from experiments.models import validate_range
        
        with pytest.raises(ValidationError):
            validate_range("1, 2, 3")

    def test_validate_range_invalid_order(self):
        """Test validate_range with min >= max."""
        from experiments.models import validate_range
        
        with pytest.raises(ValidationError):
            validate_range("10, 5")

    def test_validate_range_invalid_non_integer(self):
        """Test validate_range with non-integer values."""
        from experiments.models import validate_range
        
        with pytest.raises(ValidationError):
            validate_range("abc, def")
