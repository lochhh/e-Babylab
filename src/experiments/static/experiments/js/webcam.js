import { Queue } from './queue.src.js';
import { getCsrfToken } from './utils.js';

export function createWebcam() {
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

	// Stream reference
	let mediaStream = null;

	// Recorder reference
	let mediaRecorder;

	// Background upload queue
	let uploadQueue = new Queue();

	// Currently recording
	let recording = false;

	// Webcam recording interval
	const recordingInterval = 1000;

	// Currently uploading
	let uploading = false;

	// Upload timeout function
	let uploadTimer = null;

	// Selected recording codec
	let codec;

	// Number of current chunk
	let chunkCounter = 0;

	// Filename under which the current recording should be uploaded
	let currentFileName;

	// Upload endpoint
	let uploadUrl;

	// Currently uploading errors
	let uploadErrors = 0;

	// Maximum number of upload errors until upload is stopped
	const maxUploadErrors = 10;

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
	w.getLength = function () {
		return uploadQueue.getLength();
	};

	/**
	 * Returns a promise that is resolved when the queue length matches the given length.
	 * @param {number} length of queue at which the Promise should be resolved
	 */
	w.waitForQueue = function (length) {
		if (length === uploadQueue.getLength()) {
			return Promise.resolve();
		}

		return new Promise((resolve, reject) => {
			if (length in queueNotify) {
				queueNotify[length].push(resolve);
			} else {
				queueNotify[length] = [resolve];
			}
		});
	};

	/**
	 * Notifies queue callbacks.
	 */
	const notify = function () {
		const currentLength = uploadQueue.getLength();
		if (currentLength in queueNotify) {
			const callbacks = queueNotify[currentLength];
			if ((currentLength === 0 && !recording) || currentLength > 0) {
				for (const callback of callbacks) {
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
	const selectCodec = function (recordingOption) {
		if (recordingOption === 'AUD') {
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
		console.log(`Selected ${codec} codec for recording.`);
	};

	/**
	 * Initialize webcam and audio stream.
	 * @param {string} recordingOption decides whether to capture audio or video
	 */
	w.initStream = function (recordingOption) {
		if (mediaStream == null) {
			selectCodec(recordingOption);

			if (recordingOption === 'AUD') {
				return navigator.mediaDevices.getUserMedia(constraintsAudio);
			}
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

		return new Promise((resolve, reject) => {
			chunkCounter = 0;
			currentFileName = fileName;

			const afterStart = function () {
				mediaRecorder.removeEventListener("start", afterStart);
				resolve();
			};

			s.then(s => {
				mediaStream = s;
				recording = true;
				mediaRecorder = new MediaRecorder(mediaStream, { mimeType: codec });
				mediaRecorder.addEventListener("dataavailable", handleStreamData);
				mediaRecorder.addEventListener("start", afterStart);
				mediaRecorder.start(recordingInterval);

				console.log(`Start webcam recording of ${fileName}`);
			});
		});
	};

	/**
	 * @param {number} trialResultId of the TrialResult object in which the video filename should be stored.
	 */
	w.stopRecording = function (trialResultId) {
		if (!recording) return Promise.resolve();

		return new Promise((resolve, reject) => {
			const afterStop = function () {
				mediaRecorder.removeEventListener("stop", afterStop);
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

			mediaRecorder.addEventListener("stop", afterStop);
			mediaRecorder.stop();
		});
	};

	/**
	 * Start uploading in background.
	 */
	w.startUploading = function (subjectUuid) {
		if (uploading) return;

		uploadUrl = `/${subjectUuid}/run/upload`;
		uploading = true;
		uploadTimer = setTimeout(uploadChunk, recordingInterval * 1.5);
	};

	/**
	 * Upload the first chunk in the queue.
	 */
	const uploadChunk = function () {
		if (uploadQueue.getLength() === 0 && uploading) {
			console.log("timeout");
			uploadTimer = setTimeout(uploadChunk, recordingInterval);
			return;
		}

		if (!uploading) return;

		const formData = new FormData();
		const chunkData = uploadQueue.peek();
		let chunkFileName;
		if ('trialResultId' in chunkData) {
			formData.append('trialResultId', chunkData.trialResultId);
			formData.append('filename', chunkData.fileName);
		} else {
			chunkFileName = `${chunkData.fileName}-${String(chunkData.number).padStart(5, '0')}.webm`;
			const file = new File([chunkData.data], chunkFileName, { type: codec });
			formData.append('file', file);
			formData.append('type', codec);
		}

		fetch(uploadUrl, {
			method: 'POST',
			headers: { 'X-CSRFToken': getCsrfToken() },
			body: formData,
		}).then(response => {
			if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
			return response.json();
		}).then(data => {
			console.log(`Upload of ${chunkFileName} was successful.`);
			uploadErrors = 0;
			uploadQueue.dequeue();
			notify();
			uploadChunk();
		}).catch(error => {
			uploadErrors++;
			console.error(`Upload of ${chunkFileName} failed.`, error);
			if (uploadErrors < maxUploadErrors) {
				uploadChunk();
			} else {
				console.error('Too many errors while uploading. Stop uploading.');
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
	 * Put a current webcam chunk in the upload queue.
	 * @param {Event} event of the MediaRecorder
	 */
	const handleStreamData = function (event) {
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
}

export const webcam = createWebcam();
