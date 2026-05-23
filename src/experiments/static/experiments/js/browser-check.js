'use strict';

export function init() {
    if (!document.getElementById('webcam_step_1')) return;

    const mediaRecorderSupported = window.MediaRecorder != null;
    const getUserMediaSupported = navigator.mediaDevices;

    const checkStepOne = () => {
        const alertWindow = document.querySelector('#webcam_step_1 .alert-danger');
        const successWindow = document.querySelector('#webcam_step_1 .alert-success');
        const button = document.querySelector('#webcam_step_1 button');

        if (!getUserMediaSupported) {
            alertWindow.style.display = 'block';
            alertWindow.insertAdjacentHTML('beforeend', '<br />Your browser does not support webcam and microphone access (getUserMedia).');
            return;
        }

        if (!mediaRecorderSupported) {
            alertWindow.style.display = 'block';
            alertWindow.insertAdjacentHTML('beforeend', '<br />Your browser does not support media recording via webcam and microphone (MediaRecorder).');
            return;
        }

        successWindow.style.display = 'block';
        button.removeAttribute('disabled');
    };

    checkStepOne();
}

init();
