'use strict';

$(function() {

    // Webcam constraints
    var constraints = {
		audio: true,
		video: {
			facingMode: "user",
			width: { min: 640, max: 640 },
			height: { min: 480, max: 480 }
		}
    };
    
    // Audio constraints
    var constraintsAudio = {
		audio: true,
    };

    // Get Django CSRF token
    var csrftoken = Cookies.get('csrftoken');

    var csrfSafeMethod = function(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    // Add CSRF to AJAX
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // Stream reference
    var mediaStream;

    // Recorder reference
    var mediaRecorder;

    // Get subject UUID
    var subjectUuid = $("#webcam-calibration").data("subjectUuid");

    // Check MediaRecorder support
    var mediaRecorderSupported = !(window.MediaRecorder == undefined);

    let startStream = function() {
        return new Promise(function(resolve, reject) {
            var recordingConstraints = constraints;
            if (recording_option == 'AUD') {
                recordingConstraints = constraintsAudio;
            }
            navigator.mediaDevices.getUserMedia(recordingConstraints).then(function (s) {
                mediaStream = s;

                if (recording_option != 'AUD') {
                    // Check video stream
                    if(mediaStream.getVideoTracks().length == 0) {
                        reject(new Error("No webcam access."));
                    }
                }

                // Check audio stream
                if(mediaStream.getAudioTracks().length == 0) {
                    reject(new Error("No microphone access."));
                }

                resolve();
            }).catch(function(e) {
                console.error(e);
                reject(e);
            });
        });
    };

    /*
     * Step 2
     */
    var checkStepTwo = function() {
        var button = $("#webcam_step_2 button");

        $("#webcam_step_1").removeClass("active");
        $("#webcam_step_2").addClass("active");
        if (recording_option == 'AUD') { // skip to audio test
            button.click(checkStepFour);
        } else { // webcam calibration
            button.click(checkStepThree);
        }
        button.removeAttr("disabled");
    };

    /*
     * Step 3
     */
    var checkStepThree = function() {
        $("#webcam_step_2").removeClass("active");
        $("#webcam_step_3").addClass("active");

        var button = $("#webcam_step_3 button.btn-primary");
        var alertWindow = $("#webcam_step_3 .alert-danger");

        // Get webcam stream
        startStream()
            .then(function() {
                // Display video stream in video tag
                $("#webcam_step_3 .embed-responsive").show();
                var video = $("#webcam_step_3 video").get(0);
                video.srcObject = mediaStream;
                video.onloadedmetadata = function (e) {
                    video.muted = true;
                    video.play();

                    // Enable button to continue
                    button.click(function() {
                        video.muted = false;
                        stopStream();
                        checkStepFour();
                    });
                    button.removeAttr("disabled");
                };
            })
            .catch(function(e) {
                alertWindow.show();
                alertWindow.append(webcam_not_found + "<br><strong>" + e.name + ":</strong> " + e.message);
                let repeatButton = $("#repeat-check-button");
                repeatButton.show();
                repeatButton.on('click', function() {
                    location.reload();
                });
            });
    };

    /*
     * Step four
     */
    let firstChunk = true;
    var checkStepFour = function() {
        if (recording_option != 'AUD') {
            $("#webcam_step_3 video").get(0).pause();
            $("#webcam_step_3").removeClass("active");
        } else {
            $("#webcam_step_2").removeClass("active");
        }
        $("#webcam_step_4").addClass("active");
        $("#webcam_step_4 .alert-danger").hide();
        $("#webcam_step_4 .alert-success").hide();
        $("#webcam_step_4 .embed-responsive").hide();
        if (recording_option == 'AUD') {
            $("#webcam_step_4 .embed-responsive audio").eq(0).empty();
        } else {
            $("#webcam_step_4 .embed-responsive video").eq(0).empty();
        }
        var button = $("#webcam_step_4 button.btn-primary");
        button.attr('disabled', true);
        var repeatButton = $("#webcam_step_4 button.btn-warning");
        repeatButton.attr('disabled', true);
        var uploadProgress = $("#upload-progress");
        uploadProgress.show();
        $("#repeatWebcamModal").modal('hide');
        firstChunk = true;

        // Start recording
        startStream()
            .then(function() {
                recordStream();
            })
            .catch(function(e) {
                uploadProgress.hide();
                var alertWindow = $("#webcam_step_4 .alert-danger");
                alertWindow.show();
                alertWindow.append(e);
                console.log(e);
                stopStream();
            });
    };

    var enableRepeat = function() {
        var repeatButton = $("#webcam_step_4 button.btn-warning");
        repeatButton.removeAttr("disabled");

        var modelRepeatButton = $("#repeatRutton");
        modelRepeatButton.one('click', function() {
            checkStepFour();
        });
    };

    var enableFinalContinue = function() {
        var button = $("#webcam_step_4 button.btn-primary");
        button.removeAttr("disabled");
        button.click(function() {
            window.location = $(this).data("target");
        });
        enableRepeat();
    };

    var recordStream = function() {
        var codec = 'video/webm';
        if (recording_option == 'AUD') {
           codec = 'audio/webm';
        } 
        mediaRecorder = new MediaRecorder(mediaStream, { mimeType: codec });
        mediaRecorder.ondataavailable = handleStreamData;

        // Record up to 5 seconds
        mediaRecorder.start(5000);

        // stop after 3 seconds
        setTimeout(function() {
            stopStream();
        }, 3000);
    };

    var handleStreamData = function(event) {
        if(!firstChunk) {
            return;
        }else{
            firstChunk = false;
        }
        var uploadProgress = $("#upload-progress");
        var alertWindow = $("#webcam_step_4 .alert-danger");
        var successWindow = $("#webcam_step_4 .alert-success");

        // Prepare post request data
        var codec = 'video/webm';
        if (recording_option == 'AUD') {
           codec = 'audio/webm';
        } 
        var file = new File([event.data], 'webcam-test.webm', { type: codec });
        var formData = new FormData();
        formData.append('file', file);
        formData.append('type', codec);

        // Send post request
        $.ajax({
            url: '/' + subjectUuid + '/webcamtest/upload',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false
        }).done(function(data, status, xhr) {
            uploadProgress.hide();

            if(data.videoUrl) {
                // Add video/audio source
                $("#webcam_step_4 .embed-responsive").empty();
                var source = document.createElement('source');
                source.src = data.videoUrl;
                source.type = data.type;
                let videoElem;
                if (recording_option == 'AUD') {
                    videoElem = document.createElement("audio");
                } else {
                    videoElem = document.createElement("video");
                }
                videoElem.controls = true;
                videoElem.className = "embed-responsive-item";
                videoElem.appendChild(source);
                $("#webcam_step_4 .embed-responsive").get(0).appendChild(videoElem);

                // Show recorded video
                successWindow.show();
                $("#webcam_step_4 .embed-responsive").show();

                // Enable continue
                enableFinalContinue();
            }
        }).fail(function(xhr, status, error) {
            uploadProgress.hide();
            alertWindow.show();
            alertWindow.append(error);
            console.error(xhr, status, error);
            enableRepeat();
        });
    };

    var stopStream = function() {
        if(mediaRecorder && mediaRecorder.state == "recording") {
            mediaRecorder.stop();
        }
        mediaStream.getAudioTracks().forEach(function(track) {
            track.stop();
        });
        mediaStream.getVideoTracks().forEach(function(track) {
            track.stop();
        });
    };

    $("#exit-button").click(function() {
        if (include_pause_page.toLowerCase() == 'true') {
            window.location.replace('/' + subjectUuid + '/run/pause');
        } else {
            window.location.replace('/' + subjectUuid + '/run/thankyou');
        }
    });
    
    // Start webcam calibration
    checkStepTwo();
});