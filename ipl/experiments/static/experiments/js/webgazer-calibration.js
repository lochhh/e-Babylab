/*
Code adapted from:
- https://github.com/brownhci/WebGazer 
- https://github.com/adriansteffan/mb2-webcam-eyetracking
*/

// Default eye-tracker calibration points 
const defaultPoints = [[50, 50], [50, 12], [12, 12], [12, 50], [12, 88], [50, 88], [88, 88], [88, 50], [88, 12]];
let validationTime = 4000;
let samplingInterval = 34;
let timeToSaccade = 1000;
let timePerPoint = 2050;
let gazeInterval;
let webgazer_data = [];

/**
 * Initialises webgazer for eye-tracking.
 */
let initWebgazer = function() {
    return new Promise(function(resolve, reject) {
        if (typeof webgazer == 'undefined') {
            const error = 'Failed to start webgazer.';
            console.error(error);
            reject(error);
        }
        let showPredictions = show_gaze_estimations.toLowerCase() == 'true';
        webgazer.params.showGazeDot = showPredictions;
        
        webgazer.setRegression('ridge')
                .setGazeListener(function(data, clock) { 
                  //console.log(data); /* data is an object containing an x and y key which are the x and y prediction coordinates (no bounds limiting) */
                  //console.log(clock); /* elapsed time in milliseconds since webgazer.begin() was called */
                })
                .saveDataAcrossSessions(false)
                .removeMouseEventListeners()
                .begin()
                .then(() => {
                    webgazer.showVideoPreview(true) /* shows all video previews */
                            .showPredictionPoints(showPredictions) /* shows a square every 100 milliseconds where current prediction is */
                            .applyKalmanFilter(true); /* Kalman Filter defaults to on. Can be toggled by user. */
                    // Set up the webgazer video feedback.
                    let setup = function() {
                        // Set up the main canvas. The main canvas is used to calibrate the webgazer.
                        let canvas = document.getElementById('plotting_canvas');
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                        canvas.style.position = 'fixed';
                        canvas.style.display = 'block';
                        // Set up the video feedback
                        let videoContainer = $('#webgazerVideoContainer');
                        videoContainer.prependTo('#webgazer-init .col');
                        videoContainer.css({'left': 'calc(50% - 160px)',
                                            'top': '10%'});
                    };
                    setup();

                    // show calibration instructions
                    $('#webgazer-init').show();

                    // enable continue button when face is detected
                    if (faceDetected) {
                        $('#webgazer-init button').prop('disabled', false);
                    } else {
                        let observer = new MutationObserver(faceDetectEventObserver);
                        observer.observe(document, {
                            attributes: true,
                            attributeFilter: ['style'],
                            subtree: true
                        });
                    }

                    $('#webgazer-init button').click(function(){
                        if (typeof observer != 'undefined') {
                            observer.disconnect();
                        }
                        webgazer.pause();
                        $('#webgazer-init').hide();
                        resolve();
                    });
                })
                .catch((error) => {
                    console.error(error);
                    reject(error);
                });
    });
};

/**
 * Checks whether face has been detected by webgazer.
 */
let faceDetected = function() {
    if (document.querySelector('#webgazerFaceFeedbackBox')){
        return document.querySelector('#webgazerFaceFeedbackBox').style.borderColor == 'green';
      } else {
        return false;
      }
};

/**
 * Enables/disables continue button depending on 
 * whether face has been detected by webgazer.
 * @param {*} mutationsList 
 * @param {*} observer 
 */
let faceDetectEventObserver = function(mutationsList, observer) {
    if (mutationsList[0].target == document.querySelector('#webgazerFaceFeedbackBox')) {
        if (mutationsList[0].type == 'attributes' && mutationsList[0].target.style.borderColor == 'green') {
            $('#webgazer-init button').prop('disabled', false);
        }
        if (mutationsList[0].type == 'attributes' && mutationsList[0].target.style.borderColor == 'red') {
            $('#webgazer-init button').prop('disabled', true);
        }
      }
};

/**
 * Wrapper function for calibrating and validating webgazer.
 * @param {*} trialObj 
 */
let calibrate = async function(trialObj) {
    for (let ptId = 0; ptId < trialObj.calibration_points.length; ptId++) {
        await showCalibrationPoint(trialObj, ptId);
        await calibrateGaze(ptId);
    }
    return await validateGaze(trialObj);
}

/**
 * Shows next calibration point and hides previous calibration point.
 * @param {*} trialObj 
 * @param {*} ptId 
 */
let showCalibrationPoint = function(trialObj, ptId) {
    return new Promise(function(resolve, reject) {
        console.log('showcalibrationpoint ' + ptId);
        // hide previous pt
        if (ptId > 0) {
            $('#Pt' + (ptId - 1)).hide(); 
        }
        // show next pt
        if (ptId < trialObj.calibration_points.length) {
            $('#Pt' + ptId).show();
        }
        resolve(ptId);
    });
};

/**
 * Calibrates webgazer without clicking, by assuming gaze locations.
 * @param {*} ptId 
 */
let calibrateGaze = function(ptId) {
    return new Promise(function(resolve, reject) {
        console.log('calibrategaze ' + ptId);
        let br = document.querySelector('#Pt' + ptId).getBoundingClientRect();
        let x = br.left + br.width / 2;
        let y = br.top + br.height / 2;
        let ptStart = performance.now() + timeToSaccade;
        let ptEnd = performance.now() + timeToSaccade + timePerPoint;
  
        requestAnimationFrame(function watch_dot() {
            if (performance.now() > ptStart) {
                webgazer.recordScreenPosition(x, y, 'click');
            }
            if (performance.now() < ptEnd) {
                requestAnimationFrame(watch_dot);
            } else {
                resolve(ptId);
            }
        });
    });
};

/**
 * Displays the first calibration point again and 
 * validates webgazer predictions based on the last 50 points.
 * @param {*} trialObj 
 */
let validateGaze = function(trialObj) {
    return new Promise(function(resolve, reject) {
        console.log('validategaze');
        $('.calibration-image').hide();
        $('#Pt0').show(); 
        // clears the canvas
        let canvas = document.getElementById('plotting_canvas');
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        webgazer.params.storingPoints = true;
        setTimeout(function() {
            webgazer.params.storingPoints = false;
            let past50 = webgazer.getStoredPoints();
            let precisionMeasurement = calculatePrecision(past50);
            let d = {
                trial_type: 'validation',
                accuracy: precisionMeasurement,
                x_points: past50[0],
                y_points: past50[1],
            };
            trialObj.webgazer_data.push(d);
            trialObj.keysPressed = '-';
            resolve(trialObj);
        }, validationTime);
    });
};

let startGazeRecording = function() {
    // reset webgazer.clockStart
    clockStart = performance.now();
    gazeInterval = setInterval(function() {
        webgazer.getCurrentPrediction()
        .then(handleGazeDataUpdate);
    }, samplingInterval)
    // repeat the call here so that we get one immediate execution. above will not
    // start until samplingInterval is reached the first time.
    webgazer.getCurrentPrediction()
    .then(handleGazeDataUpdate);
}

let stopGazeRecording = function() {
    clearInterval(gazeInterval);
};

let handleGazeDataUpdate = function(data, elapsedTime) {
    if (data !== null) {
        data = webgazer.util.bound(data)
        let d = {
            x: Math.round(data.x),
            y: Math.round(data.y),
            t: performance.now() - clockStart,
        }
        webgazer_data.push(d);
    }
};

/*
 * This function calculates a measurement for how precise 
 * the eye tracker currently is which is displayed to the user
 */
let calculatePrecision = function(past50Array) {
    let windowHeight = $(window).height();
    //let windowWidth = $(window).width();
    let br = document.querySelector('#Pt0').getBoundingClientRect();
   
    // Retrieve the last 50 gaze prediction points
    let x50 = past50Array[0];
    let y50 = past50Array[1];
  
    // Calculate the position of the point the user is staring at
    let staringPointX = br.left + br.width / 2; //windowWidth / 2;
    let staringPointY = br.top + br.height / 2; //windowHeight / 2;
  
    let precisionPercentages = new Array(50);
    calculatePrecisionPercentages(precisionPercentages, windowHeight, x50, y50, staringPointX, staringPointY);
    let precision = calculateAverage(precisionPercentages);
  
    // Return the precision measurement as a rounded percentage
    return Math.round(precision);
};
  
/*
* Calculate percentage accuracy for each prediction based on distance of
* the prediction point from the centre point (uses the window height as
* lower threshold 0%)
*/
let calculatePrecisionPercentages = function(precisionPercentages, windowHeight, x50, y50, staringPointX, staringPointY) {
    for (x = 0; x < 50; x++) {
        // Calculate distance between each prediction and staring point
        let xDiff = staringPointX - x50[x];
        let yDiff = staringPointY - y50[x];
        let distance = Math.sqrt((xDiff * xDiff) + (yDiff * yDiff));
  
        // Calculate precision percentage
        let halfWindowHeight = windowHeight / 2;
        let precision = 0;
        if (distance <= halfWindowHeight && distance > -1) {
            precision = 100 - (distance / halfWindowHeight * 100);
        } else if (distance > halfWindowHeight) {
            precision = 0;
        } else if (distance > -1) {
            precision = 100;
        }
  
        // Store the precision
        precisionPercentages[x] = precision;
    }
};
  
/*
* Calculates the average of all precision percentages calculated
*/
let calculateAverage = function(precisionPercentages) {
    let precision = 0;
    for (x = 0; x < 50; x++) {
        precision += precisionPercentages[x];
    }
    precision = precision / 50;
    return precision;
};