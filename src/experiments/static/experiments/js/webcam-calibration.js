'use strict';

$(function () {

    // Webcam constraints
    const constraints = {
        audio: true,
        video: {
            facingMode: "user",
            width: { min: 640, max: 640 },
            height: { min: 480, max: 480 }
        }
    };

    // Audio constraints
    const constraintsAudio = {
        audio: true,
    };

    // Get Django CSRF token
    const csrftoken = Cookies.get('csrftoken');

    const csrfSafeMethod = function (method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    // Add CSRF to AJAX
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // Stream reference
    let mediaStream;

    // Recorder reference
    let mediaRecorder;

    // Get configuration from data attributes
    const config = $("#webcam-calibration").data();
    const subjectUuid = config.subjectUuid;
    const include_pause_page = config.includePausePage;
    const recording_option = config.recordingOption;
    const webcam_not_found = config.webcamNotFound ?? `Unfortunately your device could not be detected.<br /><br />Please make sure a device is connected and click "Repeat test recording" to return to the test.<br /><br />If you do not agree to allow access to your device and have therefore selected "do not allow", please close the browser window.`;

    // Check MediaRecorder support
    const mediaRecorderSupported = window.MediaRecorder != null;

    const startStream = function () {
        return new Promise((resolve, reject) => {
            const recordingConstraints = recording_option === 'AUD' ? constraintsAudio : constraints;
            navigator.mediaDevices.getUserMedia(recordingConstraints).then(s => {
                mediaStream = s;

                if (recording_option !== 'AUD') {
                    if (mediaStream.getVideoTracks().length === 0) {
                        reject(new Error("No webcam access."));
                    }
                }

                if (mediaStream.getAudioTracks().length === 0) {
                    reject(new Error("No microphone access."));
                }

                resolve();
            }).catch(e => {
                console.error(e);
                reject(e);
            });
        });
    };

    /*
     * Step 2
     */
    const checkStepTwo = function () {
        const button = $("#webcam_step_2 button");

        $("#webcam_step_1").removeClass("active");
        $("#webcam_step_2").addClass("active");
        if (recording_option === 'AUD') { // Skip to audio test
            button.click(checkStepFour);
        } else { // Webcam calibration
            button.click(checkStepThree);
        }
        button.removeAttr("disabled");
    };

    /*
     * Step 3
     */
    const checkStepThree = function () {
        $("#webcam_step_2").removeClass("active");
        $("#webcam_step_3").addClass("active");

        const button = $("#webcam_step_3 button.btn-primary");
        const alertWindow = $("#webcam_step_3 .alert-danger");

        // Start webcam stream
        startStream()
            .then(() => {
                $("#webcam_step_3 .media-container").show();
                const video = $("#webcam_step_3 video").get(0);
                video.srcObject = mediaStream;
                video.onloadedmetadata = function () {
                    video.muted = true;
                    video.play();

                    // Enable continue button
                    button.click(() => {
                        video.muted = false;
                        stopStream();
                        checkStepFour();
                    });
                    button.removeAttr("disabled");
                };
            })
            .catch(e => {
                alertWindow.show();
                alertWindow.append(`${webcam_not_found}<br><strong>${e.name}:</strong> ${e.message}`);
                const repeatButton = $("#repeat-check-button");
                repeatButton.show();
                repeatButton.on('click', () => { location.reload(); });
            });
    };

    /*
     * Step four
     */
    let firstChunk = true;
    const checkStepFour = function () {
        if (recording_option !== 'AUD') {
            $("#webcam_step_3 video").get(0).pause();
            $("#webcam_step_3").removeClass("active");
        } else {
            $("#webcam_step_2").removeClass("active");
        }
        $("#webcam_step_4").addClass("active");
        $("#webcam_step_4 .alert-danger").hide();
        $("#webcam_step_4 .alert-success").hide();
        $("#webcam_step_4 .media-container").hide();
        if (recording_option === 'AUD') {
            $("#webcam_step_4 .media-container audio").eq(0).empty();
        } else {
            $("#webcam_step_4 .media-container video").eq(0).empty();
        }
        const button = $("#webcam_step_4 button.btn-primary");
        button.attr('disabled', true);
        const repeatButton = $("#webcam_step_4 button.btn-warning");
        repeatButton.attr('disabled', true);
        const uploadProgress = $("#upload-progress");
        uploadProgress.show();
        $("#repeatWebcamModal").modal('hide');
        firstChunk = true;

        // Start recording
        startStream()
            .then(() => { recordStream(); })
            .catch(e => {
                uploadProgress.hide();
                const alertWindow = $("#webcam_step_4 .alert-danger");
                alertWindow.show();
                alertWindow.append(e);
                console.log(e);
                stopStream();
            });
    };

    const enableRepeat = function () {
        const repeatButton = $("#webcam_step_4 button.btn-warning");
        repeatButton.removeAttr("disabled");

        const modelRepeatButton = $("#repeatRutton");
        modelRepeatButton.one('click', () => { checkStepFour(); });
    };

    const enableFinalContinue = function () {
        const button = $("#webcam_step_4 button.btn-primary");
        button.removeAttr("disabled");
        button.click(function () {
            window.location = $(this).data("target");
        });
        enableRepeat();
    };

    const recordStream = function () {
        const codec = recording_option === 'AUD' ? 'audio/webm' : 'video/webm';
        mediaRecorder = new MediaRecorder(mediaStream, { mimeType: codec });
        mediaRecorder.ondataavailable = handleStreamData;

        // Record for up to 5 seconds
        mediaRecorder.start(5000);

        // Stop recording after 3 seconds
        setTimeout(() => { stopStream(); }, 3000);
    };

    const handleStreamData = function (event) {
        if (!firstChunk) return;
        firstChunk = false;

        const uploadProgress = $("#upload-progress");
        const alertWindow = $("#webcam_step_4 .alert-danger");
        const successWindow = $("#webcam_step_4 .alert-success");

        const codec = recording_option === 'AUD' ? 'audio/webm' : 'video/webm';
        const file = new File([event.data], 'webcam-test.webm', { type: codec });
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', codec);

        $.ajax({
            url: `/${subjectUuid}/webcamtest/upload`,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false
        }).done(function (data) {
            uploadProgress.hide();

            if (data.videoUrl) {
                $("#webcam_step_4 .media-container").empty();
                const source = document.createElement('source');
                source.src = data.videoUrl;
                source.type = data.type;
                const videoElem = recording_option === 'AUD'
                    ? document.createElement("audio")
                    : document.createElement("video");
                videoElem.controls = true;
                videoElem.appendChild(source);
                $("#webcam_step_4 .media-container").get(0).appendChild(videoElem);

                // Show recorded media
                successWindow.show();
                $("#webcam_step_4 .media-container").show();

                enableFinalContinue();
            }
        }).fail(function (xhr, status, error) {
            uploadProgress.hide();
            alertWindow.show();
            alertWindow.append(error);
            console.error(xhr, status, error);
            enableRepeat();
        });
    };

    const stopStream = function () {
        if (mediaRecorder?.state === 'recording') {
            mediaRecorder.stop();
        }
        mediaStream.getAudioTracks().forEach(track => track.stop());
        mediaStream.getVideoTracks().forEach(track => track.stop());
    };

    $("#exit-button").click(() => {
        if (include_pause_page) {
            window.location.replace(`/${subjectUuid}/run/pause`);
        } else {
            window.location.replace(`/${subjectUuid}/run/thankyou`);
        }
    });

    // Start webcam calibration
    checkStepTwo();
});
