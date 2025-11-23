"""
Tests for CDI (Communicative Development Inventory) functionality.

This module tests:
- CDI form generation
- Vocabulary checklist processing
- Ability estimation
"""
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, Mock
import json

from experiments.models import CdiResult
from tests.helpers import (
    ExperimentFactory, InstrumentFactory, ListItemFactory, 
    SubjectDataFactory
)


class CdiViewTest(TestCase):
    """Test CDI views."""
    
    def test_cdi_run_view_without_instrument(self):
        """Test CDI view when experiment has no instrument."""
        experiment = ExperimentFactory(instrument=None)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:vocabChecklist', args=[subject.id])
        response = self.client.get(url)
        
        # Should redirect if no instrument
        self.assertEqual(response.status_code, 302)
    
    def test_cdi_run_view_with_instrument(self):
        """Test CDI view when experiment has instrument."""
        instrument = InstrumentFactory()
        experiment = ExperimentFactory(instrument=instrument, num_words=10)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:vocabChecklist', args=[subject.id])
        
        # Mock file reading since we don't have actual CSV files
        with patch('experiments.cdi.pd.read_csv') as mock_read_csv:
            mock_df = Mock()
            mock_df.sample.return_value = Mock()
            mock_df.sample.return_value.to_dict.return_value = {
                'Word': {0: 'apple', 1: 'ball'},
                'Category': {0: 'food', 1: 'toy'}
            }
            mock_read_csv.return_value = mock_df
            
            response = self.client.get(url)
            
            # Should render CDI page
            self.assertEqual(response.status_code, 200)
    
    def test_cdi_submit_creates_result(self):
        """Test CDI submission creates CdiResult."""
        instrument = InstrumentFactory()
        experiment = ExperimentFactory(instrument=instrument, num_words=5)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:vocabChecklistSubmit', args=[subject.id])
        
        # Mock the ability estimation
        with patch('experiments.cdi.estimator') as mock_estimator:
            mock_est = Mock()
            mock_est.est_theta.return_value = 0.75
            mock_estimator.return_value = mock_est
            
            vocab_data = json.dumps([
                {'word': 'apple', 'response': 'yes'},
                {'word': 'ball', 'response': 'no'}
            ])
            
            data = {'vocab_data': vocab_data}
            response = self.client.post(url, data)
            
            # Should redirect after submission
            self.assertEqual(response.status_code, 302)
            
            # Check CdiResult was created
            cdi_results = CdiResult.objects.filter(subjectdata=subject)
            self.assertEqual(cdi_results.count(), 1)


class CdiAbilityEstimationTest(TestCase):
    """Test CDI ability estimation logic."""
    
    @patch('experiments.cdi.estimator')
    def test_ability_estimation_called(self, mock_estimator):
        """Test that ability estimation is called during CDI processing."""
        mock_est = Mock()
        mock_est.est_theta.return_value = 0.5
        mock_estimator.return_value = mock_est
        
        instrument = InstrumentFactory()
        experiment = ExperimentFactory(instrument=instrument)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:vocabChecklistSubmit', args=[subject.id])
        vocab_data = json.dumps([{'word': 'test', 'response': 'yes'}])
        
        self.client.post(url, {'vocab_data': vocab_data})
        
        # Estimator should have been called
        mock_estimator.assert_called_once()
