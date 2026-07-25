/**
 * Intercepts webgazer.min.js and replaces it with a lightweight stub.
 * The real library ends with `webgazer=r.default`, overwriting any addInitScript stub.
 * Call before page.goto() in tests that trigger initWebgazer() (EYE/ALL modes).
 * @param {import('@playwright/test').Page} page
 */
export async function stubWebgazerScript(page) {
  const stub = `
    window.webgazer = {
      params:                    { showGazeDot: false },
      pause:                     () => {},
      resume:                    () => Promise.resolve(),
      setRegression:             () => window.webgazer,
      setGazeListener:           () => window.webgazer,
      setTracker:                () => window.webgazer,
      saveDataAcrossSessions:    () => window.webgazer,
      removeMouseEventListeners: () => window.webgazer,
      showPredictionPoints:      () => window.webgazer,
      showVideoPreview:          () => window.webgazer,
      applyKalmanFilter:         () => window.webgazer,
      begin:                     () => Promise.resolve(window.webgazer),
      getCurrentPrediction:      () => Promise.resolve(null),
    };
  `
  await page.route('**/webgazer.min.js', route => route.fulfill({
    contentType: 'application/javascript',
    body: stub,
  }))
}

/**
 * Waits for #webgazer-init to appear, force-enables the button, and clicks it.
 * Also sets pointer-events:none on #plotting_canvas, which setup() in
 * webgazer-calibration.js renders as a full-viewport fixed overlay that otherwise
 * blocks the button click (fixed elements stack above static ones).
 * @param {import('@playwright/test').Page} page
 */
export async function proceedPastWebgazerInit(page) {
  await page.waitForSelector('#webgazer-init', { state: 'visible', timeout: 8000 })
  await page.evaluate(() => {
    const canvas = document.getElementById('plotting_canvas')
    if (canvas) canvas.style.pointerEvents = 'none'
    document.querySelector('#webgazer-init button').disabled = false
  })
  await page.locator('#webgazer-init button').click()
}

/**
 * Stubs browser APIs that require hardware or real fullscreen.
 * Call via page.addInitScript(stubBrowserAPIs) in beforeEach.
 */
export function stubBrowserAPIs() {
  // Fullscreen API — Chromium/WebKit block requestFullscreen in tests.
  // Guard against documentElement being null on blank frames before HTML parses.
  if (document.documentElement) {
    document.documentElement.requestFullscreen = () => Promise.resolve()
  }
  document.exitFullscreen = () => Promise.resolve()
  Object.defineProperty(document, 'fullscreenElement', {
    get: () => document.documentElement,
    configurable: true,
  })

  // WebGazer — vendored script, not an ES module.
  // Methods must cover the full initWebgazer() chain in webgazer-calibration.js:
  // setRegression → setGazeListener → saveDataAcrossSessions → removeMouseEventListeners
  // → begin() → showVideoPreview → showPredictionPoints → applyKalmanFilter
  window.webgazer = {
    params:                    { showGazeDot: false },
    pause:                     () => {},
    resume:                    () => Promise.resolve(),
    setRegression:             () => window.webgazer,
    setGazeListener:           () => window.webgazer,
    setTracker:                () => window.webgazer,
    saveDataAcrossSessions:    () => window.webgazer,
    removeMouseEventListeners: () => window.webgazer,
    showPredictionPoints:      () => window.webgazer,
    showVideoPreview:          () => window.webgazer,
    applyKalmanFilter:         () => window.webgazer,
    begin:                     () => Promise.resolve(window.webgazer),
    getCurrentPrediction:      () => Promise.resolve(null),
  }

  // MediaRecorder — Playwright's WebKit build lacks this API; webcam.js calls
  // MediaRecorder.isTypeSupported() inside selectCodec() which is called from initStream().
  if (!window.MediaRecorder) {
    window.MediaRecorder = class {
      constructor() {}
      start() {}
      stop() {}
      addEventListener() {}
      static isTypeSupported() { return false }
    }
  }

  // Playwright's WebKit build has no working audio backend in this environment:
  // <audio>/<video> elements load fully (loadeddata fires) but readyState never
  // advances past HAVE_CURRENT_DATA, so 'canplay' never fires and experiment.js's
  // trial flow (which waits on it) hangs forever. Real Safari has no such issue.
  // Force 'canplay' shortly after 'loadeddata' as a test-only workaround.
  document.addEventListener('loadeddata', e => {
    const media = e.target
    setTimeout(() => {
      if (media.readyState < 3) media.dispatchEvent(new Event('canplay'))
    }, 50)
  }, true)

  // getUserMedia — avoids real camera/mic permission dialogs
  const fakeStream = {
    getTracks: () => [{ stop: () => {} }],
    getVideoTracks: () => [{ stop: () => {} }],
    getAudioTracks: () => [{ stop: () => {} }],
  }
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(fakeStream)
  } else {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: () => Promise.resolve(fakeStream) },
      configurable: true,
    })
  }
}
