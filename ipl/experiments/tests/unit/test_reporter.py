"""Unit tests for reporter.py"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from ipl.experiments.reporter import Reporter


class DummyZipFile:
    """Mock ZipFile for testing."""
    
    def __init__(self, *args, **kwargs):
        self.files = []
    
    def write(self, filename, arcname=None):
        self.files.append((filename, arcname))
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class DummyDataFrame:
    """Mock pandas DataFrame for testing."""
    
    def __init__(self, data=None):
        self.data = data or {}
    
    def to_excel(self, writer, sheet_name=None, index=False):
        pass
    
    @classmethod
    def from_dict(cls, data, orient='index'):
        return cls(data)


class TestReporter:
    """Test Reporter class initialization."""
    
    def test_reporter_init(self, monkeypatch, experiment_factory):
        """Test Reporter initialization."""
        experiment = experiment_factory(exp_name='Test Experiment')
        
        # Mock settings
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        # Mock os operations
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        
        # Mock zipfile
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        
        assert reporter.experiment == experiment
        assert 'Test_Experiment.zip' in reporter.output_file


class TestCalcTrialDuration:
    """Test calc_trial_duration method."""
    
    def test_calc_trial_duration_with_valid_times(self, monkeypatch, experiment_factory):
        """Test duration calculation with valid times."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        result = reporter.calc_trial_duration(100.5, 150.5)
        
        assert result == '50.0'
    
    def test_calc_trial_duration_with_none(self, monkeypatch, experiment_factory):
        """Test duration calculation with None values."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        result = reporter.calc_trial_duration(None, 150.5)
        
        assert result == ''
    
    def test_calc_trial_duration_both_none(self, monkeypatch, experiment_factory):
        """Test duration calculation when both times are None."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        result = reporter.calc_trial_duration(None, None)
        
        assert result == ''


class TestCalcRoiResponse:
    """Test calc_roi_response method."""
    
    def test_calc_roi_response_valid_coords(self, monkeypatch, experiment_factory, 
                                            listitem_factory, outerblock_factory,
                                            blockitem_factory, trialitem_factory,
                                            subjectdata_factory, trialresult_factory):
        """Test ROI calculation with valid coordinates."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        
        # Create mock trial result
        result = Mock()
        result.resolution_w = 1000
        result.resolution_h = 800
        result.trialitem = Mock()
        result.trialitem.grid_row = 2
        result.trialitem.grid_col = 2
        
        roi = reporter.calc_roi_response(result, [500, 400])
        
        assert '(' in roi and ')' in roi
    
    def test_calc_roi_response_empty_coords(self, monkeypatch, experiment_factory):
        """Test ROI calculation with empty coordinates."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        
        result = Mock()
        result.resolution_w = 1000
        result.resolution_h = 800
        
        roi = reporter.calc_roi_response(result, [])
        
        assert roi == ''


class TestGcd:
    """Test gcd recursive function."""
    
    def test_gcd_basic(self, monkeypatch, experiment_factory):
        """Test GCD calculation."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        
        assert reporter.gcd(48, 18) == 6
        assert reporter.gcd(100, 50) == 50
        assert reporter.gcd(17, 19) == 1
    
    def test_gcd_zero(self, monkeypatch, experiment_factory):
        """Test GCD with zero."""
        experiment = experiment_factory()
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        reporter = Reporter(experiment)
        
        assert reporter.gcd(10, 0) == 10


class TestCreateSubjectWorksheet:
    """Test create_subject_worksheet method."""
    
    def test_create_subject_worksheet(self, monkeypatch, experiment_factory, 
                                      listitem_factory, subjectdata_factory,
                                      consent_question_factory):
        """Test subject worksheet creation."""
        experiment = experiment_factory(exp_name='Test Exp')
        listitem = listitem_factory(experiment, list_name='List A')
        subject = subjectdata_factory(experiment, listitem=listitem, 
                                     resolution_w=1920, resolution_h=1080)
        
        # Create consent question
        consent_question_factory(experiment, text='Do you consent?', position=1)
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        # Mock pandas DataFrame
        monkeypatch.setattr('pandas.DataFrame.from_dict', DummyDataFrame.from_dict)
        
        reporter = Reporter(experiment)
        result = reporter.create_subject_worksheet(subject)
        
        assert isinstance(result, DummyDataFrame)


class TestCreateTrialWorksheet:
    """Test create_trial_worksheet method."""
    
    def test_create_trial_worksheet_empty(self, monkeypatch, experiment_factory, 
                                          subjectdata_factory):
        """Test trial worksheet with empty trial results."""
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment)
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        # Mock TrialResult.objects.filter to return empty
        from ipl.experiments import reporter as reporter_module
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = []
        monkeypatch.setattr(reporter_module.TrialResult.objects, 'filter', 
                          lambda **kwargs: mock_queryset)
        
        # Mock pandas DataFrame
        monkeypatch.setattr('pandas.DataFrame', DummyDataFrame)
        
        reporter = Reporter(experiment)
        result = reporter.create_trial_worksheet(subject)
        
        assert isinstance(result, DummyDataFrame)


class TestCreateWebgazerWorksheet:
    """Test create_webgazer_worksheet method."""
    
    def test_create_webgazer_worksheet_empty(self, monkeypatch, experiment_factory, 
                                             subjectdata_factory):
        """Test webgazer worksheet with empty results."""
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment)
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        # Mock TrialResult.objects.filter to return empty
        from ipl.experiments import reporter as reporter_module
        mock_queryset = Mock()
        mock_queryset.filter.return_value = []
        monkeypatch.setattr(reporter_module.TrialResult.objects, 'filter', 
                          lambda **kwargs: mock_queryset)
        
        # Mock pandas DataFrame
        monkeypatch.setattr('pandas.DataFrame', DummyDataFrame)
        
        reporter = Reporter(experiment)
        result = reporter.create_webgazer_worksheet(subject)
        
        assert isinstance(result, DummyDataFrame)


class TestCreateReport:
    """Test create_report end-to-end."""
    
    def test_create_report(self, monkeypatch, experiment_factory, subjectdata_factory):
        """Test full report creation flow."""
        experiment = experiment_factory(exp_name='Test Report')
        subject = subjectdata_factory(experiment)
        
        from django.conf import settings
        settings.REPORTS_ROOT = '/tmp/reports'
        
        import os
        monkeypatch.setattr(os, 'makedirs', lambda *args, **kwargs: None)
        monkeypatch.setattr(os, 'remove', lambda *args: None)
        monkeypatch.setattr(os.path, 'exists', lambda *args: True)
        monkeypatch.setattr('zipfile.ZipFile', DummyZipFile)
        
        # Mock SubjectData.objects.filter
        from ipl.experiments import reporter as reporter_module
        mock_queryset = Mock()
        mock_queryset.filter.return_value = [subject]
        monkeypatch.setattr(reporter_module.SubjectData.objects, 'filter', 
                          lambda **kwargs: mock_queryset)
        
        # Mock worksheet creation methods
        def mock_create_subject(self, subj):
            return DummyDataFrame()
        
        def mock_create_trial(self, subj):
            return DummyDataFrame()
        
        def mock_create_webgazer(self, subj):
            return DummyDataFrame()
        
        monkeypatch.setattr(Reporter, 'create_subject_worksheet', mock_create_subject)
        monkeypatch.setattr(Reporter, 'create_trial_worksheet', mock_create_trial)
        monkeypatch.setattr(Reporter, 'create_webgazer_worksheet', mock_create_webgazer)
        
        # Mock xlsxwriter
        mock_workbook = Mock()
        mock_workbook.close = Mock()
        monkeypatch.setattr('xlsxwriter.Workbook', lambda *args, **kwargs: mock_workbook)
        
        # Mock shutil
        monkeypatch.setattr('shutil.rmtree', lambda *args, **kwargs: None)
        
        reporter = Reporter(experiment)
        filename = reporter.create_report()
        
        assert filename is not None
        assert 'Test_Report.zip' in filename
