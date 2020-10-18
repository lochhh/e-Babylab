'use strict';

$(function() {
    // Check MediaRecorder support
    var mediaRecorderSupported = !(window.MediaRecorder == undefined);

    /*
     * Step 1
     */
    var checkStepOne = function() {
        var alertWindow = $("#webcam_step_1 .alert-danger");
        var successWindow = $("#webcam_step_1 .alert-success");
        var button = $("#webcam_step_1 button");

        // TODO: Try to check manually (DetectRTC could be removed then)
        if(!DetectRTC.isGetUserMediaSupported) {
            alertWindow.show();
            alertWindow.append("<br />Ihr Browser unterstützt den Zugriff auf Webcam und Mikrofon nicht (getUserMedia).");
            return;
        }

        if(!mediaRecorderSupported) {
            alertWindow.show();
            alertWindow.append("<br />Ihr Browser unterstützt die Aufnahme von Videos über Webcam und Mikrofon nicht (MediaRecorder).");
            return;
        }

        successWindow.show();
        button.removeAttr("disabled");
    };

    // Start webcam calibration
    DetectRTC.load(function() {
        checkStepOne();
    });
});
