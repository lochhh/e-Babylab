import { describe, it, expect, beforeEach } from 'vitest'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/browser-check.js')
const src = readFileSync(SRC, 'utf8')

function run({ hasMediaRecorder, hasGetUserMedia }) {
  document.body.innerHTML = `
    <div id="webcam_step_1">
      <div class="alert-danger" style="display:none"></div>
      <div class="alert-success" style="display:none"></div>
      <button disabled>Continue</button>
    </div>
  `
  if (hasMediaRecorder) {
    globalThis.MediaRecorder = class MediaRecorder {}
  } else {
    delete globalThis.MediaRecorder
  }
  Object.defineProperty(navigator, 'mediaDevices', {
    value: hasGetUserMedia ? {} : null,
    writable: true,
    configurable: true,
  })
  eval(src)
  return document.getElementById('webcam_step_1')
}

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
