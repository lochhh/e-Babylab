import { describe, it, expect, beforeAll } from 'vitest'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { loadScript } from './helpers/load-script.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(__dirname, '../../src/experiments/static/experiments/js/webgazer-calibration.js')

// All calculation functions are let-declared, so we capture them explicitly.
let calculateAccuracy, calculatePrecisionRMS, calculatePrecisionSD
beforeAll(() => {
  ;({ calculateAccuracy, calculatePrecisionRMS, calculatePrecisionSD } = loadScript(
    SRC,
    ['calculateAccuracy', 'calculatePrecisionRMS', 'calculatePrecisionSD'],
  ))
})

// Helper: build the [xArray, yArray] format webgazer uses
const pts = (xs, ys) => [xs, ys]

describe('calculateAccuracy', () => {
  // Mean Euclidean distance from each prediction to the target point.

  it('returns 0 when all predictions are exactly on target', () => {
    const result = calculateAccuracy(pts([100, 100], [200, 200]), 2, 100, 200)
    expect(result).toBe(0)
  })

  it('computes mean distance for known points', () => {
    // Prediction 1: (0,0) → target (0,0) = distance 0
    // Prediction 2: (3,4) → target (0,0) = distance 5
    // Mean = 2.5
    const result = calculateAccuracy(pts([0, 3], [0, 4]), 2, 0, 0)
    expect(result).toBeCloseTo(2.5)
  })

  it('handles single prediction', () => {
    // (5,12) → target (0,0) = sqrt(25+144) = 13
    const result = calculateAccuracy(pts([5], [12]), 1, 0, 0)
    expect(result).toBeCloseTo(13)
  })

  it('uses only numPredictions entries, ignoring extras', () => {
    // Only first 2 of 3 points counted
    const result = calculateAccuracy(pts([0, 0, 999], [0, 0, 999]), 2, 0, 0)
    expect(result).toBe(0)
  })
})

describe('calculatePrecisionRMS', () => {
  // RMS of successive inter-sample distances.

  it('returns 0 when all points are identical', () => {
    const result = calculatePrecisionRMS(pts([100, 100, 100], [200, 200, 200]), 3)
    expect(result).toBe(0)
  })

  it('computes RMS for single step', () => {
    // Step: (0→3, 0→4) → dist² = 9+16 = 25, mean = 25, RMS = 5
    const result = calculatePrecisionRMS(pts([0, 3], [0, 4]), 2)
    expect(result).toBeCloseTo(5)
  })

  it('computes RMS for equal steps', () => {
    // Step 1: (0→3, 0→4) dist²=25; Step 2: (3→6, 4→8) dist²=9+16=25
    // mean = 25, RMS = 5
    const result = calculatePrecisionRMS(pts([0, 3, 6], [0, 4, 8]), 3)
    expect(result).toBeCloseTo(5)
  })

  it('computes RMS for unequal steps', () => {
    // Step 1: (0→4, 0→3) dist²=16+9=25; Step 2: (4→4, 3→3) dist²=0
    // mean = 12.5, RMS = sqrt(12.5)
    const result = calculatePrecisionRMS(pts([0, 4, 4], [0, 3, 3]), 3)
    expect(result).toBeCloseTo(Math.sqrt(12.5))
  })
})

describe('calculatePrecisionSD', () => {
  // Population standard deviation of gaze locations in X and Y separately.

  it('returns [0,0] when all points are identical', () => {
    const [sdX, sdY] = calculatePrecisionSD(pts([5, 5, 5], [10, 10, 10]), 3)
    expect(sdX).toBe(0)
    expect(sdY).toBe(0)
  })

  it('computes known SD for two-point spread', () => {
    // x=[1,3] mean=2, var=((1-2)²+(3-2)²)/2=1, sd=1
    // y=[2,4] mean=3, var=((2-3)²+(4-3)²)/2=1, sd=1
    const [sdX, sdY] = calculatePrecisionSD(pts([1, 3], [2, 4]), 2)
    expect(sdX).toBeCloseTo(1)
    expect(sdY).toBeCloseTo(1)
  })

  it('returns [0,0] for single prediction', () => {
    const [sdX, sdY] = calculatePrecisionSD(pts([42], [99]), 1)
    expect(sdX).toBe(0)
    expect(sdY).toBe(0)
  })

  it('X and Y dimensions are independent', () => {
    // x all same → sdX=0; y varies → sdY>0
    const [sdX, sdY] = calculatePrecisionSD(pts([5, 5, 5], [1, 3, 5]), 3)
    expect(sdX).toBe(0)
    expect(sdY).toBeGreaterThan(0)
  })
})
