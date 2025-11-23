"""
Tests for experiments app URL configuration.

This module tests:
- URL reverse lookup
- Correct view mapping
- URL pattern matching
"""
from django.test import TestCase
from django.urls import reverse, resolve
from experiments import views, webcam, cdi
from tests.helpers import ExperimentFactory, SubjectDataFactory
import uuid


class URLPatternsTest(TestCase):
    """Test URL patterns and reverse resolution."""
    
    def test_index_url(self):
        """Test the index URL resolves correctly."""
        url = reverse('experiments:index')
        self.assertEqual(url, '/experiments/')
        self.assertEqual(resolve(url).func, views.index)
    
    def test_information_page_url(self):
        """Test the information page URL with experiment ID."""
        experiment = ExperimentFactory()
        url = reverse('experiments:informationPage', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertEqual(resolve(url).func, views.informationPage)
    
    def test_browser_check_url(self):
        """Test the browser check URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:browserCheck', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertEqual(resolve(url).func, views.browserCheck)
    
    def test_consent_form_url(self):
        """Test the consent form URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:consentForm', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertEqual(resolve(url).func, views.consentForm)
    
    def test_consent_form_submit_url(self):
        """Test the consent form submit URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:consentFormSubmit', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertIn('/submit', url)
        self.assertEqual(resolve(url).func, views.consentFormSubmit)
    
    def test_subject_form_url(self):
        """Test the subject form URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:subjectForm', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertEqual(resolve(url).func, views.subjectForm)
    
    def test_subject_form_submit_url(self):
        """Test the subject form submit URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:subjectFormSubmit', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertEqual(resolve(url).func, views.subjectFormSubmit)
    
    def test_vocab_checklist_url(self):
        """Test the vocabulary checklist URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:vocabChecklist', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/vocab', url)
        self.assertEqual(resolve(url).func, cdi.cdiRun)
    
    def test_vocab_checklist_submit_url(self):
        """Test the vocabulary checklist submit URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:vocabChecklistSubmit', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertEqual(resolve(url).func, cdi.cdiSubmit)
    
    def test_webcam_test_url(self):
        """Test the webcam test URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:webcamTest', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertEqual(resolve(url).func, webcam.webcam_test)
    
    def test_webcam_upload_url(self):
        """Test the webcam upload URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:webcamUpload', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertEqual(resolve(url).func, webcam.webcam_test_upload)
    
    def test_experiment_run_url(self):
        """Test the experiment run URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:experimentRun', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/run', url)
        self.assertEqual(resolve(url).func, views.experimentRun)
    
    def test_experiment_webcam_upload_url(self):
        """Test the experiment webcam upload URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:experimentWebcamUpload', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertEqual(resolve(url).func, webcam.webcam_upload)
    
    def test_store_result_url(self):
        """Test the store result URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:storeResult', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/storeresult', url)
        self.assertEqual(resolve(url).func, views.storeResult)
    
    def test_experiment_pause_url(self):
        """Test the experiment pause URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:experimentPause', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/pause', url)
        self.assertEqual(resolve(url).func, views.experimentPause)
    
    def test_experiment_end_url(self):
        """Test the experiment end URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:experimentEnd', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/thankyou', url)
        self.assertEqual(resolve(url).func, views.experimentEnd)
    
    def test_delete_subject_url(self):
        """Test the delete subject URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:deleteSubject', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/deletesubject', url)
        self.assertEqual(resolve(url).func, views.deleteSubject)
    
    def test_experiment_error_url(self):
        """Test the experiment error URL."""
        run_uuid = uuid.uuid4()
        url = reverse('experiments:experimentError', args=[run_uuid])
        self.assertIn(str(run_uuid), url)
        self.assertIn('/error', url)
        self.assertEqual(resolve(url).func, views.experimentError)
    
    def test_experiment_report_url(self):
        """Test the experiment report URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:experimentReport', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertIn('/report', url)
        self.assertEqual(resolve(url).func, views.experimentReport)
    
    def test_experiment_export_url(self):
        """Test the experiment export URL."""
        experiment = ExperimentFactory()
        url = reverse('experiments:experimentExport', args=[experiment.id])
        self.assertIn(str(experiment.id), url)
        self.assertIn('/export', url)
        self.assertEqual(resolve(url).func, views.experimentExport)
    
    def test_experiment_import_url(self):
        """Test the experiment import URL."""
        url = reverse('experiments:experimentImport')
        self.assertIn('/import', url)
        self.assertEqual(resolve(url).func, views.experimentImport)
