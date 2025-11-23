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

    def test_visual_folder_structure(self):
        """Test visual_folder path structure."""
        from experiments.models import visual_folder
        
        # Create a mock instance with the expected attribute chain
        class MockBlockItem:
            class MockListItem:
                class MockExperiment:
                    exp_name = "Test Exp"
                experiment = MockExperiment()
                list_name = "List 1"
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        path = visual_folder(instance, "test.png")
        
        assert path == "uploads/Test Exp/List 1/visual/test.png"

    def test_audio_folder_structure(self):
        """Test audio_folder path structure."""
        from experiments.models import audio_folder
        
        # Create a mock instance with the expected attribute chain
        class MockBlockItem:
            class MockListItem:
                class MockExperiment:
                    exp_name = "Test Exp"
                experiment = MockExperiment()
                list_name = "List 1"
            listitem = MockListItem()
        
        class MockInstance:
            blockitem = MockBlockItem()
        
        instance = MockInstance()
        path = audio_folder(instance, "test.mp3")
        
        assert path == "uploads/Test Exp/List 1/audio/test.mp3"


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
