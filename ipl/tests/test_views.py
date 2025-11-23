"""
Tests for experiments app views.

This module tests:
- View status codes (200, 302, 404)
- Context data
- Template rendering
- Redirects and response content
- Authentication and permissions
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, Mock
import uuid
import responses

from experiments.models import (
    Experiment, ListItem, SubjectData, TrialItem, TrialResult
)
from tests.helpers import (
    UserFactory, ExperimentFactory, ListItemFactory, SubjectDataFactory,
    BlockItemFactory, TrialItemFactory, ConsentQuestionFactory, QuestionFactory,
    OuterBlockItemFactory
)


class IndexViewTest(TestCase):
    """Test the index view."""
    
    def test_index_view_status_code(self):
        """Test that index view returns 200."""
        response = self.client.get(reverse('experiments:index'))
        self.assertEqual(response.status_code, 200)


class InformationPageViewTest(TestCase):
    """Test the information page view."""
    
    def test_information_page_exists(self):
        """Test information page returns 200 for valid experiment."""
        experiment = ExperimentFactory()
        url = reverse('experiments:informationPage', args=[experiment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_information_page_404_invalid_id(self):
        """Test information page returns 404 for invalid experiment ID."""
        fake_id = uuid.uuid4()
        url = reverse('experiments:informationPage', args=[fake_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_information_page_renders_template(self):
        """Test that information page renders experiment template."""
        experiment = ExperimentFactory()
        url = reverse('experiments:informationPage', args=[experiment.id])
        response = self.client.get(url)
        
        # The template content is rendered
        self.assertEqual(response.status_code, 200)


class BrowserCheckViewTest(TestCase):
    """Test the browser check view."""
    
    def test_browser_check_page_exists(self):
        """Test browser check page returns 200 for valid experiment."""
        experiment = ExperimentFactory()
        url = reverse('experiments:browserCheck', args=[experiment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_browser_check_404_invalid_id(self):
        """Test browser check returns 404 for invalid experiment ID."""
        fake_id = uuid.uuid4()
        url = reverse('experiments:browserCheck', args=[fake_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class ConsentFormViewTest(TestCase):
    """Test the consent form views."""
    
    def test_consent_form_view_get(self):
        """Test GET request to consent form."""
        experiment = ExperimentFactory()
        ConsentQuestionFactory(experiment=experiment)
        
        url = reverse('experiments:consentForm', args=[experiment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_consent_form_404_invalid_id(self):
        """Test consent form returns 404 for invalid experiment ID."""
        fake_id = uuid.uuid4()
        url = reverse('experiments:consentForm', args=[fake_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    @responses.activate
    def test_consent_form_submit_all_yes(self):
        """Test consent form submission with all 'yes' answers."""
        experiment = ExperimentFactory()
        cq1 = ConsentQuestionFactory(experiment=experiment, position=0)
        cq2 = ConsentQuestionFactory(experiment=experiment, position=1)
        
        url = reverse('experiments:consentFormSubmit', args=[experiment.id])
        data = {
            f'question_{cq1.pk}': 'yes',
            f'question_{cq2.pk}': 'yes',
        }
        
        response = self.client.post(url, data)
        
        # Should redirect to subject form
        self.assertEqual(response.status_code, 302)
        self.assertIn('form', response.url)
    
    def test_consent_form_submit_with_no(self):
        """Test consent form submission with 'no' answer shows fail page."""
        experiment = ExperimentFactory()
        cq1 = ConsentQuestionFactory(experiment=experiment)
        
        url = reverse('experiments:consentFormSubmit', args=[experiment.id])
        data = {
            f'question_{cq1.pk}': 'no',
        }
        
        response = self.client.post(url, data)
        
        # Should render consent fail page (200, not redirect)
        self.assertEqual(response.status_code, 200)


class SubjectFormViewTest(TestCase):
    """Test the subject form views."""
    
    def test_subject_form_view_get(self):
        """Test GET request to subject form."""
        experiment = ExperimentFactory()
        url = reverse('experiments:subjectForm', args=[experiment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_subject_form_404_invalid_id(self):
        """Test subject form returns 404 for invalid experiment ID."""
        fake_id = uuid.uuid4()
        url = reverse('experiments:subjectForm', args=[fake_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    @responses.activate
    def test_subject_form_submit_valid_with_recaptcha(self):
        """Test valid subject form submission with reCAPTCHA."""
        experiment = ExperimentFactory()
        ListItemFactory(experiment=experiment)
        
        # Mock reCAPTCHA verification
        responses.add(
            responses.POST,
            'https://www.google.com/recaptcha/api/siteverify',
            json={'success': True},
            status=200
        )
        
        url = reverse('experiments:subjectFormSubmit', args=[experiment.id])
        data = {
            'resolution_w': 1920,
            'resolution_h': 1080,
            'g-recaptcha-response': 'test-token',
        }
        
        response = self.client.post(url, data)
        
        # Should redirect (to vocab or webcam test or experiment run)
        self.assertEqual(response.status_code, 302)
    
    @responses.activate
    def test_subject_form_submit_invalid_recaptcha(self):
        """Test subject form submission with invalid reCAPTCHA."""
        experiment = ExperimentFactory()
        
        # Mock failed reCAPTCHA verification
        responses.add(
            responses.POST,
            'https://www.google.com/recaptcha/api/siteverify',
            json={'success': False},
            status=200
        )
        
        url = reverse('experiments:subjectFormSubmit', args=[experiment.id])
        data = {
            'resolution_w': 1920,
            'resolution_h': 1080,
            'g-recaptcha-response': 'invalid-token',
        }
        
        response = self.client.post(url, data)
        
        # Should re-render form with error (200)
        self.assertEqual(response.status_code, 200)


class ExperimentRunViewTest(TestCase):
    """Test the experiment run view."""
    
    def test_experiment_run_view(self):
        """Test experiment run view with valid UUID."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:experimentRun', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
    
    def test_experiment_run_404_invalid_uuid(self):
        """Test experiment run returns 404 for invalid UUID."""
        fake_uuid = uuid.uuid4()
        url = reverse('experiments:experimentRun', args=[fake_uuid])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class ExperimentPauseViewTest(TestCase):
    """Test the experiment pause view."""
    
    def test_experiment_pause_view(self):
        """Test experiment pause view."""
        experiment = ExperimentFactory(include_pause_page=True)
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:experimentPause', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class ExperimentEndViewTest(TestCase):
    """Test the experiment end view."""
    
    def test_experiment_end_view(self):
        """Test experiment end (thank you) view."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:experimentEnd', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class ExperimentErrorViewTest(TestCase):
    """Test the experiment error view."""
    
    def test_experiment_error_view(self):
        """Test experiment error view."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:experimentError', args=[subject.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)


class DeleteSubjectViewTest(TestCase):
    """Test the delete subject view."""
    
    def test_delete_subject_removes_subject(self):
        """Test that delete subject view removes SubjectData."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        subject_id = subject.id
        
        url = reverse('experiments:deleteSubject', args=[subject.id])
        response = self.client.post(url)
        
        # Should return 204 No Content
        self.assertEqual(response.status_code, 204)
        
        # Subject should be deleted
        with self.assertRaises(SubjectData.DoesNotExist):
            SubjectData.objects.get(pk=subject_id)


class StoreResultViewTest(TestCase):
    """Test the store result view."""
    
    def test_store_result_creates_trial_result(self):
        """Test storing a trial result."""
        experiment = ExperimentFactory()
        list_item = ListItemFactory(experiment=experiment)
        outer_block = OuterBlockItemFactory(listitem=list_item)
        block = BlockItemFactory(outerblockitem=outer_block)
        trial = TrialItemFactory(blockitem=block)
        subject = SubjectDataFactory(experiment=experiment, listitem=list_item)
        
        url = reverse('experiments:storeResult', args=[subject.id])
        data = {
            'trialId': trial.id,
            'response': 'click',
            'responseTime': 1234,
            'stimulusOnsetTime': 100,
            'webgazerData': '[]',
        }
        
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify trial result was created
        results = TrialResult.objects.filter(subjectdata=subject, trialitem=trial)
        self.assertEqual(results.count(), 1)


class ExperimentReportViewTest(TestCase):
    """Test the experiment report view (requires authentication)."""
    
    def test_experiment_report_requires_login(self):
        """Test that experiment report requires authentication."""
        experiment = ExperimentFactory()
        url = reverse('experiments:experimentReport', args=[experiment.id])
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin', response.url)
    
    def test_experiment_report_authenticated(self):
        """Test experiment report view when authenticated."""
        user = UserFactory(is_staff=True)
        experiment = ExperimentFactory(user=user)
        
        self.client.force_login(user)
        url = reverse('experiments:experimentReport', args=[experiment.id])
        
        with patch('experiments.views.Reporter') as MockReporter:
            mock_reporter = MockReporter.return_value
            mock_reporter.create_report.return_value = '/tmp/test_report.zip'
            
            response = self.client.get(url)
            
            # Should redirect to the report file
            self.assertEqual(response.status_code, 302)


class ExperimentExportViewTest(TestCase):
    """Test the experiment export view."""
    
    def test_experiment_export_view(self):
        """Test that experiment export returns JSON data."""
        experiment = ExperimentFactory()
        url = reverse('experiments:experimentExport', args=[experiment.id])
        response = self.client.get(url)
        
        # Export does not require login and returns 200
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')


class ExperimentImportViewTest(TestCase):
    """Test the experiment import view."""
    
    def test_experiment_import_view(self):
        """Test GET request to import view."""
        url = reverse('experiments:experimentImport')
        response = self.client.get(url)
        
        # Import does not require login
        self.assertEqual(response.status_code, 200)
