import { describe, it, expect } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/browser-check.js')

function run({ hasMediaRecorder, hasGetUserMedia }) {
  const dom = {}
  const jq = (sel) => ({
    show:       ()    => { dom[sel] = { ...dom[sel], shown: true } },
    append:     (html)=> { dom[sel] = { ...dom[sel], appended: (dom[sel]?.appended ?? '') + html } },
    removeAttr: (attr)=> { dom[sel] = { ...dom[sel], removedAttr: attr } },
  })
  const $ = (arg) => { if (typeof arg === 'function') { arg(); return } return jq(arg) }
  loadScript(SRC, [], {
    $,
    window:    { MediaRecorder: hasMediaRecorder ? class MediaRecorder {} : undefined },
    navigator: { mediaDevices: hasGetUserMedia ? {} : null },
  })
  return dom
}

describe('browser-check.js', () => {
  it('shows success and enables button when both APIs are available', () => {
    const dom = run({ hasMediaRecorder: true, hasGetUserMedia: true })
    expect(dom['#webcam_step_1 .alert-success']?.shown).toBe(true)
    expect(dom['#webcam_step_1 button']?.removedAttr).toBe('disabled')
    expect(dom['#webcam_step_1 .alert-danger']?.shown).toBeUndefined()
  })

  it('shows danger alert and getUserMedia message when mediaDevices is missing', () => {
    const dom = run({ hasMediaRecorder: true, hasGetUserMedia: false })
    expect(dom['#webcam_step_1 .alert-danger']?.shown).toBe(true)
    expect(dom['#webcam_step_1 .alert-danger']?.appended).toContain('getUserMedia')
    expect(dom['#webcam_step_1 .alert-success']?.shown).toBeUndefined()
  })

  it('shows danger alert and MediaRecorder message when MediaRecorder is missing', () => {
    const dom = run({ hasMediaRecorder: false, hasGetUserMedia: true })
    expect(dom['#webcam_step_1 .alert-danger']?.shown).toBe(true)
    expect(dom['#webcam_step_1 .alert-danger']?.appended).toContain('MediaRecorder')
  })

  it('reports getUserMedia error first when both APIs are missing', () => {
    const dom = run({ hasMediaRecorder: false, hasGetUserMedia: false })
    expect(dom['#webcam_step_1 .alert-danger']?.shown).toBe(true)
    expect(dom['#webcam_step_1 .alert-danger']?.appended).toContain('getUserMedia')
  })
})
