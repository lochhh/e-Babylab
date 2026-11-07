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
    abandonRecording: vi.fn(),
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
  setGazeOrigin:      vi.fn(),
}))

import { webcam } from '../../src/experiments/static/experiments/js/webcam.js'
import { initWebgazer, setGazeOrigin } from '../../src/experiments/static/experiments/js/webgazer-calibration.js'
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
    stimulus_type: 'image',
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
  // Mirrors experiment_run: first pending trial, the one after it, and every pending video
  document.getElementById('trials-data').textContent = JSON.stringify({
    trial: trials[0] ?? null,
    upcoming: trials[1] ?? null,
    videos: trials
      .filter(t => t.stimulus_type === 'video')
      .map(t => ({ trial_id: t.trial_id, visual_file: t.visual_file })),
  })

  const locationReplace = vi.fn()
  vi.stubGlobal('location', { replace: locationReplace, href: '', assign: vi.fn() })
  vi.stubGlobal('webgazer', {
    pause:                vi.fn(),
    resume:               vi.fn().mockResolvedValue(undefined),
    getCurrentPrediction: vi.fn().mockResolvedValue(null),
  })
  const ModalClass = bootstrapModal || class { constructor() {} show() {} }
  vi.stubGlobal('bootstrap', { Modal: ModalClass })
  const pendingTrials = trials.slice(1)
  vi.stubGlobal('fetch', vi.fn((url) => {
    if (String(url).includes('/run/nexttrial')) {
      const trial = pendingTrials.shift()
      const upcoming = pendingTrials[0] ?? null
      return Promise.resolve({
        ok:   true,
        json: () => Promise.resolve(trial ? { done: false, trial, upcoming } : { done: true }),
        text: () => Promise.resolve(''),
      })
    }
    return Promise.resolve({
      ok:   true,
      json: () => Promise.resolve({ resultId: 42 }),
      text: () => Promise.resolve(''),
    })
  }))

  vi.mocked(webcam.initStream).mockResolvedValue({})
  vi.mocked(webcam.getLength).mockReturnValue(0)
  vi.mocked(webcam.waitForQueue).mockResolvedValue(undefined)
  vi.mocked(webcam.stopRecording).mockResolvedValue(undefined)
  vi.mocked(webcam.abandonRecording).mockResolvedValue(undefined)
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

describe.each([
  ['the global timeout', { globalTimeout: '100' }, () => vi.advanceTimersByTimeAsync(110)],
  // Earlier tests' init() calls left their listeners on document, so call only this one's
  ['leaving fullscreen', {}, (onFullscreenChange) => onFullscreenChange()],
])('experiment.js — %s waits for queued uploads', (_, env, leaveBy) => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  let onFullscreenChange
  const leave = () => leaveBy(onFullscreenChange)

  // A video trial still running when the participant leaves
  const start = async () => {
    const listen = vi.spyOn(document, 'addEventListener')
    const result = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ max_duration: 5000 })],
      includePausePage: 'true',
      ...env,
    })
    onFullscreenChange = listen.mock.calls.findLast(([ev]) => ev === 'fullscreenchange')[1]
    listen.mockRestore()
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    return result
  }
  const PAUSE = '/test-uuid/run/pause?trialitem=1&trial_number=1'

  it('goes to the pause page once the upload queue is empty', async () => {
    const { locationReplace } = await start()
    let drain
    vi.mocked(webcam.waitForQueue).mockReturnValue(new Promise(r => { drain = r }))

    await leave()
    await flush()
    expect(locationReplace).not.toHaveBeenCalled()

    drain()
    await flush()
    expect(locationReplace).toHaveBeenCalledWith(PAUSE)
    expect(webcam.stopUploading).toHaveBeenCalled()
  })

  it('stops the interrupted recording without a merge request', async () => {
    await start()
    await leave()
    await flush()
    expect(webcam.abandonRecording).toHaveBeenCalled()
    expect(webcam.stopRecording).not.toHaveBeenCalled()
  })

  it('stops waiting after 30 seconds', async () => {
    const { locationReplace } = await start()
    vi.mocked(webcam.waitForQueue).mockReturnValue(new Promise(() => {}))

    await leave()
    await flush()
    await vi.advanceTimersByTimeAsync(29000)
    expect(locationReplace).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1100)
    await flush()
    expect(locationReplace).toHaveBeenCalledWith(PAUSE)
  })

  it('does not store a trial that ends while waiting', async () => {
    await start()
    vi.mocked(webcam.waitForQueue).mockReturnValue(new Promise(() => {}))

    await leave()
    await flush()
    await vi.advanceTimersByTimeAsync(6000)
    await flush()
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining('storeresult'), expect.anything())
  })
})

describe('experiment.js — interrupted between trials', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('does not show the next trial that arrives after leaving fullscreen', async () => {
    const listen = vi.spyOn(document, 'addEventListener')
    const { locationReplace } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ trial_id: 1, max_duration: 500 }), makeTrial({ trial_id: 2, trial_number: 2 })],
      includePausePage: 'true',
    })
    const onFullscreenChange = listen.mock.calls.findLast(([ev]) => ev === 'fullscreenchange')[1]
    listen.mockRestore()
    // Hold the next-trial request so the participant leaves while it is in flight
    let sendNextTrial
    const respond = fetch.getMockImplementation()
    vi.mocked(fetch).mockImplementation((url, ...rest) => String(url).includes('/run/nexttrial')
      ? new Promise(r => { sendNextTrial = () => r(respond(url, ...rest)) })
      : respond(url, ...rest))
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(600) // trial 1 ends; its result is stored
    await flush()
    expect(sendNextTrial).toBeDefined()

    onFullscreenChange()
    sendNextTrial()
    await flush()

    expect(webcam.startRecording).toHaveBeenCalledTimes(1) // trial 2 never starts
    expect(document.querySelector('.trial-image')).toBeNull()
    await flush()
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/pause?trialitem=1&trial_number=1')
  })
})

describe('experiment.js — leaving after the last trial', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('still goes to the thank-you page once uploads finish', async () => {
    const listen = vi.spyOn(document, 'addEventListener')
    const { locationReplace } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ max_duration: 500 })],
      includePausePage: 'true',
    })
    const onFullscreenChange = listen.mock.calls.findLast(([ev]) => ev === 'fullscreenchange')[1]
    listen.mockRestore()
    let drain
    vi.mocked(webcam.waitForQueue).mockReturnValue(new Promise(r => { drain = r }))
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(600) // the only trial ends; waiting for uploads
    await flush()

    onFullscreenChange()
    await vi.advanceTimersByTimeAsync(31000)
    expect(locationReplace).not.toHaveBeenCalled()

    drain()
    await flush()
    expect(locationReplace).toHaveBeenCalledTimes(1)
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })

  it('goes to the thank-you page, not the pause page, when the exit button is clicked', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'VID',
      trials: [makeTrial({ max_duration: 500 })],
      includePausePage: 'true',
    })
    vi.mocked(webcam.waitForQueue).mockReturnValue(new Promise(() => {}))
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(600) // the only trial ends; waiting for uploads
    await flush()

    document.getElementById('exit-button').click()

    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
    expect(locationReplace).not.toHaveBeenCalledWith(expect.stringContaining('pause'))
  })
})

describe('experiment.js — pause redirect carries the trial on screen', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('adds trialitem and trial_number to the pause URL on timeout', async () => {
    const { locationReplace } = makeEnv({
      trials: [makeTrial({ trial_id: 7, trial_number: 3, max_duration: 500 })],
      globalTimeout: '100',
      includePausePage: 'true',
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(110)
    await flush()
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/pause?trialitem=7&trial_number=3')
  })

  it('adds the params when the exit button is clicked mid-trial', async () => {
    const { locationReplace } = makeEnv({
      trials: [makeTrial({ trial_id: 7, trial_number: 3, max_duration: 500 })],
      includePausePage: 'true',
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    document.getElementById('exit-button').click()
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/pause?trialitem=7&trial_number=3')
  })

  it('still carries the last trial after its result was posted', async () => {
    const { locationReplace } = makeEnv({
      trials: [makeTrial({ trial_id: 7, trial_number: 3, max_duration: 50 })],
      includePausePage: 'true',
    })
    // Hold the next-trial request: the run is between trials, not finished
    const respond = fetch.getMockImplementation()
    vi.mocked(fetch).mockImplementation((url, ...rest) =>
      String(url).includes('/run/nexttrial') ? new Promise(() => {}) : respond(url, ...rest))
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(100)
    await flush()
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('storeresult'), expect.anything())
    document.getElementById('exit-button').click()
    expect(locationReplace).toHaveBeenLastCalledWith('/test-uuid/run/pause?trialitem=7&trial_number=3')
  })

  it('uses the plain pause URL when no trial is on screen', () => {
    const { locationReplace } = makeEnv({ trials: [], includePausePage: 'true' })
    document.getElementById('exit-button').click()
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/pause')
  })
})

describe('experiment.js — video trial', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('renders video container and completes trial on video end', async () => {
    HTMLVideoElement.prototype.play = vi.fn().mockReturnValue(Promise.resolve())
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ stimulus_type: 'video', require_user_input: 'NO' })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    // preloadVideo runs synchronously inside showNextTrial — #video-container-1 is in DOM
    const video = document.querySelector('#video-container-1 > video')
    video.dispatchEvent(new Event('canplay'))       // triggers displayVideo
    await vi.advanceTimersByTimeAsync(1)            // past visual_onset(0) setTimeout
    await flush()
    expect(document.querySelector('#video-container-1').style.display).toBe('block')
    video.dispatchEvent(new Event('ended'))         // triggers setupVideoEnd resolve
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/run/storeresult'),
      expect.objectContaining({ method: 'POST' }),
    )
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })

  it('creates and unlocks an element for every pending video in the fullscreen tap', async () => {
    const play = vi.fn().mockReturnValue(Promise.resolve())
    HTMLVideoElement.prototype.play = play
    makeEnv({
      recordingOption: 'NON',
      trials: [
        makeTrial({ trial_id: 1 }),
        makeTrial({ trial_id: 2, stimulus_type: 'video', visual_file: '/media/a.mp4' }),
        makeTrial({ trial_id: 3, stimulus_type: 'video', visual_file: '/media/b.mp4' }),
      ],
    })
    await flush()
    const videos = ['#video-container-2 > video', '#video-container-3 > video']
      .map(sel => document.querySelector(sel))
    expect(videos).not.toContain(null)
    document.getElementById('fullscreen-button').click()
    // iOS only allows later play() on elements played inside the user gesture
    expect(play.mock.contexts).toEqual(videos)
  })

  it('preloads the upcoming video while the current trial runs', async () => {
    HTMLVideoElement.prototype.play = vi.fn().mockReturnValue(Promise.resolve())
    const load = vi.fn()
    HTMLVideoElement.prototype.load = load
    makeEnv({
      recordingOption: 'NON',
      trials: [
        makeTrial({ trial_id: 1, max_duration: 500 }),
        makeTrial({ trial_id: 2, stimulus_type: 'video', visual_file: '/media/a.mp4' }),
      ],
    })
    await flush()
    const video = document.querySelector('#video-container-2 > video')
    expect(video.preload).toBe('none')  // no data fetched before the tap
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(1)  // past visual_onset(0)
    await flush()
    // Trial 1 (image) is on screen; trial 2's video is loading behind it
    expect(document.querySelector('.trial-image')).not.toBeNull()
    expect(video.preload).toBe('auto')
    expect(load.mock.contexts).toContain(video)
  })

  it('keeps an attention getter video element (hidden, rewound) for reuse', async () => {
    HTMLVideoElement.prototype.play = vi.fn().mockReturnValue(Promise.resolve())
    makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ stimulus_type: 'video', require_user_input: 'NO', is_attention_getter: true })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    const video = document.querySelector('#video-container-1 > video')
    video.dispatchEvent(new Event('canplay'))
    await vi.advanceTimersByTimeAsync(1)
    await flush()
    video.currentTime = 3
    video.dispatchEvent(new Event('ended'))
    await flush()
    const container = document.querySelector('#video-container-1')
    expect(container).not.toBeNull()          // regular trials remove it
    expect(container.style.display).toBe('none')
    expect(video.currentTime).toBe(0)
  })
})

describe('experiment.js — keypress response', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('resolves trial on expected key press before max_duration', async () => {
    // codes['a'] = 97 - 32 = 65 (experiment.js:64)
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ require_user_input: 'YES', response_keys: ['a'], max_duration: 500 })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(1)  // past visual_onset(0) and waitPromise(0)
    await flush()
    // setupKeyPresses listener is now registered; max_duration (500ms) has not fired
    document.dispatchEvent(new KeyboardEvent('keydown', { which: 65, bubbles: true }))
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    expect(fetch).toHaveBeenCalled()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })
})

describe('experiment.js — gaze timing', () => {
  it('sets the gaze origin to the trial start time, after stimuli are shown', async () => {
    makeEnv({
      recordingOption: 'EYE',
      trials: [makeTrial({ record_gaze: true, max_duration: 10 })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush(30)
    await new Promise(r => setTimeout(r, 30))
    await flush(30)
    const post = vi.mocked(fetch).mock.calls.find(([url]) => String(url).includes('storeresult'))
    const startTime = Number(post[1].body.get('start_time'))
    expect(setGazeOrigin).toHaveBeenCalledWith(startTime)
  })
})

describe('experiment.js — click response', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('resolves trial on document click when response_keys includes "click"', async () => {
    const { locationReplace } = makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ require_user_input: 'YES', response_keys: ['click'], max_duration: 500 })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(1)
    await flush()
    // click handler registered; dispatch on body so event.target is an Element (has .closest)
    // dispatching on document directly makes event.target = document which lacks .closest
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    expect(fetch).toHaveBeenCalled()
    expect(locationReplace).toHaveBeenCalledWith(expect.stringContaining('thankyou'))
  })

  it('ignores clicks in the exit confirmation modal', async () => {
    makeEnv({
      recordingOption: 'NON',
      trials: [makeTrial({ require_user_input: 'YES', response_keys: ['click'], max_duration: 500 })],
    })
    await flush()
    document.getElementById('fullscreen-button').click()
    await flush()
    await vi.advanceTimersByTimeAsync(1)
    await flush()
    // "Quit" / "Return to study" are not responses to the trial
    document.getElementById('exitStudyModal').innerHTML = '<button id="confirmExitButton"></button>'
    document.getElementById('confirmExitButton').dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flush()
    await vi.advanceTimersByTimeAsync(10)
    await flush()
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining('storeresult'), expect.anything())
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

  it('moves focus out of the exit box as it closes', () => {
    makeEnv({ recordingOption: 'NON', trials: [] })
    const modal = document.getElementById('exitStudyModal')
    modal.innerHTML = '<button id="return-to-study">Return to study</button>'
    const button = document.getElementById('return-to-study')
    button.focus()
    expect(document.activeElement).toBe(button)

    // Bootstrap fires this before hiding the box with aria-hidden
    modal.dispatchEvent(new Event('hide.bs.modal'))

    expect(document.activeElement).not.toBe(button)
  })
})
