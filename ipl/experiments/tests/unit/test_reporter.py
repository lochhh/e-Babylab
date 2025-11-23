"""Unit tests for ipl/experiments/reporter.py"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from experiments.reporter import Reporter


class DummyZipFile:
    """Dummy ZipFile for testing."""
    def __init__(self, *args, **kwargs):
        self.files = []
    
    def write(self, filename, arcname=None):
        self.files.append((filename, arcname))
    
    def writestr(self, arcname, data):
        self.files.append((arcname, data))
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class DummyDataFrame:
    """Dummy DataFrame for testing."""
    def __init__(self, data=None, orient=None):
        self.data = data or {}
        self.orient = orient
    
    def to_excel(self, writer, sheet_name, index=True):
        pass


class TestReporter:
    """Test Reporter class methods."""
    
    @patch('experiments.reporter.zipfile.ZipFile', DummyZipFile)
    @patch('experiments.reporter.os.makedirs')
    @patch('experiments.reporter.os.remove')
    @patch('experiments.reporter.os.path.exists')
    def test_reporter_init(self, mock_exists, mock_remove, mock_makedirs, experiment_factory):
        """Test Reporter initialization."""
        experiment = experiment_factory(exp_name='Test Exp')
        
        mock_exists.return_value = True
        
        with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
            reporter = Reporter(experiment)
            
            assert reporter.experiment == experiment
            assert reporter.output_file == 'Test_Exp.zip'
            assert reporter.output_folder == '/reports'
            assert mock_makedirs.called
    
    def test_calc_trial_duration_with_times(self):
        """Test calc_trial_duration with valid times."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        duration = reporter.calc_trial_duration(1000, 2500)
                        assert duration == '1500'
    
    def test_calc_trial_duration_missing_times(self):
        """Test calc_trial_duration with missing times."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        assert reporter.calc_trial_duration(None, 2500) == ''
                        assert reporter.calc_trial_duration(1000, None) == ''
                        assert reporter.calc_trial_duration(None, None) == ''
    
    def test_calc_roi_response_valid_coords(self):
        """Test calc_roi_response with valid coordinates."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        # Mock result
                        mock_result = Mock()
                        mock_result.resolution_w = 1920
                        mock_result.resolution_h = 1080
                        mock_result.trialitem.grid_row = 2
                        mock_result.trialitem.grid_col = 2
                        
                        # Test coordinates in first quadrant
                        roi = reporter.calc_roi_response(mock_result, [500, 300])
                        assert roi == '(0,0)'
    
    def test_calc_roi_response_empty_coords(self):
        """Test calc_roi_response with empty coordinates."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        mock_result = Mock()
                        mock_result.resolution_w = 1920
                        mock_result.resolution_h = 1080
                        mock_result.trialitem.grid_row = 2
                        mock_result.trialitem.grid_col = 2
                        
                        roi = reporter.calc_roi_response(mock_result, [])
                        assert roi == ''
    
    def test_gcd_basic(self):
        """Test gcd function."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        assert reporter.gcd(48, 18) == 6
                        assert reporter.gcd(100, 50) == 50
                        assert reporter.gcd(17, 13) == 1
    
    def test_gcd_with_zero(self):
        """Test gcd function with zero."""
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        assert reporter.gcd(10, 0) == 10
                        assert reporter.gcd(0, 10) == 10
    
    @patch('experiments.reporter.pd.DataFrame.from_dict')
    @patch('experiments.reporter.ConsentQuestion')
    @patch('experiments.reporter.AnswerBase')
    @patch('experiments.reporter.CdiResult')
    def test_create_subject_worksheet(self, mock_cdi_result, mock_answer_base, 
                                      mock_consent_q, mock_from_dict, 
                                      experiment_factory, subjectdata_factory,
                                      listitem_factory):
        """Test create_subject_worksheet creates DataFrame."""
        experiment = experiment_factory(exp_name='Test Exp')
        listitem = listitem_factory(experiment, list_name='List1')
        subject = subjectdata_factory(experiment, listitem=listitem)
        subject.resolution_w = 1920
        subject.resolution_h = 1080
        subject.participant_id = 1
        subject.cdi_estimate = 50.0
        
        # Mock ConsentQuestion
        mock_consent_q.objects.filter.return_value = []
        
        # Mock AnswerBase
        mock_answer_base.objects.filter.return_value = []
        
        # Mock CdiResult
        mock_cdi_result.objects.filter.return_value = []
        
        # Mock DataFrame.from_dict
        mock_from_dict.return_value = DummyDataFrame()
        
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        result = reporter.create_subject_worksheet(subject)
                        
                        assert mock_from_dict.called
                        assert isinstance(result, DummyDataFrame)
    
    @patch('experiments.reporter.OuterBlockItem')
    @patch('experiments.reporter.BlockItem')
    @patch('experiments.reporter.TrialResult')
    @patch('experiments.reporter.pd.DataFrame')
    def test_create_trial_worksheet_empty_results(self, mock_df, mock_trial_result,
                                                   mock_block_item, mock_outer_block,
                                                   experiment_factory, subjectdata_factory,
                                                   listitem_factory):
        """Test create_trial_worksheet with empty TrialResult queryset."""
        experiment = experiment_factory()
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, listitem=listitem)
        
        # Mock empty querysets
        mock_outer_block.objects.filter.return_value.values_list.return_value = []
        mock_block_item.objects.filter.return_value.values_list.return_value = []
        mock_trial_result.objects.filter.return_value.order_by.return_value = []
        
        # Mock DataFrame
        mock_df.return_value = DummyDataFrame()
        
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        result = reporter.create_trial_worksheet(subject)
                        
                        assert mock_df.called
    
    @patch('experiments.reporter.TrialResult')
    @patch('experiments.reporter.pd.DataFrame')
    def test_create_webgazer_worksheet_empty_results(self, mock_df, mock_trial_result,
                                                      experiment_factory, subjectdata_factory):
        """Test create_webgazer_worksheet with empty TrialResult queryset."""
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment)
        
        # Mock empty queryset
        mock_trial_result.objects.filter.return_value = []
        
        # Mock DataFrame
        mock_df.return_value = DummyDataFrame()
        
        mock_exp = Mock()
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(mock_exp)
                        
                        result = reporter.create_webgazer_worksheet(subject)
                        
                        assert mock_df.called
    
    @patch('experiments.reporter.SubjectData')
    def test_create_report_flow(self, mock_subject_data, experiment_factory):
        """Test create_report flow with mocked methods."""
        experiment = experiment_factory(exp_name='Test')
        
        # Mock SubjectData queryset
        mock_subject = Mock()
        mock_subject.id = 'subj1'
        mock_subject_data.objects.filter.return_value = [mock_subject]
        
        with patch('experiments.reporter.zipfile.ZipFile', DummyZipFile):
            with patch('experiments.reporter.settings.REPORTS_ROOT', '/reports'):
                with patch('experiments.reporter.os.makedirs'):
                    with patch('experiments.reporter.os.path.exists', return_value=False):
                        reporter = Reporter(experiment)
                        
                        # Mock worksheet creation methods
                        reporter.create_subject_worksheet = Mock(return_value=DummyDataFrame())
                        reporter.create_trial_worksheet = Mock(return_value=DummyDataFrame())
                        reporter.create_webgazer_worksheet = Mock(return_value=DummyDataFrame())
                        
                        # Mock xlsxwriter
                        with patch('experiments.reporter.xlsxwriter.Workbook') as mock_workbook:
                            mock_wb_instance = Mock()
                            mock_workbook.return_value = mock_wb_instance
                            
                            # Mock shutil and os operations
                            with patch('experiments.reporter.shutil.rmtree'):
                                with patch('experiments.reporter.os.path.join', side_effect=lambda *args: '/'.join(args)):
                                    result = reporter.create_report()
                                    
                                    # Verify methods were called
                                    assert reporter.create_subject_worksheet.called
                                    assert reporter.create_trial_worksheet.called
                                    assert reporter.create_webgazer_worksheet.called
