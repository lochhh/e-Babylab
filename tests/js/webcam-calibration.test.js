import { describe, it, expect } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/webcam-calibration.js')

function makeEnv({ recordingOption = 'VID', getUserMedia = () => new Promise(() => {}) } = {}) {
  const classState = {}   // selector -> { added: Set, removed: Set }
  const clickHandlers = {}

  const el = (sel) => ({
    data:       ()       => ({ subjectUuid: 'test-uuid', includePausePage: false, recordingOption, webcamNotFound: null }),
    show:       ()       => {},
    hide:       ()       => {},
    empty:      ()       => {},
    append:     ()       => {},
    remove:     ()       => {},
    attr:       ()       => {},
    removeAttr: ()       => {},
    prop:       ()       => {},
    eq:         ()       => el(sel),
    get:        ()       => ({ pause: () => {}, play: () => {}, srcObject: null, muted: false, onloadedmetadata: null }),
    on:         ()       => el(sel),
    one:        ()       => el(sel),
    modal:      ()       => {},
    click:      (fn)     => { clickHandlers[sel] = fn },
    addClass:   (cls)    => {
      classState[sel] ??= { added: new Set(), removed: new Set() }
      classState[sel].added.add(cls)
    },
    removeClass: (cls)   => {
      classState[sel] ??= { added: new Set(), removed: new Set() }
      classState[sel].removed.add(cls)
    },
  })

  const $ = (arg) => { if (typeof arg === 'function') { arg(); return } return el(arg) }
  $.ajaxSetup = () => {}
  $.ajax      = () => ({ done: (fn) => ({ fail: () => {} }) })

  loadScript(SRC, [], {
    $,
    Cookies:   { get: () => 'test-csrf' },
    window:    { MediaRecorder: class MediaRecorder {}, location: { replace: () => {} } },
    navigator: { mediaDevices: { getUserMedia } },
    console:   { log: () => {}, error: () => {} },
  })

  return { classState, clickHandlers }
}

describe('webcam-calibration.js — init (checkStepTwo)', () => {
  it('removes active class from step 1', () => {
    const { classState } = makeEnv()
    expect(classState['#webcam_step_1']?.removed?.has('active')).toBe(true)
  })

  it('adds active class to step 2', () => {
    const { classState } = makeEnv()
    expect(classState['#webcam_step_2']?.added?.has('active')).toBe(true)
  })
})

describe('webcam-calibration.js — recording option routing', () => {
  it('VID mode: step 2 click activates step 3', () => {
    const { classState, clickHandlers } = makeEnv({ recordingOption: 'VID' })
    clickHandlers['#webcam_step_2 button']?.()
    expect(classState['#webcam_step_2']?.removed?.has('active')).toBe(true)
    expect(classState['#webcam_step_3']?.added?.has('active')).toBe(true)
  })

  it('AUD mode: step 2 click activates step 4, skipping step 3', () => {
    const { classState, clickHandlers } = makeEnv({ recordingOption: 'AUD' })
    clickHandlers['#webcam_step_2 button']?.()
    expect(classState['#webcam_step_4']?.added?.has('active')).toBe(true)
    expect(classState['#webcam_step_3']?.added?.has('active')).toBeUndefined()
  })
})

describe('webcam-calibration.js — startStream error handling', () => {
  it('shows danger alert in step 3 when getUserMedia rejects', async () => {
    const domState = {}
    const el = (sel) => ({
      data:       ()    => ({ subjectUuid: 'test-uuid', includePausePage: false, recordingOption: 'VID', webcamNotFound: null }),
      show:       ()    => { domState[sel] = { ...domState[sel], shown: true } },
      hide:       ()    => {},
      empty:      ()    => {},
      append:     (msg) => { domState[sel] = { ...domState[sel], appended: (domState[sel]?.appended ?? '') + msg } },
      remove:     ()    => {},
      attr:       ()    => {},
      removeAttr: ()    => {},
      prop:       ()    => {},
      eq:         ()    => el(sel),
      get:        ()    => ({ pause: () => {}, play: () => {}, srcObject: null, muted: false, onloadedmetadata: null }),
      on:         (ev, fn) => { if (ev === 'click') el(sel).click(fn); return el(sel) },
      one:        ()    => el(sel),
      modal:      ()    => {},
      click:      (fn)  => { clickHandlers[sel] = fn },
      addClass:   ()    => {},
      removeClass:()    => {},
    })
    const clickHandlers = {}
    const $ = (arg) => { if (typeof arg === 'function') { arg(); return } return el(arg) }
    $.ajaxSetup = () => {}
    $.ajax      = () => ({ done: (fn) => ({ fail: () => {} }) })

    loadScript(SRC, [], {
      $,
      Cookies:   { get: () => 'test-csrf' },
      window:    { MediaRecorder: class MediaRecorder {}, location: { replace: () => {} } },
      navigator: { mediaDevices: { getUserMedia: () => Promise.reject(new Error('NotAllowedError')) } },
      console:   { log: () => {}, error: () => {} },
    })

    // Trigger step 2 button click → calls checkStepThree (VID mode)
    clickHandlers['#webcam_step_2 button']?.()
    // Flush the rejected promise chain
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(domState['#webcam_step_3 .alert-danger']?.shown).toBe(true)
    expect(domState['#webcam_step_3 .alert-danger']?.appended).toContain('NotAllowedError')
  })
})
