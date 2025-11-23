"""
Unit tests for ipl.experiments.models module.
"""
import os
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock
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
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
    _delete_file,
)


class TestInstrument:
    """Tests for Instrument model."""

    def test_instrument_str(self, instrument_factory):
        """Test __str__ method of Instrument."""
        instrument = instrument_factory(instr_name="Test CDI Instrument")
        assert str(instrument) == "Test CDI Instrument"


class TestExperiment:
    """Tests for Experiment model."""

    def test_experiment_str(self, experiment_factory):
        """Test __str__ method of Experiment."""
        experiment = experiment_factory(exp_name="My Test Experiment")
        assert str(experiment) == "My Test Experiment"

    def test_subject_questions(self, experiment_factory, question_factory):
        """Test subject_questions method."""
        experiment = experiment_factory()
        q1 = question_factory(experiment=experiment, position=2, text="Question 2")
        q2 = question_factory(experiment=experiment, position=1, text="Question 1")
        
        questions = experiment.subject_questions()
        assert questions.count() == 2
        # Check ordering by position
        assert list(questions.values_list('text', flat=True)) == ['Question 1', 'Question 2']

    def test_subject_questions_no_pk(self):
        """Test subject_questions when experiment has no pk."""
        experiment = Experiment()
        assert experiment.subject_questions() is None

    def test_consent_questions(self, experiment_factory, consent_question_factory):
        """Test consent_questions method."""
        experiment = experiment_factory()
        cq1 = consent_question_factory(experiment=experiment, position=2, text="Consent 2")
        cq2 = consent_question_factory(experiment=experiment, position=1, text="Consent 1")
        
        questions = experiment.consent_questions()
        assert questions.count() == 2
        # Check ordering by position
        assert list(questions.values_list('text', flat=True)) == ['Consent 1', 'Consent 2']

    def test_consent_questions_no_pk(self):
        """Test consent_questions when experiment has no pk."""
        experiment = Experiment()
        assert experiment.consent_questions() is None

    def test_get_list_item_none(self, experiment_factory):
        """Test get_list_item when no list items exist."""
        experiment = experiment_factory()
        assert experiment.get_list_item() is None

    def test_get_list_item_no_pk(self):
        """Test get_list_item when experiment has no pk."""
        experiment = Experiment()
        assert experiment.get_list_item() is None

    def test_get_list_item_all_excluded(self, experiment_factory, listitem_factory):
        """Test get_list_item when all lists are excluded."""
        experiment = experiment_factory()
        listitem_factory(experiment=experiment, exclude_list=True)
        assert experiment.get_list_item() is None

    def test_get_list_item_least_played(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test get_list_item with least played first strategy."""
        experiment = experiment_factory(list_selection_strategy='LPF')
        li1 = listitem_factory(experiment=experiment, list_name="List 1")
        li2 = listitem_factory(experiment=experiment, list_name="List 2")
        
        # Create more subject data for li1
        subjectdata_factory(experiment=experiment, listitem=li1)
        subjectdata_factory(experiment=experiment, listitem=li1)
        subjectdata_factory(experiment=experiment, listitem=li2)
        
        # Should return li2 as it has fewer participants
        result = experiment.get_list_item()
        assert result == li2

    def test_get_list_item_sequential(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test get_list_item with sequential strategy."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        li1 = listitem_factory(experiment=experiment, list_name="List 1")
        li2 = listitem_factory(experiment=experiment, list_name="List 2")
        
        # No subjects yet - should return first list
        result = experiment.get_list_item()
        assert result == li1
        
        # Add a subject with li1
        subjectdata_factory(experiment=experiment, listitem=li1)
        
        # Should now return li2
        result = experiment.get_list_item()
        assert result == li2

    @patch('ipl.experiments.models.random.choice')
    def test_get_list_item_random(self, mock_choice, experiment_factory, listitem_factory):
        """Test get_list_item with random strategy."""
        experiment = experiment_factory(list_selection_strategy='RAN')
        li1 = listitem_factory(experiment=experiment, list_name="List 1")
        li2 = listitem_factory(experiment=experiment, list_name="List 2")
        
        # Mock random.choice to return li1's pk
        mock_choice.return_value = li1.pk
        
        result = experiment.get_list_item()
        assert result == li1
        assert mock_choice.called


class TestListItem:
    """Tests for ListItem model."""

    def test_listitem_str(self, experiment_factory, listitem_factory):
        """Test __str__ method of ListItem."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment, list_name="My List")
        assert str(listitem) == "My List"


class TestOuterBlockItem:
    """Tests for OuterBlockItem model."""

    def test_outerblock_str(self, experiment_factory, listitem_factory, outerblock_factory):
        """Test __str__ method of OuterBlockItem."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment)
        outerblock = outerblock_factory(listitem=listitem, outer_block_name="Block A")
        assert str(outerblock) == "Block A"


class TestBlockItem:
    """Tests for BlockItem model."""

    def test_blockitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        """Test __str__ method of BlockItem."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment)
        outerblock = outerblock_factory(listitem=listitem)
        blockitem = blockitem_factory(outerblockitem=outerblock, label="Inner Block 1")
        assert str(blockitem) == "Inner Block 1"


class TestTrialItem:
    """Tests for TrialItem model."""

    def test_trialitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
        """Test __str__ method of TrialItem."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment)
        outerblock = outerblock_factory(listitem=listitem)
        blockitem = blockitem_factory(outerblockitem=outerblock)
        trialitem = trialitem_factory(blockitem=blockitem, label="Trial 1")
        assert str(trialitem) == "Trial 1"


class TestSubjectData:
    """Tests for SubjectData model."""

    def test_subjectdata_str(self, experiment_factory, subjectdata_factory):
        """Test __str__ method of SubjectData."""
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment=experiment, id="test-uuid-123")
        assert str(subject) == "test-uuid-123"


class TestTrialResult:
    """Tests for TrialResult model."""

    def test_filename_property(self, experiment_factory, listitem_factory, outerblock_factory, 
                              blockitem_factory, trialitem_factory, subjectdata_factory, 
                              trialresult_factory):
        """Test filename property of TrialResult."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment)
        outerblock = outerblock_factory(listitem=listitem)
        blockitem = blockitem_factory(outerblockitem=outerblock)
        trialitem = trialitem_factory(blockitem=blockitem)
        subject = subjectdata_factory(experiment=experiment)
        
        # Create trial result with mocked webcam_file
        trial_result = trialresult_factory(subject=subject, trialitem=trialitem)
        trial_result.webcam_file.name = 'path/to/video.mp4'
        
        assert trial_result.filename == 'video.mp4'

    @patch('ipl.experiments.models.os.path.isfile')
    @patch('ipl.experiments.models.os.remove')
    def test_delete_file_function(self, mock_remove, mock_isfile):
        """Test _delete_file helper function."""
        mock_isfile.return_value = True
        
        _delete_file('/path/to/file.txt')
        
        mock_isfile.assert_called_once_with('/path/to/file.txt')
        mock_remove.assert_called_once_with('/path/to/file.txt')

    @patch('ipl.experiments.models.os.path.isfile')
    @patch('ipl.experiments.models.os.remove')
    def test_delete_file_not_exists(self, mock_remove, mock_isfile):
        """Test _delete_file when file doesn't exist."""
        mock_isfile.return_value = False
        
        _delete_file('/path/to/nonexistent.txt')
        
        mock_isfile.assert_called_once()
        mock_remove.assert_not_called()

    @patch('ipl.experiments.models._delete_file')
    @patch('ipl.experiments.models.settings')
    def test_delete_file_receiver(self, mock_settings, mock_delete_file, experiment_factory, 
                                  listitem_factory, outerblock_factory, blockitem_factory, 
                                  trialitem_factory, subjectdata_factory, trialresult_factory):
        """Test delete_file signal receiver."""
        mock_settings.WEBCAM_ROOT = '/media/webcam'
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment=experiment)
        outerblock = outerblock_factory(listitem=listitem)
        blockitem = blockitem_factory(outerblockitem=outerblock)
        trialitem = trialitem_factory(blockitem=blockitem)
        subject = subjectdata_factory(experiment=experiment)
        
        trial_result = trialresult_factory(subject=subject, trialitem=trialitem)
        trial_result.webcam_file.name = 'test/video.mp4'
        
        # Delete the trial result - this should trigger the signal
        trial_result.delete()
        
        # Verify _delete_file was called with the correct path
        expected_path = os.path.join('/media/webcam', 'test/video.mp4')
        mock_delete_file.assert_called_once_with(expected_path)


class TestQuestion:
    """Tests for Question model."""

    def test_question_str(self, experiment_factory, question_factory):
        """Test __str__ method of Question."""
        experiment = experiment_factory()
        question = question_factory(experiment=experiment, text="What is your name?")
        assert str(question) == "What is your name?"

    def test_get_choices(self, experiment_factory, question_factory):
        """Test get_choices method."""
        experiment = experiment_factory()
        question = question_factory(
            experiment=experiment,
            question_type='radio',
            choices='Option A, Option B, Option C'
        )
        
        result = question.get_choices()
        expected = (('Option A', 'Option A'), ('Option B', 'Option B'), ('Option C', 'Option C'))
        assert result == expected

    def test_get_choices_with_spaces(self, experiment_factory, question_factory):
        """Test get_choices with extra spaces."""
        experiment = experiment_factory()
        question = question_factory(
            experiment=experiment,
            question_type='select',
            choices='  Yes  ,  No  ,  Maybe  '
        )
        
        result = question.get_choices()
        expected = (('Yes', 'Yes'), ('No', 'No'), ('Maybe', 'Maybe'))
        assert result == expected

    def test_clean_radio_valid(self, experiment_factory, question_factory):
        """Test clean method for radio type with valid choices."""
        experiment = experiment_factory()
        question = question_factory(
            experiment=experiment,
            question_type='radio',
            choices='A, B'
        )
        # Should not raise
        question.clean()

    def test_clean_radio_invalid(self, experiment_factory):
        """Test clean method for radio type with invalid choices."""
        experiment = experiment_factory()
        question = Question(
            experiment=experiment,
            text="Test?",
            required=True,
            question_type='radio',
            choices='Only one option'
        )
        
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_num_range_valid(self, experiment_factory, question_factory):
        """Test clean method for num_range type with valid range."""
        experiment = experiment_factory()
        question = question_factory(
            experiment=experiment,
            question_type='number-range',
            choices='1, 10'
        )
        # Should not raise
        question.clean()

    def test_clean_num_range_invalid_not_two_values(self, experiment_factory):
        """Test clean method for num_range with wrong number of values."""
        experiment = experiment_factory()
        question = Question(
            experiment=experiment,
            text="Test?",
            required=True,
            question_type='number-range',
            choices='1, 5, 10'
        )
        
        with pytest.raises(ValidationError):
            question.clean()

    def test_clean_num_range_invalid_min_greater_than_max(self, experiment_factory):
        """Test clean method for num_range with min > max."""
        experiment = experiment_factory()
        question = Question(
            experiment=experiment,
            text="Test?",
            required=True,
            question_type='number-range',
            choices='10, 5'
        )
        
        with pytest.raises(ValidationError):
            question.clean()


class TestConsentQuestion:
    """Tests for ConsentQuestion model."""

    def test_consent_question_str(self, experiment_factory, consent_question_factory):
        """Test __str__ method of ConsentQuestion."""
        experiment = experiment_factory()
        consent_q = consent_question_factory(
            experiment=experiment,
            text="Do you agree to participate?"
        )
        assert str(consent_q) == "Do you agree to participate?"


class TestValidators:
    """Tests for validator functions."""

    def test_validate_list_valid(self):
        """Test validate_list with valid input."""
        # Should not raise
        validate_list('a, b')
        validate_list('option1, option2, option3')

    def test_validate_list_invalid_single(self):
        """Test validate_list with single option."""
        with pytest.raises(ValidationError):
            validate_list('only one')

    def test_validate_list_invalid_empty(self):
        """Test validate_list with empty string."""
        with pytest.raises(ValidationError):
            validate_list('')

    def test_validate_range_valid(self):
        """Test validate_range with valid range."""
        validate_range('1, 10')
        validate_range('0, 100')

    def test_validate_range_invalid_three_values(self):
        """Test validate_range with three values."""
        with pytest.raises(ValidationError):
            validate_range('1, 5, 10')

    def test_validate_range_invalid_min_greater(self):
        """Test validate_range with min > max."""
        with pytest.raises(ValidationError):
            validate_range('10, 5')

    def test_validate_range_invalid_non_integer(self):
        """Test validate_range with non-integer values."""
        with pytest.raises(ValidationError):
            validate_range('a, b')


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_experiment_folder(self):
        """Test experiment_folder function."""
        mock_instance = Mock()
        mock_instance.exp_name = 'test_exp'
        
        result = experiment_folder(mock_instance, 'file.png')
        expected = 'uploads/experiments/test_exp/file.png'
        assert result == expected

    def test_visual_folder(self):
        """Test visual_folder function."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'exp1'
        mock_instance.blockitem.listitem.list_name = 'list1'
        
        result = visual_folder(mock_instance, 'image.jpg')
        expected = 'uploads/exp1/list1/visual/image.jpg'
        assert result == expected

    def test_audio_folder(self):
        """Test audio_folder function."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'exp2'
        mock_instance.blockitem.listitem.list_name = 'list2'
        
        result = audio_folder(mock_instance, 'sound.mp3')
        expected = 'uploads/exp2/list2/audio/sound.mp3'
        assert result == expected

    def test_default_calibration_points(self):
        """Test default_calibration_points function."""
        result = default_calibration_points()
        expected = [[50,50], [50,12], [12,12], [12,50], [12,88], [50,88], [88,88], [88,50], [88,12]]
        assert result == expected
        assert len(result) == 9
