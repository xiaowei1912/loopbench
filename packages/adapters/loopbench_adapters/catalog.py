"""Import probe for upstream libraries.

The callable adapters live in loopbench-bridges and loopbench-sim-mujoco.
This catalog only answers "is the third-party module importable?" and records
the function those adapters call.
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
        "glue": "loopbench_sim_mujoco.MujocoTabletop 在本进程里 mj_step。Gym id Loopbench/MuJoCo-Tabletop-v0。",
        "url": "https://github.com/google-deepmind/mujoco",
    },
    {
        "id": "maniskill",
        "module": "mani_skill",
        "role": "操作基准",
        "glue": "gym.make('PickCube-v1', obs_mode='rgb', control_mode='pd_ee_delta_pose')。见 loopbench_bridges.simulators.open_maniskill。",
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
    {
        "id": "robotwin",
        "module": "envs",
        "role": "双臂基准",
        "glue": "importlib.import_module('envs.' + task).setup_demo / take_action / check_success。",
        "url": "https://github.com/RoboTwin-Platform/RoboTwin",
    },
    {
        "id": "act",
        "module": "lerobot",
        "role": "VLA / 策略",
        "glue": "ACTPolicy.from_pretrained(checkpoint).select_action(batch)。环境变量 LOOPBENCH_ACT_CHECKPOINT。",
        "url": "https://github.com/huggingface/lerobot",
    },
    {
        "id": "openvla",
        "module": "transformers",
        "role": "VLA / 策略",
        "glue": "AutoModelForVision2Seq.from_pretrained(checkpoint, trust_remote_code=True).predict_action。LOOPBENCH_OPENVLA_CHECKPOINT。",
        "url": "https://github.com/openvla/openvla",
    },
    {
        "id": "gr00t",
        "module": "gr00t",
        "role": "VLA / 策略",
        "glue": "Gr00tPolicy(embodiment_tag, model_path, device).get_action(observation)。LOOPBENCH_GR00T_CHECKPOINT。",
        "url": "https://github.com/NVIDIA/Isaac-GR00T",
    },
    {
        "id": "openpi",
        "module": "openpi",
        "role": "VLA / 策略",
        "glue": "policy_config.create_trained_policy(get_config('pi0_droid'|'pi05_droid'), checkpoint).infer(example)['actions']。",
        "url": "https://github.com/Physical-Intelligence/openpi",
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
