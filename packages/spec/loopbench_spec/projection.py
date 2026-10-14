"""Pinhole bookkeeping shared by renderers and perception.

Simulators and policies both import this. Neither imports the other.
`cam_dx` and `cam_dy` are meters. Callers that have not calibrated pass 0.
"""

from __future__ import annotations


def world_to_px(
    x: float,
    y: float,
    cam_dx: float,
    cam_dy: float,
    *,
    size: int,
    world_x: float,
    world_y: float,
) -> tuple[float, float]:
    u = (x - cam_dx) / world_x * (size - 1)
    v = (size - 1) - (y - cam_dy) / world_y * (size - 1)
    return u, v


def px_to_world(
    u: float,
    v: float,
    cam_dx: float,
    cam_dy: float,
    *,
    size: int,
    world_x: float,
    world_y: float,
) -> tuple[float, float]:
    x = u / (size - 1) * world_x + cam_dx
    y = (size - 1 - v) / (size - 1) * world_y + cam_dy
    return x, y
