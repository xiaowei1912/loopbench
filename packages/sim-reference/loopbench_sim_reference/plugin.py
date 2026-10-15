"""Entry point for the reference simulator repository."""

from __future__ import annotations

from loopbench_sim_reference.env import TabletopEnv, register_gym


class ReferenceBackend:
    name = "reference"

    def probe(self) -> dict:
        return {
            "name": self.name,
            "available": True,
            "kind": "simulator",
            "support": "runnable",
            "detail": "准静态桌面，纯 NumPy，不需要 GPU。CI 和产品默认走这里。",
            "gym_id": register_gym(),
            "upstream": "Gymnasium Env",
            "upstream_url": "https://gymnasium.farama.org/api/env/",
        }

    def accepts(self, definition) -> None:
        scene = getattr(definition, "scene", None)
        embodiment = getattr(definition, "embodiment", None)
        if (scene, embodiment) != ("tabletop", "planar_gripper"):
            raise ValueError(
                f"Reference simulator compiles tabletop × planar_gripper, not {scene} × {embodiment}."
            )

    def make(self, *, expose_privileged: bool = False, render_size: int = 160) -> TabletopEnv:
        return TabletopEnv(expose_privileged=expose_privileged, render_size=render_size)
