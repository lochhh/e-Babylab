import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/experiment.js')
const src = readFileSync(SRC, 'utf8')

// Minimal image trial fixture. Adjust fields when testing other trial types.
const imageTrial = {
  trial_id: 1, trial_number: 1, trial_type: 'image', image_file: 'test.jpg',
  audio_file: '', require_user_input: 'NO', max_duration: 5, record_media: false,
  is_calibration: false, record_gaze: false, background_colour: '#ffffff', label: 'trial-1',
}

const BASE_HTML = `
  <div id="trials"
       data-loading-image=""
       data-global-timeout="99999"
       data-include-pause-page="false"
       data-recording-option="NON"
       data-general-onset="0"
       data-show-gaze-estimations="false"
       data-subject-uuid="test-uuid"
       data-subject-id="1">
  </div>
  <div id="trials-data">[]</div>
  <button id="fullscreen-button">Fullscreen</button>
  <button id="exit-button">Exit</button>
`

function makeEnv({ recordingOption = 'NON', trials = [] } = {}) {
  document.body.innerHTML = BASE_HTML
  document.getElementById('trials').dataset.recordingOption = recordingOption
  document.getElementById('trials-data').textContent = JSON.stringify(trials)

  const locationReplace = vi.fn()
  vi.stubGlobal('location', { replace: locationReplace, href: '', assign: vi.fn() })

  const mockInitWebgazer = vi.fn().mockResolvedValue(undefined)
  const mockWebcam = {
    stopUploading:  vi.fn(),
    stopRecording:  vi.fn().mockResolvedValue(undefined),
    startUploading: vi.fn(),
    initStream:     vi.fn().mockResolvedValue({}),
    startRecording: vi.fn().mockResolvedValue(undefined),
    getLength:      vi.fn().mockReturnValue(0),
    waitForQueue:   vi.fn().mockResolvedValue(undefined),
  }
  const mockWebgazer = {
    pause:                vi.fn(),
    resume:               vi.fn().mockResolvedValue(undefined),
    getCurrentPrediction: vi.fn().mockResolvedValue(null),
  }

  globalThis.getCsrfToken         = vi.fn().mockReturnValue('test-csrf')
  globalThis.webcam               = mockWebcam
  globalThis.webgazer             = mockWebgazer
  globalThis.initWebgazer         = mockInitWebgazer
  globalThis.startGazeRecording   = vi.fn()
  globalThis.stopGazeRecording    = vi.fn()
  globalThis.calibrate            = vi.fn().mockResolvedValue(undefined)
  globalThis.webgazer_data        = []
  globalThis.bootstrap            = { Modal: class { constructor() {} show() {} } }
  globalThis.fetch                = vi.fn().mockResolvedValue({
    ok:   true,
    json: () => Promise.resolve({ resultId: 42 }),
    text: () => Promise.resolve(''),
  })

  eval(src)

  return { locationReplace, mockWebcam, mockInitWebgazer }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('experiment.js — loading', () => {
  it('loads without throwing with NON mode and no trials', () => {
    expect(() => makeEnv()).not.toThrow()
  })
})

describe('experiment.js — recording option: initStream', () => {
  it('calls webcam.initStream with VID before fullscreen click', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'VID' })
    await new Promise(resolve => setTimeout(resolve, 10))
    expect(mockWebcam.initStream).toHaveBeenCalledWith('VID')
  })

  it('calls webcam.initStream with AUD before fullscreen click', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'AUD' })
    await new Promise(resolve => setTimeout(resolve, 10))
    expect(mockWebcam.initStream).toHaveBeenCalledWith('AUD')
  })

  it('does not call webcam.initStream for NON mode', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'NON' })
    await new Promise(resolve => setTimeout(resolve, 10))
    expect(mockWebcam.initStream).not.toHaveBeenCalled()
  })
})

describe('experiment.js — after fullscreen click', () => {
  it('calls webcam.startUploading with subject UUID', async () => {
    const { mockWebcam } = makeEnv()
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockWebcam.startUploading).toHaveBeenCalledWith('test-uuid')
  })

  it('calls initWebgazer for EYE mode', async () => {
    const { mockInitWebgazer } = makeEnv({ recordingOption: 'EYE' })
    await new Promise(resolve => setTimeout(resolve, 10)) // let initStream settle + register click handler
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockInitWebgazer).toHaveBeenCalled()
  })

  it('does not call initWebgazer for NON mode', async () => {
    const { mockInitWebgazer } = makeEnv()
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockInitWebgazer).not.toHaveBeenCalled()
  })
})

describe('experiment.js — trial flow', () => {
  it('navigates to thankyou immediately when no trials remain', async () => {
    const { locationReplace } = makeEnv({ trials: [] })
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })

  it('calls webcam.startRecording for a VID trial with record_media=true', async () => {
    const trial = { ...imageTrial, record_media: true }
    const { mockWebcam } = makeEnv({ recordingOption: 'VID', trials: [trial] })
    await new Promise(resolve => setTimeout(resolve, 10)) // initStream settles + click handler registered
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 30))
    expect(mockWebcam.startRecording).toHaveBeenCalled()
  })

  it('navigates to thankyou after a single image trial completes (NON mode)', async () => {
    const { locationReplace } = makeEnv({ trials: [imageTrial] })
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    document.getElementById('fullscreen-button').click()
    // max_duration=5ms + microtask chain for postResult + stopRecording + showNextTrial
    await new Promise(resolve => setTimeout(resolve, 50))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })

  it('navigates to thankyou after a single image trial completes (VID mode, no recording)', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'VID',
      trials: [{ ...imageTrial, record_media: false }],
    })
    await new Promise(resolve => setTimeout(resolve, 10)) // initStream + click handler registered
    document.getElementById('fullscreen-button').click()
    await new Promise(resolve => setTimeout(resolve, 50))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })
})
