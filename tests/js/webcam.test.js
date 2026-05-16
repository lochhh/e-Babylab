import { describe, it, expect, vi } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const WEBCAM_SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/webcam.js')
const QUEUE_SRC  = resolve(__dirname, '../../src/experiments/static/experiments/js/queue.src.js')

function makeWebcam({ getUserMedia = async () => ({}) } = {}) {
  const { Queue } = loadScript(QUEUE_SRC)

  class MockMediaRecorder {
    constructor() { this._ev = {} }
    start()  { this._ev['start']?.forEach(fn => fn()) }
    stop()   { this._ev['stop']?.forEach(fn => fn()) }
    addEventListener(ev, fn)    { (this._ev[ev] ??= []).push(fn) }
    removeEventListener(ev, fn) { if (this._ev[ev]) this._ev[ev] = this._ev[ev].filter(l => l !== fn) }
  }
  MockMediaRecorder.isTypeSupported = () => true

  const { webcam } = loadScript(WEBCAM_SRC, ['webcam'], {
    Cookies:   { get: () => 'test-csrf' },
    $:         { ajaxSetup: () => {} },
    Queue,
    MediaRecorder: MockMediaRecorder,
    navigator: { mediaDevices: { getUserMedia } },
    console:   { log: () => {}, error: () => {} },
    setTimeout:  (fn, ms) => setTimeout(fn, ms),
    clearTimeout: (id) => clearTimeout(id),
    FormData: class { append() {} },
    File:     class { constructor() {} },
  })

  return webcam
}

describe('webcam.js — getLength', () => {
  it('returns 0 on fresh instance', () => {
    expect(makeWebcam().getLength()).toBe(0)
  })
})

describe('webcam.js — waitForQueue', () => {
  it('resolves immediately when queue is already at requested length', async () => {
    await expect(makeWebcam().waitForQueue(0)).resolves.toBeUndefined()
  })

  it('does not resolve while queue is shorter than requested length', async () => {
    const w = makeWebcam()
    let resolved = false
    w.waitForQueue(1).then(() => { resolved = true })
    await Promise.resolve() // flush microtasks
    expect(resolved).toBe(false)
  })
})

describe('webcam.js — startUploading / stopUploading', () => {
  it('stopUploading is a no-op when not uploading', () => {
    expect(() => makeWebcam().stopUploading()).not.toThrow()
  })

  it('startUploading followed by stopUploading does not throw', () => {
    const w = makeWebcam()
    w.startUploading('test-uuid')
    expect(() => w.stopUploading()).not.toThrow()
  })
})

describe('webcam.js — startRecording / stopRecording', () => {
  it('startRecording resolves after MediaRecorder fires start event', async () => {
    const w = makeWebcam()
    await w.startRecording('trial-1', 'VID', Promise.resolve({}))
    expect(w.getLength()).toBe(0) // no chunks enqueued yet
  })

  it('stopRecording resolves immediately when not recording', async () => {
    await expect(makeWebcam().stopRecording(42)).resolves.toBeUndefined()
  })

  it('stopRecording enqueues a merge task after a completed recording', async () => {
    const w = makeWebcam()
    await w.startRecording('trial-1', 'VID', Promise.resolve({}))
    await w.stopRecording(99)
    expect(w.getLength()).toBe(1)
  })

  it('waitForQueue(1) resolves once stopRecording enqueues the merge task', async () => {
    const w = makeWebcam()
    await w.startRecording('trial-1', 'VID', Promise.resolve({}))
    const waitP = w.waitForQueue(1)
    await w.stopRecording(99)
    await waitP
    expect(w.getLength()).toBe(1)
  })
})
