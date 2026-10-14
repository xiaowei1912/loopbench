"""Top-down rasterizer. Flat colors, no GPU, deterministic."""

from __future__ import annotations

import numpy as np

from loopbench_sim_reference.constants import (
    BACKGROUND,
    BIN_HALF,
    BIN_XY,
    FIDUCIAL_RADIUS,
    FIDUCIALS,
    NOMINAL_RGB,
    RENDER_SIZE,
    WORLD_X,
    WORLD_Y,
    ZONE_TOL,
    ZONE_XY,
    apply_lighting,
    camera_offset_of,
)
from loopbench_spec.projection import world_to_px as _world_to_px


def world_to_px(x: float, y: float, cam_dx: float, cam_dy: float, size: int = RENDER_SIZE) -> tuple[float, float]:
    return _world_to_px(x, y, cam_dx, cam_dy, size=size, world_x=WORLD_X, world_y=WORLD_Y)


def _disk(img: np.ndarray, u: float, v: float, rad: float, color: tuple[int, int, int]) -> None:
    height, width, _ = img.shape
    ui, vi = int(round(u)), int(round(v))
    r = int(np.ceil(rad)) + 1
    y0, y1 = max(0, vi - r), min(height, vi + r + 1)
    x0, x1 = max(0, ui - r), min(width, ui + r + 1)
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (yy - vi) ** 2 + (xx - ui) ** 2 <= rad ** 2
    img[y0:y1, x0:x1][mask] = color


def _square(img: np.ndarray, u: float, v: float, hu: float, hv: float, color: tuple[int, int, int]) -> None:
    height, width, _ = img.shape
    x0 = max(0, int(round(u - hu)))
    x1 = min(width, int(round(u + hu)) + 1)
    y0 = max(0, int(round(v - hv)))
    y1 = min(height, int(round(v + hv)) + 1)
    if y0 >= y1 or x0 >= x1:
        return
    img[y0:y1, x0:x1] = color


def _meters_to_px(meters: float, size: int, span: float) -> float:
    return meters / span * (size - 1)


def render_scene(bodies: list, ee: tuple[float, float, float, float], factors, size: int = RENDER_SIZE) -> np.ndarray:
    cam_dx, cam_dy = camera_offset_of(factors)
    lighting = factors.lighting
    img = np.empty((size, size, 3), dtype=np.uint8)
    img[:] = BACKGROUND[lighting]

    def px(x: float, y: float) -> tuple[float, float]:
        return world_to_px(x, y, cam_dx, cam_dy, size)

    ink = (232, 232, 232)
    bu, bv = px(*BIN_XY)
    hu = _meters_to_px(BIN_HALF[0], size, WORLD_X)
    hv = _meters_to_px(BIN_HALF[1], size, WORLD_Y)
    _square(img, bu, bv, hu, hv, ink)
    _square(img, bu, bv, hu - 2, hv - 2, BACKGROUND[lighting])

    zu, zv = px(*ZONE_XY)
    _disk(img, zu, zv, _meters_to_px(ZONE_TOL, size, WORLD_X), (232, 232, 232))
    _disk(img, zu, zv, _meters_to_px(ZONE_TOL, size, WORLD_X) - 2, BACKGROUND[lighting])

    for body in bodies:
        if body.role == "obstacle":
            color = NOMINAL_RGB["obstacle"]
            u, v = px(body.x, body.y)
            rad = _meters_to_px(body.sx, size, WORLD_X)
            _disk(img, u, v, rad, color)
            continue
        base = NOMINAL_RGB[body.color]
        color = apply_lighting(base, lighting, protect=False)
        u, v = px(body.x, body.y)
        if body.kind in {"cube", "drawer"}:
            hu = _meters_to_px(body.sx, size, WORLD_X)
            hv = _meters_to_px(body.sy, size, WORLD_Y)
            _square(img, u, v, hu, hv, color)
        else:
            rad = _meters_to_px(body.radius, size, WORLD_X)
            _disk(img, u, v, rad, color)

    fid_color = apply_lighting(NOMINAL_RGB["magenta"], lighting)
    fid_r = _meters_to_px(FIDUCIAL_RADIUS, size, WORLD_X)
    for fx, fy in FIDUCIALS:
        u, v = px(fx, fy)
        _disk(img, u, v, fid_r, fid_color)

    eu, ev = px(ee[0], ee[1])
    ee_r = _meters_to_px(0.018, size, WORLD_X)
    _disk(img, eu, ev, ee_r + 1.0, (250, 248, 242))
    _disk(img, eu, ev, ee_r, (24, 24, 28))
    if ee[3] > 0.5:
        _disk(img, eu, ev, ee_r * 0.45, (250, 248, 242))

    if lighting == "glare":
        # A wash in the near corner that does not recolor objects.
        cy, cx = int(size * 0.82), int(size * 0.78)
        yy, xx = np.ogrid[0:size, 0:size]
        falloff = np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * (size * 0.16) ** 2)))
        bg = np.array(BACKGROUND["glare"], dtype=np.int16)
        unchanged = np.all(img == bg, axis=2)
        wash = (img.astype(np.int16) + (falloff[..., None] * 28)).clip(0, 255).astype(np.uint8)
        img[unchanged] = wash[unchanged]
    return img
