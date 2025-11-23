"""Unit tests for ipl.experiments.models"""
import pytest
import os
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
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
    validate_list,
    validate_range,
    _delete_file,
)


# Test __str__ methods
def test_instrument_str(instrument_factory):
    """Test Instrument __str__ method."""
    instrument = instrument_factory(instr_name="Test CDI Instrument")
    assert str(instrument) == "Test CDI Instrument"


def test_experiment_str(experiment_factory):
    """Test Experiment __str__ method."""
    experiment = experiment_factory(exp_name="My Experiment")
    assert str(experiment) == "My Experiment"


def test_listitem_str(experiment_factory, listitem_factory):
    """Test ListItem __str__ method."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment, list_name="List A")
    assert str(listitem) == "List A"


def test_outerblockitem_str(experiment_factory, listitem_factory, outerblock_factory):
    """Test OuterBlockItem __str__ method."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    outerblock = outerblock_factory(listitem, outer_block_name="Outer 1")
    assert str(outerblock) == "Outer 1"


def test_blockitem_str(experiment_factory, listitem_factory, outerblock_factory, blockitem_factory):
    """Test BlockItem __str__ method."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    outerblock = outerblock_factory(listitem)
    blockitem = blockitem_factory(outerblock, label="Block Label")
    assert str(blockitem) == "Block Label"


def test_trialitem_str(experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, trialitem_factory):
    """Test TrialItem __str__ method."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    outerblock = outerblock_factory(listitem)
    blockitem = blockitem_factory(outerblock)
    trialitem = trialitem_factory(blockitem, label="Trial 1")
    assert str(trialitem) == "Trial 1"


def test_subjectdata_str(experiment_factory, subjectdata_factory):
    """Test SubjectData __str__ method."""
    experiment = experiment_factory()
    subject = subjectdata_factory(experiment, id="subject-123")
    assert str(subject) == "subject-123"


# Test Question methods
def test_question_get_choices(experiment_factory, question_factory):
    """Test Question.get_choices method."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.RADIO,
        choices="option1, option2, option3"
    )
    choices = question.get_choices()
    assert choices == (('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3'))


def test_question_get_choices_with_empty_strings(experiment_factory, question_factory):
    """Test Question.get_choices handles empty strings."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.SELECT,
        choices="a, , b,  ,c"
    )
    choices = question.get_choices()
    assert choices == (('a', 'a'), ('b', 'b'), ('c', 'c'))


def test_validate_list_valid(experiment_factory, question_factory):
    """Test validate_list with valid choices."""
    # Should not raise for valid list
    validate_list("choice1, choice2")
    validate_list("a, b, c, d")


def test_validate_list_invalid(experiment_factory, question_factory):
    """Test validate_list with invalid choices."""
    with pytest.raises(ValidationError):
        validate_list("single_choice")
    with pytest.raises(ValidationError):
        validate_list("")


def test_validate_range_valid():
    """Test validate_range with valid range."""
    validate_range("1, 10")
    validate_range("0, 100")


def test_validate_range_invalid_single_value():
    """Test validate_range with single value."""
    with pytest.raises(ValidationError):
        validate_range("5")


def test_validate_range_invalid_min_max():
    """Test validate_range with min >= max."""
    with pytest.raises(ValidationError):
        validate_range("10, 5")
    with pytest.raises(ValidationError):
        validate_range("5, 5")


def test_validate_range_invalid_non_integer():
    """Test validate_range with non-integer values."""
    with pytest.raises(ValidationError):
        validate_range("a, b")
    with pytest.raises(ValidationError):
        validate_range("1.5, 2.5")


def test_question_clean_radio_valid(experiment_factory, question_factory):
    """Test Question.clean for radio type with valid choices."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.RADIO,
        choices="yes, no"
    )
    # Should not raise
    question.clean()


def test_question_clean_radio_invalid(experiment_factory, question_factory):
    """Test Question.clean for radio type with invalid choices."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.RADIO,
        choices="single"
    )
    with pytest.raises(ValidationError):
        question.clean()


def test_question_clean_range_valid(experiment_factory, question_factory):
    """Test Question.clean for range type with valid range."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.NUM_RANGE,
        choices="1, 10"
    )
    # Should not raise
    question.clean()


def test_question_clean_range_invalid(experiment_factory, question_factory):
    """Test Question.clean for range type with invalid range."""
    experiment = experiment_factory()
    question = question_factory(
        experiment,
        question_type=Question.NUM_RANGE,
        choices="10, 5"
    )
    with pytest.raises(ValidationError):
        question.clean()


# Test Experiment methods
def test_experiment_subject_questions(experiment_factory, question_factory):
    """Test Experiment.subject_questions method."""
    experiment = experiment_factory()
    q1 = question_factory(experiment, text="Question 1", position=1)
    q2 = question_factory(experiment, text="Question 2", position=2)
    
    questions = experiment.subject_questions()
    assert questions.count() == 2
    assert list(questions) == [q1, q2]


def test_experiment_consent_questions(experiment_factory, consent_question_factory):
    """Test Experiment.consent_questions method."""
    experiment = experiment_factory()
    cq1 = consent_question_factory(experiment, text="Consent 1", position=1)
    cq2 = consent_question_factory(experiment, text="Consent 2", position=2)
    
    questions = experiment.consent_questions()
    assert questions.count() == 2
    assert list(questions) == [cq1, cq2]


def test_experiment_get_list_item_random(monkeypatch, experiment_factory, listitem_factory):
    """Test Experiment.get_list_item with random strategy."""
    experiment = experiment_factory(list_selection_strategy='RAN')
    li1 = listitem_factory(experiment, list_name="List 1")
    li2 = listitem_factory(experiment, list_name="List 2")
    
    # Monkeypatch random.choice to return predictable result
    import random
    monkeypatch.setattr(random, 'choice', lambda x: x[0])
    
    result = experiment.get_list_item()
    assert result == li1


def test_experiment_get_list_item_sequential_first(experiment_factory, listitem_factory):
    """Test Experiment.get_list_item with sequential strategy - first item."""
    experiment = experiment_factory(list_selection_strategy='SEQ')
    li1 = listitem_factory(experiment, list_name="List 1")
    li2 = listitem_factory(experiment, list_name="List 2")
    
    # No subjects yet, should return first list
    result = experiment.get_list_item()
    assert result == li1


def test_experiment_get_list_item_sequential_next(experiment_factory, listitem_factory, subjectdata_factory):
    """Test Experiment.get_list_item with sequential strategy - next item."""
    experiment = experiment_factory(list_selection_strategy='SEQ')
    li1 = listitem_factory(experiment, list_name="List 1")
    li2 = listitem_factory(experiment, list_name="List 2")
    
    # Create subject with first list
    subject = subjectdata_factory(experiment, id="subj1", listitem=li1)
    
    # Should return second list
    result = experiment.get_list_item()
    assert result == li2


def test_experiment_get_list_item_least_played(experiment_factory, listitem_factory, subjectdata_factory):
    """Test Experiment.get_list_item with least played strategy."""
    experiment = experiment_factory(list_selection_strategy='LPF')
    li1 = listitem_factory(experiment, list_name="List 1")
    li2 = listitem_factory(experiment, list_name="List 2")
    
    # Create two subjects with first list, one with second
    subjectdata_factory(experiment, id="subj1", listitem=li1)
    subjectdata_factory(experiment, id="subj2", listitem=li1)
    subjectdata_factory(experiment, id="subj3", listitem=li2)
    
    # Should return second list (played less)
    result = experiment.get_list_item()
    assert result == li2


def test_experiment_get_list_item_no_lists(experiment_factory):
    """Test Experiment.get_list_item with no lists."""
    experiment = experiment_factory()
    result = experiment.get_list_item()
    assert result is None


def test_experiment_get_list_item_excluded_lists(experiment_factory, listitem_factory):
    """Test Experiment.get_list_item excludes lists marked as excluded."""
    experiment = experiment_factory()
    li1 = listitem_factory(experiment, list_name="List 1", exclude_list=True)
    li2 = listitem_factory(experiment, list_name="List 2", exclude_list=False)
    
    result = experiment.get_list_item()
    assert result == li2


# Test TrialResult.filename property
def test_trialresult_filename(experiment_factory, listitem_factory, outerblock_factory, blockitem_factory, 
                                trialitem_factory, subjectdata_factory, trialresult_factory):
    """Test TrialResult.filename property."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    outerblock = outerblock_factory(listitem)
    blockitem = blockitem_factory(outerblock)
    trialitem = trialitem_factory(blockitem)
    subject = subjectdata_factory(experiment)
    
    # Create a TrialResult with a webcam file
    trialresult = trialresult_factory(subject, trialitem)
    trialresult.webcam_file.name = "uploads/experiments/test/visual/video.mp4"
    
    assert trialresult.filename == "video.mp4"


def test_trialresult_filename_empty(experiment_factory, listitem_factory, outerblock_factory, blockitem_factory,
                                     trialitem_factory, subjectdata_factory, trialresult_factory):
    """Test TrialResult.filename property with empty file."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    outerblock = outerblock_factory(listitem)
    blockitem = blockitem_factory(outerblock)
    trialitem = trialitem_factory(blockitem)
    subject = subjectdata_factory(experiment)
    
    trialresult = trialresult_factory(subject, trialitem)
    trialresult.webcam_file.name = ""
    
    assert trialresult.filename == ""


# Test delete file functions
def test_delete_file_function(monkeypatch):
    """Test _delete_file function."""
    mock_isfile = Mock(return_value=True)
    mock_remove = Mock()
    
    monkeypatch.setattr(os.path, 'isfile', mock_isfile)
    monkeypatch.setattr(os, 'remove', mock_remove)
    
    _delete_file("/path/to/file.txt")
    
    mock_isfile.assert_called_once_with("/path/to/file.txt")
    mock_remove.assert_called_once_with("/path/to/file.txt")


def test_delete_file_function_not_exists(monkeypatch):
    """Test _delete_file function when file doesn't exist."""
    mock_isfile = Mock(return_value=False)
    mock_remove = Mock()
    
    monkeypatch.setattr(os.path, 'isfile', mock_isfile)
    monkeypatch.setattr(os, 'remove', mock_remove)
    
    _delete_file("/path/to/nonexistent.txt")
    
    mock_isfile.assert_called_once_with("/path/to/nonexistent.txt")
    mock_remove.assert_not_called()


# Test helper path functions
def test_experiment_folder():
    """Test experiment_folder helper."""
    instance = Mock()
    instance.exp_name = "my_experiment"
    
    result = experiment_folder(instance, "file.jpg")
    assert result == "uploads/experiments/my_experiment/file.jpg"


def test_visual_folder():
    """Test visual_folder helper."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = "exp1"
    instance.blockitem.listitem.list_name = "list1"
    
    result = visual_folder(instance, "image.png")
    assert result == "uploads/exp1/list1/visual/image.png"


def test_audio_folder():
    """Test audio_folder helper."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = "exp2"
    instance.blockitem.listitem.list_name = "list2"
    
    result = audio_folder(instance, "sound.mp3")
    assert result == "uploads/exp2/list2/audio/sound.mp3"


def test_default_calibration_points():
    """Test default_calibration_points helper."""
    result = default_calibration_points()
    assert isinstance(result, list)
    assert len(result) == 9
    assert result[0] == [50, 50]
    assert result[1] == [50, 12]
    assert result[-1] == [88, 12]
