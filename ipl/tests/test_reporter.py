"""
Tests for reporter functionality.

This module tests:
- Report generation
- Data export
- File creation
"""
from django.test import TestCase
from unittest.mock import patch, Mock, MagicMock
import os

from experiments.reporter import Reporter
from experiments.models import TrialResult, SubjectData
from tests.helpers import (
    ExperimentFactory, ListItemFactory, SubjectDataFactory,
    TrialResultFactory, TrialItemFactory, BlockItemFactory,
    OuterBlockItemFactory
)


class ReporterTest(TestCase):
    """Test the Reporter class."""
    
    def test_reporter_initialization(self):
        """Test Reporter initialization with an experiment."""
        experiment = ExperimentFactory()
        reporter = Reporter(experiment)
        
        self.assertEqual(reporter.experiment, experiment)
    
    @patch('experiments.reporter.Reporter.create_results_worksheet')
    @patch('experiments.reporter.Reporter.create_webgazer_worksheet')
    @patch('experiments.reporter.zipfile.ZipFile')
    @patch('experiments.reporter.os.makedirs')
    def test_create_report_generates_zip(
        self, mock_makedirs, mock_zipfile, mock_webgazer, mock_results
    ):
        """Test that create_report generates a zip file."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        reporter = Reporter(experiment)
        
        # Mock the workbook
        mock_workbook = MagicMock()
        mock_results.return_value = mock_workbook
        mock_webgazer.return_value = mock_workbook
        
        with patch.object(reporter, 'get_subjects') as mock_get_subjects:
            mock_get_subjects.return_value = SubjectData.objects.filter(pk=subject.pk)
            
            filename = reporter.create_report()
            
            # Should return a filename
            self.assertIsNotNone(filename)
            self.assertIn(experiment.exp_name, filename)
    
    def test_get_subjects_returns_subject_data(self):
        """Test get_subjects returns SubjectData queryset."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject1 = SubjectDataFactory(experiment=experiment, listitem=list_item)
        subject2 = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        # Create another experiment's subject that shouldn't be included
        other_experiment = ExperimentFactory()
        other_list = ListItemFactory(experiment=other_experiment)
        SubjectDataFactory(experiment=other_experiment, listitem=other_list)
        
        reporter = Reporter(experiment)
        subjects = reporter.get_subjects()
        
        self.assertEqual(subjects.count(), 2)
        self.assertIn(subject1, subjects)
        self.assertIn(subject2, subjects)
    
    @patch('experiments.reporter.xlsxwriter.Workbook')
    def test_create_results_worksheet(self, mock_workbook_class):
        """Test creating results worksheet."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        outer_block = OuterBlockItemFactory(listitem=list_item)
        block = BlockItemFactory(outerblockitem=outer_block)
        trial = TrialItemFactory(blockitem=block)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        result = TrialResultFactory(subjectdata=subject, trialitem=trial)
        
        mock_workbook = MagicMock()
        mock_workbook_class.return_value = mock_workbook
        
        reporter = Reporter(experiment)
        
        with patch.object(reporter, 'get_subjects') as mock_get_subjects:
            mock_get_subjects.return_value = SubjectData.objects.filter(pk=subject.pk)
            
            workbook = reporter.create_results_worksheet('/tmp/test.xlsx')
            
            # Workbook should be created
            self.assertIsNotNone(workbook)
    
    def test_reporter_with_no_subjects(self):
        """Test reporter handles experiment with no subjects."""
        experiment = ExperimentFactory()
        reporter = Reporter(experiment)
        subjects = reporter.get_subjects()
        
        self.assertEqual(subjects.count(), 0)
