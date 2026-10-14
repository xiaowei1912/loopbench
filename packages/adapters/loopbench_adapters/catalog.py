"""Upstream systems this workspace does not vendor.

Each record is the real integration seam: the import name, the Gymnasium id
or the function a separate repository would call, and where that code lives.
`make()` is intentionally absent. Installing Isaac Lab or LIBERO is a different
repository; this one only reports whether that import is present.
"""

from __future__ import annotations

import importlib

UPSTREAM = (
    {
        "id": "gymnasium",
        "module": "gymnasium",
        "role": "环境契约",
        "glue": "Env.reset(*, seed, options) -> (obs, info); Env.step(action) -> (obs, reward, terminated, truncated, info)",
        "url": "https://gymnasium.farama.org/api/env/",
    },
    {
        "id": "lerobot",
        "module": "lerobot",
        "role": "策略契约",
        "glue": "PreTrainedPolicy.select_action(batch) -> Tensor。用 loopbench_policies.bridge.SelectActionAdapter 接进来。",
        "url": "https://huggingface.co/docs/lerobot/bring_your_own_policies",
    },
    {
        "id": "isaac-lab",
        "module": "isaaclab",
        "role": "GPU 仿真",
        "glue": "gym.register(id='Isaac-Lift-Cube-Franka-v0', entry_point='isaaclab.envs:ManagerBasedRLEnv', kwargs={'env_cfg_entry_point': ...})",
        "url": "https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/register_rl_env_gym.html",
    },
    {
        "id": "mujoco",
        "module": "mujoco",
        "role": "物理后端",
        "glue": "独立仓库实现 gymnasium.Env，在 loopbench.simulators 注册自己的 Backend.make()。",
        "url": "https://github.com/google-deepmind/mujoco",
    },
    {
        "id": "maniskill",
        "module": "mani_skill",
        "role": "操作基准",
        "glue": "gym.make('PickCube-v1')。任务 id 已经写在 loopbench-spec 的 pick_place / stack 上。",
        "url": "https://github.com/haosulab/ManiSkill",
    },
    {
        "id": "libero",
        "module": "libero",
        "role": "终身学习基准",
        "glue": "benchmark.get_benchmark_dict()[suite].get_task(i) 给出 language 和 bddl_file，再交给 OffScreenRenderEnv。",
        "url": "https://github.com/Lifelong-Robot-Learning/LIBERO",
    },
    {
        "id": "robocasa",
        "module": "robocasa",
        "role": "厨房操作",
        "glue": "RoboCasa 任务通过 robosuite 环境构建。drawer 任务对应这一族。",
        "url": "https://github.com/robocasa/robocasa",
    },
    {
        "id": "robosuite",
        "module": "robosuite",
        "role": "机器人仿真栈",
        "glue": "suite.load_composite_controller_config + robosuite.make。LIBERO 和 RoboCasa 都坐在它上面。",
        "url": "https://github.com/ARISE-Initiative/robosuite",
    },
)


class UpstreamCatalog:
    name = "upstream"

    def probe(self) -> list[dict]:
        rows = []
        for item in UPSTREAM:
            try:
                module = importlib.import_module(item["module"])
                version = getattr(module, "__version__", "installed")
                available = True
                detail = str(version)
            except Exception as exc:  # import error or optional dependency noise
                available = False
                detail = exc.__class__.__name__
            rows.append({**item, "available": available, "detail": detail})
        return rows
