import { afterEach, describe, expect, it, vi } from 'vitest'
import { createWebcam } from '../../src/experiments/static/experiments/js/webcam.js'

function makeWebcam({ getUserMedia = async () => ({}) } = {}) {
  class MockMediaRecorder {
    constructor() { this._ev = {} }
    start()  { this._ev['start']?.forEach(fn => fn()) }
    stop()   { this._ev['stop']?.forEach(fn => fn()) }
    addEventListener(ev, fn)    { (this._ev[ev] ??= []).push(fn) }
    removeEventListener(ev, fn) { if (this._ev[ev]) this._ev[ev] = this._ev[ev].filter(l => l !== fn) }
  }
  MockMediaRecorder.isTypeSupported = () => true

  vi.stubGlobal('MediaRecorder', MockMediaRecorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia },
    writable: true,
    configurable: true,
  })

  return createWebcam()
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('webcam', () => {
  it('getLength returns 0 on fresh instance', () => {
    const w = makeWebcam()
    expect(w.getLength()).toBe(0)
  })

  it('waitForQueue resolves immediately when queue is empty', async () => {
    const w = makeWebcam()
    await expect(w.waitForQueue(0)).resolves.toBeUndefined()
  })

  it('stopUploading is safe when not uploading', () => {
    const w = makeWebcam()
    expect(() => w.stopUploading()).not.toThrow()
  })

  it('startRecording and stopRecording complete without error', async () => {
    let dataAvailableHandler
    class MockMR {
      constructor() { this._ev = {} }
      start() {}
      stop() { this._ev['stop']?.forEach(fn => fn()) }
      addEventListener(ev, fn) { (this._ev[ev] ??= []).push(fn); if (ev === 'dataavailable') dataAvailableHandler = fn }
      removeEventListener() {}
    }
    MockMR.isTypeSupported = () => true
    vi.stubGlobal('MediaRecorder', MockMR)

    const stream = { getTracks: () => [{ stop: vi.fn() }] }
    const w = makeWebcam({ getUserMedia: async () => stream })

    await w.initStream('VID')
    const recordPromise = w.startRecording('test-file', 'VID', Promise.resolve(stream))
    dataAvailableHandler?.({ data: new Blob(['x']) })
    const stopPromise = w.stopRecording('test-result-id')
    await Promise.all([recordPromise, stopPromise])
  })
})
