"""Unit tests for ipl/experiments/cdi.py"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory
from ipl.experiments import cdi


class TestSortItems:
    """Test sort_items function."""
    
    @patch('ipl.experiments.cdi.max_info_hpc')
    @patch('ipl.experiments.cdi.inf_hpc')
    def test_sort_items_returns_sorted_indices(self, mock_inf_hpc, mock_max_info_hpc):
        """Test sort_items returns sorted item indices."""
        import numpy as np
        
        # Mock the item_params
        item_params = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        
        # Mock return values
        mock_max_info_hpc.return_value = 0.5
        mock_inf_hpc.return_value = np.array([0.8, 0.3])
        
        result = cdi.sort_items(item_params)
        
        # Should return argsort of negative inf_hpc values
        assert isinstance(result, np.ndarray)
        mock_max_info_hpc.assert_called_once()
        mock_inf_hpc.assert_called_once()


class TestEstimateCDI:
    """Test estimateCDI function."""
    
    @patch('ipl.experiments.cdi.get_object_or_404')
    @patch('ipl.experiments.cdi.pd.read_csv')
    @patch('ipl.experiments.cdi.csv.DictReader')
    @patch('ipl.experiments.cdi.norm.pdf')
    @patch('builtins.open', new_callable=mock_open)
    def test_estimate_cdi_returns_numeric_estimate(self, mock_file, mock_norm_pdf, 
                                                    mock_dict_reader, mock_read_csv, 
                                                    mock_get_object):
        """Test estimateCDI returns numeric estimate and saves to subject_data."""
        import numpy as np
        import pandas as pd
        
        # Mock SubjectData
        mock_subject = Mock()
        mock_subject.experiment.pk = 'exp1'
        mock_subject.created.date.return_value = Mock()
        mock_subject.cdi_estimate = None
        
        # Mock Experiment
        mock_experiment = Mock()
        mock_experiment.instrument.pk = 'instr1'
        
        # Mock Instrument
        mock_instrument = Mock()
        mock_instrument.words_list.path = 'words.csv'
        mock_instrument.f_lm_np_mean.path = 'f_lm_np_mean.csv'
        mock_instrument.f_lm_np_sd.path = 'f_lm_np_sd.csv'
        mock_instrument.f_lm_p_mean.path = 'f_lm_p_mean.csv'
        mock_instrument.f_lm_p_sd.path = 'f_lm_p_sd.csv'
        mock_instrument.f_bmin.path = 'f_bmin.csv'
        mock_instrument.f_slope.path = 'f_slope.csv'
        
        # Mock get_object_or_404 calls
        mock_get_object.side_effect = [mock_subject, mock_experiment, mock_instrument]
        
        # Mock DictReader for word list
        mock_dict_reader.return_value = [
            {'word': 'apple', 'word_id': '1'},
            {'word': 'banana', 'word_id': '2'}
        ]
        
        # Mock CdiResult queryset
        mock_cdi_result = Mock()
        mock_cdi_result.given_label = 'apple'
        mock_cdi_result.response = True
        
        with patch('ipl.experiments.cdi.CdiResult') as MockCdiResult:
            MockCdiResult.objects.filter.return_value.order_by.return_value.distinct.return_value = [mock_cdi_result]
            
            # Mock AnswerText and AnswerRadio
            with patch('ipl.experiments.cdi.AnswerText') as MockAnswerText:
                with patch('ipl.experiments.cdi.AnswerRadio') as MockAnswerRadio:
                    with patch('ipl.experiments.cdi.Question') as MockQuestion:
                        # Mock age answer
                        mock_age_answer = Mock()
                        mock_age_answer.body = '2020-01-01'
                        MockAnswerText.objects.filter.return_value.first.return_value = mock_age_answer
                        
                        # Mock sex answer
                        mock_sex_answer = Mock()
                        mock_sex_answer.body = 'Female'
                        MockAnswerRadio.objects.filter.return_value.first.return_value = mock_sex_answer
                        
                        # Mock question choices
                        mock_question = Mock()
                        mock_question.choices = 'Female, Male'
                        MockQuestion.objects.filter.return_value.first.return_value = mock_question
                        
                        # Mock pandas DataFrames
                        mock_df = pd.DataFrame({
                            'word_id': [1, 2],
                            '24': [0.5, 0.6]
                        })
                        mock_read_csv.return_value = mock_df
                        
                        # Mock norm.pdf
                        mock_norm_pdf.return_value = np.array([0.1, 0.2, 0.3])
                        
                        # Mock settings.MEDIA_ROOT
                        with patch('ipl.experiments.cdi.settings.MEDIA_ROOT', '/media'):
                            result = cdi.estimateCDI('test-uuid')
                            
                            # Should return numeric estimate
                            assert isinstance(result, (int, float))
                            # Should save to subject_data
                            assert mock_subject.save.called


class TestCdiRun:
    """Test cdiRun function."""
    
    @patch('ipl.experiments.cdi.get_object_or_404')
    @patch('ipl.experiments.cdi.pd.read_csv')
    @patch('ipl.experiments.cdi.csv.DictReader')
    @patch('ipl.experiments.cdi.sort_items')
    @patch('ipl.experiments.cdi.FixedPointInitializer')
    @patch('ipl.experiments.cdi.VocabularyChecklistForm')
    @patch('ipl.experiments.cdi.Template')
    @patch('builtins.open', new_callable=mock_open)
    def test_cdi_run_returns_response(self, mock_file, mock_template, mock_form_class,
                                      mock_initializer, mock_sort_items, mock_read_csv,
                                      mock_get_object):
        """Test cdiRun sets session keys and returns HttpResponse."""
        import numpy as np
        import pandas as pd
        
        # Create request with session
        factory = RequestFactory()
        request = factory.get('/vocab')
        request.session = {}
        
        # Mock SubjectData
        mock_subject = Mock()
        mock_subject.experiment.pk = 'exp1'
        
        # Mock Experiment
        mock_experiment = Mock()
        mock_experiment.instrument.pk = 'instr1'
        mock_experiment.cdi_page_tpl = '<html>CDI Page</html>'
        
        # Mock Instrument
        mock_instrument = Mock()
        mock_instrument.words_list.path = 'words.csv'
        mock_instrument.irt_params.path = 'irt.csv'
        
        # Mock get_object_or_404
        mock_get_object.side_effect = [mock_subject, mock_experiment, mock_instrument]
        
        # Mock DictReader
        with patch('ipl.experiments.cdi.csv.DictReader') as mock_dict_reader:
            mock_dict_reader.return_value = [
                {'word': 'apple'},
                {'word': 'banana'}
            ]
            
            # Mock read_csv for IRT params
            mock_df = pd.DataFrame({
                'col1': [1, 2],
                'col2': [3, 4],
                'col3': [5, 6],
                'col4': [7, 8]
            })
            mock_read_csv.return_value = mock_df
            
            # Mock sort_items
            mock_sort_items.return_value = np.array([[0]])
            
            # Mock FixedPointInitializer
            mock_init_instance = Mock()
            mock_init_instance.initialize.return_value = -5
            mock_initializer.return_value = mock_init_instance
            
            # Mock VocabularyChecklistForm
            mock_form = Mock()
            mock_form_class.return_value = mock_form
            
            # Mock Template
            mock_template_instance = Mock()
            mock_template_instance.render.return_value = '<html>Rendered</html>'
            mock_template.return_value = mock_template_instance
            
            # Mock settings.MEDIA_ROOT
            with patch('ipl.experiments.cdi.settings.MEDIA_ROOT', '/media'):
                result = cdi.cdiRun(request, 'test-uuid')
                
                # Should set session keys
                assert 'all_words' in request.session
                assert 'item_params' in request.session
                assert 'administered_items' in request.session
                assert 'irt_run' in request.session
                assert 'est_theta' in request.session
                assert 'words' in request.session
                assert 'responses' in request.session
                
                # Should return HttpResponse
                assert isinstance(result, HttpResponse)


class TestCdiSubmit:
    """Test cdiSubmit function."""
    
    @patch('ipl.experiments.cdi.get_object_or_404')
    @patch('ipl.experiments.cdi.VocabularyChecklistForm')
    @patch('ipl.experiments.cdi.estimateCDI')
    @patch('ipl.experiments.cdi.proceedToExperiment')
    def test_cdi_submit_valid_form_below_threshold(self, mock_proceed, mock_estimate,
                                                    mock_form_class, mock_get_object):
        """Test cdiSubmit with valid form and count below threshold."""
        # Create request
        factory = RequestFactory()
        request = factory.post('/vocab/submit', {'word_apple': 'on'})
        request.session = {'responses': []}
        
        # Mock SubjectData
        mock_subject = Mock()
        
        # Mock Experiment
        mock_experiment = Mock()
        mock_experiment.num_words = 25
        
        # Mock get_object_or_404
        mock_get_object.side_effect = [mock_subject, mock_experiment]
        
        # Mock form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        # Mock CdiResult count
        with patch('ipl.experiments.cdi.CdiResult') as MockCdiResult:
            mock_queryset = Mock()
            mock_queryset.order_by.return_value.distinct.return_value.count.return_value = 5
            MockCdiResult.objects.filter.return_value = mock_queryset
            
            # Mock cdiGenerateNextItem
            with patch('ipl.experiments.cdi.cdiGenerateNextItem') as mock_gen_next:
                mock_gen_next.return_value = HttpResponse('Next Item')
                
                result = cdi.cdiSubmit(request, 'test-uuid')
                
                # Should call cdiGenerateNextItem
                assert mock_gen_next.called
                assert not mock_estimate.called
    
    @patch('ipl.experiments.cdi.get_object_or_404')
    @patch('ipl.experiments.cdi.VocabularyChecklistForm')
    @patch('ipl.experiments.cdi.estimateCDI')
    @patch('ipl.experiments.cdi.proceedToExperiment')
    @patch('ipl.experiments.cdi.ListItem')
    def test_cdi_submit_valid_form_at_threshold_with_listitem(self, mock_listitem_class,
                                                               mock_proceed, mock_estimate,
                                                               mock_form_class, mock_get_object):
        """Test cdiSubmit with valid form at threshold and ListItem exists."""
        # Create request
        factory = RequestFactory()
        request = factory.post('/vocab/submit', {'word_apple': 'on'})
        request.session = {'responses': []}
        
        # Mock SubjectData
        mock_subject = Mock()
        
        # Mock Experiment
        mock_experiment = Mock()
        mock_experiment.num_words = 5
        
        # Mock get_object_or_404
        mock_get_object.side_effect = [mock_subject, mock_experiment]
        
        # Mock form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        # Mock CdiResult count
        with patch('ipl.experiments.cdi.CdiResult') as MockCdiResult:
            mock_queryset = Mock()
            mock_queryset.order_by.return_value.distinct.return_value.count.return_value = 5
            MockCdiResult.objects.filter.return_value = mock_queryset
            
            # Mock ListItem.objects.filter to return truthy
            mock_listitem_class.objects.filter.return_value = [Mock()]
            
            # Mock estimateCDI and proceedToExperiment
            mock_estimate.return_value = 50.0
            mock_proceed.return_value = HttpResponseRedirect('/experiment/run')
            
            result = cdi.cdiSubmit(request, 'test-uuid')
            
            # Should call estimateCDI and proceedToExperiment
            assert mock_estimate.called
            assert mock_proceed.called
            assert isinstance(result, HttpResponseRedirect)
    
    @patch('ipl.experiments.cdi.get_object_or_404')
    @patch('ipl.experiments.cdi.VocabularyChecklistForm')
    def test_cdi_submit_invalid_form(self, mock_form_class, mock_get_object):
        """Test cdiSubmit with invalid form."""
        # Create request
        factory = RequestFactory()
        request = factory.post('/vocab/submit', {})
        request.session = {}
        
        # Mock SubjectData
        mock_subject = Mock()
        
        # Mock Experiment
        mock_experiment = Mock()
        mock_experiment.cdi_page_tpl = '<html>CDI Page</html>'
        
        # Mock get_object_or_404
        mock_get_object.side_effect = [mock_subject, mock_experiment]
        
        # Mock form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form
        
        # Mock Template
        with patch('ipl.experiments.cdi.Template') as mock_template:
            mock_template_instance = Mock()
            mock_template_instance.render.return_value = '<html>Rendered</html>'
            mock_template.return_value = mock_template_instance
            
            result = cdi.cdiSubmit(request, 'test-uuid')
            
            # Should return HttpResponse with form
            assert isinstance(result, HttpResponse)
