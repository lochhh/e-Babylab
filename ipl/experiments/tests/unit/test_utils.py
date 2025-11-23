"""
Unit tests for utility functions in ipl.experiments.models.
"""
import pytest
from unittest.mock import Mock
from experiments.models import (
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


class TestUtilityFunctions:
    """Tests for utility functions used in models."""

    def test_experiment_folder(self):
        """Test experiment_folder generates correct path."""
        mock_instance = Mock()
        mock_instance.exp_name = 'my_experiment'
        
        result = experiment_folder(mock_instance, 'test_file.png')
        assert result == 'uploads/experiments/my_experiment/test_file.png'

    def test_experiment_folder_different_names(self):
        """Test experiment_folder with different experiment names."""
        mock_instance = Mock()
        mock_instance.exp_name = 'another_exp'
        
        result = experiment_folder(mock_instance, 'image.jpg')
        assert result == 'uploads/experiments/another_exp/image.jpg'

    def test_visual_folder(self):
        """Test visual_folder generates correct path."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'experiment1'
        mock_instance.blockitem.listitem.list_name = 'list1'
        
        result = visual_folder(mock_instance, 'visual.mp4')
        assert result == 'uploads/experiment1/list1/visual/visual.mp4'

    def test_visual_folder_different_paths(self):
        """Test visual_folder with different experiment and list names."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'exp_test'
        mock_instance.blockitem.listitem.list_name = 'list_a'
        
        result = visual_folder(mock_instance, 'video.webm')
        assert result == 'uploads/exp_test/list_a/visual/video.webm'

    def test_audio_folder(self):
        """Test audio_folder generates correct path."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'audio_exp'
        mock_instance.blockitem.listitem.list_name = 'list_b'
        
        result = audio_folder(mock_instance, 'sound.mp3')
        assert result == 'uploads/audio_exp/list_b/audio/sound.mp3'

    def test_audio_folder_wav_file(self):
        """Test audio_folder with wav file."""
        mock_instance = Mock()
        mock_instance.blockitem.listitem.experiment.exp_name = 'test'
        mock_instance.blockitem.listitem.list_name = 'test_list'
        
        result = audio_folder(mock_instance, 'audio.wav')
        assert result == 'uploads/test/test_list/audio/audio.wav'

    def test_default_calibration_points(self):
        """Test default_calibration_points returns correct grid."""
        result = default_calibration_points()
        
        # Should return 9 points
        assert len(result) == 9
        
        # Expected points for 3x3 grid with specific coordinates
        expected = [
            [50, 50],  # center
            [50, 12],  # top center
            [12, 12],  # top left
            [12, 50],  # center left
            [12, 88],  # bottom left
            [50, 88],  # bottom center
            [88, 88],  # bottom right
            [88, 50],  # center right
            [88, 12],  # top right
        ]
        
        assert result == expected

    def test_default_calibration_points_immutable(self):
        """Test default_calibration_points returns a new list each time."""
        result1 = default_calibration_points()
        result2 = default_calibration_points()
        
        # Should be equal but not the same object
        assert result1 == result2
        assert result1 is not result2
        
        # Modifying one shouldn't affect the other
        result1[0] = [0, 0]
        assert result2[0] == [50, 50]
