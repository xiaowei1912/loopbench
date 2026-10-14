"""Bridge for policies that already implement LeRobot's select_action.

OpenVLA, ACT, GR00T and π0 are not reimplemented here. If a checkpoint is
loaded by LeRobot (`PreTrainedPolicy.select_action`) or by any object with the
same method, this adapter is the only glue the eval runner needs.
"""

from __future__ import annotations

import numpy as np


class SelectActionAdapter:
    name = "external"
    needs_privileged = False

    def __init__(self, inner, name: str = "external") -> None:
        self.inner = inner
        self.name = name
        self.phase = "external"

    def reset(self) -> None:
        reset = getattr(self.inner, "reset", None)
        if reset is not None:
            reset()

    def select_action(self, observation: dict, info: dict | None = None) -> np.ndarray:
        del info
        action = self.inner.select_action(observation)
        if hasattr(action, "detach"):
            action = action.detach().cpu().numpy()
        array = np.asarray(action, dtype=np.float64).reshape(-1)
        if array.size < 4:
            raise ValueError(f"{self.name} returned {array.size} numbers; the tabletop action is 4-D.")
        return array[:4]
