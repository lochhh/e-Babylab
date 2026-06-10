import { describe, it, expect } from 'vitest'
import {
  calculateAccuracy,
  calculatePrecisionRMS,
  calculatePrecisionSD,
  calculateAverage,
} from '../../src/experiments/static/experiments/js/webgazer-calibration.js'

const pts = (xs, ys) => [xs, ys]

describe('calculateAccuracy', () => {
  it('returns 0 when all predictions are exactly on target', () => {
    const result = calculateAccuracy(pts([100, 100], [200, 200]), 2, 100, 200)
    expect(result).toBe(0)
  })

  it('computes mean distance for known points', () => {
    const result = calculateAccuracy(pts([0, 3], [0, 4]), 2, 0, 0)
    expect(result).toBeCloseTo(2.5)
  })

  it('handles single prediction', () => {
    const result = calculateAccuracy(pts([5], [12]), 1, 0, 0)
    expect(result).toBeCloseTo(13)
  })

  it('uses only numPredictions entries, ignoring extras', () => {
    const result = calculateAccuracy(pts([0, 0, 999], [0, 0, 999]), 2, 0, 0)
    expect(result).toBe(0)
  })
})

describe('calculatePrecisionRMS', () => {
  it('returns 0 when all points are identical', () => {
    const result = calculatePrecisionRMS(pts([100, 100, 100], [200, 200, 200]), 3)
    expect(result).toBe(0)
  })

  it('computes RMS for single step', () => {
    const result = calculatePrecisionRMS(pts([0, 3], [0, 4]), 2)
    expect(result).toBeCloseTo(5)
  })

  it('computes RMS for equal steps', () => {
    const result = calculatePrecisionRMS(pts([0, 3, 6], [0, 4, 8]), 3)
    expect(result).toBeCloseTo(5)
  })

  it('computes RMS for unequal steps', () => {
    const result = calculatePrecisionRMS(pts([0, 4, 4], [0, 3, 3]), 3)
    expect(result).toBeCloseTo(Math.sqrt(12.5))
  })
})

describe('calculatePrecisionSD', () => {
  it('returns [0,0] when all points are identical', () => {
    const [sdX, sdY] = calculatePrecisionSD(pts([5, 5, 5], [10, 10, 10]), 3)
    expect(sdX).toBe(0)
    expect(sdY).toBe(0)
  })

  it('computes known SD for two-point spread', () => {
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
    const [sdX, sdY] = calculatePrecisionSD(pts([5, 5, 5], [1, 3, 5]), 3)
    expect(sdX).toBe(0)
    expect(sdY).toBeGreaterThan(0)
  })
})

describe('calculateAverage', () => {
  it('returns the mean of a single-element array', () => {
    expect(calculateAverage([42], 1)).toBe(42)
  })

  it('returns the mean of a uniform array', () => {
    expect(calculateAverage([100, 100, 100], 3)).toBe(100)
  })

  it('returns the mean of a mixed array', () => {
    expect(calculateAverage([0, 100], 2)).toBeCloseTo(50)
  })

  it('only considers the first numPredictions entries', () => {
    expect(calculateAverage([50, 50, 999], 2)).toBeCloseTo(50)
  })

  it('returns NaN when numPredictions is 0', () => {
    expect(calculateAverage([], 0)).toBeNaN()
  })
})
