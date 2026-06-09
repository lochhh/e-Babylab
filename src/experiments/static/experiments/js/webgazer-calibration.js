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
let clockStart;
export function resetGazeData() { webgazer_data = []; }
export function getGazeData() { return webgazer_data; }
export function setTimePerPoint(ms) { timePerPoint = ms; }

/**
 * Initialises webgazer for eye-tracking.
 */
export let initWebgazer = function () {
    return new Promise((resolve, reject) => {
        if (typeof webgazer === 'undefined') {
            const error = 'Failed to start webgazer.';
            console.error(error);
            reject(error);
        }
        const showPredictions = window.show_gaze_estimations?.toLowerCase() === 'true';
        webgazer.params.showGazeDot = showPredictions;

        // webgazer's default faceMeshSolutionPath ("./mediapipe/face_mesh") resolves
        // relative to the page URL (e.g. /{uuid}/run), causing 404s on the MediaPipe
        // binary assets. Resolve from this module's own URL so Django serves them from
        // the correct static path. Assets are installed via `npm run build` at the root.
        webgazer.params.faceMeshSolutionPath = new URL('./mediapipe/face_mesh', import.meta.url).href;

        webgazer.setRegression('ridge')
                .setGazeListener((data, clock) => {
                  //console.log(data); /* data is an object containing an x and y key which are the x and y prediction coordinates (no bounds limiting) */
                  //console.log(clock); /* elapsed time in milliseconds since webgazer.begin() was called */
                })
                .saveDataAcrossSessions(false)
                .removeMouseEventListeners()
                .begin()
                .then(() => {
                    webgazer.showVideoPreview(true)
                            .showPredictionPoints(showPredictions)
                            .applyKalmanFilter(true);

                    const setup = function () {
                        const canvas = document.getElementById('plotting_canvas');
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                        canvas.style.position = 'fixed';
                        canvas.style.zIndex = '1';
                        canvas.style.display = 'block';

                        // Set up video feedback
                        const videoContainer = document.getElementById('webgazerVideoContainer');
                        if (videoContainer) {
                            document.querySelector('#webgazer-init .col')?.prepend(videoContainer);
                            videoContainer.style.left = 'calc(50% - 160px)';
                            videoContainer.style.top = '10%';
                        }
                    };
                    setup();

                    // Show calibration instructions above the plotting canvas
                    const initDiv = document.getElementById('webgazer-init');
                    initDiv.style.position = 'relative';
                    initDiv.style.zIndex = '2';
                    initDiv.style.display = 'block';

                    // Enable continue button if face is detected
                    if (faceDetected) {
                        document.querySelector('#webgazer-init button').disabled = false;
                    } else {
                        let observer = new MutationObserver(faceDetectEventObserver);
                        observer.observe(document, {
                            attributes: true,
                            attributeFilter: ['style'],
                            subtree: true
                        });
                    }

                    document.querySelector('#webgazer-init button').addEventListener('click', function () {
                        if (typeof observer !== 'undefined') {
                            observer.disconnect();
                        }
                        webgazer.pause();
                        document.getElementById('webgazer-init').style.display = 'none';
                        resolve();
                    });
                })
                .catch(error => {
                    console.error(error);
                    reject(error);
                });
    });
};

/**
 * Checks whether face has been detected by webgazer.
 */
let faceDetected = function () {
    const feedbackBox = document.querySelector('#webgazerFaceFeedbackBox');
    return feedbackBox ? feedbackBox.style.borderColor === 'green' : false;
};

/**
 * Enables/disables continue button depending on
 * whether face has been detected by webgazer.
 * @param {MutationRecord[]} mutationsList
 * @param {MutationObserver} observer
 */
let faceDetectEventObserver = function (mutationsList, observer) {
    if (mutationsList[0].target === document.querySelector('#webgazerFaceFeedbackBox')) {
        const btn = document.querySelector('#webgazer-init button');
        if (mutationsList[0].type === 'attributes' && mutationsList[0].target.style.borderColor === 'green') {
            btn.disabled = false;
        }
        if (mutationsList[0].type === 'attributes' && mutationsList[0].target.style.borderColor === 'red') {
            btn.disabled = true;
        }
    }
};

/**
 * Wrapper function for calibrating and validating webgazer.
 * @param {object} trialObj
 */
export let calibrate = async function (trialObj) {
    for (let ptId = 0; ptId < trialObj.calibration_points.length; ptId++) {
        await showCalibrationPoint(trialObj, ptId);
        await calibrateGaze(ptId);
    }
    return await validateGaze(trialObj);
};

/**
 * Shows next calibration point and hides previous calibration point.
 * @param {object} trialObj
 * @param {number} ptId
 */
let showCalibrationPoint = function (trialObj, ptId) {
    return new Promise(resolve => {
        console.log(`showcalibrationpoint ${ptId}`);
        if (ptId > 0) {
            document.getElementById(`Pt${ptId - 1}`).style.display = 'none';
        }
        if (ptId < trialObj.calibration_points.length) {
            document.getElementById(`Pt${ptId}`).style.display = 'block';
        }
        resolve(ptId);
    });
};

/**
 * Calibrates webgazer without clicking, by assuming gaze locations.
 * @param {number} ptId
 */
let calibrateGaze = function (ptId) {
    return new Promise((resolve) => {
        console.log(`calibrategaze ${ptId}`);
        const br = document.querySelector(`#Pt${ptId}`).getBoundingClientRect();
        const x = br.left + br.width / 2;
        const y = br.top + br.height / 2;
        const ptStart = performance.now() + timeToSaccade;
        const ptEnd = performance.now() + timeToSaccade + timePerPoint;

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
 * @param {object} trialObj
 */
let validateGaze = function (trialObj) {
    return new Promise(resolve => {
        console.log('validategaze');
        document.querySelectorAll('.calibration-image').forEach(el => { el.style.display = 'none'; });
        document.getElementById('Pt0').style.display = 'block';

        const canvas = document.getElementById('plotting_canvas');
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        webgazer.params.storingPoints = true;
        setTimeout(() => {
            webgazer.params.storingPoints = false;
            const past50 = webgazer.getStoredPoints();
            const target = document.querySelector('#Pt0').getBoundingClientRect();
            const targetX = target.left + target.width / 2;
            const targetY = target.top + target.height / 2;
            const numPredictions = past50[0].filter(Boolean).length;
            const accuracy = calculateAccuracy(past50, numPredictions, targetX, targetY);
            const precisionRMS = calculatePrecisionRMS(past50, numPredictions);
            const precisionSD = calculatePrecisionSD(past50, numPredictions);

            const d = {
                trial_type: 'validation',
                target_x: targetX,
                target_y: targetY,
                x: past50[0],
                y: past50[1],
                accuracy,
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

export let startGazeRecording = function () {
    // reset webgazer.clockStart
    clockStart = performance.now();
    gazeInterval = setInterval(() => {
        webgazer.getCurrentPrediction().then(handleGazeDataUpdate);
    }, samplingInterval);
    // repeat the call here so that we get one immediate execution. above will not
    // start until samplingInterval is reached the first time.
    webgazer.getCurrentPrediction().then(handleGazeDataUpdate);
};

export let stopGazeRecording = function () {
    clearInterval(gazeInterval);
};

let handleGazeDataUpdate = function (data) {
    if (data !== null) {
        data = webgazer.util.bound(data);
        const d = {
            x: Math.round(data.x),
            y: Math.round(data.y),
            t: performance.now() - clockStart,
        };
        webgazer_data.push(d);
    }
};

/**
 * Calculates accuracy as mean Euclidean distance (pixels) between gaze locations and target centre.
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
 * @param {Array} past50Array
 * @param {number} numPredictions
 * @param {number} targetX
 * @param {number} targetY
 */
export let calculateAccuracy = function (past50Array, numPredictions, targetX, targetY) {
    let totalDistance = 0;

    for (let i = 0; i < numPredictions; i++) {
        const xDiff = past50Array[0][i] - targetX;
        const yDiff = past50Array[1][i] - targetY;
        totalDistance += Math.sqrt(xDiff * xDiff + yDiff * yDiff);
    }

    return totalDistance / numPredictions;
};

/**
 * Calculates precision as RMS distance between successive gaze locations.
Since such inter-sample distances only compare 
 * temporally adjacent samples, they may be less sensitive to large overall spatial 
 * dispersion of the data.
 * 
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
 * @param {Array} past50Array
 * @param {number} numPredictions
 */
export let calculatePrecisionRMS = function (past50Array, numPredictions) {
    let sumSquaredDistances = 0;

    for (let i = 1; i < numPredictions; i++) {
        const xDiff = past50Array[0][i] - past50Array[0][i - 1];
        const yDiff = past50Array[1][i] - past50Array[1][i - 1];
        sumSquaredDistances += xDiff * xDiff + yDiff * yDiff;
    }

    return Math.sqrt(sumSquaredDistances / (numPredictions - 1));
};

/**
 * Calculates precision as population SD of gaze locations in X and Y separately.
 * This measures how dispersed samples are from their mean value.
 * 
 * See Holmqvist, K., Nystroem, M., Andersson, R., Dewhurst, R., Halszka, J., & van de Weijer, J. (2011).
  * @param {Array} past50Array
 * @param {number} numPredictions
 */
export let calculatePrecisionSD = function (past50Array, numPredictions) {
    let meanX = 0;
    let meanY = 0;
    for (let i = 0; i < numPredictions; i++) {
        meanX += past50Array[0][i];
        meanY += past50Array[1][i];
    }
    meanX /= numPredictions;
    meanY /= numPredictions;

    let sumSquaredDifferencesX = 0;
    let sumSquaredDifferencesY = 0;
    for (let i = 0; i < numPredictions; i++) {
        const diffX = past50Array[0][i] - meanX;
        const diffY = past50Array[1][i] - meanY;
        sumSquaredDifferencesX += diffX * diffX;
        sumSquaredDifferencesY += diffY * diffY;
    }

    return [
        Math.sqrt(sumSquaredDifferencesX / numPredictions),
        Math.sqrt(sumSquaredDifferencesY / numPredictions),
    ];
};

/**
 * Calculates a precision measurement for display to the user.
 */
let calculatePrecision = function (past50Array, numPredictions, targetX, targetY) {
    const windowHeight = window.innerHeight;

    const x50 = past50Array[0];
    const y50 = past50Array[1];

    const precisionPercentages = new Array(numPredictions);
    calculatePrecisionPercentages(precisionPercentages, numPredictions, windowHeight, x50, y50, targetX, targetY);
    const precision = calculateAverage(precisionPercentages, numPredictions);

    return Math.round(precision);
};

/*
 * Calculate percentage accuracy for each prediction based on distance from
 * the centre point (uses the window height as the lower threshold 0%).
 */
let calculatePrecisionPercentages = function (precisionPercentages, numPredictions, windowHeight, x50, y50, targetX, targetY) {
    for (let i = 0; i < numPredictions; i++) {
        const xDiff = targetX - x50[i];
        const yDiff = targetY - y50[i];
        const distance = Math.sqrt(xDiff * xDiff + yDiff * yDiff);

        const halfWindowHeight = windowHeight / 2;
        let precision = 0;
        if (distance <= halfWindowHeight && distance > -1) {
            precision = 100 - (distance / halfWindowHeight * 100);
        } else if (distance > halfWindowHeight) {
            precision = 0;
        } else if (distance > -1) {
            precision = 100;
        }

        precisionPercentages[i] = precision;
    }
};

/*
 * Calculates the average of all precision percentages.
 */
export let calculateAverage = function (precisionPercentages, numPredictions) {
    let precision = 0;
    for (let i = 0; i < numPredictions; i++) {
        precision += precisionPercentages[i];
    }
    return precision / numPredictions;
};
