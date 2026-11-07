import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

  it('abandonRecording stops the recorder without queueing a merge request', async () => {
    let dataAvailableHandler
    const stopped = vi.fn()
    class MockMR {
      constructor() { this._ev = {} }
      start() { this._ev['start']?.forEach(fn => fn()) }
      stop() { stopped(); this._ev['stop']?.forEach(fn => fn()) }
      addEventListener(ev, fn) { (this._ev[ev] ??= []).push(fn); if (ev === 'dataavailable') dataAvailableHandler = fn }
      removeEventListener(ev, fn) { if (this._ev[ev]) this._ev[ev] = this._ev[ev].filter(l => l !== fn) }
    }
    MockMR.isTypeSupported = () => true
    const stream = { getTracks: () => [{ stop: vi.fn() }] }
    const w = makeWebcam({ getUserMedia: async () => stream })
    vi.stubGlobal('MediaRecorder', MockMR) // after makeWebcam, which stubs its own
    await w.initStream('VID')
    await w.startRecording('test-file', 'VID', Promise.resolve(stream))
    dataAvailableHandler({ data: new Blob(['x']) })

    await w.abandonRecording()

    expect(stopped).toHaveBeenCalled()
    expect(w.getLength()).toBe(1) // the chunk, but no merge request
    // Recording has ended, so a later recording can start
    await expect(w.startRecording('next', 'VID', Promise.resolve(stream))).resolves.toBeUndefined()
  })

  describe('abandonRecording drops the abandoned recording\'s queued chunks', () => {
    let w, stream, recorder
    // Deliver n chunks to the current recording
    const emit = (n) => {
      for (let i = 0; i < n; i++) recorder._ev['dataavailable'].forEach(fn => fn({ data: new Blob(['x']) }))
    }
    beforeEach(async () => {
      class MockMR {
        constructor() { this._ev = {}; recorder = this }
        start() { this._ev['start']?.forEach(fn => fn()) }
        stop() { this._ev['stop']?.forEach(fn => fn()) }
        addEventListener(ev, fn) { (this._ev[ev] ??= []).push(fn) }
        removeEventListener(ev, fn) { this._ev[ev] = this._ev[ev].filter(l => l !== fn) }
      }
      MockMR.isTypeSupported = () => true
      stream = { getTracks: () => [{ stop: vi.fn() }] }
      w = makeWebcam({ getUserMedia: async () => stream })
      vi.stubGlobal('MediaRecorder', MockMR) // after makeWebcam, which stubs its own
      await w.initStream('VID')
    })

    it('keeps a finished recording\'s chunks and merge request', async () => {
      await w.startRecording('finished', 'VID', Promise.resolve(stream))
      emit(1)
      await w.stopRecording(7)
      await w.startRecording('interrupted', 'VID', Promise.resolve(stream))
      emit(2)
      expect(w.getLength()).toBe(4)

      await w.abandonRecording()

      expect(w.getLength()).toBe(2) // finished chunk + its merge request
    })

    it('keeps the front chunk, which may be uploading', async () => {
      await w.startRecording('interrupted', 'VID', Promise.resolve(stream))
      emit(3)

      await w.abandonRecording()

      expect(w.getLength()).toBe(1)
    })
  })

  it('abandonRecording is safe when not recording', async () => {
    const w = makeWebcam()
    await expect(w.abandonRecording()).resolves.toBeUndefined()
  })

  describe('uploading', () => {
    afterEach(() => {
      vi.useRealTimers()
    })

    // Record one chunk and stop, leaving a chunk and a merge request in the queue.
    async function queueChunk() {
      let dataAvailableHandler
      class MockMR {
        constructor() { this._ev = {} }
        start() { this._ev['start']?.forEach(fn => fn()) }
        stop() { this._ev['stop']?.forEach(fn => fn()) }
        addEventListener(ev, fn) { (this._ev[ev] ??= []).push(fn); if (ev === 'dataavailable') dataAvailableHandler = fn }
        removeEventListener() {}
      }
      MockMR.isTypeSupported = () => true
      const w = makeWebcam()
      vi.stubGlobal('MediaRecorder', MockMR)
      await w.startRecording('test-file', 'VID', Promise.resolve({}))
      dataAvailableHandler({ data: new Blob(['x']) })
      await w.stopRecording('test-result-id')
      return w
    }

    const ok = () => Promise.resolve(new Response(null, { status: 204 }))
    const hang = (url, opts) => new Promise((_, reject) => {
      opts.signal?.addEventListener('abort', () => reject(opts.signal.reason))
    })

    it('times out a hung upload and retries it', async () => {
      vi.useFakeTimers()
      const fetchMock = vi.fn().mockImplementationOnce(hang).mockImplementation(ok)
      vi.stubGlobal('fetch', fetchMock)
      const w = await queueChunk()

      w.startUploading('uuid')
      await vi.advanceTimersByTimeAsync(1500)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(60000)
      expect(fetchMock.mock.calls.length).toBeGreaterThan(1)
      expect(w.getLength()).toBe(0)
    })

    it('waits before retrying a failed upload', async () => {
      vi.useFakeTimers()
      const fetchMock = vi.fn()
        .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')))
        .mockImplementation(ok)
      vi.stubGlobal('fetch', fetchMock)
      const w = await queueChunk()

      w.startUploading('uuid')
      await vi.advanceTimersByTimeAsync(1500)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(500)
      expect(fetchMock).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(1000)
      expect(w.getLength()).toBe(0)
    })
  })
})
