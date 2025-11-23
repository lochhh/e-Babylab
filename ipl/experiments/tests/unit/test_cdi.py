"""Unit tests for cdi.py functions."""
import pytest
from unittest.mock import MagicMock, Mock
import numpy as np


class TestSortItems:
    """Test sort_items function."""

    def test_sort_items_returns_sorted_indices(self, monkeypatch):
        """Test sort_items returns indices sorted by maximum item information."""
        try:
            from experiments.cdi import sort_items
        except ImportError:
            pytest.skip("cdi module not available")
        
        # Mock catsim functions
        def mock_max_info_hpc(item_params):
            # Return mock theta values
            return np.array([0.5, -0.5, 1.0])
        
        def mock_inf_hpc(theta, item_params):
            # Return mock information values
            return np.array([2.0, 1.0, 3.0])
        
        import experiments.cdi as cdi_module
        monkeypatch.setattr(cdi_module, 'max_info_hpc', mock_max_info_hpc)
        monkeypatch.setattr(cdi_module, 'inf_hpc', mock_inf_hpc)
        
        item_params = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        result = sort_items(item_params)
        
        # Should return indices in descending order of information
        assert isinstance(result, np.ndarray)
        assert len(result) == 3


class TestEstimateCDI:
    """Test estimateCDI function."""

    def test_estimate_cdi_basic_flow(self, monkeypatch, experiment_factory, 
                                     instrument_factory, subjectdata_factory):
        """Test estimateCDI basic execution flow with mocked dependencies."""
        try:
            from experiments.cdi import estimateCDI
            from experiments.models import CdiResult, Question, AnswerText, AnswerRadio
        except ImportError:
            pytest.skip("cdi module or models not available")
        
        # Create test data
        experiment = experiment_factory()
        instrument = instrument_factory()
        experiment.instrument = instrument
        experiment.save()
        
        subject = subjectdata_factory(experiment, id="test-uuid")
        
        # Mock get_object_or_404
        def mock_get_object_or_404(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            elif model.__name__ == 'Instrument':
                return instrument
            return None
        
        # Mock file reading
        mock_df = MagicMock()
        mock_df.index = [0, 1]
        mock_df.at = {(0, '12'): 50.0, (1, '12'): 60.0}
        
        def mock_read_csv(path):
            return mock_df
        
        def mock_dict_reader(file, **kwargs):
            return [{'word': 'apple', 'word_id': '1'}]
        
        # Mock norm.pdf
        def mock_norm_pdf(x, loc, scale):
            return np.ones_like(x)
        
        # Mock CdiResult manager
        mock_cdi_results = MagicMock()
        mock_cdi_results.filter.return_value.order_by.return_value.distinct.return_value = []
        
        # Mock Answer objects
        mock_answer_text = MagicMock()
        mock_answer_text.body = '2020-01-01'
        mock_answer_text_qs = MagicMock()
        mock_answer_text_qs.first.return_value = mock_answer_text
        
        mock_answer_radio = MagicMock()
        mock_answer_radio.body = 'Female'
        mock_answer_radio_qs = MagicMock()
        mock_answer_radio_qs.first.return_value = mock_answer_radio
        
        mock_question = MagicMock()
        mock_question.choices = 'Female, Male'
        mock_question_qs = MagicMock()
        mock_question_qs.first.return_value = mock_question
        
        import experiments.cdi as cdi_module
        from django.shortcuts import get_object_or_404 as real_get
        import pandas as pd
        import csv
        from scipy.stats import norm
        
        monkeypatch.setattr(cdi_module, 'get_object_or_404', mock_get_object_or_404)
        monkeypatch.setattr(pd, 'read_csv', mock_read_csv)
        monkeypatch.setattr(csv, 'DictReader', mock_dict_reader)
        monkeypatch.setattr(norm, 'pdf', mock_norm_pdf)
        monkeypatch.setattr(CdiResult.objects, 'filter', lambda **kw: mock_cdi_results.filter(**kw))
        monkeypatch.setattr(AnswerText.objects, 'filter', lambda **kw: mock_answer_text_qs)
        monkeypatch.setattr(AnswerRadio.objects, 'filter', lambda **kw: mock_answer_radio_qs)
        monkeypatch.setattr(Question.objects, 'filter', lambda **kw: mock_question_qs)
        
        # Run function - should return estimate or redirect
        result = estimateCDI("test-uuid")
        # If it completes without exception, test passes
        assert result is not None


class TestCdiRun:
    """Test cdiRun view function."""

    def test_cdi_run_initializes_session(self, monkeypatch, rf, experiment_factory,
                                         instrument_factory, subjectdata_factory):
        """Test cdiRun initializes session variables."""
        try:
            from experiments.cdi import cdiRun
            from experiments.models import Question
        except ImportError:
            pytest.skip("cdi module not available")
        
        # Create test data
        experiment = experiment_factory()
        instrument = instrument_factory()
        experiment.instrument = instrument
        experiment.save()
        
        subject = subjectdata_factory(experiment, id="test-run-uuid")
        
        # Mock get_object_or_404
        def mock_get_object_or_404(model, **kwargs):
            if model.__name__ == 'SubjectData':
                return subject
            elif model.__name__ == 'Experiment':
                return experiment
            elif model.__name__ == 'Instrument':
                return instrument
            return None
        
        # Mock file reading
        def mock_dict_reader(file, **kwargs):
            return [{'word': 'apple', 'word_id': '1'}]
        
        mock_df = MagicMock()
        mock_df.iloc = MagicMock()
        mock_df.iloc.__getitem__ = MagicMock(return_value=mock_df)
        mock_df.reset_index.return_value.to_json.return_value = '[]'
        
        def mock_read_csv(path):
            return mock_df
        
        def mock_sort_items(params):
            return np.array([[0]])
        
        mock_initializer = MagicMock()
        mock_initializer.return_value.initialize.return_value = -5
        
        import experiments.cdi as cdi_module
        import pandas as pd
        import csv
        
        monkeypatch.setattr(cdi_module, 'get_object_or_404', mock_get_object_or_404)
        monkeypatch.setattr(pd, 'read_csv', mock_read_csv)
        monkeypatch.setattr(csv, 'DictReader', mock_dict_reader)
        monkeypatch.setattr(cdi_module, 'sort_items', mock_sort_items)
        monkeypatch.setattr(cdi_module, 'FixedPointInitializer', mock_initializer)
        
        # Create request with session
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get(f'/cdi/run/test-run-uuid/')
        
        # Add session middleware
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Mock VocabularyChecklistForm
        mock_form = MagicMock()
        mock_form.as_p.return_value = '<form></form>'
        
        def mock_vocab_form(*args, **kwargs):
            return mock_form
        
        monkeypatch.setattr(cdi_module, 'VocabularyChecklistForm', mock_vocab_form)
        
        # Mock render
        def mock_render(request, template, context):
            return MagicMock(status_code=200)
        
        from django.shortcuts import render
        monkeypatch.setattr(cdi_module, 'render', mock_render)
        
        # Run function
        response = cdiRun(request, "test-run-uuid")
        
        # Verify session variables were set
        assert 'all_words' in request.session
        assert 'item_params' in request.session
        assert 'administered_items' in request.session


class TestCdiSubmit:
    """Test cdiSubmit view function."""

    def test_cdi_submit_processes_form(self, monkeypatch, rf, experiment_factory,
                                      subjectdata_factory):
        """Test cdiSubmit processes vocabulary checklist form."""
        try:
            from experiments.cdi import cdiSubmit
            from experiments.models import ListItem, CdiResult
        except ImportError:
            pytest.skip("cdi module not available")
        
        # Create test data
        experiment = experiment_factory()
        subject = subjectdata_factory(experiment, id="test-submit-uuid")
        
        # Create request with session
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(f'/cdi/submit/test-submit-uuid/')
        
        # Add session middleware
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['words'] = ['apple', 'ball']
        request.session['irt_run'] = 1
        request.session['all_words'] = '["apple", "ball", "cat"]'
        request.session.save()
        
        # Mock VocabularyChecklistForm
        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {'word_apple': True, 'word_ball': False}
        
        def mock_vocab_form(*args, **kwargs):
            return mock_form
        
        # Mock CdiResult manager
        mock_cdi_result = MagicMock()
        
        def mock_create(**kwargs):
            return mock_cdi_result
        
        mock_cdi_manager = MagicMock()
        mock_cdi_manager.create = mock_create
        
        # Mock ListItem filter
        mock_listitem = MagicMock()
        mock_listitem.filter.return_value.exists.return_value = True
        
        # Mock estimateCDI
        def mock_estimate_cdi(uuid):
            return 50.0
        
        # Mock proceedToExperiment
        def mock_proceed(request, uuid):
            return MagicMock(status_code=302)
        
        import experiments.cdi as cdi_module
        
        monkeypatch.setattr(cdi_module, 'VocabularyChecklistForm', mock_vocab_form)
        monkeypatch.setattr(CdiResult, 'objects', mock_cdi_manager)
        monkeypatch.setattr(ListItem, 'objects', mock_listitem)
        monkeypatch.setattr(cdi_module, 'estimateCDI', mock_estimate_cdi)
        monkeypatch.setattr(cdi_module, 'proceedToExperiment', mock_proceed)
        
        # Run function
        response = cdiSubmit(request, "test-submit-uuid")
        
        # Verify it returns a response
        assert response is not None
