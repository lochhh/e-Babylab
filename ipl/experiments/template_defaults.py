information_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Online-Studie der Kindsköpfe Göttingen{% endblock %} 

{% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Online-Studie der Kindsköpfe Göttingen</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body text-justify">
                    <p class="card-text">
                        Liebe Eltern,<br /><br />

                        herzlich Willkommen zu dieser Studie der Kindsköpfe Göttingen.<br /><br />

                        Wenn Sie zusammen mit Ihrem Kind teilnehmen möchten, lesen Sie bitte die folgenden Informationen aufmerksam durch:<br />
                        - In dieser Studie untersuchen wir XXX<br />
                        - Für die Teilnahme muss Ihr Kind XXX alt sein.<br />
                        - Um diese Online-Studie auswerten zu können, benötigen wir Video-Mitschnitte. Dafür möchten wir die Webcam Ihres Computers nutzen. Für die Teilnahme müssen Sie a einem Computer oder Laptop mit Webcam sein und dazu bereit sein, diese zur Aufnahme freizugeben. Die Videos werden über eine sichere Verbindung (TLS-Verschlüsselung, 256 Bit) direkt auf die Server der Universität Göttingen übertragen, wo sie unter höchsten Sicherheitsstandards gespeichert werden.<br /> 
                        - Für die Aufnahme muss Ihr Kind auf Ihrem Schoß sitzen und die Webcam muss so ausgerichtet sein, dass Ihr Kind sichtbar ist. <br />
                        - Wir werden Ihnen vorab ein paar Fragen stellen. Sie Speicherung Ihrer persönlichen Daten erfolgt separat von den Daten und Videos der Studie.<br />
                        - Die Studie ist nur mit den Browsern Firefox und Google Chrome kompatibel. Bitte nutzen Sie einen dieser Browser. <br />
                        - Sie können die Studie jederzeit ohne Begründung abbrechen. Während der gesamten Erhebung wird rechts unten im Bild ein Feld „Abbrechen“ sichtbar sein. Klicken Sie dieses an, falls Sie die Studie vorzeitig abbrechen möchten.<br />
                        - Sie können jederzeit die Löschung Ihrer Daten veranlassen. Schreiben Sie dazu eine Email an XXX und nennen Sie den genauen Namen, den Sie ins Namensfeld eingegeben haben.<br /><br />

                        Wenn Sie einverstanden sind, klicken Sie bitte unten auf „Weiter“. Bevor es losgeht werden wir Ihnen noch einige Fragen stellen und einige technische Checks durchführen.<br /><br />

                        Wir freuen uns über Ihre Teilnahme!
                    </p>
                    <form action="{% url 'experiments:browserCheck' experiment.id %}" method="post">
                        {% csrf_token %}
                        <div class="text-center">
                            <button type="submit" class="btn btn-primary" id="nextbutton">Weiter</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

browser_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Prüfe Kompatibilität des Browsers{% endblock %}
{% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Prüfe Kompatibilität des Browsers</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_1">
                <!-- h4 class="card-header">1. Schritt</h4-->
                <div class="card-body">
                    <!--h4 class="card-title">Prüfe Kompatibilität des Browsers</h4-->
                    <p class="card-text">
                        Wir prüfen nun die Kompatibilität Ihres Browsers. Die Studie ist nur mit Firefox und Google Chrome kompatibel. Falls der Test fehlschlägt, starten Sie die Studie bitte erneut mit einem dieser Browser.
                    </p>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        Sie benutzen einen kompatiblen Browser. Bitte fahren Sie fort.
                    </div>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        Sie benutzen einen inkompatiblen Browser. Bitte benutzen Sie Google Chrome oder Mozilla Firefox und öffnen Sie die Seite
                        erneut.
                    </div>
                    <form action="{% url 'experiments:consentForm' experiment.id %}" method="post">
                        {% csrf_token %}
                        <button type="submit" disabled="disabled" class="btn btn-primary" id="nextbutton">Weiter</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<script src="{% static 'experiments/js/detectrtc.min.js' %}"></script>
<script src="{% static 'experiments/js/browser-check.js' %}"></script>
{% endblock %}'''

introduction_page_content = '''{% extends "experiments/base.html" %} {% block title %}Einverständnis zur Studienteilnahme{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Einverständnis zur Studienteilnahme</h1>
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
                            Bitte lesen Sie die folgenden Punkte aufmerksam durch und geben Sie an, ob Sie diesen zustimmen.<br /><br />
                            Die Teilnahme an der Studie ist nur möglich, wenn Sie mit jedem der folgenden Punkte einverstanden sind.
                        </p>
                        <p><br><span class="asterix">* Pflichtfeld</span></p>
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
                        <button type="submit" class="btn btn-primary">Weiter</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

consent_fail_page_content = '''{% extends "experiments/base.html" %} 
{% load static %}
{% block title %}Einverständnis nicht erteilt{% endblock %} 

{% block content %}
<div class="container" id="consentFail">
    <div class="row">
        <div class="col text-center">
            <h1>Einverständnis nicht erteilt</h1>
        </div>
    </div>
    <div class="row">
        <div class="col text-center ">
            <div class= "card-body alert alert-danger">
                <p class="card-text">
                        Sie waren nicht mit allen Punkten einverstanden. Daher können wir mit der Studie nicht fortfahren.<br /><br />
                        Falls Sie tatsächlich nicht einverstanden sind, schließen Sie bitte Ihr Browserfenster.<br /><br />
                        Falls Sie zurückkehren und Ihre Eingabe ändern möchten, klicken Sie bitte „zurück“.
                </p>
            </div>
            <form action="{% url 'experiments:consentForm' experiment.id %}" method="post">
            {% csrf_token %}        
                <button type="submit" class="btn btn-primary" id="resumebutton">Zurück</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}'''

demographic_data_page_content = '''{% extends "experiments/base.html" %} {% block title %}Persönliche Angaben{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Persönliche Angaben</h1>
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

                    <form action="{% url 'experiments:subjectFormSubmit' experiment.id %}" method="post" novalidate>
                        {% csrf_token %}
                        <p class="card-text">
                            Bitte füllen Sie die Felder unten aus. Sie müssen mindestens alle mit einem * versehenen Felder ausfüllen, um an der Studie teilnehmen zu können.
                        </p>
                        <p><br><span class="asterix">* Pflichtfeld</span></p>
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
                        <button type="submit" class="btn btn-primary">Weiter</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

webcam_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Webcam und Mikrofon einrichten{% endblock %} {% block content%}
<div class="container" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}">
    <div class="row">
        <div class="col text-center">
            <h1>Webcam und Mikrofon einrichten</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_2">
                <div class="card-body">
                    <p class="card-text">
                        Für diese Studie ist es notwendig, dass Sie Zugriff auf Webcam und Mikrofon erlauben.<br /><br />
                        Ihr Browser wird Sie im nächsten Schritt um Erlaubnis bitten, Webcam und Mikrofon freizuschalten. Klicken Sie dann bitte auf "Erlauben", um mit dem Experiment fortzufahren.<br /><br />
                        Falls Ihnen die Option „immer erlauben“ angeboten wird, wählen Sie bitte diese, damit Ihr Browser die Einstellung speichert (nur für unseren Server). Sie können auch nur den Einzelfall erlauben. Dann wird Ihr Browser in den nächsten Schritten noch mehrmals um Erlaubnis zur Freischaltung von Webcam und Mikrofon bitten.
                    </p>
                    <button type="button" class="btn btn-primary" disabled>Weiter</button>
                </div>
            </div>

            <div class="card" id="webcam_step_3">
                <div class="card-body">
                    <p class="card-text">
                        Sie sehen nun unten ein Fenster mit dem Kamerabild. Bitte justieren Sie Ihre Kamera so, dass Ihr Kind gut sichtbar ist.<br /><br />
                        Gleich machen wir eine kurze Probeaufnahme (ca. 3 Sekunden) um zu testen, ob die Aufnahme mit Bild und Ton funktioniert. Sobald sie unten klicken, startet die Probeaufnahme. Bitte sagen Sie nachdem Sie geklickt haben laut etwas (z.B. „hallo“), damit Sie die Tonaufnahme überprüfen können.
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;"></div>
                    <div class="embed-responsive" style="display: none;">
                        <video controls class="embed-responsive-item"></video>
                    </div>
                    <button type="button" class="btn btn-primary" disabled>Probeaufnahme jetzt starten</button>
                    <button type="button" class="btn btn-warning" id="repeat-check-button" style="display: none;">Webcam-Test wiederholen</button>
                </div>
            </div>

            <div class="card" id="webcam_step_4">
                <div class="card-body">
                    <p class="card-text">
                        Unten sehen Sie das Probevideo. Bitte spielen Sie dieses ab und beurteilen Sie, ob Ihr Kind und Sie gut sichtbar sind und ob der Ton aufgenommen wurde.<br /><br />
                        Achten dabei bitte darauf, dass der Sound auf Ihrem Computer aktiviert ist.
                    </p>
                    <p class="card-text" id="upload-progress">
                        <img src="{% static 'experiments/img/loading.gif' %}" alt="Laden" title="Loading" />
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        Der Upload des Videos ist fehlgeschlagen.<br />
                    </div>
                    <div class="embed-responsive" style="display: none;">
                    </div>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        Der Upload des Videos war erfolgreich, bitte fahren Sie fort.
                    </div>

                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Weiter (Bild und Ton haben funktioniert)</button>
                    <button type="button" class="btn btn-warning" disabled data-toggle="modal" data-target="#repeatWebcamModal">Test Wiederholen (Es gab Probleme bei der Probeaufnahme)</button>
                </div>
            </div>

        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" role="dialog" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Webcam Test Wiederholen</h5>
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body">
                Falls Sie keinen Ton hören konnten: Stellen Sie bitte in den Soundeinstellungen Ihres Computers sicher, dass Ihr  und Ihr Lautsprecher aktiviert sind und überprüfen Sie, dass Ihr Ton nicht zu leise gestellt ist.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Abbrechen</button>
                <button type="button" class="btn btn-primary" id="repeatRutton">Test Wiederholen</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Beenden</button>
<script>
    var webcam_not_found = `Leider konnte Ihre Webcam nicht gefunden werden.<br /><br />Bitte stellen Sie sicher, dass eine Webcam angeschlossen ist und klicken Sie „Prüfung wiederholen“ um zum Webcam-Test zurückzukehren.<br /><br />Sollten Sie mit der Freischaltung Ihrer Webcam nicht einverstanden sein und deshalb auf „nicht erlauben“ ausgewählt haben, schließen Sie bitte das Browser-Fenster.`;
    var include_pause_page = "{{ experiment.include_pause_page }}";
    var recording_option = "{{ experiment.recording_option }}";
</script>
<script src="{% static 'experiments/js/detectrtc.min.js' %}"></script>
<script src="{% static 'experiments/js/webcam-calibration.js' %}"></script>
{% endblock %}'''

microphone_check_page_content = '''{% extends "experiments/base.html" %} {% load static %} {% block title %}Mikrofon einrichten{% endblock %} {% block content%}
<div class="container" id="webcam-calibration" data-subject-uuid="{{ subject_data.id }}">
    <div class="row">
        <div class="col text-center">
            <h1>Mikrofon einrichten</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="webcam_step_2">
                <div class="card-body">
                    <p class="card-text">
                        Für diese Studie ist es notwendig, dass Sie Zugriff auf Mikrofon erlauben.<br /><br />
                        Ihr Browser wird Sie im nächsten Schritt um Erlaubnis bitten, Mikrofon freizuschalten. Klicken Sie dann bitte auf "Erlauben", um mit dem Experiment fortzufahren.<br /><br />
                        Falls Ihnen die Option „immer erlauben“ angeboten wird, wählen Sie bitte diese, damit Ihr Browser die Einstellung speichert (nur für unseren Server). Sie können auch nur den Einzelfall erlauben. Dann wird Ihr Browser in den nächsten Schritten noch mehrmals um Erlaubnis zur Freischaltung von Mikrofon bitten.
                    </p>
                    <button type="button" class="btn btn-primary" disabled>Weiter</button>
                </div>
            </div>

            <div class="card" id="webcam_step_4">
                <div class="card-body">
                    <p class="card-text">
                        Unten sehen Sie das Probeaudio. Bitte spielen Sie dieses ab und beurteilen Sie, ob Ihr Kind und Sie gut sichtbar sind und ob der Ton aufgenommen wurde.<br /><br />
                        Achten dabei bitte darauf, dass der Sound auf Ihrem Computer aktiviert ist.
                    </p>
                    <p class="card-text" id="upload-progress">
                        <img src="{% static 'experiments/img/loading.gif' %}" alt="Laden" title="Loading" />
                    </p>
                    <div class="alert alert-danger" role="alert" style="display: none;">
                        Der Audio-Upload ist fehlgeschlagen.<br />
                    </div>
                    <div class="embed-responsive" style="display: none;">
                    </div>
                    <div class="alert alert-success" role="alert" style="display: none;">
                        Der Audio-Upload war erfolgreich, bitte fahren Sie fort.
                    </div>

                    <button type="button" class="btn btn-primary" disabled data-target="{% url 'experiments:experimentRun' subject_data.pk %}">Weiter (Ton haben funktioniert)</button>
                    <button type="button" class="btn btn-warning" disabled data-toggle="modal" data-target="#repeatWebcamModal">Test Wiederholen (Es gab Probleme bei der Probeaufnahme)</button>
                </div>
            </div>

        </div>
    </div>
</div>

<div class="modal fade" id="repeatWebcamModal" tabindex="-1" role="dialog" aria-labelledby="repeatWebcamModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="repeatWebcamModalLabel">Mikrofon-Test Wiederholen</h5>
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body">
                Falls Sie keinen Ton hören konnten: Stellen Sie bitte in den Soundeinstellungen Ihres Computers sicher, dass Ihr  und Ihr Lautsprecher aktiviert sind und überprüfen Sie, dass Ihr Ton nicht zu leise gestellt ist.
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Abbrechen</button>
                <button type="button" class="btn btn-primary" id="repeatRutton">Test Wiederholen</button>
            </div>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Beenden</button>
<script>
    var webcam_not_found = `Leider konnte Ihr Microfon nicht gefunden werden.<br /><br />Bitte stellen Sie sicher, dass ein Microfon angeschlossen ist und klicken Sie „Prüfung wiederholen“ um zum Mikrofon-Test zurückzukehren.<br /><br />Sollten Sie mit der Freischaltung Ihres Mikrofons nicht einverstanden sein und deshalb auf „nicht erlauben“ ausgewählt haben, schließen Sie bitte das Browser-Fenster.`;
    var include_pause_page = "{{ experiment.include_pause_page }}";
    var recording_option = "{{ experiment.recording_option }}";
</script>
<script src="{% static 'experiments/js/detectrtc.min.js' %}"></script>
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
                Gleich geht es los!<br /><br />
                Bevor die Studie startet, möchten wir noch eine kurze Erklärung von Ihnen aufzeichnen. Lesen Sie dafür bitte den Text auf der nächsten Seite mit Ihrem Kind auf dem Schoß laut vor. <br /><br />
                Diese wiederholte Erklärung ist uns wichtig, da wir wirklich sichergehen möchten, dass Sie die Rahmenbedingungen verstanden haben und mit Ihnen einverstanden sind. Sollte uns diese Aufnahme nicht vorliegen, werden wir Ihre Daten und Videos löschen. <br /><br />
                Nach der Erklärung startet die Studie direkt. Folgen Sie dann bitte den Hinweisen auf dem Monitor. <br />
                Die Studie wird im Vollbild dargeboten. Sollten Sie die Studie zwischendurch beenden oder unterbrechen wollen, klicken Sie bitte unten rechts auf „beenden“. <br /><br />
                Um fortzufahren, klicken Sie bitte „Vollbild aktivieren“
            </p>
            <button id="fullscreen-button" type="button" class="btn btn-primary">Vollbild aktivieren</button>
        </div>
    </div>
</div>

<button id="exit-button" type="button" class="btn btn-secondary btn-sm">Beenden</button>

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
</script>
 
<script src="{% static 'experiments/js/experiment.js' %}"></script>
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
                        Das Experiment wurde pausiert und die Aufnahme unterbrochen.<br /><br />
                        Wenn Sie die Studie abbrechen möchten, klicken Sie unten bitte auf „Experiment beenden“. <br /><br />
                        Um fortzufahren, klicken Sie bitte „Experiment fortsetzen“. Sie werden dann zu einem erneuten Webcam-Test geleitet und anschließend an die Stelle der Studie, an der Sie pausiert haben.
                    </p>
                    <div id="side-by-side-left"> 
                        <form action="{% url 'experiments:webcamTest' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-primary" id="resumebutton">Experiment Fortsetzen</button>
                        </form>
                    </div>
                    <div id="side-by-side-right"> 
                        <form action="{% url 'experiments:experimentEnd' subject_id %}" method="post">
                            {% csrf_token %}        
                            <button type="submit" class="btn btn-danger" id="exitbutton">Experiment Beenden</button>
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
{% block title %}Fertig{% endblock %} 

{% block content %}
<div class="container" id="thank-you">
    <div class="row">
        <div class="col text-center">
            <h1>Fertig</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="end_page_step_1">
                <div class="card-body text-center">
                    <p class="card-text">
                        Die Studie ist nun abgeschlossen und die Webcamaufnahme wurde beendet.<br /><br />
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
                        Vielen Dank für Ihre Teilnahme!<br /><br />
                        Bitte schließen Sie jetzt dieses Browser-Fenster.
                    </p>
                </div>
            </div>
            <div class="card" id="end_page_disapprove">
                <div class="card-body text-center">
                    <p class="card-text">
                        Alle Ihre Daten wurden entfernt.<br /><br />
                        Bitte schließen Sie jetzt dieses Browser-Fenster.
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
{% block title %}Fertig{% endblock %} 

{% block content %}
<div class="container" id="thank-you">
    <div class="row">
        <div class="col text-center">
            <h1>Fertig</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card active" id="end_page_step_1">
                <div class="card-body text-center">
                    <p class="card-text">
                        Schade, dass Sie die Studie abgebrochen haben. Die Webcamaufnahme wurde beendet. Bitte schließen Sie jetzt dieses Browser-Fenster.<br /><br />
                        Wir würden gerne erfahren, warum Sie die Studie abgebrochen haben. Falls Sie uns dies mitteilen möchten, schreiben Sie bitte eine Email an XXX.
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
                        Vielen Dank für Ihre Teilnahme!<br /><br />
                        Bitte schließen Sie jetzt dieses Browser-Fenster.
                    </p>
                </div>
            </div>
            <div class="card" id="end_page_disapprove">
                <div class="card-body text-center">
                    <p class="card-text">
                        Alle Ihre Daten wurden entfernt.<br /><br />
                        Bitte schließen Sie jetzt dieses Browser-Fenster.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="{% static 'experiments/js/endpage.js' %}"></script>
{% endblock %}'''

error_page_content = '''{% extends "experiments/base.html" %} {% block title %}Fehler{% endblock %} {% block content %}
<div class="container" id="information">
    <div class="row">
        <div class="col text-center">
            <h1>Fehler</h1>
        </div>
    </div>
    <div class="row">
        <div class="col">
            <div class="card">
                <div class="card-body text-justify">
                    <p class="card-text">
                        Es ist ein Fehler aufgetreten. Das Experiment wurde beendet.
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

cdi_page_content = '''{% extends "experiments/base.html" %} {% block title %}Vocabulary Checklist{% endblock %} {% block content %}
<div class="container">
    <div class="row">
        <div class="col text-center">
            <h1>Vocabulary Checklist</h1>
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

                    <form id="parentform" action="{% url 'experiments:parentFormSubmit' subject_data.id %}" method="post" novalidate>
                        {% csrf_token %}
                        <p class="card-text">
                            Please mark the boxes for words your child understands. If your child uses another word with the same meaning (e.g., nana for grandma), mark it anyway. </br></br>
                        </p>
                        {{ parent_form.non_field_errors }}
                        {% for field in parent_form %}
                        {% if field.name == 'resolution_w' or field.name == 'resolution_h' or field.name == 'experiment' or field.name == 'parent_form' %}
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
        $("#parentform").on('submit', function() {
            // to each unchecked checkbox
            $('input:checkbox:not(:checked)').each(function () {
                // add hidden checkbox to be posted
                $("#parentform").append("<input type='hidden' name='" + this.name + "' value='0' />");
            });
        })
    })
</script>
{% endblock %}'''