"""JSON codec for observations. Images travel as raw uint8 bytes, not nested lists."""

from __future__ import annotations

import base64
from typing import Any

import numpy as np


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__image__") is True:
            return value
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        if array.dtype == np.uint8 and array.ndim == 3:
            return {
                "__image__": True,
                "shape": list(array.shape),
                "b64": base64.b64encode(array.tobytes()).decode("ascii"),
            }
        return array.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def from_jsonable(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__image__") is True:
        raw = base64.b64decode(value["b64"])
        return np.frombuffer(raw, dtype=np.uint8).reshape(value["shape"]).copy()
    if isinstance(value, dict):
        return {key: from_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [from_jsonable(item) for item in value]
    return value
