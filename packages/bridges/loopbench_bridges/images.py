"""Pull an RGB frame out of whatever observation dict an upstream env returned."""

from __future__ import annotations

import numpy as np


def as_numpy(value):
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy") and not isinstance(value, np.ndarray):
        value = value.numpy()
    return np.asarray(value)


def find_image(obs, *, size: int = 160) -> np.ndarray:
    found: list[np.ndarray] = []

    def consider(value) -> None:
        if isinstance(value, dict):
            for item in value.values():
                consider(item)
            return
        if isinstance(value, (list, tuple)) and value and not isinstance(value[0], (int, float)):
            consider(value[0])
            return
        try:
            array = as_numpy(value)
        except (TypeError, ValueError):
            return
        if array.dtype == object or array.size == 0 or array.ndim < 3:
            return
        if array.shape[-1] in (1, 3, 4) and min(array.shape[-3], array.shape[-2]) >= 8:
            found.append(array)
            return
        if array.shape[-3] in (1, 3, 4) and min(array.shape[-2], array.shape[-1]) >= 8:
            found.append(np.moveaxis(array, -3, -1))

    if isinstance(obs, dict):
        consider(obs)
    else:
        consider(obs)
    if not found:
        blank = np.zeros((size, size, 3), dtype=np.uint8)
        return blank
    image = found[0]
    while image.ndim > 3:
        image = image[0]
    if image.shape[-1] == 1:
        image = np.repeat(image, 3, axis=-1)
    if image.shape[-1] == 4:
        image = image[..., :3]
    if image.dtype != np.uint8:
        scale = 255.0 if float(np.nanmax(image)) <= 1.5 else 1.0
        image = np.clip(image * scale, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(image)


def find_state(obs) -> np.ndarray:
    found: list[np.ndarray] = []

    def consider(value) -> None:
        if isinstance(value, dict):
            for item in value.values():
                consider(item)
            return
        try:
            array = as_numpy(value).astype(np.float64, copy=False).reshape(-1)
        except (TypeError, ValueError):
            return
        if array.size >= 1 and array.size <= 64 and np.issubdtype(array.dtype, np.number):
            found.append(array)

    if isinstance(obs, dict):
        # Prefer an explicit state key over the first numeric leaf, which may be a pixel.
        for key in ("observation.state", "state", "qpos", "joint_position"):
            if key in obs:
                consider(obs[key])
                if found:
                    return found[0]
        consider(obs)
    if not found:
        return np.zeros(4, dtype=np.float64)
    return found[0]
