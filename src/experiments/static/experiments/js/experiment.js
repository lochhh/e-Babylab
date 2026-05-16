'use strict';

(function () {
    const config = $('#trials').data();
    const trials = JSON.parse($('#trials-data').text());
    const loading_image = config.loadingImage;
    const global_timeout = config.globalTimeout;
    const include_pause_page = config.includePausePage;
    const recording_option = config.recordingOption;
    const general_onset = config.generalOnset;
    const show_gaze_estimations = config.showGazeEstimations;

    // Subject id
    const subjectUuid = $('#trials').data('subjectUuid');
    const subjectId = $('#trials').data('subjectId');

    // Body tag reference
    let body = $('body');

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

    // Populate keycode dictionary with letters
    for (let i = 97; i < 123; i++) {
        codes[String.fromCharCode(i)] = i - 32;
    }
    // Populate keycode dictionary with numbers
    for (let i = 48; i < 58; i++) {
        codes[i - 48] = i;
    }

    // Get Django CSRF token
    const csrftoken = Cookies.get('csrftoken');

    const csrfSafeMethod = method => /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);

    // Add CSRF to AJAX
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

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

            body.css('background-color', trialObj.background_colour);

            // Set up trial
            trialObj.webgazer_data = [];
            webgazer_data = [];
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
                $(document).off('keydown');
                $(document).off('click');
                if ((trialObj.is_calibration || trialObj.record_gaze) && (recording_option === 'EYE' || recording_option === 'ALL')) {
                    stopGazeRecording();
                }
                webgazer.pause();

                trialObj.end_time = performance.now();
                trialObj.webgazer_data = trialObj.webgazer_data.concat(webgazer_data);

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

                $(document).off('keydown mozfullscreenchange webkitfullscreenchange fullscreenchange');
                exitFullscreen();

                $.get(`/${subjectUuid}/run/error`).then(data => {
                    $("body").html(data);
                    $("div.alert").html(e);
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
    const preloadVideo = function (trialObj) {
        if (trialObj.trial_type !== 'video') return;

        console.log(`Preload video of trial ${trialObj.trial_id}`);
        const div = document.createElement('div');
        div.className = 'trial-video';
        div.style.display = 'none';
        div.id = `video-container-${trialObj.trial_id}`;

        const video = document.createElement('video');
        video.preload = 'auto';

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
        video.load();
    };

    /**
     * Load and play audio trial.
     * @param {object} trialObj
     */
    const playTrialAudio = function (trialObj) {
        return new Promise((resolve, reject) => {
            const audio = document.querySelector('.trial-audio audio');
            audio.querySelector('source').src = trialObj.audio_file;
            $(audio).on('canplay', function () {
                setTimeout(() => {
                    audio.play();
                    resolve(trialObj);
                }, Number(trialObj.audio_onset));
            });
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
                    video.play();
                    resolve(trialObj);
                }, Number(trialObj.visual_onset));
            };

            if (video.readyState > 3) {
                console.log("Video is fully loaded.");
                displayVideo();
            } else {
                console.log("Video is still loading.");
                $(video).on('canplay', displayVideo);
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
            timePerPoint = trialObj.max_duration / trialObj.calibration_points.length;
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
        $('#trials').css({
            'height': '100%', 'width': '100%',
            'background-image': `url('${loading_image}')`,
            'background-position': 'center',
            'background-repeat': 'no-repeat',
            'background-size': 'contain'
        });
        $('#trials').show();
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
        if (document.querySelector('.trial-audio audio')) {
            $('.trial-audio audio').off('canplay');
            document.querySelector('.trial-audio audio').pause();
            document.querySelector('.trial-audio audio source').src = '';
        }
    };

    /**
     * Remove trial video from page.
     */
    const removeTrialVideo = function (trialObj) {
        const video = document.querySelector(`#video-container-${trialObj.trial_id} > video`);
        $(video).off('canplay');
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
            $.ajax({
                url: `/${subjectUuid}/run/storeresult`,
                data: {
                    'trialitem': trialObj.trial_id,
                    'start_time': trialObj.start_time,
                    'end_time': trialObj.end_time,
                    'key_pressed': keysPressed,
                    'trial_number': trialObj.trial_number,
                    'resolution_w': window.screen.width,
                    'resolution_h': window.screen.height,
                    'webgazer_data': JSON.stringify(trialObj.webgazer_data),
                },
                method: 'POST'
            }).done(function (data) {
                trialObj.resultId = data.resultId;
                resolve(trialObj);
            }).fail(function () {
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
            $(document).off('keydown');
            $(document).on('keydown', function (event) {
                // Get key and convert to code
                const key = Object.keys(codes).find(key => codes[key] === event.which).toString();
                trialObj.keysPressed.push(key);
                // Check if the pressed key is in expected response keys
                if (trialObj.response_keys.indexOf(key) !== -1) {
                    console.log("Trial ended with keypress.");
                    resetGlobalTimer();
                    resolve(trialObj);
                }
            });
            // Click response allowed
            if (trialObj.response_keys.indexOf('click') !== -1) {
                $(document).off('click');
                $(document).on('click', function (event) {
                    // Ignore clicks on exit button
                    if (!$(event.target).closest('#exit-button').length) {
                        const key = `mouseX: ${event.screenX} - mouseY: ${event.screenY}`;
                        trialObj.keysPressed.push(key);
                        console.log("Trial ended with click.");
                        resetGlobalTimer();
                        resolve(trialObj);
                    }
                });
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
            $(video).on('ended', function () {
                console.log("Trial ended with video end.", trialObj);
                trialObj.keysPressed = '-';
                resolve(trialObj);
            });
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
        return new Promise((resolve, reject) => {
            $("#fullscreen-button").click(function () {
                const docElem = document.documentElement;
                docElem.requestFullscreen?.() ?? docElem.mozRequestFullScreen?.() ??
                    docElem.webkitRequestFullScreen?.() ?? docElem.msRequestFullscreen?.();
                $("#fullscreen-message").remove();
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

    $(document).on('mozfullscreenchange webkitfullscreenchange fullscreenchange', function () {
        const fullScreen = document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen;
        if (!fullScreen) {
            terminateStudy();
        }
    });

    $(window).on('load', function () {
        $('#fullscreen-button').prop('disabled', false);
    });

    $('#confirmExitButton').click(function () {
        terminateStudy();
    });

    const exitModalElement = document.getElementById('exitStudyModal');
    let exitModal = null;
    if (exitModalElement) {
        exitModal = new bootstrap.Modal(exitModalElement);
        // Resolve "aria-hidden on focused element" warning by using 'inert' on background
        exitModalElement.addEventListener('show.bs.modal', function () {
            $('.container').not('#exitStudyModal').attr('inert', '');
        });
        exitModalElement.addEventListener('hidden.bs.modal', function () {
            $('.container').removeAttr('inert');
        });
    }

    $("#exit-button").click(function () {
        if (webcam.getLength()) { // Upload queue not empty, show warning modal
            exitModal?.show();
        } else {
            terminateStudy();
        }
    });

})();
