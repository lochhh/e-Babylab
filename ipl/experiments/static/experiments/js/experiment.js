'use strict';

(function (trials, loading_image, global_timeout, include_pause_page, recording_option, general_onset) {

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
            
            // TODO: Properly stop recording and make sure to delete files
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

            // Start webcam recording
            let recording;
            if(recording_option != 'NON' && trialObj.record_media) {
                recording = webcam.startRecording(subjectId + "_trial" + String(currentTrial+1) + "_" + trialObj.label + "_" + subjectUuid, recording_option, mediaStream);
            }else{
                recording = Promise.resolve();
            }
            recording.then(function() {
                // Setup trial
                let trialSetupPromises = [];
                if (trialObj.audio_file != '') {
                    trialSetupPromises.push(playTrialAudio(trialObj));
                }
                if (trialObj.trial_type == 'video') {
                    trialSetupPromises.push(playTrialVideo(trialObj));
                } else {
                    trialSetupPromises.push(showTrialImage(trialObj));
                }

                // wait before accepting responses
                let waitTime = parseInt(general_onset);
                trialSetupPromises.push(waitPromise(waitTime, trialObj));
                return Promise.all(trialSetupPromises)

            }).then(function(values) {
                let trialObj = values[0]; // Get trialObj from first promise

                // Set start time
                trialObj.start_time = new Date().toISOString();
                
                // Register promise to determine end of trial
                let trialDonePromises = [];
                if (trialObj.trial_type == 'video' && trialObj.require_user_input == 'NO') {
                    trialDonePromises.push(setupVideoEnd(trialObj));
                }
                if (trialObj.trial_type == 'image' || (trialObj.trial_type == 'video' && trialObj.require_user_input == 'YES')) {
                    trialDonePromises.push(setupMaxDuration(trialObj));
                }
                if (trialObj.require_user_input == 'YES') {
                    trialDonePromises.push(setupKeyPresses(trialObj));
                }
                return Promise.race(trialDonePromises);

            }).then(function(trialObj) {
                $(document).off('keydown');
                $(document).off('click');
                trialObj.end_time = new Date().toISOString();

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

                // Turn off listeners
                $(document).off('keydown mozfullscreenchange webkitfullscreenchange fullscreenchange');
                exitFullscreen();

                $.get('/' + subjectUuid + '/run/error').then(function(data) {
                    $("body").html(data);
                    $("div.alert").html(e);
                });

                console.log("Error during experiment:", e);
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
                setTimeout(displayVideo, Number(trialObj.visual_onset));
            }else{ // Video is still loading
                $(video).on('canplay', displayVideo);
            }
        });
    };

    /**
     * Load and show image trial.
     * @param {*} trialObj 
     */
    let showTrialImage = function(trialObj) {
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
        document.querySelector('.trial-image').outerHTML = '';
    };

    /**
     * Remove trial audio from page.
     */
    let removeTrialAudio = function() {
        $('.trial-audio audio').off('canplay');
        document.querySelector('.trial-audio audio').pause();
        document.querySelector('.trial-audio').outerHTML = '';
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
                },
                method: 'POST'
            }).done(function(data) {
                trialObj.resultId = data.resultId;
                resolve(trialObj);
            }).fail(function() {
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
                var docElem = document.documentElement;
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

    $(document).on('mozfullscreenchange webkitfullscreenchange fullscreenchange', function() {
        let fullScreen = document.fullScreen || document.mozFullScreen || document.webkitIsFullScreen;
        // Go to pause page or end experiment immediately when leaving fullscreen
        if(!fullScreen) {
            if (include_pause_page.toLowerCase() == 'true') {
                window.location.replace('/' + subjectUuid + '/run/pause');
            } else {
                window.location.replace('/' + subjectUuid + '/run/thankyou');
            }
        }
    });

    $("#exit-button").click(function() {
        if (include_pause_page.toLowerCase() == 'true') {
            window.location.replace('/' + subjectUuid + '/run/pause');
        } else {
            window.location.replace('/' + subjectUuid + '/run/thankyou');
        }
    });

})(trials, loading_image, global_timeout, include_pause_page, recording_option, general_onset);
