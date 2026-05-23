import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../src/experiments/static/experiments/js/webcam.js', () => ({
  webcam: {
    initStream:     vi.fn(),
    startRecording: vi.fn(),
    stopRecording:  vi.fn(),
    startUploading: vi.fn(),
    stopUploading:  vi.fn(),
    getLength:      vi.fn(),
    waitForQueue:   vi.fn(),
  },
}))

vi.mock('../../src/experiments/static/experiments/js/utils.js', () => ({
  getCsrfToken: vi.fn().mockReturnValue('test-csrf'),
}))

vi.mock('../../src/experiments/static/experiments/js/webgazer-calibration.js', () => ({
  initWebgazer:       vi.fn(),
  startGazeRecording: vi.fn(),
  stopGazeRecording:  vi.fn(),
  calibrate:          vi.fn(),
  resetGazeData:      vi.fn(),
  getGazeData:        vi.fn().mockReturnValue([]),
}))

import { webcam } from '../../src/experiments/static/experiments/js/webcam.js'
import { initWebgazer } from '../../src/experiments/static/experiments/js/webgazer-calibration.js'
import { init } from '../../src/experiments/static/experiments/js/experiment.js'

const BASE_HTML = `
  <div id="trials"
       data-loading-image=""
       data-global-timeout="600000"
       data-include-pause-page="false"
       data-recording-option="NON"
       data-general-onset="0"
       data-show-gaze-estimations="false"
       data-subject-uuid="test-uuid"
       data-subject-id="1">
  </div>
  <script id="trials-data" type="application/json">[]</script>
  <button id="fullscreen-button">Fullscreen</button>
  <div id="exitStudyModal"></div>
  <button id="exit-button"></button>
`

function makeEnv({ recordingOption = 'NON', trials = [] } = {}) {
  document.body.innerHTML = BASE_HTML
  document.getElementById('trials').dataset.recordingOption = recordingOption
  document.getElementById('trials-data').textContent = JSON.stringify(trials)

  const locationReplace = vi.fn()
  vi.stubGlobal('location', { replace: locationReplace, href: '', assign: vi.fn() })
  vi.stubGlobal('webgazer', {
    pause:                vi.fn(),
    resume:               vi.fn().mockResolvedValue(undefined),
    getCurrentPrediction: vi.fn().mockResolvedValue(null),
  })
  vi.stubGlobal('bootstrap', { Modal: class { constructor() {} show() {} } })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok:   true,
    json: () => Promise.resolve({ resultId: 42 }),
    text: () => Promise.resolve(''),
  }))

  vi.mocked(webcam.initStream).mockResolvedValue({})
  vi.mocked(webcam.getLength).mockReturnValue(0)
  vi.mocked(webcam.waitForQueue).mockResolvedValue(undefined)
  vi.mocked(webcam.stopRecording).mockResolvedValue(undefined)
  vi.mocked(initWebgazer).mockResolvedValue(undefined)

  init()
  return { locationReplace, mockWebcam: webcam, mockInitWebgazer: initWebgazer }
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('experiment.js — initStream', () => {
  it('does not call initStream for NON recording', () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'NON' })
    document.getElementById('fullscreen-button').click()
    expect(mockWebcam.initStream).not.toHaveBeenCalled()
  })

  it('calls initStream with VID for VID recording', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'VID' })
    document.getElementById('fullscreen-button').click()
    await new Promise(r => setTimeout(r, 0))
    expect(mockWebcam.initStream).toHaveBeenCalledWith('VID')
  })
})

describe('experiment.js — trial flow', () => {
  it('navigates to thankyou when trials list is empty', async () => {
    const { locationReplace } = makeEnv({ recordingOption: 'NON', trials: [] })
    await new Promise(r => setTimeout(r, 10))
    document.getElementById('fullscreen-button').click()
    await new Promise(r => setTimeout(r, 50))
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })
})
