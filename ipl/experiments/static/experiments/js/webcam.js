'use strict';

let webcam = (function () {

	let w = {};

	// Webcam constraints
	const constraints = {
		audio: true,
		video: {
			facingMode: "user",
			width: { min: 640, max: 640 },
			height: { min: 480, max: 480 }
		}
	};

	const constraintsAudio = {
		audio: true,
	};

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

	// Stream reference
	let mediaStream = null;

	// Recorder reference
	let mediaRecorder;

	// Background upload queue
	let uploadQueue = new Queue();

	// Currently recording
	let recording = false;

	// Webcam recording interval
	let recordingInterval = 1000;

	// Currently uploading
	let uploading = false;

	// Upload timeout function
	let uploadTimer = null;

	// Selected recording codec codec
	let codec;

	// Number of current chunk
	let chunkCounter = 0;

	// Filename under which the current recording should be uploaded
	let currentFileName;

	// Upload enpoint
	let uploadUrl;

	// Currently uploading errors
	let uploadErrors = 0;

	// Maximum number of upload errors until upload is stopped
	let maxUploadErrors = 10; //3;

	// List of possible recording codecs for video (from less preferred to most preferred)
	const contentTypes = [
		"video/webm",
		//"video/webm;codecs=vp8",
		//"video/webm;codecs=vp9"
	];

	// List of possible recording codecs for audio
	const contentTypesAudio = [
		"audio/webm", 
		//"audio/webm;codecs=opus",
	];

	// Dictionary with notification callbacks
	let queueNotify = {};

	/**
	 * Returns the length of the upload queue.
	 */
	w.getLength = function() {
		return uploadQueue.getLength();
	}

	/**
	 * Returns a promise that is resolved when the queue length matches the given length.
	 * @param {int} length of queue at which the Promise should be resolved
	 */
	w.waitForQueue = function(length) {
		// If current queue length matches
		if(length == uploadQueue.getLength()) {
			return Promise.resolve()
		}

		// otherwise register callback
		return new Promise(function(resolve, reject) {
			// else, put in notification dictionary
			if(length in queueNotify) {
				queueNotify[length].push(resolve);
			}else{
				queueNotify[length] = [resolve];
			}
		});
	};

	/**
	 * Notifies queue callbacks.
	 */
	let notify = function() {
		let currentLength = uploadQueue.getLength();
		if(currentLength in queueNotify) {
			let callbacks = queueNotify[currentLength];
			if((currentLength == 0 && !recording) || currentLength > 0) {
				for (let callback of callbacks) {
					callback();
				}
			}
			queueNotify[currentLength] = [];
		}
	};

	/**
	 * Select the best supported video/audio codec.
	 * @param {string} recordingOption decides whether to capture audio or video
	 */
	let selectCodec = function (recordingOption) {
		
		if (recordingOption == 'AUD') {
			contentTypesAudio.forEach(contentType => {
				if (MediaRecorder.isTypeSupported(contentType)) {
					codec = contentType;
				} 
			});
		} else {
			contentTypes.forEach(contentType => {
				if (MediaRecorder.isTypeSupported(contentType)) {
					codec = contentType;
				}
			});
		}
		console.log("Selected " + codec + " codec for recording.");
	};

	/**
	 * Initialize webcam and audio stream.
	 * @param {string} recordingOption decides whether to capture audio or video
	*/

	w.initStream = function(recordingOption) {
		if (mediaStream == null) {
			// Select recording codec
			selectCodec(recordingOption);

			if (recordingOption == 'AUD') {
				return navigator.mediaDevices.getUserMedia(constraintsAudio);
			}
			// Init audio and video streams
			return navigator.mediaDevices.getUserMedia(constraints);
		}
		return Promise.resolve(mediaStream);
	};

	/**
	 * Start a webcam recording session.
	 * @param {string} fileName under which the video should be stored
	 * @param {string} recordingOption decides whether to capture audio or video
	 */
	w.startRecording = function (fileName, recordingOption, s) {
		if (recording) return Promise.resolve();

		return new Promise(function(resolve, reject) {
			chunkCounter = 0;
			currentFileName = fileName;

			let afterStart = function() {
				mediaRecorder.removeEventListener("start", afterStart);
				resolve();
			};

			//initStream(recordingOption).then(function (s) {});
			s.then(function (s) {
				mediaStream = s;
				recording = true;
				mediaRecorder = new MediaRecorder(mediaStream, { mimeType: codec });
				mediaRecorder.addEventListener("dataavailable", handleStreamData);
				mediaRecorder.addEventListener("start", afterStart);
				mediaRecorder.start(recordingInterval);

				console.log("Start webcam recording of " + fileName);
			});
			
		});
	};

	/**
	 * 
	 * @param {int} trialResultId of the TrialResult object in which the video filename should be stored.
	 */
	w.stopRecording = function (trialResultId) {
		if (!recording) return Promise.resolve();

		return new Promise(function(resolve, reject) {
			// Register stop event
			let afterStop = function() {
				mediaRecorder.removeEventListener("stop", afterStop);
				// Put merge request in queue
				uploadQueue.enqueue({
					"fileName": currentFileName,
					"trialResultId": trialResultId
				});
				notify();
				chunkCounter++;
				recording = false;
				console.log("Stop webcam recording");
				resolve();
			};

			// Stop recording
			mediaRecorder.addEventListener("stop", afterStop);
			mediaRecorder.stop();
		});
	};

	/**
	 * Start uploading in background.
	 */
	w.startUploading = function (subjectUuid) {
		if (uploading) return;

		uploadUrl = "/" + subjectUuid + "/run/upload";
		uploading = true;
		uploadTimer = setTimeout(uploadChunk, recordingInterval * 1.5);
	};

	/**
	 * Upload the first chunk in the queue.
	 */
	let uploadChunk = function () {
		// If queue is empty, try again later
		if (uploadQueue.getLength() == 0 && uploading) {
			console.log("timeout");
			uploadTimer = setTimeout(uploadChunk, recordingInterval);
			return;
		}

		// Abort if upload was stopped
		if (!uploading) {
			return;
		}

		// Prepare upload data
		let formData = new FormData();
		let chunkData = uploadQueue.peek();
		let chunkFileName;
		if('trialResultId' in chunkData) {
			formData.append('trialResultId', chunkData.trialResultId)
			formData.append('filename', chunkData.fileName);
		}else{
			chunkFileName = chunkData.fileName + '-' + formatNumber(chunkData.number, 5) + ".webm";
			let file = new File([chunkData.data], chunkFileName, { type: codec });
			formData.append('file', file);
			formData.append('type', codec);
		}

		// Upload
		$.ajax({
			url: uploadUrl,
			method: 'POST',
			data: formData,
			processData: false,
			contentType: false
		}).done(function (data, status, xhr) {
			// Do upload
			console.log("Upload of " + chunkFileName + " was successful.");
			uploadErrors = 0; // Reset upload errors after successful upload

			// In case of error, try again
			uploadQueue.dequeue();
			notify();

			// Continue uploading
			uploadChunk();
		}).fail(function (xhr, status, error) {
			uploadErrors++;
			console.error("Upload of " + chunkFileName + " failed.", error);

			// Try again
			if (uploadErrors < maxUploadErrors) {
				uploadChunk();
			} else {
				console.error("Too many errors while uploading. Stop uploading.");
				w.stopUploading();
			}
		});
	};

	/**
	 * Stop background uploading process.
	 */
	w.stopUploading = function () {
		if (!uploading) return;

		uploading = false;
		clearTimeout(uploadTimer);
	};

	/**
	 * Prepend a number with zeroes.
	 * @param {int} number
	 * @param {int} size of the resulting number
	 */
	let formatNumber = function (number, size) {
		var s = String(number);
		while (s.length < (size || 2)) { s = "0" + s; }
		return s;
	}

	/**
	 * Put a current webcam chunk in the upload queue.
	 * @param {event} event of the MediaRecorder
	 */
	let handleStreamData = function (event) {
		uploadQueue.enqueue({
			"number": chunkCounter,
			"data": event.data,
			"fileName": currentFileName
		});
		notify();
		chunkCounter++;
		console.log("Queue size:", uploadQueue.getLength());
	};

	return w;
})();
