"""Unit tests for helper functions in ipl.experiments.models"""
import pytest
from unittest.mock import Mock

from ipl.experiments.models import (
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


def test_experiment_folder():
    """Test experiment_folder helper function."""
    instance = Mock()
    instance.exp_name = 'my_experiment'
    
    result = experiment_folder(instance, 'test_file.jpg')
    
    assert result == 'uploads/experiments/my_experiment/test_file.jpg'


def test_experiment_folder_with_spaces():
    """Test experiment_folder with spaces in name."""
    instance = Mock()
    instance.exp_name = 'My Test Experiment'
    
    result = experiment_folder(instance, 'image.png')
    
    assert result == 'uploads/experiments/My Test Experiment/image.png'


def test_visual_folder():
    """Test visual_folder helper function."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = 'exp1'
    instance.blockitem.listitem.list_name = 'list1'
    
    result = visual_folder(instance, 'visual.jpg')
    
    assert result == 'uploads/exp1/list1/visual/visual.jpg'


def test_visual_folder_different_names():
    """Test visual_folder with different experiment and list names."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = 'experiment_a'
    instance.blockitem.listitem.list_name = 'list_b'
    
    result = visual_folder(instance, 'photo.png')
    
    assert result == 'uploads/experiment_a/list_b/visual/photo.png'


def test_audio_folder():
    """Test audio_folder helper function."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = 'exp2'
    instance.blockitem.listitem.list_name = 'list2'
    
    result = audio_folder(instance, 'sound.mp3')
    
    assert result == 'uploads/exp2/list2/audio/sound.mp3'


def test_audio_folder_different_files():
    """Test audio_folder with different filenames."""
    instance = Mock()
    instance.blockitem.listitem.experiment.exp_name = 'test_exp'
    instance.blockitem.listitem.list_name = 'test_list'
    
    result = audio_folder(instance, 'audio_track.wav')
    
    assert result == 'uploads/test_exp/test_list/audio/audio_track.wav'


def test_default_calibration_points():
    """Test default_calibration_points returns expected structure."""
    result = default_calibration_points()
    
    # Should be a list
    assert isinstance(result, list)
    
    # Should have 9 points
    assert len(result) == 9
    
    # Each point should be a list of 2 integers
    for point in result:
        assert isinstance(point, list)
        assert len(point) == 2
        assert isinstance(point[0], int)
        assert isinstance(point[1], int)


def test_default_calibration_points_values():
    """Test default_calibration_points returns correct values."""
    result = default_calibration_points()
    
    # Check specific known points
    assert result[0] == [50, 50]  # Center
    assert result[1] == [50, 12]  # Top center
    assert result[2] == [12, 12]  # Top left
    assert result[3] == [12, 50]  # Middle left
    assert result[4] == [12, 88]  # Bottom left
    assert result[5] == [50, 88]  # Bottom center
    assert result[6] == [88, 88]  # Bottom right
    assert result[7] == [88, 50]  # Middle right
    assert result[8] == [88, 12]  # Top right


def test_default_calibration_points_immutable():
    """Test default_calibration_points returns a new list each time."""
    result1 = default_calibration_points()
    result2 = default_calibration_points()
    
    # Should be equal but not the same object
    assert result1 == result2
    assert result1 is not result2
