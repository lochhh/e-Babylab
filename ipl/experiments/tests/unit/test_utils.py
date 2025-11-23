"""
Unit tests for utility functions in the experiments app.

Tests helper functions and utilities.
"""

import os

import pytest


class TestFilePathHelpers:
    """Tests for file path helper functions."""

    def test_experiment_folder(self, experiment):
        """Test experiment_folder returns correct path."""
        from experiments.models import experiment_folder
        
        # Create a mock instance with exp_name attribute
        class MockInstance:
            exp_name = "Test Experiment"
        
        instance = MockInstance()
        path = experiment_folder(instance, "test_file.jpg")
        
        expected_path = "uploads/experiments/Test Experiment/test_file.jpg"
        assert path == expected_path

    def test_visual_folder(self, trial_item):
        """Test visual_folder returns correct path structure."""
        from experiments.models import visual_folder
        
        path = visual_folder(trial_item, "test_visual.png")
        
        # Path should include experiment name, list name, and visual folder
        assert "uploads" in path
        assert "visual" in path
        assert "test_visual.png" in path

    def test_audio_folder(self, trial_item):
        """Test audio_folder returns correct path structure."""
        from experiments.models import audio_folder
        
        path = audio_folder(trial_item, "test_audio.mp3")
        
        # Path should include experiment name, list name, and audio folder
        assert "uploads" in path
        assert "audio" in path
        assert "test_audio.mp3" in path


class TestDefaultCalibrationPoints:
    """Tests for default calibration points."""

    def test_default_calibration_points(self):
        """Test default_calibration_points returns correct points."""
        from experiments.models import default_calibration_points
        
        points = default_calibration_points()
        
        # Should return 9 calibration points
        assert len(points) == 9
        
        # First point should be center
        assert points[0] == [50, 50]
        
        # Check some corner points exist
        assert [12, 12] in points
        assert [88, 88] in points
