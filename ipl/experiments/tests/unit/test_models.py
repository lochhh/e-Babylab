"""Unit tests for models.py"""
import pytest
import os
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
)


class TestModelStringRepresentations:
    """Test __str__ methods for all models."""
    
    def test_instrument_str(self, instrument_factory):
        instrument = instrument_factory(instr_name='My Instrument')
        assert str(instrument) == 'My Instrument'
    
    def test_experiment_str(self, experiment_factory):
        experiment = experiment_factory(exp_name='My Experiment')
        assert str(experiment) == 'My Experiment'
    
    def test_listitem_str(self, experiment_factory, listitem_factory):
        experiment = experiment_factory()
        listitem = listitem_factory(experiment, list_name='List A')
        assert str(listitem) == 'List A'
    
    def test_outerblock_str(self, experiment_factory, listitem_factory, outerblock_factory):
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem, outer_block_name='Outer Block 1')
        assert str(outerblock) == 'Outer Block 1'
    
    def test_blockitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock, label='Block 1')
        assert str(blockitem) == 'Block 1'
    
    def test_trialitem_str(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem, label='Trial 1')
        assert str(trialitem) == 'Trial 1'
    
    def test_subjectdata_str(self, experiment_factory, subjectdata_factory):
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment, id='test-uuid-123')
        assert str(subject) == 'test-uuid-123'
    
    def test_question_str(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(experiment, text='What is your name?')
        assert str(question) == 'What is your name?'
    
    def test_consent_question_str(self, experiment_factory, consent_question_factory):
        experiment = experiment_factory()
        consent_q = consent_question_factory(experiment, text='Do you agree?')
        assert str(consent_q) == 'Do you agree?'


class TestQuestionModel:
    """Test Question model methods and validation."""
    
    def test_get_choices(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.RADIO,
            choices='option1, option2, option3'
        )
        choices = question.get_choices()
        assert choices == (('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3'))
    
    def test_get_choices_with_extra_spaces(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.RADIO,
            choices='  option1  ,  option2  '
        )
        choices = question.get_choices()
        assert choices == (('option1', 'option1'), ('option2', 'option2'))
    
    def test_clean_radio_requires_choices(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.RADIO,
            choices='single'
        )
        with pytest.raises(ValidationError):
            question.clean()
    
    def test_clean_select_requires_choices(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.SELECT,
            choices='only_one'
        )
        with pytest.raises(ValidationError):
            question.clean()
    
    def test_clean_num_range_requires_two_values(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.NUM_RANGE,
            choices='1'
        )
        with pytest.raises(ValidationError):
            question.clean()
    
    def test_clean_num_range_min_less_than_max(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.NUM_RANGE,
            choices='10, 5'
        )
        with pytest.raises(ValidationError):
            question.clean()
    
    def test_clean_age_requires_valid_range(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        question = question_factory(
            experiment,
            question_type=Question.AGE,
            choices='not, numbers'
        )
        with pytest.raises(ValidationError):
            question.clean()


class TestValidationFunctions:
    """Test validation helper functions."""
    
    def test_validate_list_valid(self):
        validate_list('option1, option2')  # Should not raise
    
    def test_validate_list_single_item(self):
        with pytest.raises(ValidationError):
            validate_list('single')
    
    def test_validate_list_empty(self):
        with pytest.raises(ValidationError):
            validate_list('')
    
    def test_validate_range_valid(self):
        validate_range('1, 10')  # Should not raise
    
    def test_validate_range_single_value(self):
        with pytest.raises(ValidationError):
            validate_range('5')
    
    def test_validate_range_three_values(self):
        with pytest.raises(ValidationError):
            validate_range('1, 5, 10')
    
    def test_validate_range_min_greater_than_max(self):
        with pytest.raises(ValidationError):
            validate_range('10, 5')
    
    def test_validate_range_non_integers(self):
        with pytest.raises(ValidationError):
            validate_range('a, b')


class TestExperimentModel:
    """Test Experiment model methods."""
    
    def test_subject_questions(self, experiment_factory, question_factory):
        experiment = experiment_factory()
        q1 = question_factory(experiment, position=2, text='Question 2')
        q2 = question_factory(experiment, position=1, text='Question 1')
        
        questions = list(experiment.subject_questions())
        assert len(questions) == 2
        assert questions[0].text == 'Question 1'
        assert questions[1].text == 'Question 2'
    
    def test_subject_questions_empty(self, experiment_factory):
        experiment = experiment_factory()
        questions = experiment.subject_questions()
        assert list(questions) == []
    
    def test_consent_questions(self, experiment_factory, consent_question_factory):
        experiment = experiment_factory()
        cq1 = consent_question_factory(experiment, position=2, text='Consent 2')
        cq2 = consent_question_factory(experiment, position=1, text='Consent 1')
        
        questions = list(experiment.consent_questions())
        assert len(questions) == 2
        assert questions[0].text == 'Consent 1'
        assert questions[1].text == 'Consent 2'
    
    def test_get_list_item_random(self, monkeypatch, experiment_factory, listitem_factory):
        """Test random list selection strategy."""
        experiment = experiment_factory(list_selection_strategy='RAN')
        li1 = listitem_factory(experiment, list_name='List 1')
        li2 = listitem_factory(experiment, list_name='List 2')
        
        # Mock random.choice to return li1.pk
        import random
        monkeypatch.setattr(random, 'choice', lambda x: li1.pk)
        
        selected = experiment.get_list_item()
        assert selected == li1
    
    def test_get_list_item_sequential_first(self, experiment_factory, listitem_factory):
        """Test sequential selection when no subjects exist."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        li1 = listitem_factory(experiment, list_name='List 1')
        li2 = listitem_factory(experiment, list_name='List 2')
        
        selected = experiment.get_list_item()
        assert selected == li1
    
    def test_get_list_item_sequential_next(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test sequential selection with existing subjects."""
        experiment = experiment_factory(list_selection_strategy='SEQ')
        li1 = listitem_factory(experiment, list_name='List 1')
        li2 = listitem_factory(experiment, list_name='List 2')
        
        # Create subject with li1
        subject = subjectdata_factory(experiment, listitem=li1)
        
        selected = experiment.get_list_item()
        assert selected == li2
    
    def test_get_list_item_least_played(self, experiment_factory, listitem_factory, subjectdata_factory):
        """Test least played selection strategy."""
        experiment = experiment_factory(list_selection_strategy='LPF')
        li1 = listitem_factory(experiment, list_name='List 1')
        li2 = listitem_factory(experiment, list_name='List 2')
        
        # Create 2 subjects with li1, 1 with li2
        subjectdata_factory(experiment, listitem=li1, id='sub1')
        subjectdata_factory(experiment, listitem=li1, id='sub2')
        subjectdata_factory(experiment, listitem=li2, id='sub3')
        
        selected = experiment.get_list_item()
        assert selected == li2
    
    def test_get_list_item_excludes_excluded_lists(self, experiment_factory, listitem_factory):
        """Test that excluded lists are not selected."""
        experiment = experiment_factory(list_selection_strategy='RAN')
        li1 = listitem_factory(experiment, exclude_list=True)
        li2 = listitem_factory(experiment, exclude_list=False)
        
        selected = experiment.get_list_item()
        assert selected == li2
    
    def test_get_list_item_returns_none_when_no_lists(self, experiment_factory):
        """Test that None is returned when no lists exist."""
        experiment = experiment_factory()
        selected = experiment.get_list_item()
        assert selected is None


class TestTrialResultModel:
    """Test TrialResult model methods."""
    
    def test_filename_property(self, experiment_factory, listitem_factory, outerblock_factory, 
                               blockitem_factory, trialitem_factory, subjectdata_factory, 
                               trialresult_factory):
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        trial_result = trialresult_factory(subject, trialitem)
        trial_result.webcam_file.name = 'path/to/file.webm'
        
        assert trial_result.filename == 'file.webm'
    
    def test_filename_empty(self, experiment_factory, listitem_factory, outerblock_factory, 
                            blockitem_factory, trialitem_factory, subjectdata_factory, 
                            trialresult_factory):
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
    """Test file deletion functionality."""
    
    def test_delete_file_function(self, monkeypatch):
        """Test _delete_file removes file when it exists."""
        removed_files = []
        
        monkeypatch.setattr(os.path, 'isfile', lambda x: True)
        monkeypatch.setattr(os, 'remove', lambda x: removed_files.append(x))
        
        _delete_file('/path/to/file.txt')
        assert '/path/to/file.txt' in removed_files
    
    def test_delete_file_function_nonexistent(self, monkeypatch):
        """Test _delete_file does nothing when file doesn't exist."""
        removed_files = []
        
        monkeypatch.setattr(os.path, 'isfile', lambda x: False)
        monkeypatch.setattr(os, 'remove', lambda x: removed_files.append(x))
        
        _delete_file('/path/to/file.txt')
        assert removed_files == []


class TestHelperFunctions:
    """Test helper path functions."""
    
    def test_experiment_folder(self, experiment_factory):
        experiment = experiment_factory(exp_name='TestExp')
        
        class MockInstance:
            exp_name = 'TestExp'
        
        result = experiment_folder(MockInstance(), 'testfile.png')
        assert result == 'uploads/experiments/TestExp/testfile.png'
    
    def test_visual_folder(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        experiment = experiment_factory(exp_name='TestExp')
        listitem = listitem_factory(experiment, list_name='ListA')
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        
        class MockInstance:
            blockitem = blockitem
        
        result = visual_folder(MockInstance(), 'visual.jpg')
        assert result == 'uploads/TestExp/ListA/visual/visual.jpg'
    
    def test_audio_folder(self, experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
        experiment = experiment_factory(exp_name='TestExp')
        listitem = listitem_factory(experiment, list_name='ListA')
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        
        class MockInstance:
            blockitem = blockitem
        
        result = audio_folder(MockInstance(), 'audio.mp3')
        assert result == 'uploads/TestExp/ListA/audio/audio.mp3'
    
    def test_default_calibration_points(self):
        points = default_calibration_points()
        assert len(points) == 9
        assert [50, 50] in points
        assert [12, 12] in points
        assert [88, 88] in points
