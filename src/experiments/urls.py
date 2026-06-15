"""URL routing for the experiments application."""

from django.contrib import admin
from django.urls import re_path

from . import cdi, views, webcam
from .captcha import altcha_challenge_view

app_name = "experiments"

urlpatterns = [
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/information/$",
        views.information_page,
        name="informationPage",
    ),
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/browsercheck/$",
        views.browser_check,
        name="browserCheck",
    ),
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/$",
        views.consent_form,
        name="consentForm",
    ),
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/consentform/submit$",
        views.consent_form_submit,
        name="consentFormSubmit",
    ),
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/form/$",
        views.subject_form,
        name="subjectForm",
    ),
    re_path(
        r"^(?P<experiment_id>[0-9A-Fa-f-]+)/form/submit$",
        views.subject_form_submit,
        name="subjectFormSubmit",
    ),
    re_path(r"^(?P<run_uuid>[0-9A-Fa-f-]+)/vocab$", cdi.cdi_run, name="vocabChecklist"),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/vocab/submit$",
        cdi.cdi_submit,
        name="vocabChecklistSubmit",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/test$", webcam.webcam_test, name="webcamTest"
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/webcamtest/upload$",
        webcam.webcam_test_upload,
        name="webcamUpload",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run$", views.experiment_run, name="experimentRun"
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/upload$",
        webcam.webcam_upload,
        name="experimentWebcamUpload",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/storeresult$",
        views.store_result,
        name="storeResult",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/nexttrial$",
        views.next_trial,
        name="nextTrial",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/pause$",
        views.experiment_pause,
        name="experimentPause",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/thankyou$",
        views.experiment_end,
        name="experimentEnd",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/deletesubject$",
        views.delete_subject,
        name="deleteSubject",
    ),
    re_path(
        r"^(?P<run_uuid>[0-9A-Fa-f-]+)/run/error$",
        views.experiment_error,
        name="experimentError",
    ),
    re_path(r"^captcha/challenge$", altcha_challenge_view, name="captchaChallenge"),
    re_path(r"^$", views.index, name="index"),
    re_path(
        r"^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/report$",
        views.experiment_report,
        name="experimentReport",
    ),
    re_path(
        r"^admin/experiments/experiment/(?P<experiment_id>[0-9A-Fa-f-]+)/export$",
        views.experiment_export,
        name="experimentExport",
    ),
    re_path(
        r"^admin/experiments/import$", views.experiment_import, name="experimentImport"
    ),
    re_path("^accounts/", admin.site.urls),
]
