information_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Online Study{% endblock %} 

{% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Online Study</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body text-justify">
                    <p class="card-text">
                        Dear parents,<br /><br />

                        Welcome to the Online Study.<br /><br />

                        If you wish to participate in this study with your child, please carefully go through the following information about the study:<br />
                        - The aim of this study is to XXX.<br />
                        - To be eligible to participate in this study, your child must be XXX years old.<br />
                        - In order to evaluate this online study, we will require video recordings and these will be recorded using your computer's webcam. Thus, to participate, you must be using a computer or a laptop with a webcam and be ready to allow access to the webcam for recording. The videos are transmitted via a secure connection (TLS, 256-bit encryption) directly to the university's servers, where they are stored under the highest security standards. <br />
                        - During the study, your child needs to be seated so that they can be properly seen on the webcam recording. <br />
                        - Before starting, we will ask you a few questions and your personal data will be stored separately from the data and videos of the study. <br />
                        - The study is only compatible with Firefox and Google Chrome browsers. Please use one of these browsers. <br />
                        - You may withdraw from the study at any time without providing a reason. During the entire study, an “Exit” button will be visible at the bottom right corner of the screen. Click on this button if in any case you wish to terminate the study. <br />
                        - You may also request for your data to be deleted at any time. To do so, please send an email to XXX and state the exact name you entered in the participant form which will be presented next. <br /><br />
                        
                        If you agree to participate in this study, please click on “Next” below. Before we begin, we will ask you a few more questions and carry out some technical checks. <br /><br />
                        We look forward to your participation!

                    </p>
                    <form action="{% url 'experiments:browserCheck' experiment.id %}" method="post">
                        {% csrf_token %}
                        <div class="text-center">
                            <button type="submit" class="btn btn-primary" id="nextbutton">Next</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

browser_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Browser compatibility check{% endblock %}
{% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Browser compatibility check</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_1">
                <!-- h4 class="card-header">Step 1</h4-->
                <div class="card-body">
                    <!--h4 class="card-title">Browser compatibility check</h4-->
                    <p class="card-text">
                        We will now check the compatibility of your browser. The study is only compatible with Firefox and Google Chrome. If the test fails, please restart the study using one of these browsers.
                    </p>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        You are using a compatible browser. Please continue.
                    </div>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        You are using an incompatible browser. Please reopen the page in Google Chrome or Mozilla Firefox.
                    </div>
                    <form action="{% url 'experiments:consentForm' experiment.id %}" method="post">
                        {% csrf_token %}
                        <button type="submit" disabled="disabled" class="btn btn-primary" id="nextbutton">Next</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<script src="{% static 'experiments/js/browser-check.js' %}"></script>
{% endblock %}'''

introduction_page_content = '''{% extends "experiments/base.html" %} {% block title %}Consent form{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Consent form</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body">
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
                        <p><br><span class="asterix">* Required</span></p>
                        {% for field in consent_form %}
                        <div class="q-item" value="{{ forloop.counter }}">
                            <div class="field-wrapper question-required">
                                {{ field.errors }}
                                <label class="label-inline">{{ field.label }}<span class="asterix"> * </span></label>
                                <div class="form-field-body">
                                    {{ field }}
                                </div>
                            </div>
                        </div><br>
                        {% endfor %}
                        <button type="submit" class="btn btn-primary">Next</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

consent_fail_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Consent not granted{% endblock %} 

{% block content %}
<div class="container" id="consentFail">
    <div class="row">
        <div class="col text-center">
            <h1>Consent not granted</h1>
        </div>
    </div>
    <div class="row">
        <div class="col text-center ">
            <div class= "card-body alert alert-danger">
                <p class="card-text">
                        You did not agree to all points. Therefore, we are unable to proceed with the study.<br /><br />
                        If you really do not agree, please close your browser window.<br /><br />
                        If you wish to return to change your responses, please click "back".
                </p>
            </div>
            <form action="{% url 'experiments:consentForm' experiment.id %}" method="post">
            {% csrf_token %}        
                <button type="submit" class="btn btn-primary" id="resumebutton">Back</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}'''

demographic_data_page_content = '''{% extends "experiments/base.html" %} {% block title %}Participant form{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Participant form</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body">
                    {% if error_message %}
                    <div class="alert alert-danger" role="alert">
                        {{ error_message }}
                    </div>{% endif %}

                    <form id="subjectForm" action="{% url 'experiments:subjectFormSubmit' experiment.id %}" method="post" novalidate>
                        {% csrf_token %}
                        <p class="card-text">
                            Please fill out the fields below. You must fill out at least all fields marked with * in order to participate in the study.
                        </p>
                        <p><br><span class="asterix">* Required</span></p>
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
                        </div><br>
                        {% endif %}
                        {% endfor %}
                        <!-- reCAPTCHA input -->
                        <input type="hidden" id="g-recaptcha-response" name="g-recaptcha-response"> 
                        <button type="submit" class="btn btn-primary">Next</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<!-- reCAPTCHA API -->
<script src='https://www.google.com/recaptcha/api.js?render={{recaptcha_site_key}}'></script>
<script>
    // global grecaptcha
    grecaptcha.ready(function() {
        $('#subjectForm').submit(function(e){
            var form = this;
            e.preventDefault();
            grecaptcha.execute('{{recaptcha_site_key}}', {action: 'submit'}).then(function(token) {
                $('#g-recaptcha-response').val(token);
                form.submit();
            });
        });
    });
</script>
{% endblock %}'''

webcam_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Webcam and microphone setup{% endblock %} {% block content%}
<div class="container" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}">
    <div class="row">
        <div class="col text-center">
            <h1>Webcam and microphone setup</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_2">
                <div class="card-body">
                    <p class="card-text">
                        For this study it is necessary that you allow access to webcam and microphone.<br /><br />
                        In the next step, your browser will ask you for permission to activate the webcam and microphone. Please click on "Allow" to continue with the study.<br /><br />
                        If you are offered the option "always allow", please select this so that your browser saves the setting (only for our server). You can also only allow individual cases. Your browser will then ask for permission to activate the webcam and microphone several times in the next few steps.
                    </p>
                    <button type="button" class="btn btn-primary" disabled>Next</button>
                </div>
            </div>

            <div class="card" id="webcam_step_3">
                <div class="card-body">
                    <p class="card-text">
                        You will now see a window with the camera image below. Please adjust your camera so that your child is clearly visible.<br /><br />
                        We are about to make a short test recording (about 3 seconds) to test whether the video recording works. As soon as you click on "Start test recording", the test recording starts. Please say something out loud (e.g. "hello") after clicking so that you can check the audio recording.
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;"></div>
                    <div class="embed-responsive" style="display: none;">
                        <video controls class="embed-responsive-item"></video>
                    </div>
                    <button type="button" class="btn btn-primary" disabled>Start test recording</button>
                    <button type="button" class="btn btn-warning" id="repeat-check-button" style="display: none;">Repeat test recording</button>
                </div>
            </div>

            <div class="card" id="webcam_step_4">
                <div class="card-body">
                    <p class="card-text">
                        Below is the sample video. Please play this and assess whether you and your child are clearly visible and whether the sound was recorded.<br /><br />
                        Please make sure that the sound is activated on your computer.
                    </p>
                    <p class="card-text" id="upload-progress">
                        <img src="{% static 'experiments/img/loading.gif' %}" alt="Loading" title="Loading" />
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        The video upload failed.<br />
                    </div>
                    <div class="embed-responsive" style="display: none;">
                    </div>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        The video upload was successful. Please proceed with the study.
                    </div>

                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Next (Image and sound were recorded.)</button>
                    <button type="button" class="btn btn-warning" disabled data-toggle="modal" data-target="#repeatWebcamModal">Repeat test (There was a problem with the test recording.)</button>
                </div>
            </div>

        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" role="dialog" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Repeat test recording</h5>
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body">
                If you could not hear any sound or see any image: Please make sure that your webcam and speakers are on and connected to your computer. Please also check that the volume is not turned down too low.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="repeatRutton">Repeat test</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Exit</button>
<script>
    var webcam_not_found = `Unfortunately your webcam could not be detected.<br /><br />Please make sure a webcam is connected and click "Repeat test recording" to return to the webcam test.<br /><br />If you do not agree to allow access to your webcam and have therefore selected "do not allow", please close the browser window.`;
    var include_pause_page = "{{ experiment.include_pause_page }}";
    var recording_option = "{{ experiment.recording_option }}";
</script>
<script src="{% static 'experiments/js/webcam-calibration.js' %}"></script>
{% endblock %}'''

microphone_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Microphone setup{% endblock %} {% block content%}
<div class="container" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}">
    <div class="row">
        <div class="col text-center">
            <h1>Mirophone setup</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_2">
                <div class="card-body">
                    <p class="card-text">
                        For this study it is necessary that you allow access to your microphone.<br /><br />
                        In the next step, your browser will ask you for permission to activate the microphone. Please click on "Allow" to continue with the study. The test recording (about 3 seconds) begins right after you allow access to your microphone. Please say something out loud (e.g. "hello") so that you can check the audio recording. <br /><br />
                        If you are offered the option "always allow", please select this so that your browser saves the setting (only for our server). You can also only allow individual cases. Then your browser will ask for permission to activate the microphone several times in the next few steps.
                    </p>
                    <button type="button" class="btn btn-primary" disabled>Next</button>
                </div>
            </div>

            <div class="card" id="webcam_step_4">
                <div class="card-body">
                    <p class="card-text">
                        Below is the sample audio. Please play this and assess whether sound was recorded.<br /><br />
                        Please make sure that sound is activated on your computer.
                    </p>
                    <p class="card-text" id="upload-progress">
                        <img src="{% static 'experiments/img/loading.gif' %}" alt="Loading" title="Loading" />
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        The audio upload failed.<br />
                    </div>
                    <div class="embed-responsive" style="display: none;">
                    </div>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        The audio upload was successful, please continue.
                    </div>

                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Next (Sound was recorded.)</button>
                    <button type="button" class="btn btn-warning" disabled data-toggle="modal" data-target="#repeatWebcamModal">Repeat test recording (There was a problem with the test recording.)</button>
                </div>
            </div>

        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" role="dialog" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Repeat test recording</h5>
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body">
                If you could not hear any sound: Please make sure that your speakers are on and connected to your computer. Please also check that the volume is not turned down too low.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" id="repeatRutton">Repeat test recording</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Exit</button>
<script>
    var webcam_not_found = `Unfortunately your microphone could not be detected.<br /><br />Please make sure a microphone is connected and click "Repeat test recording" to return to the microphone test.<br /><br />If you do not agree to allow access to your microphone and have therefore selected "do not allow", please close the browser window.`;
    var include_pause_page = "{{ experiment.include_pause_page }}";
    var recording_option = "{{ experiment.recording_option }}";
</script>
<script src="{% static 'experiments/js/webcam-calibration.js' %}"></script>
{% endblock %}'''

experiment_page_content = '''{% extends "experiments/base.html" %} 
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

<div id="trials" style="display: none;" data-subject-uuid="{{ subject_data.id }}" data-subject-id="{{ subject_data.participant_id }}"></div>

<div id="exitStudyModal" class="modal fade" tabindex="-1" role="dialog" aria-labelledby="exitStudyModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 id="exitStudyModalLabel" class="modal-title">Terminate the study</h5>
                <button class="close" type="button" data-dismiss="modal" aria-label="Close"> <span aria-hidden="true">&times;</span> </button>
            </div>
            <div class="modal-body">
                Media recordings are still being uploaded. If you quit the study now, these recordings will be lost. Are you sure you want to quit?
            </div>
            <div class="modal-footer">
                <button id="confirmExitButton" class="btn btn-danger" type="button">Quit</button> 
                <button class="btn btn-primary" type="button" data-dismiss="modal">Return to study</button>
            </div>
        </div>
    </div>
</div>
<script>
    var trials = {{ trials|safe }}
    var loading_image = "{{ loading_image.url }}";
    var global_timeout = "{{ global_timeout }}";
    var include_pause_page = "{{ include_pause_page }}";
    var recording_option = "{{ recording_option }}";
    var general_onset = "{{ general_onset }}";
    var show_gaze_estimations = "{{ show_gaze_estimations }}";
</script>
 
<script src="{% static 'experiments/js/experiment.js' %}"></script>
<script src="{% static 'experiments/js/webgazer.min.js' %}"></script>
<script src="{% static 'experiments/js/webgazer-calibration.js' %}"></script>
{% endblock %}
'''

pause_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Pause{% endblock %} 

{% block content %}
<div class="container" id="pause">
    <div class="row">
        <div class="col text-center">
            <h1>Pause</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body text-center">
                    <p>
                        The study is paused and the recording stopped.<br /><br />
                        If you wish to terminate the study, please click "Exit study" below. <br /><br />
                        To continue, please click "Resume study". You will then be taken back to the point in the study where you paused.
                    </p>
                    <div id="side-by-side-left"> 
                        <form action="{% url 'experiments:webcamTest' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-primary" id="resumebutton">Resume study</button>
                        </form>
                    </div>
                    <div id="side-by-side-right"> 
                        <form action="{% url 'experiments:experimentEnd' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-danger" id="exitbutton">Exit study</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

thank_you_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Thank you{% endblock %} 

{% block content %}
<div class="container" id="thank-you">
    <div class="row">
        <div class="col text-center">
            <h1>Thank you</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="end_page_step_1">
                <div class="card-body text-center">
                    <p class="card-text">
                        You have reached the end of the study. Please click "Approve processing and use of data" to confirm your participation in the study. If you wish to withdraw from the study, please click "Remove all my data".<br /><br />
                    </p>
                    <div id="side-by-side-left"> 
                        <button type="button" class="btn btn-primary" id="approve-data-button">Approve processing and use of data</button>
                    </div>
                    <div id="side-by-side-right"> 
                        <form action="{% url 'experiments:deleteSubject' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-danger" id="delete-data-button">Remove all my data</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="card" id="end_page_approve">
                <div class="card-body text-center">
                    <p class="card-text">
                        Thank you for your participation!<br /><br />
                        You may now close your browser window.
                    </p>
                </div>
            </div>
            <div class="card" id="end_page_disapprove">
                <div class="card-body text-center">
                    <p class="card-text">
                        All of your data has been deleted.<br /><br />
                        You may now close your browser window.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="{% static 'experiments/js/endpage.js' %}"></script>
{% endblock %}'''

thank_you_abort_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Study incomplete{% endblock %} 

{% block content %}
<div class="container" id="thank-you">
    <div class="row">
        <div class="col text-center">
            <h1>Study incomplete</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="end_page_step_1">
                <div class="card-body text-center">
                    <p class="card-text">
                        It is a pity that you aborted the study. The recording has ended. You may now close the browser window.<br /><br />
                        We would like to know why you aborted the study. If you wish to tell us about this, please send an email to XXX.
                    </p>
                    <div id="side-by-side-left"> 
                        <button type="button" class="btn btn-primary" id="approve-data-button">Approve processing and use of data</button>
                    </div>
                    <div id="side-by-side-right"> 
                        <form action="{% url 'experiments:deleteSubject' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-danger" id="delete-data-button">Remove all my data</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="card" id="end_page_approve">
                <div class="card-body text-center">
                    <p class="card-text">
                        Thank you for your participation!<br /><br />
                        You may now close your browser window.
                    </p>
                </div>
            </div>
            <div class="card" id="end_page_disapprove">
                <div class="card-body text-center">
                    <p class="card-text">
                        All of your data has been deleted.<br /><br />
                        You may now close your browser window.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="{% static 'experiments/js/endpage.js' %}"></script>
{% endblock %}'''

error_page_content = '''{% extends "experiments/base.html" %} {% block title %}Error{% endblock %} {% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Error</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body text-justify">
                    <p class="card-text">
                        An error has occurred. The study has now terminated.
                    </p>
                    <div class="alert alert-danger" role="alert">
                        Error message
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

cdi_page_content = '''{% extends "experiments/base.html" %} {% block title %}Vocabulary checklist{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Vocabulary checklist</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body">
                    {% if error_message %}
                    <div class="alert alert-danger" role="alert">
                        {{ error_message }}
                    </div>
                    {% endif %}

                    <form id="cdiForm" action="{% url 'experiments:vocabChecklistSubmit' subject_data.id %}" method="post" novalidate>
                        {% csrf_token %}
                        <p class="card-text">
                            Please mark the box if your child understands the word. If your child uses another word with the same meaning (e.g., nana for grandma), mark it anyway. </br></br>
                        </p>
                        {{ cdi_form.non_field_errors }}
                        {% for field in cdi_form %}
                        {% if field.name == 'experiment' %}
                            {{ field }}
                        {% else %}
                        <div class="word-item" value="{{ forloop.counter }}">
                            <div class="field-wrapper">
                                {{ field.errors }}
                                {{ field }} &emsp; <label class="label-inline">{{ field.label }}</label>
                                    
                                <small class="form-text text-muted">{{ field.help_text }}</small>
                            </div>
                        </div>
                        <br>
                        {% endif %}
                        {% endfor %}
                        <button type="submit" class="btn btn-primary">Submit</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    $(document).ready(function() {
        $("#cdiForm").on('submit', function() {
            // to each unchecked checkbox
            $('input:checkbox:not(:checked)').each(function () {
                // add hidden checkbox to be posted
                $("#cdiForm").append("<input type='hidden' name='" + this.name + "' value='0' />");
            });
        })
    })
</script>
{% endblock %}'''