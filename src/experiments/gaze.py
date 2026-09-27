"""Pure gaze helpers: grid cells and dwell time from WebGazer samples.

Shared by the reporter (report time) and ``nexttrial`` (attention getter check).
"""

import math
from collections.abc import Sequence
from itertools import pairwise
from typing import TypedDict

#: Longest interval credited to one sample; larger gaps mean the face was lost.
MAX_SAMPLE_GAP_MS = 100.0

#: A 1-based ``(row, col)`` grid cell; 0 on an axis means off-screen.
Cell = tuple[int, int]


class GazeSample(TypedDict):
    """One WebGazer prediction as stored in ``TrialResult.webgazer_data``."""

    x: float
    y: float
    t: float


def _axis_cell(value: float, size: int, count: int) -> int:
    """Return the 1-based cell index of ``value`` along one axis, or 0 if off-screen."""
    if value <= 0 or value >= size:
        return 0
    return min(count, max(1, math.ceil(value * count / size)))


def roi_cell(x: float, y: float, width: int, height: int, rows: int, cols: int) -> Cell:
    """Return the grid cell containing a gaze or click coordinate.

    WebGazer clamps off-screen predictions onto the screen edge, so a coordinate
    on (or beyond) an edge is reported as 0 on that axis rather than as the
    edge cell.

    Args:
        x (float): Horizontal coordinate in pixels.
        y (float): Vertical coordinate in pixels.
        width (int): Screen width in pixels.
        height (int): Screen height in pixels.
        rows (int): Number of grid rows.
        cols (int): Number of grid columns.

    Returns:
        Cell: 1-based ``(row, col)``; an axis is 0 when off-screen.

    """
    return _axis_cell(y, height, rows), _axis_cell(x, width, cols)


def parse_samples(raw: object) -> list[GazeSample]:
    """Return the well-formed gaze samples from client-supplied JSON.

    Entries that are not objects, lack ``x``/``y``/``t``, or hold non-numeric
    or non-finite values are dropped, so malformed data can never raise.

    Args:
        raw (object): Decoded ``webgazer_data`` as stored on a ``TrialResult``.

    Returns:
        list[GazeSample]: Samples with float coordinates, in their original order.

    """
    if not isinstance(raw, list):
        return []
    samples: list[GazeSample] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            x, y, t = float(item["x"]), float(item["y"]), float(item["t"])
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(v) for v in (x, y, t)):
            samples.append(GazeSample(x=x, y=y, t=t))
    return samples


def dwell_time(
    samples: Sequence[GazeSample],
    width: int,
    height: int,
    rows: int,
    cols: int,
    target: Cell | None,
) -> float:
    """Return how long gaze stayed in the target, in milliseconds.

    Each interval between consecutive samples is credited to the first sample
    of the pair, capped at ``MAX_SAMPLE_GAP_MS``. Off-screen samples never count.

    Args:
        samples (Sequence[GazeSample]): Time-ordered gaze samples.
        width (int): Screen width in pixels.
        height (int): Screen height in pixels.
        rows (int): Number of grid rows.
        cols (int): Number of grid columns.
        target (Cell | None): Cell to measure, or ``None`` for any on-screen cell.

    Returns:
        float: Dwell time in milliseconds.

    """
    total = 0.0
    for current, following in pairwise(samples):
        cell = roi_cell(current["x"], current["y"], width, height, rows, cols)
        if 0 in cell or (target is not None and cell != target):
            continue
        total += min(max(following["t"] - current["t"], 0.0), MAX_SAMPLE_GAP_MS)
    return total
