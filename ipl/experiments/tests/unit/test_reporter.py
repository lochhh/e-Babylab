"""Unit tests for ipl.experiments.reporter"""
import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import pandas as pd

try:
    from ipl.experiments.reporter import Reporter
    REPORTER_AVAILABLE = True
except ImportError:
    REPORTER_AVAILABLE = False


class DummyZipFile:
    """Dummy ZipFile for testing without actual file I/O."""
    def __init__(self, *args, **kwargs):
        self.files = []
    
    def write(self, source, arcname=None):
        self.files.append((source, arcname))
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class DummyDataFrame:
    """Dummy DataFrame for testing without pandas operations."""
    def __init__(self, data=None, *args, **kwargs):
        self.data = data or {}
    
    @staticmethod
    def from_dict(data, orient='index'):
        return DummyDataFrame(data)
    
    def to_excel(self, *args, **kwargs):
        pass


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_reporter_init(monkeypatch, experiment_factory):
    """Test Reporter initialization."""
    experiment = experiment_factory(exp_name="Test Exp")
    
    # Mock settings.REPORTS_ROOT
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        # Mock os.makedirs and zipfile
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    assert reporter.experiment == experiment
                    assert reporter.output_file == 'Test_Exp.zip'


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_calc_trial_duration():
    """Test Reporter.calc_trial_duration method."""
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        experiment = Mock()
        experiment.exp_name = "Test"
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    # Test with valid times
                    result = reporter.calc_trial_duration(100.5, 150.5)
                    assert result == '50.0'
                    
                    # Test with None values
                    result = reporter.calc_trial_duration(None, 150.5)
                    assert result == ''
                    
                    result = reporter.calc_trial_duration(100.5, None)
                    assert result == ''


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_calc_roi_response():
    """Test Reporter.calc_roi_response edge cases."""
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        experiment = Mock()
        experiment.exp_name = "Test"
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    # Create mock result
                    result = Mock()
                    result.resolution_w = 1000
                    result.resolution_h = 800
                    result.trialitem.grid_row = 2
                    result.trialitem.grid_col = 2
                    
                    # Test normal coordinates
                    roi = reporter.calc_roi_response(result, [250, 200])
                    assert roi == '(1,1)'
                    
                    # Test edge case: coords beyond boundaries
                    roi = reporter.calc_roi_response(result, [1100, 900])
                    assert ',' in roi  # Should still return something
                    
                    # Test empty coords
                    roi = reporter.calc_roi_response(result, [])
                    assert roi == ''


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_gcd_recursion():
    """Test Reporter.gcd method."""
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        experiment = Mock()
        experiment.exp_name = "Test"
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    assert reporter.gcd(48, 18) == 6
                    assert reporter.gcd(100, 50) == 50
                    assert reporter.gcd(17, 13) == 1
                    assert reporter.gcd(0, 5) == 5


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_create_subject_worksheet(monkeypatch, experiment_factory, subjectdata_factory,
                                   consent_question_factory):
    """Test Reporter.create_subject_worksheet."""
    experiment = experiment_factory()
    subject = subjectdata_factory(experiment, resolution_w=1920, resolution_h=1080)
    
    # Create consent questions
    cq1 = consent_question_factory(experiment, text="Consent 1", position=0)
    cq2 = consent_question_factory(experiment, text="Consent 2", position=1)
    
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    # Monkeypatch pandas DataFrame
                    with patch('ipl.experiments.reporter.pd.DataFrame.from_dict', DummyDataFrame.from_dict):
                        reporter = Reporter(experiment)
                        
                        result = reporter.create_subject_worksheet(subject)
                        
                        # Should return a DataFrame-like object
                        assert result is not None


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_create_trial_worksheet_empty(monkeypatch, experiment_factory, subjectdata_factory, listitem_factory):
    """Test Reporter.create_trial_worksheet with no trial results."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    subject = subjectdata_factory(experiment, listitem=listitem)
    
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    # Mock empty querysets
                    with patch('ipl.experiments.reporter.OuterBlockItem.objects.filter') as mock_ob:
                        mock_ob.return_value.values_list.return_value = []
                        with patch('ipl.experiments.reporter.BlockItem.objects.filter') as mock_b:
                            mock_b.return_value.values_list.return_value = []
                            with patch('ipl.experiments.reporter.TrialResult.objects.filter') as mock_tr:
                                mock_tr.return_value.order_by.return_value = []
                                
                                # Monkeypatch pandas DataFrame
                                with patch('ipl.experiments.reporter.pd.DataFrame', DummyDataFrame):
                                    result = reporter.create_trial_worksheet(subject)
                                    
                                    assert result is not None


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_create_webgazer_worksheet_empty(monkeypatch, experiment_factory, subjectdata_factory, listitem_factory):
    """Test Reporter.create_webgazer_worksheet with no trial results."""
    experiment = experiment_factory()
    listitem = listitem_factory(experiment)
    subject = subjectdata_factory(experiment, listitem=listitem)
    
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                    reporter = Reporter(experiment)
                    
                    # Mock empty querysets
                    with patch('ipl.experiments.reporter.OuterBlockItem.objects.filter') as mock_ob:
                        mock_ob.return_value.values_list.return_value = []
                        with patch('ipl.experiments.reporter.BlockItem.objects.filter') as mock_b:
                            mock_b.return_value.values_list.return_value = []
                            with patch('ipl.experiments.reporter.TrialResult.objects.filter') as mock_tr:
                                mock_tr.return_value.order_by.return_value = []
                                mock_tr.return_value.values_list.return_value = []
                                
                                # Monkeypatch pandas DataFrame
                                with patch('ipl.experiments.reporter.pd.DataFrame', DummyDataFrame):
                                    result = reporter.create_webgazer_worksheet(subject)
                                    
                                    assert result is not None


@pytest.mark.skipif(not REPORTER_AVAILABLE, reason="Reporter module not available")
def test_create_report_end_to_end(monkeypatch, experiment_factory, subjectdata_factory):
    """Test Reporter.create_report end-to-end flow."""
    experiment = experiment_factory()
    subject = subjectdata_factory(experiment)
    
    with patch('ipl.experiments.reporter.settings') as mock_settings:
        mock_settings.REPORTS_ROOT = '/tmp/reports'
        
        with patch('os.makedirs'):
            with patch('os.remove'):
                with patch('os.path.exists', return_value=True):
                    with patch('ipl.experiments.reporter.zipfile.ZipFile', DummyZipFile):
                        reporter = Reporter(experiment)
                        
                        # Mock SubjectData.objects.filter
                        with patch('ipl.experiments.reporter.SubjectData.objects.filter') as mock_sd:
                            mock_sd.return_value = [subject]
                            
                            # Mock the worksheet creation methods to return DummyDataFrames
                            reporter.create_subject_worksheet = Mock(return_value=DummyDataFrame())
                            reporter.create_trial_worksheet = Mock(return_value=DummyDataFrame())
                            reporter.create_webgazer_worksheet = Mock(return_value=DummyDataFrame())
                            
                            # Mock xlsxwriter
                            with patch('ipl.experiments.reporter.xlsxwriter.Workbook') as mock_wb:
                                mock_workbook = Mock()
                                mock_wb.return_value = mock_workbook
                                mock_workbook.add_worksheet.return_value = Mock()
                                
                                # Mock shutil.rmtree
                                with patch('shutil.rmtree'):
                                    result = reporter.create_report()
                                    
                                    # Should return a filename
                                    assert result is not None
                                    assert 'Test_Exp.zip' in result
