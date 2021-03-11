from django.conf.urls import re_path
from django.contrib import admin

from . import views, webcam

app_name = 'experiments'

urlpatterns = [
    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/information/$', views.informationPage, name='informationPage'),
    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/browsercheck/$', views.browserCheck, name='browserCheck'),
    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/$', views.consentForm, name='consentForm'),
    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/submit$', views.consentFormSubmit, name='consentFormSubmit'),

    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/form/$', views.subjectForm, name='subjectForm'),
    re_path(r'^(?P<experiment_id>[0-9A-Fa-f-]+)/form/submit$', views.subjectFormSubmit, name='subjectFormSubmit'),

    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/test$', webcam.webcam_test, name='webcamTest'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/webcamtest/upload$', webcam.webcam_test_upload, name='webcamUpload'),

    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run$', views.experimentRun, name='experimentRun'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/upload$', webcam.webcam_upload, name='experimentWebcamUpload'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/storeresult$', views.storeResult, name='storeResult'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/pause$', views.experimentPause, name='experimentPause'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/thankyou$', views.experimentEnd, name='experimentEnd'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/deletesubject$', views.deleteSubject, name='deleteSubject'),
    re_path(r'^(?P<run_uuid>[0-9A-Fa-f-]+)/run/error$', views.experimentError, name='experimentError'),

    re_path(r'^$', views.index, name='index'),

    re_path(r'^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/report$', views.experimentReport, name='experimentReport'),
    re_path(r'^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/export$', views.experimentExport, name='experimentExport'),
    re_path(r'^admin/experiments/import$', views.experimentImport, name='experimentImport'),

    re_path('^accounts/', admin.site.urls),
]
