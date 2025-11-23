"""Unit tests for reporter.py functions."""
import pytest
from unittest.mock import MagicMock, Mock, patch
import datetime


class DummyDF:
    """Dummy DataFrame to avoid pandas dependency in tests."""
    def __init__(self, data=None):
        self.data = data or {}
    
    def to_excel(self, writer, **kwargs):
        pass


class DummyZipFile:
    """Dummy ZipFile to avoid file I/O in tests."""
    def __init__(self, *args, **kwargs):
        self.written_files = []
    
    def write(self, filename, arcname=None):
        self.written_files.append((filename, arcname))
    
    def close(self):
        pass


class TestReporterInit:
    """Test Reporter.__init__ method."""

    def test_reporter_init(self, monkeypatch, experiment_factory):
        """Test Reporter initializes with experiment."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory(name="Test Exp")
        
        # Mock os operations
        mock_makedirs = MagicMock()
        mock_remove = MagicMock()
        mock_exists = MagicMock(return_value=False)
        
        import os
        monkeypatch.setattr(os, 'makedirs', mock_makedirs)
        monkeypatch.setattr(os, 'remove', mock_remove)
        monkeypatch.setattr(os.path, 'exists', mock_exists)
        
        # Mock zipfile
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        
        # Mock settings
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        assert reporter.experiment == experiment
        assert 'Test_Exp.zip' in reporter.output_file or 'Test-Exp.zip' in reporter.output_file


class TestCalcTrialDuration:
    """Test Reporter.calc_trial_duration method."""

    def test_calc_trial_duration_with_times(self, monkeypatch, experiment_factory):
        """Test calc_trial_duration returns duration string."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        
        # Mock initialization
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        result = reporter.calc_trial_duration(1000.5, 1500.75)
        assert result == '500.25'

    def test_calc_trial_duration_missing_times(self, monkeypatch, experiment_factory):
        """Test calc_trial_duration returns empty string when times are None."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        assert reporter.calc_trial_duration(None, 1500) == ''
        assert reporter.calc_trial_duration(1000, None) == ''
        assert reporter.calc_trial_duration(None, None) == ''


class TestCalcRoiResponse:
    """Test Reporter.calc_roi_response method."""

    def test_calc_roi_response_with_coords(self, monkeypatch, experiment_factory,
                                          listitem_factory, outerblock_factory,
                                          blockitem_factory, trialitem_factory,
                                          subjectdata_factory, trialresult_factory):
        """Test calc_roi_response calculates correct ROI."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        result = trialresult_factory(subject, trialitem)
        
        result.resolution_w = 1000
        result.resolution_h = 1000
        result.trialitem.grid_row = 2
        result.trialitem.grid_col = 2
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        # Click in top-left quadrant
        roi = reporter.calc_roi_response(result, [250, 250])
        assert roi == '(1,1)'
        
        # Click in bottom-right quadrant
        roi = reporter.calc_roi_response(result, [750, 750])
        assert roi == '(2,2)'

    def test_calc_roi_response_empty_coords(self, monkeypatch, experiment_factory,
                                           listitem_factory, outerblock_factory,
                                           blockitem_factory, trialitem_factory,
                                           subjectdata_factory, trialresult_factory):
        """Test calc_roi_response returns empty string for invalid coords."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment)
        result = trialresult_factory(subject, trialitem)
        
        result.resolution_w = 1000
        result.resolution_h = 1000
        result.trialitem.grid_row = 2
        result.trialitem.grid_col = 2
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        assert reporter.calc_roi_response(result, []) == ''
        assert reporter.calc_roi_response(result, [100]) == ''


class TestGcd:
    """Test Reporter.gcd method."""

    def test_gcd_calculation(self, monkeypatch, experiment_factory):
        """Test gcd calculates greatest common divisor."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        reporter = Reporter(experiment)
        
        assert reporter.gcd(1920, 1080) == 120
        assert reporter.gcd(100, 50) == 50
        assert reporter.gcd(17, 19) == 1
        assert reporter.gcd(0, 5) == 5


class TestCreateSubjectWorksheet:
    """Test Reporter.create_subject_worksheet method."""

    def test_create_subject_worksheet(self, monkeypatch, experiment_factory,
                                     listitem_factory, subjectdata_factory):
        """Test create_subject_worksheet creates DataFrame with subject data."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, listitem=listitem)
        subject.resolution_w = 1920
        subject.resolution_h = 1080
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        # Mock pandas DataFrame
        monkeypatch.setattr('experiments.reporter.pd.DataFrame', DummyDF)
        
        reporter = Reporter(experiment)
        
        # Should not raise exception
        result = reporter.create_subject_worksheet(subject)
        assert result is not None


class TestCreateTrialWorksheet:
    """Test Reporter.create_trial_worksheet method."""

    def test_create_trial_worksheet_with_results(self, monkeypatch, experiment_factory,
                                                listitem_factory, outerblock_factory,
                                                blockitem_factory, trialitem_factory,
                                                subjectdata_factory, trialresult_factory):
        """Test create_trial_worksheet creates DataFrame with trial results."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        outerblock = outerblock_factory(listitem)
        blockitem = blockitem_factory(outerblock)
        trialitem = trialitem_factory(blockitem)
        subject = subjectdata_factory(experiment, listitem=listitem)
        result = trialresult_factory(subject, trialitem)
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        monkeypatch.setattr('experiments.reporter.pd.DataFrame', DummyDF)
        
        reporter = Reporter(experiment)
        
        # Should not raise exception
        result_df = reporter.create_trial_worksheet(subject, [result])
        assert result_df is not None

    def test_create_trial_worksheet_empty_results(self, monkeypatch, experiment_factory,
                                                 listitem_factory, subjectdata_factory):
        """Test create_trial_worksheet handles empty results."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, listitem=listitem)
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        monkeypatch.setattr('experiments.reporter.pd.DataFrame', DummyDF)
        
        reporter = Reporter(experiment)
        
        # Should handle empty results
        result_df = reporter.create_trial_worksheet(subject, [])
        assert result_df is not None


class TestCreateWebgazerWorksheet:
    """Test Reporter.create_webgazer_worksheet method."""

    def test_create_webgazer_worksheet(self, monkeypatch, experiment_factory,
                                      listitem_factory, subjectdata_factory):
        """Test create_webgazer_worksheet creates DataFrame."""
        try:
            from experiments.reporter import Reporter
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, listitem=listitem)
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        
        monkeypatch.setattr('experiments.reporter.pd.DataFrame', DummyDF)
        
        reporter = Reporter(experiment)
        
        # Should not raise exception
        result_df = reporter.create_webgazer_worksheet(subject, [])
        assert result_df is not None


class TestCreateReport:
    """Test Reporter.create_report method."""

    def test_create_report_flow(self, monkeypatch, experiment_factory,
                                listitem_factory, subjectdata_factory):
        """Test create_report executes full report generation flow."""
        try:
            from experiments.reporter import Reporter
            from experiments.models import SubjectData
            from django.conf import settings
        except ImportError:
            pytest.skip("reporter module not available")
        
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, listitem=listitem)
        
        import os
        monkeypatch.setattr(os, 'makedirs', MagicMock())
        monkeypatch.setattr(os, 'remove', MagicMock())
        monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
        monkeypatch.setattr('experiments.reporter.zipfile.ZipFile', DummyZipFile)
        if not hasattr(settings, 'REPORTS_ROOT'):
            monkeypatch.setattr(settings, 'REPORTS_ROOT', '/tmp/reports')
        if not hasattr(settings, 'WEBCAM_ROOT'):
            monkeypatch.setattr(settings, 'WEBCAM_ROOT', '/tmp/webcam')
        
        monkeypatch.setattr('experiments.reporter.pd.DataFrame', DummyDF)
        
        # Mock SubjectData.objects.filter
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = [subject]
        
        def mock_filter(**kwargs):
            return mock_queryset
        
        monkeypatch.setattr(SubjectData.objects, 'filter', mock_filter)
        
        reporter = Reporter(experiment)
        
        # Should execute without exception
        reporter.create_report()
