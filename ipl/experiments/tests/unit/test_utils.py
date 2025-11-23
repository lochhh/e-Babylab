"""Unit tests for utility functions in ipl.experiments.models."""
import pytest
from experiments.models import (
    experiment_folder,
    visual_folder,
    audio_folder,
    default_calibration_points,
)


class TestExperimentFolder:
    """Test experiment_folder helper function."""

    def test_generates_correct_path(self):
        """Test experiment_folder generates correct upload path."""
        class MockInstance:
            exp_name = "MyExperiment"
        
        instance = MockInstance()
        result = experiment_folder(instance, "test_file.jpg")
        assert result == "uploads/experiments/MyExperiment/test_file.jpg"

    def test_handles_different_filenames(self):
        """Test experiment_folder works with various filenames."""
        class MockInstance:
            exp_name = "Exp1"
        
        instance = MockInstance()
        assert experiment_folder(instance, "image.png") == "uploads/experiments/Exp1/image.png"
        assert experiment_folder(instance, "data.csv") == "uploads/experiments/Exp1/data.csv"


class TestVisualFolder:
    """Test visual_folder helper function."""

    def test_generates_correct_path(self):
        """Test visual_folder generates correct upload path."""
        class MockExperiment:
            exp_name = "ExpA"
        
        class MockListItem:
            experiment = MockExperiment()
            list_name = "List1"
        
        class MockBlockItem:
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        result = visual_folder(instance, "visual.mp4")
        assert result == "uploads/ExpA/List1/visual/visual.mp4"


class TestAudioFolder:
    """Test audio_folder helper function."""

    def test_generates_correct_path(self):
        """Test audio_folder generates correct upload path."""
        class MockExperiment:
            exp_name = "ExpB"
        
        class MockListItem:
            experiment = MockExperiment()
            list_name = "List2"
        
        class MockBlockItem:
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        result = audio_folder(instance, "audio.wav")
        assert result == "uploads/ExpB/List2/audio/audio.wav"


class TestDefaultCalibrationPoints:
    """Test default_calibration_points helper function."""

    def test_returns_correct_structure(self):
        """Test default_calibration_points returns 9-point calibration grid."""
        points = default_calibration_points()
        assert isinstance(points, list)
        assert len(points) == 9

    def test_returns_expected_points(self):
        """Test default_calibration_points returns expected coordinates."""
        points = default_calibration_points()
        expected = [
            [50, 50], [50, 12], [12, 12], [12, 50],
            [12, 88], [50, 88], [88, 88], [88, 50], [88, 12]
        ]
        assert points == expected

    def test_returns_new_list_each_time(self):
        """Test default_calibration_points returns new list instance each time."""
        points1 = default_calibration_points()
        points2 = default_calibration_points()
        assert points1 is not points2
        assert points1 == points2
