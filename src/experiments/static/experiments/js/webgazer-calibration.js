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
  
        requestAnimationFrame(function watchDot() {
            if (performance.now() > ptStart) {
                webgazer.recordScreenPosition(x, y, 'click');
            }
            if (performance.now() < ptEnd) {
                requestAnimationFrame(watchDot);
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
            let target = document.querySelector('#Pt0').getBoundingClientRect();
            // Calculate the centre position of the target
            let targetX = target.left + target.width / 2; 
            let targetY = target.top + target.height / 2;
            let numPredictions = past50[0].filter(Boolean).length;
            let accuracy = calculateAccuracy(past50, numPredictions, targetX, targetY);
            let precisionRMS = calculatePrecisionRMS(past50, numPredictions);
            let precisionSD = calculatePrecisionSD(past50, numPredictions);
            //let precisionMeasurement = calculatePrecision(past50, numPredictions, targetX, targetY);

            let d = {
                trial_type: 'validation',
                target_x: targetX,
                target_y: targetY,
                x: past50[0],
                y: past50[1],
                accuracy: accuracy,
                precision_rms: precisionRMS,
                precision_sd_x: precisionSD[0],
                precision_sd_y: precisionSD[1],
                //precision_perc: precisionMeasurement,
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

/**
 * This function calculates Accuracy as the mean Euclidean distance (in pixels)
 * between a given array of gaze locations and the centre position of the target.
 * 
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
 * @param {*} past50Array
 * @param {number} numPredictions
 * @param {number} targetX
 * @param {number} targetY
 */
let calculateAccuracy = function(past50Array, numPredictions, targetX, targetY) {
    let totalDistance = 0;

    for (let i = 0; i < numPredictions; i++) {
        let xDiff = past50Array[0][i] - targetX;
        let yDiff = past50Array[1][i] - targetY;
        let distance = Math.sqrt((xDiff * xDiff) + (yDiff * yDiff));
        totalDistance += distance;
    }
    
    let accuracy = totalDistance / numPredictions;

    return accuracy;    
};

/**
 * This function calculates precision as the root mean square distance between 
 * successive gaze locations. Since such inter-sample distances only compare 
 * temporally adjacent samples, they may be less sensitive to large overall spatial 
 * dispersion of the data.
 * 
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
 * @param {*} past50Array
 * @param {number} numPredictions
 */
let calculatePrecisionRMS = function(past50Array, numPredictions) {
    let sumSquaredDistances = 0;

    for (let i = 1; i < numPredictions; i++) {
        let xDiff = past50Array[0][i] - past50Array[0][i - 1];
        let yDiff = past50Array[1][i] - past50Array[1][i - 1];
        let squaredDistance = (xDiff * xDiff) + (yDiff * yDiff);
        sumSquaredDistances += squaredDistance;
    }

    let meanSquaredDistance = sumSquaredDistances / (numPredictions - 1);
    let precision = Math.sqrt(meanSquaredDistance);

    return precision;
};

/**
 * This function calculates precision as the standard deviation of the gaze 
 * locations in the X and Y dimensions separately. This measures how dispersed
 * samples are from their mean value.
 * 
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
 * @param {*} past50Array
 * @param {number} numPredictions
 */
let calculatePrecisionSD = function(past50Array, numPredictions) {
    // Calculate mean x and y coordinates
    let meanX = 0;
    let meanY = 0;
    for (let i = 0; i < numPredictions; i++) {
        meanX += past50Array[0][i];
        meanY += past50Array[1][i];
    }
    meanX /= numPredictions;
    meanY /= numPredictions;

    // Calculate sum of squared differences for x and y dimensions
    let sumSquaredDifferencesX = 0;
    let sumSquaredDifferencesY = 0;
    for (let i = 0; i < numPredictions; i++) {
        let diffX = past50Array[0][i] - meanX;
        let diffY = past50Array[1][i] - meanY;
        sumSquaredDifferencesX += diffX * diffX;
        sumSquaredDifferencesY += diffY * diffY;
    }

    // Calculate variance for x and y dimensions
    let varX = sumSquaredDifferencesX / numPredictions;
    let varY = sumSquaredDifferencesY / numPredictions;

    // Calculate standard deviation for x and y dimensions
    let sdX = Math.sqrt(varX);
    let sdY = Math.sqrt(varY);

    return [sdX, sdY];
};


/**
 * This function calculates a measurement for how precise 
 * the eye tracker currently is which is displayed to the user
 */
let calculatePrecision = function(past50Array, numPredictions, targetX, targetY) {
    let windowHeight = $(window).height();
    //let windowWidth = $(window).width();

    // Retrieve the last 50 gaze prediction points
    let x50 = past50Array[0];
    let y50 = past50Array[1];

    let precisionPercentages = new Array(numPredictions);
    calculatePrecisionPercentages(precisionPercentages, numPredictions, windowHeight, x50, y50, targetX, targetY);
    let precision = calculateAverage(precisionPercentages, numPredictions);

    // Return the precision measurement as a rounded percentage
    return Math.round(precision);
};

/*
* Calculate percentage accuracy for each prediction based on distance of
* the prediction point from the centre point (uses the window height as
* lower threshold 0%)
*/
let calculatePrecisionPercentages = function(precisionPercentages, numPredictions, windowHeight, x50, y50, targetX, targetY) {
    for (let i = 0; i < numPredictions; i++) {
        // Calculate distance between each prediction and staring point
        let xDiff = targetX - x50[i];
        let yDiff = targetY - y50[i];
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
        precisionPercentages[i] = precision;
    }
};

/*
* Calculates the average of all precision percentages calculated
*/
let calculateAverage = function(precisionPercentages, numPredictions) {
    let precision = 0;
    for (let i = 0; i < numPredictions; i++) {
        precision += precisionPercentages[i];
    }
    precision = precision / numPredictions;
    return precision;
};