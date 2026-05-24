import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Flush N levels of chained Promise microtasks.
// Each await yields to pending microtasks scheduled by the previous round.
// The init chain in experiment.js is ~10 levels deep before/after a click.
const flush = async (n = 15) => { for (let i = 0; i < n; i++) await Promise.resolve() }

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

function makeTrial(overrides = {}) {
  return {
    trial_id: 1,
    trial_number: 1,
    trial_type: 'image',
    label: 'test',
    visual_file: '/media/test.jpg',
    audio_file: '',
    require_user_input: 'NO',
    is_calibration: false,
    record_gaze: false,
    record_media: true,
    response_keys: [],
    max_duration: 50,
    background_colour: '#ffffff',
    audio_onset: '0',
    visual_onset: '0',
    ...overrides,
  }
}

function makeEnv({
  recordingOption = 'NON',
  trials = [],
  globalTimeout = '600000',
  includePausePage = 'false',
  bootstrapModal = null,
} = {}) {
  document.body.innerHTML = BASE_HTML
  const trialsEl = document.getElementById('trials')
  trialsEl.dataset.recordingOption = recordingOption
  trialsEl.dataset.globalTimeout = globalTimeout
  trialsEl.dataset.includePausePage = includePausePage
  document.getElementById('trials-data').textContent = JSON.stringify(trials)

  const locationReplace = vi.fn()
  vi.stubGlobal('location', { replace: locationReplace, href: '', assign: vi.fn() })
  vi.stubGlobal('webgazer', {
    pause:                vi.fn(),
    resume:               vi.fn().mockResolvedValue(undefined),
    getCurrentPrediction: vi.fn().mockResolvedValue(null),
  })
  const ModalClass = bootstrapModal || class { constructor() {} show() {} }
  vi.stubGlobal('bootstrap', { Modal: ModalClass })
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

describe('experiment.js — postResult', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('POSTs to storeresult URL with trial data', async () => {
    makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(60)
    await flush()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/run/storeresult'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('passes resultId from response to webcam.stopRecording', async () => {
    const { mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(60)
    await flush()
    expect(mockWebcam.stopRecording).toHaveBeenCalledWith(42)
  })
})

describe('experiment.js — trial rendering', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('appends .trial-image to body for image trial', async () => {
    makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(1)
    await flush()
    expect(document.querySelector('.trial-image')).not.toBeNull()
  })

  it('renders second trial after first completes via max_duration', async () => {
    const trial1 = makeTrial({ trial_id: 1, visual_file: '/media/a.jpg' })
    const trial2 = makeTrial({ trial_id: 2, trial_number: 2, visual_file: '/media/b.jpg' })
    makeEnv({ recordingOption: 'NON', trials: [trial1, trial2] })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(60)
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    const img = document.querySelector('.trial-image')
    expect(img).not.toBeNull()
    expect(img.style.backgroundImage).toContain('b.jpg')
  })

  it('navigates to thankyou after all trials complete', async () => {
    const { locationReplace } = makeEnv({ recordingOption: 'NON', trials: [makeTrial()] })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(60)
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })
})

describe('experiment.js — webcam recording', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('calls startRecording for VID trial with record_media true', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ record_media: true })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    expect(mockWebcam.startRecording).toHaveBeenCalledWith(
      expect.stringContaining('trial1'),
      'VID',
      expect.anything(),
    )
  })

  it('does not call startRecording when record_media is false', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ record_media: false })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    expect(mockWebcam.startRecording).not.toHaveBeenCalled()
  })

  it('does not call startRecording for NON recording option', async () => {
    const { mockWebcam } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ record_media: true })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    expect(mockWebcam.startRecording).not.toHaveBeenCalled()
  })
})

describe('experiment.js — global timeout', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('navigates to thankyou on timeout when include_pause_page is false', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ max_duration: 500 })],
      globalTimeout: '100',
      includePausePage: 'false',
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(110)
    await flush()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })

  it('navigates to pause on timeout when include_pause_page is true', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ max_duration: 500 })],
      globalTimeout: '100',
      includePausePage: 'true',
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(110)
    await flush()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('pause'))
  })
})

describe('experiment.js — exit button', () => {
  it('navigates when exit button clicked and upload queue is empty', () => {
    const { locationReplace, mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [] })
    vi.mocked(mockWebcam.getLength).mockReturnValue(0)
    document.getElementById('exit-button').click()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringMatching(/thankyou|pause/))
  })

  it('does not navigate when exit button clicked and upload queue is non-empty', () => {
    const { locationReplace, mockWebcam } = makeEnv({ recordingOption: 'NON', trials: [] })
    vi.mocked(mockWebcam.getLength).mockReturnValue(3)
    document.getElementById('exit-button').click()
    expect(locationReplace).not.toHaveBeenCalled()
  })

  it('shows modal when exit button clicked and upload queue is non-empty', () => {
    const showSpy = vi.fn()
    const { mockWebcam } = makeEnv({
      recordingOption: 'NON',
      trials: [],
      bootstrapModal: class { constructor() {} show() { showSpy() } },
    })
    vi.mocked(mockWebcam.getLength).mockReturnValue(3)
    document.getElementById('exit-button').click()
    expect(showSpy).toHaveBeenCalled()
  })
})
