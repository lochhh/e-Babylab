"""Unit tests for ipl.experiments.models."""
import pytest
from django.core.exceptions import ValidationError
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
    validate_list,
    validate_range,
    _delete_file,
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


class TestModelStrMethods:
    """Test __str__ methods for all models."""

    def test_instrument_str(self, instrument_factory):
        """Test Instrument __str__ returns instrument name."""
        instrument = instrument_factory(name="Test CDI Instrument")
        assert str(instrument) == "Test CDI Instrument"

    def test_experiment_str(self, experiment_factory):
        """Test Experiment __str__ returns experiment name."""
        experiment = experiment_factory(name="My Test Experiment")
        assert str(experiment) == "My Test Experiment"

    def test_listitem_str(self, experiment_factory, listitem_factory):
        """Test ListItem __str__ returns list name."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment, name="List A")
        assert str(listitem) == "List A"

    def test_outerblock_str(self, experiment_factory, listitem_factory, outerblock_factory):
        """Test OuterBlockItem __str__ returns outer block name."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem, name="Block 1")
        assert str(outerblock) == "Block 1"

    def test_blockitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        """Test BlockItem __str__ returns label."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock, label="Trial Block A")
        assert str(blockitem) == "Trial Block A"

    def test_trialitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
        """Test TrialItem __str__ returns label."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem, label="Trial 1")
        assert str(trialitem) == "Trial 1"

    def test_subjectdata_str(self, experiment_factory, subjectdata_factory):
        """Test SubjectData __str__ returns id."""
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment, id="test-uuid-123")
        assert str(subject) == "test-uuid-123"

    def test_question_str(self, experiment_factory, question_factory):
        """Test Question __str__ returns text."""
        experiment = experiment_factory()
        question = question_factory(experiment, text="What is your age?")
        assert str(question) == "What is your age?"

    def test_consent_question_str(self, experiment_factory, consent_question_factory):
        """Test ConsentQuestion __str__ returns text."""
        experiment = experiment_factory()
        consent_q = consent_question_factory(experiment, text="Do you consent?")
        assert str(consent_q) == "Do you consent?"


class TestQuestionGetChoices:
    """Test Question.get_choices method."""

    def test_get_choices_radio(self, experiment_factory, question_factory):
        """Test get_choices for radio type question."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='radio',
            choices='Option A, Option B, Option C'
        )
        choices = question.get_choices()
        assert choices == (('Option A', 'Option A'), ('Option B', 'Option B'), ('Option C', 'Option C'))

    def test_get_choices_with_spaces(self, experiment_factory, question_factory):
        """Test get_choices strips whitespace."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='select',
            choices=' Yes ,  No  , Maybe '
        )
        choices = question.get_choices()
        assert choices == (('Yes', 'Yes'), ('No', 'No'), ('Maybe', 'Maybe'))

    def test_get_choices_empty_items(self, experiment_factory, question_factory):
        """Test get_choices filters empty items."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='radio',
            choices='A,,B,,,C'
        )
        choices = question.get_choices()
        assert choices == (('A', 'A'), ('B', 'B'), ('C', 'C'))


class TestValidateList:
    """Test validate_list validator."""

    def test_validate_list_valid(self):
        """Test validate_list accepts valid comma-separated list."""
        validate_list("Option A, Option B")  # Should not raise

    def test_validate_list_single_item_raises(self):
        """Test validate_list raises ValidationError for single item."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list("Only One")
        assert 'choices' in exc_info.value.message_dict

    def test_validate_list_empty_raises(self):
        """Test validate_list raises ValidationError for empty string."""
        with pytest.raises(ValidationError):
            validate_list("")

    def test_validate_list_whitespace_only_raises(self):
        """Test validate_list raises ValidationError for whitespace only."""
        with pytest.raises(ValidationError):
            validate_list("   ,   ")


class TestValidateRange:
    """Test validate_range validator."""

    def test_validate_range_valid(self):
        """Test validate_range accepts valid min,max pair."""
        validate_range("1, 10")  # Should not raise
        validate_range("0, 100")  # Should not raise

    def test_validate_range_not_two_values_raises(self):
        """Test validate_range raises for not exactly 2 values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range("1, 2, 3")
        assert 'choices' in exc_info.value.message_dict

        with pytest.raises(ValidationError):
            validate_range("1")

    def test_validate_range_min_greater_than_max_raises(self):
        """Test validate_range raises when min >= max."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range("10, 1")
        assert 'choices' in exc_info.value.message_dict

        with pytest.raises(ValidationError):
            validate_range("5, 5")

    def test_validate_range_non_integer_raises(self):
        """Test validate_range raises for non-integer values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range("abc, def")
        assert 'choices' in exc_info.value.message_dict


class TestQuestionClean:
    """Test Question.clean validation."""

    def test_clean_radio_requires_list(self, experiment_factory, question_factory):
        """Test clean validates radio type requires valid list."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='radio',
            choices='OnlyOne'
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_select_requires_list(self, experiment_factory, question_factory):
        """Test clean validates select type requires valid list."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='select',
            choices='Single'
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_select_multiple_requires_list(self, experiment_factory, question_factory):
        """Test clean validates select-multiple type requires valid list."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='select-multiple',
            choices='JustOne'
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_sex_requires_list(self, experiment_factory, question_factory):
        """Test clean validates sex type requires valid list."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='sex',
            choices='Male'
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_num_range_requires_valid_range(self, experiment_factory, question_factory):
        """Test clean validates number-range type requires valid range."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='number-range',
            choices='10, 1'  # Invalid: min > max
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_age_requires_valid_range(self, experiment_factory, question_factory):
        """Test clean validates age type requires valid range."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='age',
            choices='50, 10'  # Invalid: min > max
        )
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_text_no_validation(self, experiment_factory, question_factory):
        """Test clean does not validate text type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='text',
            choices=None
        )
        question.clean()  # Should not raise

    def test_clean_integer_no_validation(self, experiment_factory, question_factory):
        """Test clean does not validate integer type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type='integer',
            choices=None
        )
        question.clean()  # Should not raise


class TestExperimentMethods:
    """Test Experiment model methods."""

    def test_subject_questions(self, experiment_factory, question_factory):
        """Test subject_questions returns questions ordered by position."""
        experiment = experiment_factory()
        q1 = question_factory(experiment, text="Q1", position=2)
        q2 = question_factory(experiment, text="Q2", position=1)
        q3 = question_factory(experiment, text="Q3", position=3)

        questions = list(experiment.subject_questions())
        assert len(questions) == 3
        assert questions[0] == q2  # position 1
        assert questions[1] == q1  # position 2
        assert questions[2] == q3  # position 3

    def test_subject_questions_empty(self, experiment_factory):
        """Test subject_questions returns empty queryset when no questions."""
        experiment = experiment_factory()
        questions = list(experiment.subject_questions())
        assert len(questions) == 0

    def test_consent_questions(self, experiment_factory, consent_question_factory):
        """Test consent_questions returns consent questions ordered by position."""
        experiment = experiment_factory()
        cq1 = consent_question_factory(experiment, text="CQ1", position=2)
        cq2 = consent_question_factory(experiment, text="CQ2", position=1)

        consent_questions = list(experiment.consent_questions())
        assert len(consent_questions) == 2
        assert consent_questions[0] == cq2  # position 1
        assert consent_questions[1] == cq1  # position 2

    def test_consent_questions_empty(self, experiment_factory):
        """Test consent_questions returns empty queryset when no questions."""
        experiment = experiment_factory()
        consent_questions = list(experiment.consent_questions())
        assert len(consent_questions) == 0

    def test_get_list_item_least_played(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test get_list_item returns least played list."""
        experiment = experiment_factory(list_selection_strategy='LPF')
        list1 = listitem_factory(experiment, name="List1")
        list2 = listitem_factory(experiment, name="List2")

        # Create subject data for list1 twice and list2 once
        subjectdata_factory(experiment, listitem=list1)
        subjectdata_factory(experiment, listitem=list1, id="uuid-2")
        subjectdata_factory(experiment, listitem=list2, id="uuid-3")

        # Should return list2 as it has fewer participants
        selected = experiment.get_list_item()
        assert selected == list2

    def test_get_list_item_sequential(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test get_list_item returns next sequential list."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        list1 = listitem_factory(experiment, name="List1")
        list2 = listitem_factory(experiment, name="List2")
        list3 = listitem_factory(experiment, name="List3")

        # Last subject used list1
        subjectdata_factory(experiment, listitem=list1)

        # Should return list2
        selected = experiment.get_list_item()
        assert selected == list2

    def test_get_list_item_sequential_wraps(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test get_list_item returns first list when sequential reaches end."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        list1 = listitem_factory(experiment, name="List1")
        list2 = listitem_factory(experiment, name="List2")

        # Last subject used list2 (last list)
        subjectdata_factory(experiment, listitem=list2)

        # Should return list1 (first list)
        selected = experiment.get_list_item()
        assert selected == list1

    def test_get_list_item_random(self, experiment_factory, listitem_factory, monkeypatch):
        """Test get_list_item returns random list."""
        import random
        
        experiment = experiment_factory(list_selection_strategy='RAN')
        list1 = listitem_factory(experiment, name="List1")
        list2 = listitem_factory(experiment, name="List2")

        # Mock random.choice to return list2's pk
        def mock_choice(items):
            return list2.pk
        monkeypatch.setattr(random, 'choice', mock_choice)

        selected = experiment.get_list_item()
        assert selected == list2

    def test_get_list_item_excludes_excluded_lists(self, experiment_factory, listitem_factory):
        """Test get_list_item excludes lists marked as excluded."""
        experiment = experiment_factory()
        list1 = listitem_factory(experiment, name="List1", exclude_list=True)
        list2 = listitem_factory(experiment, name="List2", exclude_list=False)

        selected = experiment.get_list_item()
        assert selected == list2

    def test_get_list_item_no_lists(self, experiment_factory):
        """Test get_list_item returns None when no lists."""
        experiment = experiment_factory()
        selected = experiment.get_list_item()
        assert selected is None


class TestTrialResultFilename:
    """Test TrialResult.filename property."""

    def test_filename_property(self, experiment_factory, listitem_factory, outerblock_factory, 
                               blockitem_factory, trialitem_factory, subjectdata_factory, 
                               trialresult_factory):
        """Test filename property returns basename of webcam_file."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        trial_result = trialresult_factory(subject, trialitem)
        trial_result.webcam_file.name = 'path/to/video_file.webm'
        
        assert trial_result.filename == 'video_file.webm'

    def test_filename_property_empty(self, experiment_factory, listitem_factory, outerblock_factory,
                                     blockitem_factory, trialitem_factory, subjectdata_factory,
                                     trialresult_factory):
        """Test filename property with empty webcam_file."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        trial_result = trialresult_factory(subject, trialitem)
        trial_result.webcam_file.name = ''
        
        assert trial_result.filename == ''


class TestDeleteFileSignal:
    """Test _delete_file and delete_file signal."""

    def test_delete_file_removes_existing_file(self, monkeypatch):
        """Test _delete_file removes file if it exists."""
        removed_files = []
        
        def mock_isfile(path):
            return True
        
        def mock_remove(path):
            removed_files.append(path)
        
        monkeypatch.setattr('os.path.isfile', mock_isfile)
        monkeypatch.setattr('os.remove', mock_remove)
        
        _delete_file('/fake/path/file.txt')
        assert '/fake/path/file.txt' in removed_files

    def test_delete_file_skips_nonexistent_file(self, monkeypatch):
        """Test _delete_file does not remove file if it doesn't exist."""
        removed_files = []
        
        def mock_isfile(path):
            return False
        
        def mock_remove(path):
            removed_files.append(path)
        
        monkeypatch.setattr('os.path.isfile', mock_isfile)
        monkeypatch.setattr('os.remove', mock_remove)
        
        _delete_file('/fake/path/nonexistent.txt')
        assert len(removed_files) == 0


class TestHelperFunctions:
    """Test helper functions in models.py."""

    def test_experiment_folder(self):
        """Test experiment_folder generates correct path."""
        class MockInstance:
            exp_name = "TestExp"
        
        instance = MockInstance()
        result = experiment_folder(instance, "myfile.png")
        assert result == "uploads/experiments/TestExp/myfile.png"

    def test_visual_folder(self):
        """Test visual_folder generates correct path."""
        class MockExperiment:
            exp_name = "ExpName"
        
        class MockListItem:
            experiment = MockExperiment()
            list_name = "ListA"
        
        class MockBlockItem:
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        result = visual_folder(instance, "image.jpg")
        assert result == "uploads/ExpName/ListA/visual/image.jpg"

    def test_audio_folder(self):
        """Test audio_folder generates correct path."""
        class MockExperiment:
            exp_name = "ExpName"
        
        class MockListItem:
            experiment = MockExperiment()
            list_name = "ListB"
        
        class MockBlockItem:
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        result = audio_folder(instance, "sound.mp3")
        assert result == "uploads/ExpName/ListB/audio/sound.mp3"

    def test_default_calibration_points(self):
        """Test default_calibration_points returns expected structure."""
        points = default_calibration_points()
        assert isinstance(points, list)
        assert len(points) == 9
        assert points[0] == [50, 50]
        assert points[1] == [50, 12]
        # Verify it's a new list each time (not a mutable default)
        points2 = default_calibration_points()
        assert points is not points2
