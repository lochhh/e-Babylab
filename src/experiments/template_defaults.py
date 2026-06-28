"""Default HTML content for experiment pages."""

information_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Online Study{% endblock %}
{% block content %}
<div class="container py-5" id="information">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Online Study</h1>
            <p class="card-text">
                Dear parents,<br /><br />

                Welcome to the Online Study.<br /><br />

                If you wish to participate in this study with your child, please carefully go through the following information about the study:<br />
                - The aim of this study is to XXX.<br />
                - To be eligible to participate in this study, your child must be XXX years old.<br />
                - In order to evaluate this online study, we will require video recordings and these will be recorded using your computer's webcam. Thus, to participate, you must be using a computer or a laptop with a webcam and be ready to allow access to the webcam for recording. The videos are transmitted via a secure, encrypted connection (HTTPS/TLS) directly to the university's servers, where they are stored under the highest security standards. <br />
                - During the study, your child needs to be seated so that they can be properly seen on the webcam recording. <br />
                - Before starting, we will ask you a few questions and your personal data will be stored separately from the data and videos of the study. <br />
                - The study is only compatible with Firefox and Google Chrome browsers. Please use one of these browsers. <br />
                - You may withdraw from the study at any time without providing a reason. During the entire study, an "Exit" button will be visible at the bottom right corner of the screen. Click on this button if in any case you wish to terminate the study. <br />
                - You may also request for your data to be deleted at any time. To do so, please send an email to XXX and state the exact name you entered in the participant form which will be presented next. <br /><br />

                If you agree to participate in this study, please click on "Next" below. Before we begin, we will ask you a few more questions and carry out some technical checks. <br /><br />
                We look forward to your participation!
            </p>
            <form action="{% url 'experiments:browserCheck' experiment.id %}" method="post" class="mt-4">
                {% csrf_token %}
                <button type="submit" class="btn btn-primary" id="nextbutton">Next</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""

browser_check_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Browser compatibility check{% endblock %}
{% block content %}
<div class="container py-5" id="information">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7" id="webcam_step_1">
            <h1>Browser compatibility check</h1>
            <p class="card-text">
                We will now check the compatibility of your browser. The study is only compatible with Firefox and Google Chrome. If the test fails, please restart the study using one of these browsers.
            </p>
            <div class="alert alert-success mt-3" role="alert" style="display: none;">
                You are using a compatible browser. Please continue.
            </div>
            <div class="alert alert-danger mt-3" role="alert" style="display: none;">
                You are using an incompatible browser. Please reopen the page in Google Chrome or Mozilla Firefox.
            </div>
            <form action="{% url 'experiments:consentForm' experiment.id %}" method="post" class="mt-4">
                {% csrf_token %}
                <button type="submit" disabled="disabled" class="btn btn-primary" id="nextbutton">Next</button>
            </form>
        </div>
    </div>
</div>
<script type="module" src="{% static 'experiments/js/browser-check.js' %}"></script>
{% endblock %}"""

introduction_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Consent form{% endblock %}
{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Consent form</h1>
            {% if error_message %}
            <div class="alert alert-danger" role="alert">
                {{ error_message }}
            </div>
            {% endif %}
            <form action="{% url 'experiments:consentFormSubmit' experiment.id %}" method="post" novalidate>
                {% csrf_token %}
                <p class="card-text">
                    Please read the following points carefully and indicate whether you agree to them.<br /><br />
                    Participation in the study is only possible if you agree to each of the following points.
                </p>
                <p class="mt-3"><span class="asterix">* Required</span></p>
                {% for field in consent_form %}
                <div class="q-item" value="{{ forloop.counter }}">
                    <div class="field-wrapper question-required">
                        {{ field.errors }}
                        <label class="label-inline">{{ field.label }}<span class="asterix"> * </span></label>
                        <div class="form-field-body">
                            {{ field }}
                        </div>
                    </div>
                </div>
                {% endfor %}
                <div class="mt-4">
                    <button type="submit" class="btn btn-primary">Next</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""

consent_fail_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Consent not granted{% endblock %}
{% block content %}
<div class="container py-5" id="consentFail">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Consent not granted</h1>
            <div class="alert alert-danger" role="alert">
                <p class="mb-2">You did not agree to all points. Therefore, we are unable to proceed with the study.</p>
                <p class="mb-2">If you really do not agree, please close your browser window.</p>
                <p class="mb-0">If you wish to return to change your responses, please click "Back".</p>
            </div>
            <div class="mt-4">
                <form action="{% url 'experiments:consentForm' experiment.id %}" method="post">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-primary" id="resumebutton">Back</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

demographic_data_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Participant form{% endblock %}
{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Participant form</h1>
            {% if error_message %}
            <div class="alert alert-danger" role="alert">
                {{ error_message }}
            </div>
            {% endif %}
            <form id="subjectForm" action="{% url 'experiments:subjectFormSubmit' experiment.id %}" method="post" novalidate {{captcha_form_attrs}}>
                {% csrf_token %}
                <p class="card-text">
                    Please fill out the fields below. You must fill out at least all fields marked with * in order to participate in the study.
                </p>
                <p class="mt-3"><span class="asterix">* Required</span></p>
                {% for field in subject_data_form %}
                {% if field.name == 'resolution_w' or field.name == 'resolution_h' %}
                    {{ field }}
                {% else %}
                <div class="q-item" value="{{ forloop.counter }}">
                    {% if field.field.required %}
                    <div class="field-wrapper question-required">
                        {{ field.errors }}
                        <label class="label-inline">{{ field.label }} <span class="asterix">*</span></label>
                    {% else %}
                    <div class="field-wrapper">
                        {{ field.errors }}
                        <label class="label-inline">{{ field.label }}</label>
                    {% endif %}
                        <div class="form-field-body">
                            {{ field }}
                        </div>
                        <small class="form-text text-muted">{{ field.help_text }}</small>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
                {{captcha_widget}}
                <div class="mt-4">
                    <button type="submit" class="btn btn-primary">Next</button>
                </div>
            </form>
        </div>
    </div>
</div>
{{captcha_scripts}}
<script type="module" src="{% static 'experiments/js/resolution.js' %}"></script>
{% endblock %}"""

webcam_check_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Webcam and microphone setup{% endblock %}
{% block content%}
<div class="container py-5" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}" data-include-pause-page="{{ experiment.include_pause_page|lower }}" data-recording-option="{{ experiment.recording_option }}" data-webcam-not-found='Unfortunately your webcam could not be detected.<br /><br />Please make sure a webcam is connected and click "Repeat test recording" to return to the webcam test.<br /><br />If you do not agree to allow access to your webcam and have therefore selected "do not allow", please close the browser window.'>
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <div class="webcam-step active" id="webcam_step_2">
                <h1>Webcam and microphone setup</h1>
                <p class="card-text">
                    For this study it is necessary that you allow access to webcam and microphone.<br /><br />
                    In the next step, your browser will ask you for permission to activate the webcam and microphone. Please click on "Allow" to continue with the study.<br /><br />
                    If you are offered the option "always allow", please select this so that your browser saves the setting (only for our server). You can also only allow individual cases. Your browser will then ask for permission to activate the webcam and microphone several times in the next few steps.
                </p>
                <div class="mt-4">
                    <button type="button" class="btn btn-primary" disabled>Next</button>
                </div>
            </div>

            <div class="webcam-step" id="webcam_step_3">
                <h1>Webcam and microphone setup</h1>
                <p class="card-text">
                    You will now see a window with the camera image below. Please adjust your camera so that your child is clearly visible.<br /><br />
                    We are about to make a short test recording (about 3 seconds) to test whether the video recording works. As soon as you click on "Start test recording", the test recording starts. Please say something out loud (e.g. "hello") after clicking so that you can check the audio recording.
                </p>
                <div class="alert alert-danger mt-3" role="alert" style="display: none;"> </div>
                <div class="media-container ratio ratio-4x3 mt-3" style="display: none;">
                    <video controls></video>
                </div>
                <div class="d-flex gap-2 flex-wrap align-items-start mt-4">
                    <button type="button" class="btn btn-primary" disabled>Start test recording</button>
                    <button type="button" class="btn btn-warning" id="repeat-check-button" style="display: none;">Repeat test recording</button>
                </div>
            </div>

            <div class="webcam-step" id="webcam_step_4">
                <h1>Webcam and microphone setup</h1>
                <p class="card-text">
                    Below is the sample video. Please play this and assess whether you and your child are clearly visible and whether the sound was recorded.<br /><br />
                    Please make sure that the sound is activated on your computer.
                </p>
                <p class="card-text" id="upload-progress">
                    <img src="{% static 'experiments/img/loading.gif' %}" alt="Loading" title="Loading" />
                </p>
                <div class="alert alert-danger mt-3" role="alert" style="display: none;">
                    The video upload failed.<br />
                </div>
                <div class="media-container ratio ratio-4x3 mt-3" style="display: none;">
                </div>
                <div class="alert alert-success mt-3" role="alert" style="display: none;">
                    The video upload was successful. Please proceed with the study.
                </div>
                <div class="d-flex gap-2 flex-wrap align-items-start mt-4">
                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Next (Image and sound were recorded.)</button>
                    <button type="button" class="btn btn-warning" disabled data-bs-toggle="modal" data-bs-target="#repeatWebcamModal">Repeat test (There was a problem with the test recording.)</button>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Repeat test recording</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                If you could not hear any sound or see any image: Please make sure that your webcam and speakers are on and connected to your computer. Please also check that the volume is not turned down too low.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="repeatButton">Repeat test</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Exit</button>
<script type="module" src="{% static 'experiments/js/webcam-calibration.js' %}"></script>
{% endblock %}"""

microphone_check_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Microphone setup{% endblock %}
{% block content%}
<div class="container py-5" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}" data-include-pause-page="{{ experiment.include_pause_page|lower }}" data-recording-option="{{ experiment.recording_option }}" data-webcam-not-found='Unfortunately your microphone could not be detected.<br /><br />Please make sure a microphone is connected and click "Repeat test recording" to return to the microphone test.<br /><br />If you do not agree to allow access to your microphone and have therefore selected "do not allow", please close the browser window.'>
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <div class="webcam-step active" id="webcam_step_2">
                <h1>Microphone setup</h1>
                <p class="card-text">
                    For this study it is necessary that you allow access to your microphone.<br /><br />
                    In the next step, your browser will ask you for permission to activate the microphone. Please click on "Allow" to continue with the study. The test recording (about 3 seconds) begins right after you allow access to your microphone. Please say something out loud (e.g. "hello") so that you can check the audio recording. <br /><br />
                    If you are offered the option "always allow", please select this so that your browser saves the setting (only for our server). You can also only allow individual cases. Then your browser will ask for permission to activate the microphone several times in the next few steps.
                </p>
                <div class="mt-4">
                    <button type="button" class="btn btn-primary" disabled>Next</button>
                </div>
            </div>

            <div class="webcam-step" id="webcam_step_4">
                <h1>Microphone setup</h1>
                <p class="card-text">
                    Below is the sample audio. Please play this and assess whether sound was recorded.<br /><br />
                    Please make sure that sound is activated on your computer.
                </p>
                <p class="card-text" id="upload-progress">
                    <img src="{% static 'experiments/img/loading.gif' %}" alt="Loading" title="Loading" />
                </p>
                <div class="alert alert-danger mt-3" role="alert" style="display: none;">
                    The audio upload failed.<br />
                </div>
                <div class="media-container mt-3" style="display: none;">
                </div>
                <div class="alert alert-success mt-3" role="alert" style="display: none;">
                    The audio upload was successful, please continue.
                </div>
                <div class="d-flex gap-2 flex-wrap align-items-start mt-4">
                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Next (Sound was recorded.)</button>
                    <button type="button" class="btn btn-warning" disabled data-bs-toggle="modal" data-bs-target="#repeatWebcamModal">Repeat test recording (There was a problem with the test recording.)</button>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Repeat test recording</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                If you could not hear any sound: Please make sure that your speakers are on and connected to your computer. Please also check that the volume is not turned down too low.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="repeatButton">Repeat test recording</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Exit</button>
<script type="module" src="{% static 'experiments/js/webcam-calibration.js' %}"></script>
{% endblock %}"""

experiment_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Experiment{% endblock %}
{% block content %}
<div class="container h-100 text-center" id="fullscreen-message">
    <div class="row h-100 justify-content-center align-items-center">
        <div class="col">
            <p class="card-text">
                Almost set!<br /><br />
                Before the study starts, we would like to record a short statement from you. Please read the text on the next page aloud with your child on your lap. <br /><br />
                This repeated declaration is important to us because we really want to make sure that you have understood the framework conditions and agree with them. If we do not have this recording, we will delete your data and videos. <br /><br />
                After the declaration, the study starts immediately. Please follow the instructions on the screen. <br />
                The study is presented in full screen. If you want to exit or interrupt the study at any time, please click on "Exit" at the bottom right. <br /><br />
                To proceed, please click "Activate full screen"
            </p>
            <button id="fullscreen-button" type="button" class="btn btn-primary" disabled>Activate full screen</button>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Exit</button>
<canvas id="plotting_canvas" style="display: none;" width="500" height="500"></canvas>
<div class="container h-100 text-center" id="webgazer-init">
    <div class="row h-100 justify-content-center align-items-center">
        <div class="col">
            <br /><br />
            <p class="card-text">
                Please position the head of your child in a way that makes its eyes clearly visible to the webcam. <br />
                The head should also be positioned in the middle of the rectangle presented.<br />
                As the experiment works best with a steady head, make sure that your child has a comfortable seating position.<br />
                As soon as the face is centered and the rectangle turns green, you can press the "Start" button to begin. <br />
            </p>
            <button type="button" class="btn btn-primary" disabled>Start</button>
        </div>
    </div>
</div>

<div id="trials-data" style="display: none;">{{ trials }}</div>
<div id="trials" style="display: none;" data-subject-uuid="{{ subject_data.id }}" data-subject-id="{{ subject_data.participant_id }}" data-loading-image="{{ loading_image.url }}" data-global-timeout="{{ global_timeout }}" data-include-pause-page="{{ include_pause_page|lower }}" data-recording-option="{{ recording_option }}" data-general-onset="{{ general_onset }}" data-show-gaze-estimations="{{ show_gaze_estimations|lower }}"></div>

<div id="exitStudyModal" class="modal fade" tabindex="-1" aria-labelledby="exitStudyModalLabel">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 id="exitStudyModalLabel" class="modal-title">Terminate the study</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                Media recordings are still being uploaded. If you quit the study now, these recordings will be lost. Are you sure you want to quit?
            </div>
            <div class="modal-footer">
                <button id="confirmExitButton" class="btn btn-danger" type="button">Quit</button>
                <button class="btn btn-primary" type="button" data-bs-dismiss="modal">Return to study</button>
            </div>
        </div>
    </div>
</div>
<script src="{% static 'experiments/js/webgazer.min.js' %}"></script>
<script type="module" src="{% static 'experiments/js/experiment.js' %}"></script>
{% endblock %}
"""

pause_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Pause{% endblock %}
{% block content %}
<div class="container py-5" id="pause">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Pause</h1>
            <p class="card-text">
                The study is paused and the recording stopped.<br /><br />
                If you wish to terminate the study, please click "Exit study" below.<br /><br />
                To continue, please click "Resume study". You will then be taken back to the point in the study where you paused.
            </p>
            <div class="d-flex gap-3 mt-4">
                <form action="{% url 'experiments:webcamTest' subject_id %}" method="post">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-primary" id="resumebutton">Resume study</button>
                </form>
                <form action="{% url 'experiments:experimentEnd' subject_id %}" method="post">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-danger" id="exitbutton">Exit study</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

thank_you_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Thank you{% endblock %}
{% block content %}
<div class="container py-5" id="thank-you">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <div id="end_page_step_1">
                <h1>Thank you</h1>
                <p class="card-text">
                    You have reached the end of the study. Please click "Approve processing and use of data" to confirm your participation in the study. If you wish to withdraw from the study, please click "Remove all my data".
                </p>
                <form action="{% url 'experiments:deleteSubject' subject_id %}" method="post">
                    {% csrf_token %}
                    <div class="d-flex gap-3 mt-4">
                        <button type="button" class="btn btn-primary" id="approve-data-button">Approve processing and use of data</button>
                        <button type="submit" class="btn btn-danger" id="delete-data-button">Remove all my data</button>
                    </div>
                </form>
            </div>
            <div id="end_page_approve" style="display:none">
                <h1>Thank you</h1>
                <p class="card-text">
                    Thank you for your participation!<br /><br />
                    You may now close your browser window.
                </p>
            </div>
            <div id="end_page_disapprove" style="display:none">
                <h1>Data removed</h1>
                <p class="card-text">
                    All of your data has been deleted.<br /><br />
                    You may now close your browser window.
                </p>
            </div>
        </div>
    </div>
</div>
<script type="module" src="{% static 'experiments/js/endpage.js' %}"></script>
{% endblock %}"""

thank_you_abort_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Study incomplete{% endblock %}
{% block content %}
<div class="container py-5" id="thank-you">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <div id="end_page_step_1">
                <h1>Study incomplete</h1>
                <p class="card-text">
                    It is a pity that you aborted the study. The recording has ended. You may now close the browser window.<br /><br />
                    We would like to know why you aborted the study. If you wish to tell us about this, please send an email to XXX.
                </p>
                <form action="{% url 'experiments:deleteSubject' subject_id %}" method="post">
                    {% csrf_token %}
                    <div class="d-flex gap-3 mt-4">
                        <button type="button" class="btn btn-primary" id="approve-data-button">Approve processing and use of data</button>
                        <button type="submit" class="btn btn-danger" id="delete-data-button">Remove all my data</button>
                    </div>
                </form>
            </div>
            <div id="end_page_approve" style="display:none">
                <h1>Thank you</h1>
                <p class="card-text">
                    Thank you for your participation!<br /><br />
                    You may now close your browser window.
                </p>
            </div>
            <div id="end_page_disapprove" style="display:none">
                <h1>Data removed</h1>
                <p class="card-text">
                    All of your data has been deleted.<br /><br />
                    You may now close your browser window.
                </p>
            </div>
        </div>
    </div>
</div>
<script type="module" src="{% static 'experiments/js/endpage.js' %}"></script>
{% endblock %}"""

error_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Error{% endblock %}
{% block content %}
<div class="container py-5" id="information">
    <div class="row justify-content-center">
        <div class="col-12 col-md-9 col-lg-7">
            <h1>Error</h1>
            <p class="card-text">An error has occurred. The study has now terminated.</p>
            <div class="alert alert-danger mt-3" role="alert">
                Error message
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

cdi_page_content = """{% extends "experiments/base.html" %}
{% load static %}
{% block title %}Vocabulary checklist{% endblock %}
{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-12 col-md-10">
            <h1>Vocabulary checklist</h1>
            {% if error_message %}
            <div class="alert alert-danger" role="alert">
                {{ error_message }}
            </div>
            {% endif %}
            <form id="cdiForm" action="{% url 'experiments:vocabChecklistSubmit' subject_data.id %}" method="post" novalidate>
                {% csrf_token %}
                <p class="card-text">
                    Please mark the box if your child understands the word. If your child uses another word with the same meaning (e.g., nana for grandma), mark it anyway.
                </p>
                {{ cdi_form.non_field_errors }}
                {% for field in cdi_form %}
                {% if field.name == 'experiment' %}
                    {{ field }}
                {% else %}
                <div class="word-item" value="{{ forloop.counter }}">
                    <div class="field-wrapper">
                        {{ field.errors }}
                        {{ field }} <label for="{{ field.id_for_label }}">{{ field.label }}</label>
                        <small class="form-text text-muted">{{ field.help_text }}</small>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
                <div class="mt-4">
                    <button type="submit" class="btn btn-primary">Submit</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""
