'use strict';

$(function () {
    // Check MediaRecorder and getUserMedia support
    const mediaRecorderSupported = window.MediaRecorder != null;
    const getUserMediaSupported = navigator.mediaDevices;

    const checkStepOne = () => {
        const alertWindow = $("#webcam_step_1 .alert-danger");
        const successWindow = $("#webcam_step_1 .alert-success");
        const button = $("#webcam_step_1 button");

        if (!getUserMediaSupported) {
            alertWindow.show();
            alertWindow.append("<br />Your browser does not support webcam and microphone access (getUserMedia).");
            return;
        }

        if (!mediaRecorderSupported) {
            alertWindow.show();
            alertWindow.append("<br />Your browser does not support media recording via webcam and microphone (MediaRecorder).");
            return;
        }

        successWindow.show();
        button.removeAttr("disabled");
    };

    checkStepOne();
});
