import { describe, it, expect, afterEach, vi } from 'vitest'
import { init } from '../../src/experiments/static/experiments/js/webcam-calibration.js'

const STEP_HTML = `
  <div id="webcam-calibration"
       data-subject-uuid="test-uuid"
       data-include-pause-page="false"
       data-recording-option="PLACEHOLDER">
  </div>
  <div id="webcam_step_1" class="active"></div>
  <div id="webcam_step_2">
    <button disabled>Continue</button>
  </div>
  <div id="webcam_step_3">
    <button class="btn-primary" disabled>Continue</button>
    <div class="alert-danger" style="display:none"></div>
    <div class="media-container" style="display:none"><video></video></div>
  </div>
  <div id="webcam_step_4">
    <div class="alert-danger" style="display:none"></div>
    <div class="alert-success" style="display:none"></div>
    <div class="media-container" style="display:none"><audio></audio><video></video></div>
    <button class="btn-primary" disabled>Continue</button>
    <button class="btn-warning" disabled>Repeat</button>
  </div>
  <div id="upload-progress" style="display:none"></div>
  <div id="repeatWebcamModal"></div>
  <button id="exit-button"></button>
  <button id="repeat-check-button" style="display:none"></button>
`

function makeEnv({ recordingOption = 'VID', getUserMedia = () => new Promise(() => {}) } = {}) {
  document.body.innerHTML = STEP_HTML.replace('PLACEHOLDER', recordingOption)

  vi.stubGlobal('MediaRecorder', class MockMediaRecorder {})
  vi.stubGlobal('bootstrap', {
    Modal: { getOrCreateInstance: vi.fn().mockReturnValue({ show: vi.fn(), hide: vi.fn() }) },
  })
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia },
    writable: true,
    configurable: true,
  })

  init()
}

afterEach(() => vi.unstubAllGlobals())

describe('webcam-calibration.js — init (checkStepTwo)', () => {
  it('removes active class from step 1', () => {
    makeEnv()
    expect(document.getElementById('webcam_step_1').classList.contains('active')).toBe(false)
  })

  it('adds active class to step 2', () => {
    makeEnv()
    expect(document.getElementById('webcam_step_2').classList.contains('active')).toBe(true)
  })
})

describe('webcam-calibration.js — recording option routing', () => {
  it('VID mode: step 2 click activates step 3', () => {
    makeEnv({ recordingOption: 'VID' })
    document.querySelector('#webcam_step_2 button').click()
    expect(document.getElementById('webcam_step_2').classList.contains('active')).toBe(false)
    expect(document.getElementById('webcam_step_3').classList.contains('active')).toBe(true)
  })

  it('AUD mode: step 2 click activates step 4, skipping step 3', () => {
    makeEnv({ recordingOption: 'AUD' })
    document.querySelector('#webcam_step_2 button').click()
    expect(document.getElementById('webcam_step_4').classList.contains('active')).toBe(true)
    expect(document.getElementById('webcam_step_3').classList.contains('active')).toBe(false)
  })
})

describe('webcam-calibration.js — startStream error handling', () => {
  it('shows danger alert in step 3 when getUserMedia rejects', async () => {
    makeEnv({
      recordingOption: 'VID',
      getUserMedia: () => Promise.reject(new Error('NotAllowedError')),
    })
    document.querySelector('#webcam_step_2 button').click()
    await new Promise(resolve => setTimeout(resolve, 0))
    const alertEl = document.querySelector('#webcam_step_3 .alert-danger')
    expect(alertEl.style.display).toBe('block')
    expect(alertEl.innerHTML).toContain('NotAllowedError')
  })
})
