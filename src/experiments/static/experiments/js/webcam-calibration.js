import { getCsrfToken } from './utils.js';

export function init() {
    const el = document.getElementById('webcam-calibration');
    if (!el) return;

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

    // Stream reference
    let mediaStream;

    // Recorder reference
    let mediaRecorder;

    // Get configuration from data attributes
    const config = el.dataset;
    const subjectUuid = config.subjectUuid;
    const include_pause_page = config.includePausePage?.toLowerCase() === 'true';
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
        const button = document.querySelector('#webcam_step_2 button');

        document.getElementById('webcam_step_1').classList.remove('active');
        document.getElementById('webcam_step_2').classList.add('active');
        if (recording_option === 'AUD') { // Skip to audio test
            button.addEventListener('click', checkStepFour);
        } else { // Webcam calibration
            button.addEventListener('click', checkStepThree);
        }
        button.removeAttribute('disabled');
    };

    /*
     * Step 3
     */
    const checkStepThree = function () {
        document.getElementById('webcam_step_2').classList.remove('active');
        document.getElementById('webcam_step_3').classList.add('active');

        const button = document.querySelector('#webcam_step_3 button.btn-primary');
        const alertWindow = document.querySelector('#webcam_step_3 .alert-danger');

        // Start webcam stream
        startStream()
            .then(() => {
                document.querySelector('#webcam_step_3 .media-container').style.display = 'block';
                const video = document.querySelector('#webcam_step_3 video');
                video.srcObject = mediaStream;
                video.onloadedmetadata = function () {
                    video.muted = true;
                    video.play();

                    // Enable continue button
                    button.addEventListener('click', () => {
                        video.muted = false;
                        stopStream();
                        checkStepFour();
                    });
                    button.removeAttribute('disabled');
                };
            })
            .catch(e => {
                alertWindow.style.display = 'block';
                alertWindow.insertAdjacentHTML('beforeend', `${webcam_not_found}<br><strong>${e.name}:</strong> ${e.message}`);
                const repeatButton = document.getElementById('repeat-check-button');
                repeatButton.style.display = 'block';
                repeatButton.addEventListener('click', () => { location.reload(); });
            });
    };

    /*
     * Step four
     */
    let firstChunk = true;
    const checkStepFour = function () {
        if (recording_option !== 'AUD') {
            document.querySelector('#webcam_step_3 video').pause();
            document.getElementById('webcam_step_3').classList.remove('active');
        } else {
            document.getElementById('webcam_step_2').classList.remove('active');
        }
        document.getElementById('webcam_step_4').classList.add('active');
        document.querySelector('#webcam_step_4 .alert-danger').style.display = 'none';
        document.querySelector('#webcam_step_4 .alert-success').style.display = 'none';
        document.querySelector('#webcam_step_4 .media-container').style.display = 'none';
        if (recording_option === 'AUD') {
            document.querySelector('#webcam_step_4 .media-container audio').innerHTML = '';
        } else {
            document.querySelector('#webcam_step_4 .media-container video').innerHTML = '';
        }
        const button = document.querySelector('#webcam_step_4 button.btn-primary');
        button.setAttribute('disabled', '');
        const repeatButton = document.querySelector('#webcam_step_4 button.btn-warning');
        repeatButton.setAttribute('disabled', '');
        const uploadProgress = document.getElementById('upload-progress');
        uploadProgress.style.display = 'block';
        bootstrap.Modal.getOrCreateInstance(document.getElementById('repeatWebcamModal')).hide();
        firstChunk = true;

        // Start recording
        startStream()
            .then(() => { recordStream(); })
            .catch(e => {
                uploadProgress.style.display = 'none';
                const alertWindow = document.querySelector('#webcam_step_4 .alert-danger');
                alertWindow.style.display = 'block';
                alertWindow.insertAdjacentHTML('beforeend', String(e));
                console.log(e);
                stopStream();
            });
    };

    const enableRepeat = function () {
        const repeatButton = document.querySelector('#webcam_step_4 button.btn-warning');
        repeatButton.removeAttribute('disabled');

        const modelRepeatButton = document.getElementById('repeatRutton');
        modelRepeatButton.addEventListener('click', () => { checkStepFour(); }, { once: true });
    };

    const enableFinalContinue = function () {
        const button = document.querySelector('#webcam_step_4 button.btn-primary');
        button.removeAttribute('disabled');
        button.addEventListener('click', function () {
            window.location = this.dataset.target;
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

        const uploadProgress = document.getElementById('upload-progress');
        const alertWindow = document.querySelector('#webcam_step_4 .alert-danger');
        const successWindow = document.querySelector('#webcam_step_4 .alert-success');

        const codec = recording_option === 'AUD' ? 'audio/webm' : 'video/webm';
        const file = new File([event.data], 'webcam-test.webm', { type: codec });
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', codec);

        fetch(`/${subjectUuid}/webcamtest/upload`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        })
        .then(r => {
            if (!r.ok) throw new Error(r.statusText);
            return r.json();
        })
        .then(data => {
            uploadProgress.style.display = 'none';

            if (data.videoUrl) {
                document.querySelector('#webcam_step_4 .media-container').innerHTML = '';
                const source = document.createElement('source');
                source.src = data.videoUrl;
                source.type = data.type;
                const videoElem = recording_option === 'AUD'
                    ? document.createElement('audio')
                    : document.createElement('video');
                videoElem.controls = true;
                videoElem.appendChild(source);
                document.querySelector('#webcam_step_4 .media-container').appendChild(videoElem);

                // Show recorded media
                successWindow.style.display = 'block';
                document.querySelector('#webcam_step_4 .media-container').style.display = 'block';

                enableFinalContinue();
            }
        })
        .catch(e => {
            uploadProgress.style.display = 'none';
            alertWindow.style.display = 'block';
            alertWindow.insertAdjacentHTML('beforeend', String(e));
            console.error(e);
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

    document.getElementById('exit-button').addEventListener('click', () => {
        if (include_pause_page) {
            window.location.replace(`/${subjectUuid}/run/pause`);
        } else {
            window.location.replace(`/${subjectUuid}/run/thankyou`);
        }
    });

    // Start webcam calibration
    checkStepTwo();
}

init();
