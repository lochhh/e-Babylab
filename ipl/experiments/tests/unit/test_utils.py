"""Unit tests for utility functions in ipl/experiments/models.py"""
from unittest.mock import Mock
from ipl.experiments.models import (
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


class TestUtilityFunctions:
    """Test utility/helper functions."""
    
    def test_experiment_folder(self):
        """Test experiment_folder path generation."""
        mock_instance = Mock()
        mock_instance.exp_name = 'TestExperiment'
        
        path = experiment_folder(mock_instance, 'stimulus.png')
        
        assert path == 'uploads/experiments/TestExperiment/stimulus.png'
    
    def test_visual_folder(self):
        """Test visual_folder path generation."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'ExpName'
        mock_instance.blockitem.listitem.list_name = 'List1'
        
        path = visual_folder(mock_instance, 'image.jpg')
        
        assert path == 'uploads/ExpName/List1/visual/image.jpg'
    
    def test_audio_folder(self):
        """Test audio_folder path generation."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'ExpName'
        mock_instance.blockitem.listitem.list_name = 'List2'
        
        path = audio_folder(mock_instance, 'sound.wav')
        
        assert path == 'uploads/ExpName/List2/audio/sound.wav'
    
    def test_default_calibration_points(self):
        """Test default_calibration_points returns correct grid."""
        points = default_calibration_points()
        
        expected = [
            [50, 50], [50, 12], [12, 12], [12, 50], [12, 88],
            [50, 88], [88, 88], [88, 50], [88, 12]
        ]
        
        assert points == expected
        assert len(points) == 9
