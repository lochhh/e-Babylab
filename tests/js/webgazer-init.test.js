import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import {
  initWebgazer,
  startGazeRecording,
  stopGazeRecording,
  resetGazeData,
  getGazeData,
  setGazeOrigin,
} from '../../src/experiments/static/experiments/js/webgazer-calibration.js'

/** Chainable webgazer stub that records the order of its calls. */
function stubWebgazer() {
  const calls = []
  const wg = { params: {}, pause: vi.fn() }
  for (const name of ['setRegression', 'setGazeListener', 'saveDataAcrossSessions',
                      'removeMouseEventListeners', 'showVideoPreview',
                      'showPredictionPoints', 'applyKalmanFilter']) {
    wg[name] = vi.fn(() => { calls.push(name); return wg })
  }
  wg.begin = vi.fn(() => { calls.push('begin'); return Promise.resolve(wg) })
  vi.stubGlobal('webgazer', wg)
  return calls
}

afterEach(() => vi.unstubAllGlobals())

describe('initWebgazer', () => {
  it('removes mouse training listeners after begin(), which adds them', async () => {
    document.body.innerHTML = `
      <canvas id="plotting_canvas"></canvas>
      <div id="webgazer-init"><div class="col"></div><button disabled></button></div>`
    const calls = stubWebgazer()
    const done = initWebgazer()
    await vi.waitFor(() => expect(calls).toContain('applyKalmanFilter'))
    const button = document.querySelector('#webgazer-init button')
    button.disabled = false // enabled by face detection in the real flow
    button.click()
    await done
    // Mouse moves and clicks must never train the gaze model, or an
    // uncalibrated tracker (e.g. after resuming) just follows the mouse
    expect(calls.lastIndexOf('removeMouseEventListeners')).toBeGreaterThan(calls.indexOf('begin'))
  })
})

describe('gaze sample times', () => {
  let now
  beforeEach(() => {
    // Fake only the sampling interval; performance.now() is driven by `now`
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    now = 1000
    vi.spyOn(performance, 'now').mockImplementation(() => now)
    vi.stubGlobal('webgazer', {
      getCurrentPrediction: () => Promise.resolve({ x: 10, y: 20 }),
      util: { bound: d => d },
    })
    resetGazeData()
  })
  afterEach(() => {
    stopGazeRecording()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  /** Advance to `at` ms and let the sampling interval record one sample. */
  const sampleAt = async at => {
    now = at
    await vi.advanceTimersByTimeAsync(34)
  }

  it('measures t from the gaze origin; samples before it are negative', async () => {
    startGazeRecording() // immediate sample at 1000, while stimuli load
    await vi.advanceTimersByTimeAsync(0)
    await sampleAt(1100)
    setGazeOrigin(1200) // trial start
    await sampleAt(1300)
    expect(getGazeData().map(d => d.t)).toEqual([-200, -100, 100])
  })

  it('defaults the origin to when gaze recording started', async () => {
    startGazeRecording()
    await vi.advanceTimersByTimeAsync(0)
    await sampleAt(1100)
    expect(getGazeData().map(d => d.t)).toEqual([0, 100])
  })
})
