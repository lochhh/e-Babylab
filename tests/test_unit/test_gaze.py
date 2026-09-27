"""Unit tests for experiments/gaze.py."""

import pytest

from experiments.gaze import MAX_SAMPLE_GAP_MS, dwell_time, parse_samples, roi_cell


@pytest.mark.parametrize(
    "x,y,expected",
    [
        (10, 10, (1, 1)),
        (99, 99, (2, 2)),
        (50, 50, (1, 1)),  # on a boundary → lower cell, as before
        (51, 10, (1, 2)),
        (0, 50, (1, 0)),  # left edge → off-screen column
        (50, 0, (0, 1)),  # top edge → off-screen row
        (100, 50, (1, 0)),  # right edge (WebGazer clamp) → off-screen column
        (50, 100, (0, 1)),  # bottom edge → off-screen row
        (-5, 150, (0, 0)),  # outside on both axes
    ],
)
def test_roi_cell_2x2(x, y, expected):
    """Cells are 1-based; screen edges and beyond map to 0 on that axis."""
    assert roi_cell(x, y, 100, 100, 2, 2) == expected


def test_roi_cell_non_divisible_size_stays_within_grid():
    """A width not divisible by cols never yields a column beyond the grid."""
    assert roi_cell(100, 10, 101, 100, 1, 2) == (1, 2)


def test_roi_cell_zero_resolution_is_off_screen():
    """Missing resolution (legacy rows default to 0) maps to (0, 0), not an error."""
    assert roi_cell(10, 10, 0, 0, 2, 2) == (0, 0)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, []),
        ("junk", []),
        ([{"x": 1, "y": 2, "t": 3}], [{"x": 1.0, "y": 2.0, "t": 3.0}]),
        ([{"x": 1, "y": 2}], []),  # missing t
        ([{"x": "a", "y": 2, "t": 3}], []),  # non-numeric
        ([{"x": "nan", "y": 2, "t": 3}], []),  # non-finite
        ([[1, 2, 3], {"x": 1, "y": 2, "t": 3}], [{"x": 1.0, "y": 2.0, "t": 3.0}]),
    ],
)
def test_parse_samples_drops_malformed_entries(raw, expected):
    """Client-supplied gaze data is filtered to well-formed finite samples."""
    assert parse_samples(raw) == expected


def _s(x, y, t):
    return {"x": x, "y": y, "t": t}


@pytest.mark.parametrize(
    "samples,target,expected",
    [
        ([], None, 0),
        ([_s(10, 10, 0)], None, 0),  # a single sample has no interval
        ([_s(10, 10, 0), _s(10, 10, 34), _s(10, 10, 68)], None, 68),
        ([_s(10, 10, 0), _s(90, 90, 34), _s(90, 90, 68)], (1, 1), 34),
        ([_s(10, 10, 0), _s(90, 90, 34), _s(90, 90, 68)], (2, 2), 34),
        ([_s(0, 10, 0), _s(10, 10, 34), _s(10, 10, 68)], None, 34),  # off-screen
        ([_s(10, 10, 0), _s(10, 10, 1000)], None, MAX_SAMPLE_GAP_MS),  # gap capped
        ([_s(10, 10, 50), _s(10, 10, 20)], None, 0),  # out-of-order never subtracts
    ],
)
def test_dwell_time(samples, target, expected):
    """Dwell sums capped sample intervals whose first sample is in the target."""
    assert dwell_time(samples, 100, 100, 2, 2, target) == expected
