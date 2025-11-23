"""Unit tests for ipl/experiments/models.py"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.core.exceptions import ValidationError
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
    validate_list,
    validate_range,
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
    _delete_file,
    delete_file,
)


class TestModelStringMethods:
    """Test __str__ methods for models."""
    
    def test_instrument_str(self, instrument_factory):
        """Test Instrument.__str__ returns instrument name."""
        instrument = instrument_factory(instr_name='CDI Test')
        assert str(instrument) == 'CDI Test'
    
    def test_experiment_str(self, experiment_factory):
        """Test Experiment.__str__ returns experiment name."""
        experiment = experiment_factory(exp_name='My Experiment')
        assert str(experiment) == 'My Experiment'
    
    def test_listitem_str(self, experiment_factory, listitem_factory):
        """Test ListItem.__str__ returns list name."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment, list_name='List A')
        assert str(listitem) == 'List A'
    
    def test_outerblock_str(self, experiment_factory, listitem_factory, outerblock_factory):
        """Test OuterBlockItem.__str__ returns outer block name."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem, outer_block_name='Block 1')
        assert str(outerblock) == 'Block 1'
    
    def test_blockitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        """Test BlockItem.__str__ returns label."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock, label='Inner Block')
        assert str(blockitem) == 'Inner Block'
    
    def test_trialitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
        """Test TrialItem.__str__ returns label."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem, label='Trial 1')
        assert str(trialitem) == 'Trial 1'


class TestQuestionModel:
    """Test Question model methods."""
    
    def test_question_get_choices(self, experiment_factory, question_factory):
        """Test Question.get_choices parses choices correctly."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.RADIO,
            choices='apple, banana, cherry'
        )
        choices = question.get_choices()
        assert choices == (('apple', 'apple'), ('banana', 'banana'), ('cherry', 'cherry'))
    
    def test_question_get_choices_with_extra_spaces(self, experiment_factory, question_factory):
        """Test Question.get_choices handles extra spaces."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.SELECT,
            choices='  a  ,  b  ,  c  '
        )
        choices = question.get_choices()
        assert choices == (('a', 'a'), ('b', 'b'), ('c', 'c'))
    
    def test_question_clean_radio_validates_list(self, experiment_factory, question_factory):
        """Test Question.clean validates list for radio type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.RADIO,
            choices='single'
        )
        with pytest.raises(ValidationError):
            question.clean()
    
    def test_question_clean_select_validates_list(self, experiment_factory, question_factory):
        """Test Question.clean validates list for select type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.SELECT,
            choices='a, b'
        )
        question.clean()  # Should not raise
    
    def test_question_clean_num_range_validates_range(self, experiment_factory, question_factory):
        """Test Question.clean validates range for num_range type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.NUM_RANGE,
            choices='1, 10'
        )
        question.clean()  # Should not raise
    
    def test_question_clean_age_validates_range(self, experiment_factory, question_factory):
        """Test Question.clean validates range for age type."""
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.AGE,
            choices='12, 36'
        )
        question.clean()  # Should not raise


class TestValidationFunctions:
    """Test validation helper functions."""
    
    def test_validate_list_success(self):
        """Test validate_list with valid input."""
        validate_list('a, b')  # Should not raise
    
    def test_validate_list_failure_single_item(self):
        """Test validate_list raises ValidationError for single item."""
        with pytest.raises(ValidationError):
            validate_list('single')
    
    def test_validate_list_failure_empty(self):
        """Test validate_list raises ValidationError for empty."""
        with pytest.raises(ValidationError):
            validate_list('')
    
    def test_validate_range_success(self):
        """Test validate_range with valid input."""
        validate_range('1, 10')  # Should not raise
    
    def test_validate_range_failure_wrong_count(self):
        """Test validate_range raises ValidationError for wrong count."""
        with pytest.raises(ValidationError):
            validate_range('1, 2, 3')
    
    def test_validate_range_failure_min_greater_than_max(self):
        """Test validate_range raises ValidationError when min >= max."""
        with pytest.raises(ValidationError):
            validate_range('10, 5')
    
    def test_validate_range_failure_non_integer(self):
        """Test validate_range raises ValidationError for non-integers."""
        with pytest.raises(ValidationError):
            validate_range('a, b')


class TestExperimentMethods:
    """Test Experiment model methods."""
    
    def test_subject_questions(self, experiment_factory, question_factory):
        """Test Experiment.subject_questions returns questions in order."""
        experiment = experiment_factory()
        q1 = question_factory(experiment, text='Q1', position=2)
        q2 = question_factory(experiment, text='Q2', position=1)
        
        questions = experiment.subject_questions()
        assert list(questions) == [q2, q1]
    
    def test_consent_questions(self, experiment_factory, consent_question_factory):
        """Test Experiment.consent_questions returns questions in order."""
        experiment = experiment_factory()
        cq1 = consent_question_factory(experiment, text='CQ1', position=2)
        cq2 = consent_question_factory(experiment, text='CQ2', position=1)
        
        questions = experiment.consent_questions()
        assert list(questions) == [cq2, cq1]
    
    def test_get_list_item_least_played(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test Experiment.get_list_item with least played strategy."""
        experiment = experiment_factory(list_selection_strategy='LPF')
        list1 = listitem_factory(experiment, list_name='List1')
        list2 = listitem_factory(experiment, list_name='List2')
        
        # Create subject data for list1 only
        subjectdata_factory(experiment, listitem=list1)
        
        # Should return list2 as it has been played less
        result = experiment.get_list_item()
        assert result == list2
    
    def test_get_list_item_sequential(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test Experiment.get_list_item with sequential strategy."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        list1 = listitem_factory(experiment, list_name='List1')
        list2 = listitem_factory(experiment, list_name='List2')
        
        # Create subject data for list1
        subjectdata_factory(experiment, subject_id='subj1', listitem=list1)
        
        # Should return list2 as it's next in sequence
        result = experiment.get_list_item()
        assert result == list2
    
    @patch('ipl.experiments.models.random.choice')
    def test_get_list_item_random(self, mock_choice, experiment_factory, listitem_factory):
        """Test Experiment.get_list_item with random strategy."""
        experiment = experiment_factory(list_selection_strategy='RAN')
        list1 = listitem_factory(experiment, list_name='List1')
        list2 = listitem_factory(experiment, list_name='List2')
        
        # Mock random.choice to return list1.pk
        mock_choice.return_value = list1.pk
        
        result = experiment.get_list_item()
        assert result == list1
        assert mock_choice.called
    
    def test_get_list_item_excludes_excluded_lists(self, experiment_factory, listitem_factory):
        """Test Experiment.get_list_item excludes excluded lists."""
        experiment = experiment_factory()
        list1 = listitem_factory(experiment, list_name='List1', exclude_list=True)
        list2 = listitem_factory(experiment, list_name='List2', exclude_list=False)
        
        result = experiment.get_list_item()
        assert result == list2


class TestTrialResult:
    """Test TrialResult model."""
    
    def test_filename_property(self, experiment_factory, listitem_factory, outerblock_factory, 
                                blockitem_factory, trialitem_factory, subjectdata_factory, 
                                trialresult_factory):
        """Test TrialResult.filename property extracts basename."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        trial_result = trialresult_factory(subject, trialitem)
        trial_result.webcam_file.name = 'path/to/video/file.mp4'
        
        assert trial_result.filename == 'file.mp4'


class TestDeleteFileFunctions:
    """Test file deletion functions."""
    
    @patch('ipl.experiments.models.os.path.isfile')
    @patch('ipl.experiments.models.os.remove')
    def test_delete_file_removes_existing_file(self, mock_remove, mock_isfile):
        """Test _delete_file removes file when it exists."""
        mock_isfile.return_value = True
        
        _delete_file('/path/to/file.mp4')
        
        mock_isfile.assert_called_once_with('/path/to/file.mp4')
        mock_remove.assert_called_once_with('/path/to/file.mp4')
    
    @patch('ipl.experiments.models.os.path.isfile')
    @patch('ipl.experiments.models.os.remove')
    def test_delete_file_does_not_remove_nonexistent_file(self, mock_remove, mock_isfile):
        """Test _delete_file does not remove file when it doesn't exist."""
        mock_isfile.return_value = False
        
        _delete_file('/path/to/nonexistent.mp4')
        
        mock_isfile.assert_called_once_with('/path/to/nonexistent.mp4')
        mock_remove.assert_not_called()
    
    @patch('ipl.experiments.models._delete_file')
    def test_delete_file_signal_handler(self, mock_delete, experiment_factory, listitem_factory,
                                        outerblock_factory, blockitem_factory, trialitem_factory,
                                        subjectdata_factory, trialresult_factory, settings):
        """Test delete_file signal handler calls _delete_file."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        trial_result = trialresult_factory(subject, trialitem)
        trial_result.webcam_file.name = 'test_video.mp4'
        
        # Mock settings.WEBCAM_ROOT
        with patch('ipl.experiments.models.settings.WEBCAM_ROOT', '/webcam'):
            # Call signal handler directly
            delete_file(TrialResult, trial_result)
            
            mock_delete.assert_called_once_with('/webcam/test_video.mp4')


class TestPathHelperFunctions:
    """Test path helper functions."""
    
    def test_experiment_folder(self):
        """Test experiment_folder generates correct path."""
        mock_instance = Mock(exp_name='MyExperiment')
        path = experiment_folder(mock_instance, 'file.png')
        assert path == 'uploads/experiments/MyExperiment/file.png'
    
    def test_visual_folder(self):
        """Test visual_folder generates correct path."""
        mock_blockitem = Mock()
        mock_blockitem.listitem.experiment.exp_name = 'ExpName'
        mock_blockitem.listitem.list_name = 'ListName'
        mock_instance = Mock(blockitem=mock_blockitem)
        
        path = visual_folder(mock_instance, 'image.jpg')
        assert path == 'uploads/ExpName/ListName/visual/image.jpg'
    
    def test_audio_folder(self):
        """Test audio_folder generates correct path."""
        mock_blockitem = Mock()
        mock_blockitem.listitem.experiment.exp_name = 'ExpName'
        mock_blockitem.listitem.list_name = 'ListName'
        mock_instance = Mock(blockitem=mock_blockitem)
        
        path = audio_folder(mock_instance, 'sound.mp3')
        assert path == 'uploads/ExpName/ListName/audio/sound.mp3'
    
    def test_default_calibration_points(self):
        """Test default_calibration_points returns correct grid."""
        points = default_calibration_points()
        expected = [[50,50], [50,12], [12,12], [12,50], [12,88], [50,88], [88,88], [88,50], [88,12]]
        assert points == expected
