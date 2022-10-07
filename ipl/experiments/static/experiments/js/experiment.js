'use strict';

(function (trials, loading_image, global_timeout, include_pause_page, recording_option, general_onset, show_gaze_estimations) {

    // Subject id
    const subjectUuid = $('#trials').data('subjectUuid');
    const subjectId = $('#trials').data('subjectId');

    // Body tag reference
    let body = $('body');

    // Key codes
    let codes = {
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

    let csrfSafeMethod = function (method) {
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

    /**
     * Setup global timeout.
     */
    let setGlobalTimer = function() {
        globaltimer = setTimeout(function() {
            
            // TODO: Properly stop recording
            webcam.stopUploading();
            if (include_pause_page.toLowerCase() == 'true') {
                // go to pause page
                window.location.replace('/' + subjectUuid + '/run/pause');
            } else {
                window.location.replace('/' + subjectUuid + '/run/thankyou');
            }
        }, Number(global_timeout));
    };

    /**
     * Reset global timeout.
     */
    let resetGlobalTimer = function() {
        clearTimeout(globaltimer);
        setGlobalTimer();
    }

    /**
     * Show next trial.
     */
    let showNextTrial = function() {
        if (currentTrial >= trials.length) { // No more trials
            // Clear global timeout
            clearTimeout(globaltimer);

            // TODO: check here 
            webgazer.pause();
            
            // Wait until webcam upload is done
            waitForWebcamUploadToFinish().then(function() {
                webcam.stopUploading();
                window.location.replace('/' + subjectUuid + '/run/thankyou');
            });

        }else{ // Start trial
            let trialObj = trials[currentTrial];

            // If current trial is first, preload
            if(currentTrial == 0) {
                preloadVideo(trialObj);
            }

            // Preload next trial
            if (currentTrial + 1 < trials.length) {
                preloadVideo(trials[currentTrial + 1]);
            }

            // Set background color
            body.css('background-color', trialObj.background_colour);

            // Setup trial
            trialObj.webgazer_data = [];
            webgazer_data = [];
            let trialSetupPromises = [];
            if (trialObj.audio_file != '') {
                trialSetupPromises.push(playTrialAudio(trialObj));
            }
            if (trialObj.trial_type == 'video') {
                trialSetupPromises.push(playTrialVideo(trialObj));
            } else {
                trialSetupPromises.push(showTrialImage(trialObj));
            }

            // Start webcam recording when recording_option == aud, vid, all 
            if (recording_option != 'NON' && recording_option != 'EYE' && trialObj.record_media) {
                trialSetupPromises.push(webcam.startRecording(subjectId + "_trial" + String(currentTrial+1) + "_" + trialObj.label + "_" + subjectUuid, recording_option, mediaStream));
            }

            // Resume webgazer and start recording gaze
            if (trialObj.is_calibration || trialObj.record_gaze && (recording_option == 'EYE' || recording_option == 'ALL')) {
                trialSetupPromises.push(webgazer.resume().then(() => {
                    if (trialObj.record_gaze) {
                        startGazeRecording();
                    }
                })); 
            }
            
            // Wait before accepting responses
            if (trialObj.require_user_input == 'YES') {
                let waitTime = parseInt(general_onset);
                trialSetupPromises.push(waitPromise(waitTime, trialObj));
            }

            Promise.all(trialSetupPromises).then(function(values) {
                let trialObj = values[0]; // Get trialObj from first promise

                // Set start time
                trialObj.start_time = performance.now();
                
                // Register promise to determine end of trial
                let trialDonePromises = [];

                if (trialObj.trial_type == 'video' && trialObj.require_user_input == 'NO') {
                    trialDonePromises.push(setupVideoEnd(trialObj));
                }
                if ((trialObj.trial_type == 'image' && !trialObj.is_calibration) || (trialObj.trial_type == 'video' && trialObj.require_user_input == 'YES')) {
                    trialDonePromises.push(setupMaxDuration(trialObj));
                }
                if (trialObj.require_user_input == 'YES' && !trialObj.is_calibration) {
                    trialDonePromises.push(setupKeyPresses(trialObj));
                }
                if (trialObj.is_calibration && (recording_option == 'EYE' || recording_option == 'ALL')) {
                    trialDonePromises.push(calibrate(trialObj));
                }
                return Promise.race(trialDonePromises);

            }).then(function(trialObj) {
                console.log(trialObj);
                $(document).off('keydown');
                $(document).off('click');
                // Pause webgazer
                if (trialObj.record_gaze && (recording_option == 'EYE' || recording_option == 'ALL')) {
                    stopGazeRecording();
                }
                webgazer.pause();

                trialObj.end_time = performance.now();
                trialObj.webgazer_data = trialObj.webgazer_data.concat(webgazer_data);

                // Remove trial
                if (trialObj.audio_file != '') {
                    removeTrialAudio();
                }
                if (trialObj.trial_type == 'video') {
                    removeTrialVideo(trialObj);
                } else {
                    removeTrialImage();
                }

                return postResult(trialObj);
                
            }).then(function(trialObj) {
                return webcam.stopRecording(trialObj.resultId);
            }).then(function() {
                currentTrial++;
                showNextTrial();
            }).catch(function(e) {
                // Clear global timeout
                clearTimeout(globaltimer);

                // Stop upload
                webcam.stopUploading();
                webcam.stopRecording("");

                // Stop webgazer
                if (trialObj.record_gaze && (recording_option == 'EYE' || recording_option == 'ALL')) {
                    stopGazeRecording();
                }
                webgazer.pause();

                // Turn off listeners
                $(document).off('keydown mozfullscreenchange webkitfullscreenchange fullscreenchange');
                exitFullscreen();

                $.get('/' + subjectUuid + '/run/error').then(function(data) {
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
    let waitPromise = function(waitTime, param) {
        return new Promise(function(resolve) {
            setTimeout(function() {
                resolve(param);
            }, waitTime);
        });
    }

    /**
     * Preload images of all trials.
     */
    let preloadImages = function() {
        let p_list = [];

        for (let t in trials) {
            if (t.trial_type == 'image') {
                let p = new Promise(function(resolve, reject) {
                    let image = new Image();
                    image.onload = function() {
                        resolve();
                    }
                    image.src = t.visual_file;
                });
                p_list.push(p);
            }
        }

        return Promise.all(p_list)
    };

    /**
     * Preload video for trial.
     * @param {*} trialObj 
     */
    let preloadVideo = function(trialObj) {
        if(trialObj.trial_type != 'video') return;

        console.log("Preload video of trial " + (trialObj.trial_id).toString());
        let div = document.createElement('div');
        div.className = 'embed-responsive trial-video';
        div.style.display = 'none';
        div.id = 'video-container-' + trialObj.trial_id;

        let video = document.createElement('video');
        video.className = 'embed-responsive-item';
        video.preload = 'auto';

        let source1 = document.createElement('source');
        source1.src = trialObj.visual_file;
        source1.type = 'video/mp4';

        let source2 = document.createElement('source');
        source2.src = trialObj.visual_file;
        source2.type = 'video/ogg';
        
        let source3 = document.createElement('source');
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
     * @param {*} trialObj 
     */
    let playTrialAudio = function(trialObj) {
        return new Promise(function(resolve, reject) {
            let div = document.createElement('div');
            div.className = 'embed-responsive trial-audio';

            let audio = document.createElement('audio');
            audio.className = 'embed-responsive-item';
            audio.hidden = 'hidden';

            let source = document.createElement('source');
            source.src = trialObj.audio_file;
            source.type = 'audio/mpeg';

            audio.append(source);
            div.append(audio);
            body.append(div);
            $(audio).on('canplay', function() {
                setTimeout(function() {
                    audio.play();
                    resolve(trialObj);
                }, Number(trialObj.audio_onset));
            });
            audio.load();
        });
    };

    /**
     * Load and play video trial.
     * @param {*} trialObj 
     */
    let playTrialVideo = function(trialObj) {
        return new Promise(function(resolve, reject) {
            // Get video element that was created by preloadVideo()
            let video = document.querySelector('#video-container-' + trialObj.trial_id + ' > video');
            let displayVideo = function() {
                setTimeout(function() {
                    document.querySelector('#video-container-' + trialObj.trial_id).style.display = 'block';
                    video.play();
                    resolve(trialObj);
                }, Number(trialObj.visual_onset));
            };

            // Video is already fully loaded
            if (video.readyState > 3) {
                console.log("Video is fully loaded.");
                displayVideo();
            }else{ // Video is still loading
                console.log("Video is still loading.");
                $(video).on('canplay', displayVideo);
            }
        });
    };

    /**
     * Load and show image.
     * @param {*} trialObj 
     */
    let showTrialImage = function(trialObj) {
        if (trialObj.is_calibration && (recording_option == 'EYE' || recording_option == 'ALL')) {
            if (trialObj.calibration_points.length == 0) {
                trialObj.calibration_points = defaultPoints;
            }
            timePerPoint = trialObj.max_duration / trialObj.calibration_points.length;
            trialObj.calibration_points.forEach(function (pt, i) {
                let img = document.createElement('img');
                img.className = 'calibration-image';
                img.src = trialObj.visual_file;
                img.id = 'Pt' + i;
                img.style = `width: 6vw; position: absolute; transform: translate(-50%, -50%); left: ${pt[0]}%; top: ${pt[1]}%; display: none`;
                body.append(img);
            });
            return waitPromise(Number(trialObj.visual_onset), trialObj);
        }
        return new Promise(function(resolve, reject) {
            let img = document.createElement('div');
            img.className = 'trial-image';
            img.style.backgroundImage = "url('" + trialObj.visual_file + "')";
            setTimeout(function() {
                body.append(img);
                resolve(trialObj);
            }, Number(trialObj.visual_onset));
        });
    };

    /**
     * Wait for upload queue to be empty.
     */
    let waitForWebcamUploadToFinish = function() {
        // Show loading image
        $('#trials').css({'height':'100%', 'width':'100%'}); 
        $('#trials').html('<img src="' + loading_image + '" alt="Loading..." style="display: block; max-height:100%; margin: 0 auto;"/>');
        $('#trials').show();
        console.log("Check queue.");
        return webcam.waitForQueue(0);
    };

    /**
     * Remove trial image from page.
     */
    let removeTrialImage = function() {
        if (document.querySelector('.calibration-image')) {
            document.querySelector('.calibration-image').outerHTML = '';
        } else {
            document.querySelector('.trial-image').outerHTML = '';
        }
    };

    /**
     * Remove trial audio from page.
     */
    let removeTrialAudio = function() {
        if (document.querySelector('.trial-audio audio')) {
            $('.trial-audio audio').off('canplay');
            document.querySelector('.trial-audio audio').pause();
            document.querySelector('.trial-audio').outerHTML = '';
        }
    };

    /**
     * Remove trial video from page.
     */
    let removeTrialVideo = function(trialObj) {
        let video = document.querySelector('#video-container-' + trialObj.trial_id + ' > video');
        $(video).off('canplay');
        video.pause();
        document.querySelector('.trial-video').outerHTML = '';
    };

    /**
     * Send trial results to backend.
     * @param {*} trialObj 
     */
    let postResult = function(trialObj) {
        return new Promise(function(resolve, reject) {
            console.log("Send results", trialObj);
            let keysPressed = trialObj.keysPressed;
            if(keysPressed instanceof Array) {
                keysPressed = keysPressed.join(',');
            }
            $.ajax({
                url: '/' + subjectUuid + '/run/storeresult',
                data: {
                    'trialitem': trialObj.trial_id,
                    'start_time': trialObj.start_time,
                    'end_time': trialObj.end_time,
                    'key_pressed': keysPressed,
                    'trial_number': currentTrial + 1,
                    'resolution_w': window.screen.width,
                    'resolution_h': window.screen.height,
                    'webgazer_data': JSON.stringify(trialObj.webgazer_data),
                },
                method: 'POST'
            }).done(function(data) {
                trialObj.resultId = data.resultId;
                resolve(trialObj);
            }).fail(function() {
                console.error('Failed to post result (ID: ' + trialObj.trial_id + ')');
                reject(trialObj);
            });
        });
    };

    /**
     * Configure promise to return after max duration time has expired.
     * @param {*} trialObj 
     */
    let setupMaxDuration = function(trialObj) {
        return new Promise(function(resolve, reject) {
            setTimeout(function() {
                trialObj.keysPressed = '-';
                console.log("Trial ended with max duration.");
                resolve(trialObj);
            }, trialObj.max_duration);
        });
    };
    
    /**
     * Configure promise to resolve after an expected response key was pressed.
     * @param {*} trialObj 
     */
    let setupKeyPresses = function(trialObj) {
        return new Promise(function(resolve, reject) {
            trialObj.keysPressed = [];
            $(document).off('keydown');
            $(document).on('keydown', function(event) {
                // Get key and convert to code
                let key = Object.keys(codes).find(key => codes[key] === event.which).toString();
                trialObj.keysPressed.push(key);
                // Correct key was pressed
                if(trialObj.response_keys.indexOf(key) !== -1) {
                    console.log("Trial ended with keypress.");
                    resetGlobalTimer();
                    resolve(trialObj);
                };
            });
            // Click response allowed
            if(trialObj.response_keys.indexOf('click') !== -1) {
                $(document).off('click');
                $(document).on('click', function(event) {
                    // if area clicked is not the exit button
                    if(!$(event.target).closest('#exit-button').length) {
                        let key = "mouseX: " + String(event.screenX) + " - mouseY: " + String(event.screenY);
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
     * @param {*} trialObj 
     */
    let setupVideoEnd = function(trialObj) {
        return new Promise(function(resolve, reject) {
            let video = document.querySelector('#video-container-' + trialObj.trial_id + ' > video');
            $(video).on('ended', function() {
                console.log("Trial ended with video end.", trialObj);
                trialObj.keysPressed = '-';
                resolve(trialObj);
            });
        });
    };

    //$('#webgazer-init').hide();
    // Preload images
    preloadImages().then(function() {

        // Prompt webcam/microphone access before fullscreen
        if(recording_option != 'NON') {
            mediaStream = webcam.initStream(recording_option);
            console.log(mediaStream);
            console.log(typeof(mediaStream));
            return mediaStream;
        }
        return Promise.resolve();
    }).then(function() {

        // Ask user to click button to go into fullscreen
        return new Promise(function(resolve, reject) {
            $("#fullscreen-button").click(function() {
                let docElem = document.documentElement;
                if(docElem.requestFullscreen) {
                    docElem.requestFullscreen();
                }else if(docElem.mozRequestFullScreen) {
                    docElem.mozRequestFullScreen();
                }else if(docElem.webkitRequestFullScreen) {
                    docElem.webkitRequestFullScreen();
                }else if(docElem.msRequestFullscreen) {
                    docElem.msRequestFullscreen();
                }
                $("#fullscreen-message").remove();
                //$("#fullscreen-button").hide();
                resolve();
            });
        });
    }).then(function() {
        // Start webcam uploading
        webcam.startUploading(subjectUuid);

        // Check if eye-tracking is required
        if (recording_option == 'EYE' || recording_option == 'ALL') {
            // initialise and setup webgazer
            return initWebgazer();
        } else {
            return Promise.resolve();
        }
    }).then(function() {
        // Start with first trial
        showNextTrial();
        
        // Set global timeout
        setGlobalTimer();
    });

    /**
     * Exit fullscreen mode.
     */
    let exitFullscreen = function() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    };

    /**
     * Go to exit/pause page.
     */
    let terminateStudy = function() {
        if (include_pause_page.toLowerCase() == 'true') {
            window.location.replace('/' + subjectUuid + '/run/pause');
        } else {
            window.location.replace('/' + subjectUuid + '/run/thankyou');
        }
    };

    $(document).on('mozfullscreenchange webkitfullscreenchange fullscreenchange', function() {
        let fullScreen = document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen;
        // Go to pause page or end experiment immediately when leaving fullscreen
        if(!fullScreen) {
            terminateStudy();
        }
    });

    $('#confirmExitButton').click(function() {
        terminateStudy();
    });
    
    $("#exit-button").click(function() {
        if (webcam.getLength()) { // Upload queue is not empty, show confirmation dialog
            $('#exitStudyModal').modal('show');
        } else {
            terminateStudy();
        }
    });

})(trials, loading_image, global_timeout, include_pause_page, recording_option, general_onset, show_gaze_estimations);