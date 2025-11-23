"""
Tests for webcam functionality.

This module tests:
- Webcam test views
- File upload handling
- Media recording
"""
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock
import json

from experiments.models import Experiment
from tests.helpers import (
    ExperimentFactory, ListItemFactory, SubjectDataFactory
)


class WebcamTestViewTest(TestCase):
    """Test webcam test views."""
    
    def test_webcam_test_view_audio_only(self):
        """Test webcam test view for audio recording."""
        experiment = ExperimentFactory(recording_option=Experiment.AUDIO)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:webcamTest', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_webcam_test_view_video(self):
        """Test webcam test view for video recording."""
        experiment = ExperimentFactory(recording_option=Experiment.VIDEO)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:webcamTest', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_webcam_test_view_eye_tracking(self):
        """Test webcam test view for eye tracking."""
        experiment = ExperimentFactory(recording_option=Experiment.EYE)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:webcamTest', args=[subject.id])
        response = self.client.get(url)
        
        # Eye tracking doesn't need webcam test, should redirect
        self.assertEqual(response.status_code, 302)
    
    def test_webcam_test_view_no_recording(self):
        """Test webcam test view when no recording is needed."""
        experiment = ExperimentFactory(recording_option=Experiment.NONE)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:webcamTest', args=[subject.id])
        response = self.client.get(url)
        
        # No recording needed, should redirect
        self.assertEqual(response.status_code, 302)


class WebcamUploadTest(TestCase):
    """Test webcam upload functionality."""
    
    def test_webcam_test_upload(self):
        """Test webcam test file upload."""
        experiment = ExperimentFactory(recording_option=Experiment.VIDEO)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:webcamUpload', args=[subject.id])
        
        # Create a simple test file
        test_file = SimpleUploadedFile(
            "test_video.webm",
            b"file_content",
            content_type="video/webm"
        )
        
        with patch('experiments.webcam.default_storage.save') as mock_save:
            mock_save.return_value = 'saved_file.webm'
            
            response = self.client.post(url, {'file': test_file})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('message', data)
    
    def test_experiment_webcam_upload(self):
        """Test experiment webcam upload during actual experiment."""
        experiment = ExperimentFactory(recording_option=Experiment.VIDEO)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:experimentWebcamUpload', args=[subject.id])
        
        test_file = SimpleUploadedFile(
            "experiment_video.webm",
            b"video_content",
            content_type="video/webm"
        )
        
        with patch('experiments.webcam.default_storage.save') as mock_save:
            mock_save.return_value = 'saved_experiment.webm'
            
            response = self.client.post(url, {'file': test_file})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('message', data)
