import { webcam } from './webcam.js';
import { getCsrfToken } from './utils.js';
import {
    initWebgazer,
    startGazeRecording,
    stopGazeRecording,
    calibrate,
    resetGazeData,
    getGazeData,
    setTimePerPoint,
} from './webgazer-calibration.js';

export function init() {
    const trialsEl = document.getElementById('trials');
    if (!trialsEl) return;
    const config = trialsEl.dataset;
    const trials = JSON.parse(document.getElementById('trials-data').textContent);
    const loading_image = config.loadingImage;
    const global_timeout = config.globalTimeout;
    const include_pause_page = config.includePausePage?.toLowerCase() === 'true';
    const recording_option = config.recordingOption;
    const general_onset = config.generalOnset;
    window.show_gaze_estimations = config.showGazeEstimations;

    // Subject id
    const subjectUuid = config.subjectUuid;
    const subjectId = config.subjectId;

    // Body tag reference
    const body = document.body;

    // Key codes
    const codes = {
        'backspace': 8,
        'tab': 9,
        'enter': 13,
        'shift': 16,
        'ctrl': 17,
        'alt': 18,
        'esc': 27,
        'space': 32,
        'left': 37,
        'up': 38,
        'right': 39,
        'down': 40,
    };

    // Global timeout reference
    let globaltimer;

    // Current trial index
    let currentTrial = 0;

    // Media stream object
    let mediaStream;

    // Event handler refs for cleanup
    let keydownHandler = null;
    let clickHandler = null;
    let audioCanPlayHandlerRef = null;
    const videoCanPlayHandlerRefs = {};
    const videoEndedHandlerRefs = {};

    // Populate keycode dictionary with letters
    for (let i = 97; i < 123; i++) {
        codes[String.fromCharCode(i)] = i - 32;
    }
    // Populate keycode dictionary with numbers
    for (let i = 48; i < 58; i++) {
        codes[i - 48] = i;
    }

    /**
     * Create and add an empty audio container.
     * @returns {Promise<HTMLDivElement>}
     */
    const createAudioContainer = function () {
        return new Promise(resolve => {
            const div = document.createElement('div');
            div.className = 'trial-audio';

            const audio = document.createElement('audio');
            audio.hidden = 'hidden';

            const source = document.createElement('source');
            source.src = '';
            source.type = 'audio/mpeg';

            audio.append(source);
            div.append(audio);
            body.append(div);
            resolve(div);
        });
    };

    /**
     * Setup global timeout.
     */
    const setGlobalTimer = function () {
        globaltimer = setTimeout(() => {
            webcam.stopUploading();
            if (include_pause_page) {
                window.location.replace(`/${subjectUuid}/run/pause`);
            } else {
                window.location.replace(`/${subjectUuid}/run/thankyou`);
            }
        }, Number(global_timeout));
    };

    /**
     * Reset global timeout.
     */
    const resetGlobalTimer = function () {
        clearTimeout(globaltimer);
        setGlobalTimer();
    };

    /**
     * Show next trial.
     */
    const showNextTrial = function () {
        if (currentTrial >= trials.length) { // No more trials
            clearTimeout(globaltimer);

            webgazer.pause();

            waitForWebcamUploadToFinish().then(() => {
                webcam.stopUploading();
                window.location.replace(`/${subjectUuid}/run/thankyou`);
            });

        } else { // Start trial
            const trialObj = trials[currentTrial];

            // Preload first trial video
            if (currentTrial === 0) {
                preloadVideo(trialObj);
            }

            // Preload next trial video
            if (currentTrial + 1 < trials.length) {
                preloadVideo(trials[currentTrial + 1]);
            }

            body.style.backgroundColor = trialObj.background_colour;

            // Set up trial
            trialObj.webgazer_data = [];
            resetGazeData();
            const trialSetupPromises = [];
            if (trialObj.audio_file !== '') {
                trialSetupPromises.push(playTrialAudio(trialObj));
            }
            if (trialObj.trial_type === 'video') {
                trialSetupPromises.push(playTrialVideo(trialObj));
            } else {
                trialSetupPromises.push(showTrialImage(trialObj));
            }

            // Start webcam recording if recording_option is aud, vid, or all
            if (recording_option !== 'NON' && recording_option !== 'EYE' && trialObj.record_media) {
                trialSetupPromises.push(webcam.startRecording(
                    `${subjectId}_trial${trialObj.trial_number}_${trialObj.label}_${subjectUuid}`,
                    recording_option,
                    mediaStream
                ));
            }

            // Resume webgazer and start gaze recording
            if ((trialObj.is_calibration || trialObj.record_gaze) && (recording_option === 'EYE' || recording_option === 'ALL')) {
                trialSetupPromises.push(webgazer.resume().then(() => {
                    if (trialObj.record_gaze) {
                        startGazeRecording();
                    }
                }));
            }

            // Wait before accepting user input
            if (trialObj.require_user_input === 'YES') {
                const waitTime = parseInt(general_onset);
                trialSetupPromises.push(waitPromise(waitTime, trialObj));
            }

            Promise.all(trialSetupPromises).then(values => {
                const trialObj = values[0];

                trialObj.start_time = performance.now();

                // Register promise to determine end of trial
                const trialDonePromises = [];

                if (trialObj.trial_type === 'video' && trialObj.require_user_input === 'NO') {
                    trialDonePromises.push(setupVideoEnd(trialObj));
                }
                if ((trialObj.trial_type === 'image' && !trialObj.is_calibration) || (trialObj.trial_type === 'video' && trialObj.require_user_input === 'YES')) {
                    trialDonePromises.push(setupMaxDuration(trialObj));
                }
                if (trialObj.require_user_input === 'YES' && !trialObj.is_calibration) {
                    trialDonePromises.push(setupKeyPresses(trialObj));
                }
                if (trialObj.is_calibration && (recording_option === 'EYE' || recording_option === 'ALL')) {
                    trialDonePromises.push(calibrate(trialObj));
                }
                return Promise.race(trialDonePromises);

            }).then(trialObj => {
                console.log(trialObj);
                if (keydownHandler) { document.removeEventListener('keydown', keydownHandler); keydownHandler = null; }
                if (clickHandler) { document.removeEventListener('click', clickHandler); clickHandler = null; }
                if ((trialObj.is_calibration || trialObj.record_gaze) && (recording_option === 'EYE' || recording_option === 'ALL')) {
                    stopGazeRecording();
                }
                webgazer.pause();

                trialObj.end_time = performance.now();
                trialObj.webgazer_data = trialObj.webgazer_data.concat(getGazeData());

                if (trialObj.audio_file !== '') {
                    removeTrialAudio();
                }
                if (trialObj.trial_type === 'video') {
                    removeTrialVideo(trialObj);
                } else {
                    removeTrialImage();
                }

                return postResult(trialObj);

            }).then(trialObj => {
                return webcam.stopRecording(trialObj.resultId);
            }).then(() => {
                currentTrial++;
                showNextTrial();
            }).catch(e => {
                clearTimeout(globaltimer);

                webcam.stopUploading();
                webcam.stopRecording("");

                if ((trialObj.is_calibration || trialObj.record_gaze) && (recording_option === 'EYE' || recording_option === 'ALL')) {
                    stopGazeRecording();
                }
                webgazer.pause();

                if (keydownHandler) { document.removeEventListener('keydown', keydownHandler); keydownHandler = null; }
                document.removeEventListener('mozfullscreenchange', onFullscreenChange);
                document.removeEventListener('webkitfullscreenchange', onFullscreenChange);
                document.removeEventListener('fullscreenchange', onFullscreenChange);
                exitFullscreen();

                fetch(`/${subjectUuid}/run/error`)
                    .then(r => r.text())
                    .then(data => {
                        document.body.innerHTML = data;
                        document.querySelector('div.alert').innerHTML = String(e);
                    });

                console.error("Error during experiment:", e);
            });
        }
    };

    /**
     * Returns a promise that resolves after waitTime with given param.
     */
    const waitPromise = function (waitTime, param) {
        return new Promise(resolve => {
            setTimeout(() => { resolve(param); }, waitTime);
        });
    };

    /**
     * Preload images of all trials.
     */
    const preloadImages = function () {
        const p_list = [];

        for (let t in trials) {
            if (t.trial_type === 'image') {
                const p = new Promise((resolve, reject) => {
                    const image = new Image();
                    image.onload = () => { resolve(); };
                    image.src = t.visual_file;
                });
                p_list.push(p);
            }
        }

        return Promise.all(p_list);
    };

    /**
     * Preload video for trial.
     * @param {object} trialObj
     */
    /**
     * Create or upgrade a video element for the given trial.
     * @param {object} trialObj
     * @param {boolean} load - true: set preload=auto and call video.load() (fetch data).
     *   false: create the element with preload=none so it can be gesture-unlocked on iOS
     *   before any data is fetched. showNextTrial upgrades elements to load=true as trials
     *   approach, preserving the original 1-2 trial lookahead window.
     */
    const preloadVideo = function (trialObj, load = true) {
        if (trialObj.trial_type !== 'video') return;

        const existing = document.getElementById(`video-container-${trialObj.trial_id}`);
        if (existing) {
            // Element already exists from the pre-gesture pass (load=false).
            // If showNextTrial now wants to load data, upgrade the element.
            if (load) {
                const video = existing.querySelector('video');
                if (video && video.preload !== 'auto') {
                    video.preload = 'auto';
                    video.load();
                }
            }
            return;
        }

        console.log(`Preload video of trial ${trialObj.trial_id}`);
        const div = document.createElement('div');
        div.className = 'trial-video';
        div.style.display = 'none';
        div.id = `video-container-${trialObj.trial_id}`;

        const video = document.createElement('video');
        video.preload = load ? 'auto' : 'none';
        // iOS Safari opens its native AVPlayer on video.play() unless playsinline is set,
        // even when the experiment page is already in document fullscreen.
        video.setAttribute('playsinline', '');

        const source1 = document.createElement('source');
        source1.src = trialObj.visual_file;
        source1.type = 'video/mp4';

        const source2 = document.createElement('source');
        source2.src = trialObj.visual_file;
        source2.type = 'video/ogg';

        const source3 = document.createElement('source');
        source3.src = trialObj.visual_file;
        source3.type = 'video/webm';

        video.append(source1);
        video.append(source2);
        video.append(source3);
        div.append(video);
        body.append(div);
        if (load) video.load();
    };

    /**
     * Load and play audio trial.
     * @param {object} trialObj
     */
    const playTrialAudio = function (trialObj) {
        return new Promise((resolve, reject) => {
            const audio = document.querySelector('.trial-audio audio');
            audio.querySelector('source').src = trialObj.audio_file;
            const handler = function () {
                audio.removeEventListener('canplay', handler);
                setTimeout(() => {
                    audio.play();
                    resolve(trialObj);
                }, Number(trialObj.audio_onset));
            };
            audioCanPlayHandlerRef = handler;
            audio.addEventListener('canplay', handler);
            audio.load();
        });
    };

    /**
     * Load and play video trial.
     * @param {object} trialObj
     */
    const playTrialVideo = function (trialObj) {
        return new Promise((resolve, reject) => {
            const video = document.querySelector(`#video-container-${trialObj.trial_id} > video`);
            const displayVideo = function () {
                setTimeout(() => {
                    document.querySelector(`#video-container-${trialObj.trial_id}`).style.display = 'block';
                    video.play().catch(err => {
                        if (err.name !== 'NotAllowedError') throw err;
                        console.warn('video.play() blocked by autoplay policy:', err.message);
                    });
                    resolve(trialObj);
                }, Number(trialObj.visual_onset));
            };

            if (video.readyState > 3) {
                console.log("Video is fully loaded.");
                displayVideo();
            } else {
                console.log("Video is still loading.");
                videoCanPlayHandlerRefs[trialObj.trial_id] = displayVideo;
                video.addEventListener('canplay', displayVideo);
            }
        });
    };

    /**
     * Load and show image.
     * @param {object} trialObj
     */
    const showTrialImage = function (trialObj) {
        if (trialObj.is_calibration && (recording_option === 'EYE' || recording_option === 'ALL')) {
            if (trialObj.calibration_points.length === 0) {
                trialObj.calibration_points = defaultPoints;
            }
            setTimePerPoint(trialObj.max_duration / trialObj.calibration_points.length);
            trialObj.calibration_points.forEach((pt, i) => {
                const img = document.createElement('img');
                img.className = 'calibration-image';
                img.src = trialObj.visual_file;
                img.id = `Pt${i}`;
                img.style = `width: 6vw; position: absolute; transform: translate(-50%, -50%); left: ${pt[0]}%; top: ${pt[1]}%; display: none`;
                body.append(img);
            });
            return waitPromise(Number(trialObj.visual_onset), trialObj);
        }
        return new Promise((resolve, reject) => {
            const img = document.createElement('div');
            img.className = 'trial-image';
            img.style.backgroundImage = `url('${trialObj.visual_file}')`;
            setTimeout(() => {
                body.append(img);
                resolve(trialObj);
            }, Number(trialObj.visual_onset));
        });
    };

    /**
     * Wait for upload queue to be empty.
     */
    const waitForWebcamUploadToFinish = function () {
        const trialsEl = document.getElementById('trials');
        trialsEl.style.height = '100%';
        trialsEl.style.width = '100%';
        trialsEl.style.backgroundImage = `url('${loading_image}')`;
        trialsEl.style.backgroundPosition = 'center';
        trialsEl.style.backgroundRepeat = 'no-repeat';
        trialsEl.style.backgroundSize = 'contain';
        trialsEl.style.display = 'block';
        console.log("Check queue.");
        return webcam.waitForQueue(0);
    };

    /**
     * Remove trial image from page.
     */
    const removeTrialImage = function () {
        if (document.querySelectorAll('.calibration-image')) {
            document.querySelectorAll('.calibration-image').forEach(img => img.remove());
        }
        if (document.querySelector('.trial-image')) {
            document.querySelector('.trial-image').outerHTML = '';
        }
    };

    /**
     * Remove trial audio source.
     */
    const removeTrialAudio = function () {
        const audioEl = document.querySelector('.trial-audio audio');
        if (audioEl) {
            if (audioCanPlayHandlerRef) {
                audioEl.removeEventListener('canplay', audioCanPlayHandlerRef);
                audioCanPlayHandlerRef = null;
            }
            audioEl.pause();
            audioEl.querySelector('source').src = '';
        }
    };

    /**
     * Remove trial video from page.
     */
    const removeTrialVideo = function (trialObj) {
        const video = document.querySelector(`#video-container-${trialObj.trial_id} > video`);
        if (videoCanPlayHandlerRefs[trialObj.trial_id]) {
            video.removeEventListener('canplay', videoCanPlayHandlerRefs[trialObj.trial_id]);
            delete videoCanPlayHandlerRefs[trialObj.trial_id];
        }
        if (videoEndedHandlerRefs[trialObj.trial_id]) {
            video.removeEventListener('ended', videoEndedHandlerRefs[trialObj.trial_id]);
            delete videoEndedHandlerRefs[trialObj.trial_id];
        }
        video.pause();
        document.querySelector('.trial-video').outerHTML = '';
    };

    /**
     * Send trial results to backend.
     * @param {object} trialObj
     */
    const postResult = function (trialObj) {
        return new Promise((resolve, reject) => {
            console.log("Send results", trialObj);
            let keysPressed = trialObj.keysPressed;
            if (keysPressed instanceof Array) {
                keysPressed = keysPressed.join(',');
            }
            const params = new URLSearchParams({
                'trialitem': trialObj.trial_id,
                'start_time': trialObj.start_time,
                'end_time': trialObj.end_time,
                'key_pressed': keysPressed,
                'trial_number': trialObj.trial_number,
                'resolution_w': window.screen.width,
                'resolution_h': window.screen.height,
                'webgazer_data': JSON.stringify(trialObj.webgazer_data),
            });
            fetch(`/${subjectUuid}/run/storeresult`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: params,
            })
            .then(r => {
                if (!r.ok) throw new Error(r.statusText);
                return r.json();
            })
            .then(data => {
                trialObj.resultId = data.resultId;
                resolve(trialObj);
            })
            .catch(() => {
                console.error(`Failed to post result (ID: ${trialObj.trial_id})`);
                reject(trialObj);
            });
        });
    };

    /**
     * Configure promise to return after max duration time has expired.
     * @param {object} trialObj
     */
    const setupMaxDuration = function (trialObj) {
        return new Promise(resolve => {
            setTimeout(() => {
                trialObj.keysPressed = '-';
                console.log("Trial ended with max duration.");
                resolve(trialObj);
            }, trialObj.max_duration);
        });
    };

    /**
     * Configure promise to resolve after an expected response key was pressed.
     * @param {object} trialObj
     */
    const setupKeyPresses = function (trialObj) {
        return new Promise((resolve, reject) => {
            trialObj.keysPressed = [];
            if (keydownHandler) { document.removeEventListener('keydown', keydownHandler); }
            keydownHandler = function (event) {
                // Get key and convert to code
                const key = Object.keys(codes).find(key => codes[key] === event.which).toString();
                trialObj.keysPressed.push(key);
                // Check if the pressed key is in expected response keys
                if (trialObj.response_keys.indexOf(key) !== -1) {
                    console.log("Trial ended with keypress.");
                    resetGlobalTimer();
                    resolve(trialObj);
                }
            };
            document.addEventListener('keydown', keydownHandler);
            // Click response allowed
            if (trialObj.response_keys.indexOf('click') !== -1) {
                if (clickHandler) { document.removeEventListener('click', clickHandler); }
                clickHandler = function (event) {
                    // Ignore clicks on exit button
                    if (!event.target.closest('#exit-button')) {
                        const key = `mouseX: ${event.screenX} - mouseY: ${event.screenY}`;
                        trialObj.keysPressed.push(key);
                        console.log("Trial ended with click.");
                        resetGlobalTimer();
                        resolve(trialObj);
                    }
                };
                document.addEventListener('click', clickHandler);
            }
        });
    };

    /**
     * Configure promise to resolve after video has finished playing.
     * @param {object} trialObj
     */
    const setupVideoEnd = function (trialObj) {
        return new Promise((resolve, reject) => {
            const video = document.querySelector(`#video-container-${trialObj.trial_id} > video`);
            const handler = function () {
                console.log("Trial ended with video end.", trialObj);
                trialObj.keysPressed = '-';
                resolve(trialObj);
            };
            videoEndedHandlerRefs[trialObj.trial_id] = handler;
            video.addEventListener('ended', handler);
        });
    };

    // Insert empty audio element
    createAudioContainer().then(() => {
        return preloadImages();
    }).then(() => {
        // Prompt webcam/microphone access
        if (recording_option !== 'NON') {
            mediaStream = webcam.initStream(recording_option);
            console.log(mediaStream);
            console.log(typeof (mediaStream));
            return mediaStream;
        }
        return Promise.resolve();
    }).then(() => {
        // Create DOM elements for all video trials (no data fetch yet) so the gesture
        // handler can unlock each element. showNextTrial will upgrade them to load=true
        // as trials approach, preserving the original 1-2 trial lookahead window.
        trials.forEach(trial => preloadVideo(trial, false));
        return new Promise((resolve, reject) => {
            document.getElementById('fullscreen-button').addEventListener('click', function () {
                const docElem = document.documentElement;
                docElem.requestFullscreen?.() ?? docElem.mozRequestFullScreen?.() ??
                    docElem.webkitRequestFullScreen?.() ?? docElem.msRequestFullscreen?.();
                document.getElementById('fullscreen-message')?.remove();
                // Unlock every video element for iOS: one play() inside a gesture handler
                // allows all subsequent play() calls on the same element without a gesture.
                trials.forEach(trial => {
                    if (trial.trial_type !== 'video') return;
                    const videoEl = document.querySelector(`#video-container-${trial.trial_id} > video`);
                    if (videoEl) videoEl.play().then(() => videoEl.pause()).catch(() => {});
                });
                resolve();
            });
        });
    }).then(() => {
        webcam.startUploading(subjectUuid);

        if (recording_option === 'EYE' || recording_option === 'ALL') {
            return initWebgazer();
        }
        return Promise.resolve();
    }).then(() => {
        // Start first trial
        showNextTrial();
        setGlobalTimer();
    });

    /**
     * Exit fullscreen mode.
     */
    const exitFullscreen = function () {
        document.exitFullscreen?.() ?? document.webkitExitFullscreen?.() ??
            document.mozCancelFullScreen?.() ?? document.msExitFullscreen?.();
    };

    /**
     * Go to exit/pause page.
     */
    const terminateStudy = function () {
        if (include_pause_page) {
            window.location.replace(`/${subjectUuid}/run/pause`);
        } else {
            window.location.replace(`/${subjectUuid}/run/thankyou`);
        }
    };

    const onFullscreenChange = function () {
        const fullScreen = document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen;
        if (!fullScreen) {
            terminateStudy();
        }
    };
    document.addEventListener('mozfullscreenchange', onFullscreenChange);
    document.addEventListener('webkitfullscreenchange', onFullscreenChange);
    document.addEventListener('fullscreenchange', onFullscreenChange);

    window.addEventListener('load', () => {
        document.getElementById('fullscreen-button')?.removeAttribute('disabled');
    });

    document.getElementById('confirmExitButton')?.addEventListener('click', function () {
        terminateStudy();
    });

    const exitModalElement = document.getElementById('exitStudyModal');
    let exitModal = null;
    if (exitModalElement) {
        exitModal = new bootstrap.Modal(exitModalElement);
        // Resolve "aria-hidden on focused element" warning by using 'inert' on background
        exitModalElement.addEventListener('show.bs.modal', function () {
            document.querySelectorAll('.container:not(#exitStudyModal)').forEach(el => el.setAttribute('inert', ''));
        });
        exitModalElement.addEventListener('hidden.bs.modal', function () {
            document.querySelectorAll('.container').forEach(el => el.removeAttribute('inert'));
        });
    }

    document.getElementById('exit-button').addEventListener('click', function () {
        if (webcam.getLength()) { // Upload queue not empty, show warning modal
            exitModal?.show();
        } else {
            terminateStudy();
        }
    });

}

init();
