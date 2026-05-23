import { describe, it, expect, afterEach, vi } from 'vitest'
import { init } from '../../src/experiments/static/experiments/js/browser-check.js'

function run({ hasMediaRecorder, hasGetUserMedia }) {
  document.body.innerHTML = `
    <div id="webcam_step_1">
      <div class="alert-danger" style="display:none"></div>
      <div class="alert-success" style="display:none"></div>
      <button disabled>Continue</button>
    </div>
  `
  if (hasMediaRecorder) {
    vi.stubGlobal('MediaRecorder', class MediaRecorder {})
  } else {
    vi.stubGlobal('MediaRecorder', undefined)
  }
  Object.defineProperty(navigator, 'mediaDevices', {
    value: hasGetUserMedia ? {} : null,
    writable: true,
    configurable: true,
  })
  init()
  return document.getElementById('webcam_step_1')
}

afterEach(() => vi.unstubAllGlobals())

describe('browser-check.js', () => {
  it('shows success and enables button when both APIs are available', () => {
    const step1 = run({ hasMediaRecorder: true, hasGetUserMedia: true })
    expect(step1.querySelector('.alert-success').style.display).toBe('block')
    expect(step1.querySelector('button').hasAttribute('disabled')).toBe(false)
    expect(step1.querySelector('.alert-danger').style.display).not.toBe('block')
  })

  it('shows danger alert and getUserMedia message when mediaDevices is missing', () => {
    const step1 = run({ hasMediaRecorder: true, hasGetUserMedia: false })
    expect(step1.querySelector('.alert-danger').style.display).toBe('block')
    expect(step1.querySelector('.alert-danger').innerHTML).toContain('getUserMedia')
    expect(step1.querySelector('.alert-success').style.display).not.toBe('block')
  })

  it('shows danger alert and MediaRecorder message when MediaRecorder is missing', () => {
    const step1 = run({ hasMediaRecorder: false, hasGetUserMedia: true })
    expect(step1.querySelector('.alert-danger').style.display).toBe('block')
    expect(step1.querySelector('.alert-danger').innerHTML).toContain('MediaRecorder')
  })

  it('reports getUserMedia error first when both APIs are missing', () => {
    const step1 = run({ hasMediaRecorder: false, hasGetUserMedia: false })
    expect(step1.querySelector('.alert-danger').style.display).toBe('block')
    expect(step1.querySelector('.alert-danger').innerHTML).toContain('getUserMedia')
  })
})
