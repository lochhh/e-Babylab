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

  // WebGazer — vendored script, not an ES module
  window.webgazer = {
    pause: () => {},
    resume: () => Promise.resolve(),
    setGazeListener: () => window.webgazer,
    setTracker: () => window.webgazer,
    saveDataAcrossSessions: () => window.webgazer,
    showPredictionPoints: () => window.webgazer,
    begin: () => Promise.resolve(window.webgazer),
    getCurrentPrediction: () => Promise.resolve(null),
  }

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
