'use strict';

$(function() {
    // Check MediaRecorder support
    var mediaRecorderSupported = !(window.MediaRecorder == undefined);
    var getUserMediaSupported = navigator.mediaDevices;
    /*
     * Step 1
     */
    var checkStepOne = function() {
        var alertWindow = $("#webcam_step_1 .alert-danger");
        var successWindow = $("#webcam_step_1 .alert-success");
        var button = $("#webcam_step_1 button");

        if(!getUserMediaSupported) {
            alertWindow.show();
            alertWindow.append("<br />Your browser does not support webcam and microphone access (getUserMedia).");
            return;
        }

        if(!mediaRecorderSupported) {
            alertWindow.show();
            alertWindow.append("<br />Your browser does not support media recording via webcam and microphone (MediaRecorder).");
            return;
        }

        successWindow.show();
        button.removeAttr("disabled");
    };

    // Start webcam calibration
    checkStepOne();
});
