"""Entry point. MuJoCo is a hard dependency of this package, so probe is available once it imports."""

from __future__ import annotations

from loopbench_sim_mujoco.env import MujocoTabletop, register_gym


class MujocoBackend:
    name = "mujoco"

    def probe(self) -> dict:
        import mujoco

        return {
            "name": self.name,
            "available": True,
            "kind": "simulator",
            "support": "runnable",
            "detail": f"MuJoCo {mujoco.__version__} 桌面。抓取、叠放、推动、抽屉和分拣都在这个进程里步进，CI 会跑一条抓取。",
            "gym_id": register_gym(),
            "upstream": "MuJoCo",
            "upstream_url": "https://github.com/google-deepmind/mujoco",
        }

    def make(self, *, expose_privileged: bool = False, render_size: int = 160) -> MujocoTabletop:
        return MujocoTabletop(expose_privileged=expose_privileged, render_size=render_size)
