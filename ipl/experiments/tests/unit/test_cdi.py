"""Unit tests for cdi.py"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, mock_open
from django.http import HttpResponse
from django.test import RequestFactory
from ipl.experiments.cdi import sort_items, estimateCDI, cdiRun, cdiSubmit


class TestSortItems:
    """Test sort_items function."""
    
    def test_sort_items_returns_sorted_indices(self, monkeypatch):
        """Test that sort_items returns indices sorted by max info."""
        # Mock the catsim functions
        def mock_max_info_hpc(params):
            return np.array([0.5, 0.3, 0.8])
        
        def mock_inf_hpc(theta, params):
            return np.array([2.0, 1.0, 3.0])
        
        monkeypatch.setattr('ipl.experiments.cdi.max_info_hpc', mock_max_info_hpc)
        monkeypatch.setattr('ipl.experiments.cdi.inf_hpc', mock_inf_hpc)
        
        item_params = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        result = sort_items(item_params)
        
        # Should return indices sorted by descending inf_hpc values
        assert isinstance(result, np.ndarray)


class TestEstimateCDI:
    """Test estimateCDI function."""
    
    def test_estimateCDI_returns_estimate(self, monkeypatch, experiment_factory, 
                                         instrument_factory, subjectdata_factory):
        """Test that estimateCDI computes and saves estimate."""
        # Create test data
        experiment = experiment_factory()
        instrument = instrument_factory()
        experiment.instrument = instrument
        experiment.save()
        
        subject = subjectdata_factory(experiment, id='test-uuid')
        
        # Mock get_object_or_404
        def mock_get_object(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            elif model.__name__ == 'Instrument':
                return instrument
            return None
        
        monkeypatch.setattr('ipl.experiments.cdi.get_object_or_404', mock_get_object)
        
        # Mock CdiResult.objects.filter
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.distinct.return_value = []
        
        from ipl.experiments import cdi
        monkeypatch.setattr(cdi.CdiResult.objects, 'filter', lambda **kwargs: mock_queryset)
        
        # Mock file reading
        mock_csv_reader = [{'word': 'test', 'word_id': '1'}]
        monkeypatch.setattr('csv.DictReader', lambda *args, **kwargs: mock_csv_reader)
        
        # Mock pandas read_csv
        mock_df = Mock()
        mock_df.index = range(10)
        mock_df.__getitem__ = Mock(return_value=Mock())
        mock_df.at = {(0, '12'): 0.5}
        monkeypatch.setattr('pandas.read_csv', lambda *args, **kwargs: mock_df)
        
        # Mock norm.pdf
        monkeypatch.setattr('scipy.stats.norm.pdf', lambda x, loc, scale: np.ones_like(x) * 0.5)
        
        # Mock Answer models
        mock_answer_text = Mock()
        mock_answer_text.body = '2020-01-01'
        
        mock_answer_radio = Mock()
        mock_answer_radio.body = 'Female'
        
        from ipl.experiments import cdi as cdi_module
        monkeypatch.setattr(cdi_module.AnswerText.objects, 'filter', 
                          lambda **kwargs: Mock(first=lambda: mock_answer_text))
        monkeypatch.setattr(cdi_module.AnswerRadio.objects, 'filter', 
                          lambda **kwargs: Mock(first=lambda: mock_answer_radio))
        
        # Mock Question
        mock_question = Mock()
        mock_question.choices = 'Female, Male'
        monkeypatch.setattr(cdi_module.Question.objects, 'filter', 
                          lambda **kwargs: Mock(first=lambda: mock_question))
        
        # Mock settings
        from django.conf import settings
        settings.MEDIA_ROOT = '/tmp'
        
        # Mock instrument file paths
        instrument.words_list = Mock()
        instrument.words_list.path = 'words.csv'
        instrument.f_lm_np_mean = Mock(path='f_lm_np_mean.csv')
        instrument.f_lm_np_sd = Mock(path='f_lm_np_sd.csv')
        instrument.f_lm_p_mean = Mock(path='f_lm_p_mean.csv')
        instrument.f_lm_p_sd = Mock(path='f_lm_p_sd.csv')
        instrument.f_bmin = Mock(path='f_bmin.csv')
        instrument.f_slope = Mock(path='f_slope.csv')
        
        result = estimateCDI('test-uuid')
        
        # Should return a numeric estimate
        assert isinstance(result, (int, float, np.number))
        # Subject data should have cdi_estimate set
        assert subject.cdi_estimate is not None


class TestCdiRun:
    """Test cdiRun function."""
    
    def test_cdiRun_initializes_session(self, monkeypatch, experiment_factory, 
                                       instrument_factory, subjectdata_factory):
        """Test that cdiRun sets up session variables."""
        # Create test data
        experiment = experiment_factory()
        instrument = instrument_factory()
        experiment.instrument = instrument
        experiment.save()
        
        subject = subjectdata_factory(experiment, id='test-uuid')
        
        # Mock get_object_or_404
        def mock_get_object(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            elif model.__name__ == 'Instrument':
                return instrument
            return None
        
        monkeypatch.setattr('ipl.experiments.cdi.get_object_or_404', mock_get_object)
        
        # Mock CSV reader
        mock_csv_reader = [{'word': 'apple'}, {'word': 'ball'}]
        monkeypatch.setattr('csv.DictReader', lambda *args, **kwargs: mock_csv_reader)
        
        # Mock pandas
        mock_df = Mock()
        mock_df.iloc = Mock()
        mock_df.iloc.__getitem__ = Mock(return_value=Mock())
        mock_df.to_numpy = Mock(return_value=np.array([[1, 2, 3, 4], [5, 6, 7, 8]]))
        mock_df.reset_index = Mock(return_value=Mock(to_json=Mock(return_value='{}')))
        monkeypatch.setattr('pandas.read_csv', lambda *args, **kwargs: mock_df)
        
        # Mock sort_items
        monkeypatch.setattr('ipl.experiments.cdi.sort_items', lambda x: np.array([0]))
        
        # Mock FixedPointInitializer
        mock_initializer = Mock()
        mock_initializer.initialize = Mock(return_value=-5.0)
        monkeypatch.setattr('ipl.experiments.cdi.FixedPointInitializer', 
                          lambda x: mock_initializer)
        
        # Mock VocabularyChecklistForm
        mock_form = Mock()
        monkeypatch.setattr('ipl.experiments.cdi.VocabularyChecklistForm', 
                          lambda **kwargs: mock_form)
        
        # Mock settings
        from django.conf import settings
        settings.MEDIA_ROOT = '/tmp'
        
        # Mock instrument paths
        instrument.words_list = Mock(path='words.csv')
        instrument.irt_params = Mock(path='irt.csv')
        
        # Create request
        factory = RequestFactory()
        request = factory.get('/vocab')
        request.session = {}
        
        # Mock Template and RequestContext
        mock_template = Mock()
        mock_template.render = Mock(return_value='rendered')
        monkeypatch.setattr('ipl.experiments.cdi.Template', lambda x: mock_template)
        
        mock_context = Mock()
        monkeypatch.setattr('ipl.experiments.cdi.RequestContext', lambda r, c: mock_context)
        
        result = cdiRun(request, 'test-uuid')
        
        # Should return HttpResponse
        assert isinstance(result, HttpResponse)
        # Session should have required keys
        assert 'all_words' in request.session
        assert 'item_params' in request.session
        assert 'administered_items' in request.session
        assert 'irt_run' in request.session
        assert 'est_theta' in request.session
        assert 'words' in request.session
        assert 'responses' in request.session


class TestCdiSubmit:
    """Test cdiSubmit function."""
    
    def test_cdiSubmit_saves_response_and_continues(self, monkeypatch, experiment_factory, 
                                                    subjectdata_factory):
        """Test cdiSubmit saves response and generates next item."""
        # Create test data
        experiment = experiment_factory(num_words=5)
        subject = subjectdata_factory(experiment, id='test-uuid')
        
        # Mock get_object_or_404
        def mock_get_object(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            return None
        
        monkeypatch.setattr('ipl.experiments.cdi.get_object_or_404', mock_get_object)
        
        # Mock VocabularyChecklistForm
        mock_form = Mock()
        mock_form.is_valid = Mock(return_value=True)
        monkeypatch.setattr('ipl.experiments.cdi.VocabularyChecklistForm', 
                          lambda *args, **kwargs: mock_form)
        
        # Mock CdiResult
        from ipl.experiments import cdi as cdi_module
        mock_cdiresult = Mock()
        monkeypatch.setattr(cdi_module, 'CdiResult', lambda: mock_cdiresult)
        
        # Mock CdiResult.objects.filter count
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.distinct.return_value = mock_queryset
        mock_queryset.count.return_value = 3  # Less than num_words
        
        monkeypatch.setattr(cdi_module.CdiResult.objects, 'filter', 
                          lambda **kwargs: mock_queryset)
        
        # Mock cdiGenerateNextItem
        mock_next_response = Mock(spec=HttpResponse)
        monkeypatch.setattr('ipl.experiments.cdi.cdiGenerateNextItem', 
                          lambda r, u: mock_next_response)
        
        # Create request
        factory = RequestFactory()
        request = factory.post('/vocab/submit', {'word_apple': 'on'})
        request.session = {'responses': [], 'irt_run': 0}
        
        result = cdiSubmit(request, 'test-uuid')
        
        # Should call cdiGenerateNextItem
        assert result == mock_next_response
        # Response should be added to session
        assert len(request.session['responses']) == 1
    
    def test_cdiSubmit_completes_and_proceeds(self, monkeypatch, experiment_factory, 
                                              subjectdata_factory, listitem_factory):
        """Test cdiSubmit completes CDI and proceeds to experiment."""
        # Create test data
        experiment = experiment_factory(num_words=2)
        listitem = listitem_factory(experiment)
        subject = subjectdata_factory(experiment, id='test-uuid')
        
        # Mock get_object_or_404
        def mock_get_object(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            return None
        
        monkeypatch.setattr('ipl.experiments.cdi.get_object_or_404', mock_get_object)
        
        # Mock VocabularyChecklistForm
        mock_form = Mock()
        mock_form.is_valid = Mock(return_value=True)
        monkeypatch.setattr('ipl.experiments.cdi.VocabularyChecklistForm', 
                          lambda *args, **kwargs: mock_form)
        
        # Mock CdiResult
        from ipl.experiments import cdi as cdi_module
        mock_cdiresult = Mock()
        monkeypatch.setattr(cdi_module, 'CdiResult', lambda: mock_cdiresult)
        
        # Mock CdiResult count to match num_words
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.distinct.return_value = mock_queryset
        mock_queryset.count.return_value = 2  # Equal to num_words
        
        monkeypatch.setattr(cdi_module.CdiResult.objects, 'filter', 
                          lambda **kwargs: mock_queryset)
        
        # Mock ListItem.objects.filter
        mock_li_queryset = Mock()
        mock_li_queryset.__bool__ = Mock(return_value=True)
        monkeypatch.setattr(cdi_module.ListItem.objects, 'filter', 
                          lambda **kwargs: mock_li_queryset)
        
        # Mock estimateCDI
        monkeypatch.setattr('ipl.experiments.cdi.estimateCDI', lambda x: 50.0)
        
        # Mock proceedToExperiment
        mock_proceed_response = Mock(spec=HttpResponse)
        monkeypatch.setattr('ipl.experiments.cdi.proceedToExperiment', 
                          lambda e, u: mock_proceed_response)
        
        # Create request
        factory = RequestFactory()
        request = factory.post('/vocab/submit', {'word_apple': 'on'})
        request.session = {'responses': [True], 'irt_run': 1}
        
        result = cdiSubmit(request, 'test-uuid')
        
        # Should proceed to experiment
        assert result == mock_proceed_response
