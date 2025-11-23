"""Unit tests for utility functions."""
import pytest
from ipl.experiments.models import (
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


class TestExperimentFolder:
    """Test experiment_folder function."""
    
    def test_experiment_folder_path(self):
        """Test experiment folder path generation."""
        class MockInstance:
            exp_name = 'MyExperiment'
        
        result = experiment_folder(MockInstance(), 'image.png')
        
        assert result == 'uploads/experiments/MyExperiment/image.png'
        assert result.startswith('uploads/experiments/')
        assert result.endswith('image.png')


class TestVisualFolder:
    """Test visual_folder function."""
    
    def test_visual_folder_path(self, experiment_factory, listitem_factory, 
                                 outerblock_factory, blockitem_factory):
        """Test visual folder path generation."""
        experiment = experiment_factory(exp_name='TestExp')
        listitem = listitem_factory(experiment, list_name='List1')
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        
        class MockInstance:
            blockitem = blockitem
        
        result = visual_folder(MockInstance(), 'visual.jpg')
        
        assert result == 'uploads/TestExp/List1/visual/visual.jpg'
        assert 'visual' in result


class TestAudioFolder:
    """Test audio_folder function."""
    
    def test_audio_folder_path(self, experiment_factory, listitem_factory, 
                                outerblock_factory, blockitem_factory):
        """Test audio folder path generation."""
        experiment = experiment_factory(exp_name='TestExp')
        listitem = listitem_factory(experiment, list_name='List1')
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        
        class MockInstance:
            blockitem = blockitem
        
        result = audio_folder(MockInstance(), 'sound.mp3')
        
        assert result == 'uploads/TestExp/List1/audio/sound.mp3'
        assert 'audio' in result


class TestDefaultCalibrationPoints:
    """Test default_calibration_points function."""
    
    def test_default_calibration_points_count(self):
        """Test that default calibration points has 9 points."""
        points = default_calibration_points()
        
        assert len(points) == 9
        assert isinstance(points, list)
    
    def test_default_calibration_points_values(self):
        """Test specific calibration point values."""
        points = default_calibration_points()
        
        # Check center point
        assert [50, 50] in points
        
        # Check corner points
        assert [12, 12] in points
        assert [88, 88] in points
        assert [12, 88] in points
        assert [88, 12] in points
        
        # Check edge points
        assert [50, 12] in points
        assert [50, 88] in points
        assert [12, 50] in points
        assert [88, 50] in points
