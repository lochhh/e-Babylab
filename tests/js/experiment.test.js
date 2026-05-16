import { describe, it, expect, vi } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/experiment.js')

// Minimal image trial fixture. Adjust fields when testing other trial types.
const imageTrial = {
  trial_id: 1, trial_number: 1, trial_type: 'image', image_file: 'test.jpg',
  audio_file: '', require_user_input: 'NO', max_duration: 5, record_media: false,
  is_calibration: false, record_gaze: false, background_colour: '#ffffff', label: 'trial-1',
}

function makeEnv({ recordingOption = 'NON', trials = [] } = {}) {
  const clickHandlers = {}
  const config = {
    loadingImage: '', globalTimeout: '99999', includePausePage: false,
    recordingOption, generalOnset: '0', showGazeEstimations: 'false',
    subjectUuid: 'test-uuid', subjectId: '1',
  }

  const el = (sel) => {
    const e = {
      data:        (key) => key ? config[key] : config,
      text:        ()    => sel === '#trials-data' ? JSON.stringify(trials) : '',
      click:       (fn)  => { clickHandlers[sel] = fn; return e },
      css:         ()    => e,
      on:          (ev, fn) => { if (typeof fn === 'function') clickHandlers[`${sel}:${ev}`] = fn; return e },
      off:         ()    => e,
      show:        ()    => e, hide: () => e, append: () => e, prop: () => e,
      html:        ()    => e,
      addClass:    ()    => e, removeClass: () => e, remove: () => e,
      not:         ()    => e, attr: () => e, removeAttr: () => e,
      get:         ()    => ({ requestFullscreen: null, mozRequestFullScreen: null,
                               webkitRequestFullScreen: null, msRequestFullscreen: null, style: {} }),
    }
    return e
  }

  const locationReplace  = vi.fn()
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

  // MockImage triggers onload via microtask when src is set, so preloadImages() resolves.
  class MockImage {
    constructor() { this._onload = null; this._src = '' }
    get onload() { return this._onload }
    set onload(fn) { this._onload = fn }
    get src() { return this._src }
    set src(v) { this._src = v; if (v && this._onload) Promise.resolve().then(() => this._onload()) }
  }

  // $.ajax calls done callback via microtask so postResult() resolves.
  const ajaxWithDone = () => {
    let doneCallback = null
    Promise.resolve().then(() => doneCallback?.({ result_id: 42 }, 'success', {}))
    return { done: (fn) => { doneCallback = fn; return { fail: () => {} } } }
  }

  const mockDoc = {
    createElement: (tag) => ({
      className: '', hidden: '', src: '', type: '', controls: false, preload: '',
      readyState: 0, load: () => {}, pause: () => {},
      style: { backgroundImage: '', display: '' },
      append: () => {}, appendChild: () => {}, addEventListener: () => {}, play: () => {},
      querySelector: () => null,
    }),
    querySelector:    () => null,
    querySelectorAll: () => [],
    documentElement: { requestFullscreen: null, mozRequestFullScreen: null,
                       webkitRequestFullScreen: null, msRequestFullscreen: null },
    getElementById:  () => null,
    exitFullscreen:  () => {},
    fullScreen: false, mozFullScreen: false, webkitIsFullScreen: false,
  }

  const $ = (arg) => el(arg)
  $.ajaxSetup = () => {}
  $.ajax = ajaxWithDone
  $.get = () => Promise.resolve('')
  $.fn = {}

  loadScript(SRC, [], {
    $,
    Cookies:    { get: () => 'test-csrf' },
    window:     { location: { replace: locationReplace }, screen: { width: 1920, height: 1080 },
                  innerWidth: 1920, innerHeight: 1080 },
    navigator:  { mediaDevices: { getUserMedia: () => Promise.resolve({}) } },
    document:   mockDoc,
    performance:{ now: () => 0 },
    Image:      MockImage,
    bootstrap:  { Modal: class { constructor() {} show() {} } },
    webcam:      mockWebcam,
    webgazer:    mockWebgazer,
    initWebgazer:       mockInitWebgazer,
    startGazeRecording: vi.fn(),
    stopGazeRecording:  vi.fn(),
    calibrate:          vi.fn().mockResolvedValue(undefined),
    show_gaze_estimations: 'false',
    webgazer_data: [],
    console:    { log: () => {}, error: () => {}, warn: () => {} },
    setTimeout,
    clearTimeout,
  })

  return { clickHandlers, locationReplace, mockWebcam, mockInitWebgazer }
}

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
    const { clickHandlers, mockWebcam } = makeEnv()
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockWebcam.startUploading).toHaveBeenCalledWith('test-uuid')
  })

  it('calls initWebgazer for EYE mode', async () => {
    const { clickHandlers, mockInitWebgazer } = makeEnv({ recordingOption: 'EYE' })
    await new Promise(resolve => setTimeout(resolve, 10)) // let initStream settle + register click handler
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockInitWebgazer).toHaveBeenCalled()
  })

  it('does not call initWebgazer for NON mode', async () => {
    const { clickHandlers, mockInitWebgazer } = makeEnv()
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(mockInitWebgazer).not.toHaveBeenCalled()
  })
})

describe('experiment.js — trial flow', () => {
  it('navigates to thankyou immediately when no trials remain', async () => {
    const { clickHandlers, locationReplace } = makeEnv({ trials: [] })
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 20))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })

  it('calls webcam.startRecording for a VID trial with record_media=true', async () => {
    const trial = { ...imageTrial, record_media: true }
    const { clickHandlers, mockWebcam } = makeEnv({ recordingOption: 'VID', trials: [trial] })
    await new Promise(resolve => setTimeout(resolve, 10)) // initStream settles + click handler registered
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 30))
    expect(mockWebcam.startRecording).toHaveBeenCalled()
  })

  it('navigates to thankyou after a single image trial completes (NON mode)', async () => {
    const { clickHandlers, locationReplace } = makeEnv({ trials: [imageTrial] })
    await new Promise(resolve => setTimeout(resolve, 10)) // let promise chain register click handler
    clickHandlers['#fullscreen-button']?.()
    // max_duration=5ms + microtask chain for postResult + stopRecording + showNextTrial
    await new Promise(resolve => setTimeout(resolve, 50))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })

  it('navigates to thankyou after a single image trial completes (VID mode, no recording)', async () => {
    const { clickHandlers, locationReplace } = makeEnv({
      recordingOption: 'VID',
      trials: [{ ...imageTrial, record_media: false }],
    })
    await new Promise(resolve => setTimeout(resolve, 10)) // initStream + click handler registered
    clickHandlers['#fullscreen-button']?.()
    await new Promise(resolve => setTimeout(resolve, 50))
    expect(locationReplace).toHaveBeenCalledWith('/test-uuid/run/thankyou')
  })
})
