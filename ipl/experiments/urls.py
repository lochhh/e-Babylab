from django.conf.urls import url
from django.contrib import admin
from . import views, webcam

app_name = 'experiments'

urlpatterns = [
    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/information/$', views.informationPage, name='informationPage'),
    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/browsercheck/$', views.browserCheck, name='browserCheck'),
    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/$', views.consentForm, name='consentForm'),
    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/submit$', views.consentFormSubmit, name='consentFormSubmit'),

    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/form/$', views.subjectForm, name='subjectForm'),
    url(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/form/submit$', views.subjectFormSubmit, name='subjectFormSubmit'),

    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/test$', webcam.webcam_test, name='webcamTest'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/webcamtest/upload$', webcam.webcam_test_upload, name='webcamUpload'),

    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run$', views.experimentRun, name='experimentRun'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/upload$', webcam.webcam_upload, name='experimentWebcamUpload'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/storeresult$', views.storeResult, name='storeResult'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/pause$', views.experimentPause, name='experimentPause'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/thankyou$', views.experimentEnd, name='experimentEnd'),
    url(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/error$', views.experimentError, name='experimentError'),

    url(r'^$', views.index, name='index'),

    url(r'^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/report$', views.experimentReport, name='experimentReport'),
    url(r'^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/export$', views.experimentExport, name='experimentExport'),
    url(r'^admin/experiments/import$', views.experimentImport, name='experimentImport'),

    url('^accounts/', admin.site.urls),
]
