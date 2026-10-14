"""Simulators that call the upstream constructor and stop there.

None of these libraries are installed with Loopbench. ``probe()`` reports
whether the import works. ``make()`` calls the official entry point. Tests
pass a fake module into the opener so the call shape is checked without GPU.
"""

from __future__ import annotations

import importlib
from typing import Any

from loopbench_bridges.session import BridgeEnv, pack_observation, unpack_step

# Official gym ids. Push and sort are not Franka tasks in Isaac Lab's list.
ISAAC_TASKS = {
    "pick_place": "Isaac-Lift-Cube-Franka-v0",
    "stack": "Isaac-Stack-Cube-Franka-v0",
    "drawer": "Isaac-Open-Drawer-Franka-v0",
}

MANISKILL_TASKS = {
    "pick_place": "PickCube-v1",
    "stack": "StackCube-v1",
    "push": "PushCube-v1",
    "drawer": "OpenCabinetDrawer-v1",
}

# Index into benchmark.get_benchmark_dict()[name]().get_task(i).
LIBERO_INDEX = {"pick_place": 0, "stack": 1, "push": 2, "drawer": 3, "sort": 4}
LIBERO_BENCHMARKS = ("libero_spatial", "libero_object", "libero_goal", "libero_10", "libero_90")

# Current gym ids, then the short names still accepted by create_env in the 0.2 docs.
ROBOCASA_TASKS = {
    "pick_place": ("robocasa/PickPlaceCounterToCabinet", "PnPCounterToCab"),
    "drawer": ("robocasa/OpenDrawer", "OpenDrawer"),
    "sort": ("robocasa/PickPlaceCounterToSink", "PnPCounterToSink"),
}

# File stem under RoboTwin's envs/ package. The class name matches the file.
ROBOTWIN_TASKS = {
    "pick_place": "place_a2b_left",
    "stack": "stack_blocks_two",
    "drawer": "open_microwave",
    "sort": "pick_diverse_bottles",
}


def _installed(module: str) -> tuple[bool, str]:
    try:
        loaded = importlib.import_module(module)
    except Exception as exc:
        return False, exc.__class__.__name__
    return True, str(getattr(loaded, "__version__", "installed"))


def _missing(task: str, table: dict, label: str) -> None:
    raise KeyError(
        f"{label} has no task for {task!r}. Mapped tasks: {sorted(table)}. "
        "The suite vocabulary is wider than this upstream."
    )


class ExternalDriver:
    """reset/step/close over a native env that already looks like Gym."""

    def __init__(self, opener) -> None:
        self._opener = opener
        self.env = None
        self.task = "pick_place"
        self.upstream_id = ""
        self.language = ""
        self.steps = 0
        self.render_size = 160
        self.factors: dict = {}

    def reset(self, *, task: str, factors: dict, seed: int, render_size: int) -> dict:
        self.close()
        self.task = task
        self.factors = factors
        self.render_size = render_size
        self.steps = 0
        self.env, self.upstream_id, self.language = self._opener(task, seed, render_size, factors)
        reset = self.env.reset
        try:
            result = reset(seed=seed)
        except TypeError:
            result = reset()
        obs = result[0] if isinstance(result, tuple) else result
        if isinstance(obs, dict) and (obs.get("task") or obs.get("language")):
            self.language = str(obs.get("task") or obs.get("language"))
        elif not self.language:
            self.language = self.upstream_id
        return self._pack(obs, 0.0, False, False, False)

    def step(self, action) -> dict:
        if self.env is None:
            raise RuntimeError("reset the upstream env before step.")
        obs, reward, terminated, truncated, info = unpack_step(self.env.step(action))
        self.steps += 1
        success = bool(info.get("success", False)) if isinstance(info, dict) else False
        if success:
            terminated = True
        return self._pack(obs, reward, terminated, truncated, success)

    def close(self) -> None:
        if self.env is None:
            return
        closer = getattr(self.env, "close", None) or getattr(self.env, "close_env", None)
        if closer is not None:
            closer()
        self.env = None

    def _pack(self, obs, reward, terminated, truncated, success) -> dict:
        events = [f"upstream:{self.upstream_id}"]
        if self.factors:
            events.append("factors_recorded_not_applied")
        return pack_observation(
            obs,
            task=self.task,
            upstream_id=self.upstream_id,
            language=self.language,
            steps=self.steps,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            success=success,
            events=events,
            render_size=self.render_size,
        )


def open_isaac(task: str, seed: int, render_size: int, factors: dict, *, gym_module=None) -> tuple[Any, str, str]:
    del seed, render_size, factors
    if task not in ISAAC_TASKS:
        _missing(task, ISAAC_TASKS, "Isaac Lab")
    if gym_module is None:
        import isaaclab  # noqa: F401  the import registers the kit runtime
        import isaaclab_tasks  # noqa: F401  gym.register of the Franka tasks
        import gymnasium as gym

        gym_module = gym
    gym_id = ISAAC_TASKS[task]
    env = gym_module.make(gym_id)
    return env, gym_id, gym_id


def open_maniskill(task: str, seed: int, render_size: int, factors: dict, *, gym_module=None) -> tuple[Any, str, str]:
    del seed, factors
    if task not in MANISKILL_TASKS:
        _missing(task, MANISKILL_TASKS, "ManiSkill")
    if gym_module is None:
        import gymnasium as gym
        import mani_skill.envs  # noqa: F401

        gym_module = gym
    gym_id = MANISKILL_TASKS[task]
    env = gym_module.make(gym_id, obs_mode="rgb", control_mode="pd_ee_delta_pose", render_mode="rgb_array")
    return env, gym_id, gym_id


def open_libero(
    task: str,
    seed: int,
    render_size: int,
    factors: dict,
    *,
    benchmark: str = "libero_object",
    benchmark_module=None,
    env_cls=None,
    path_fn=None,
) -> tuple[Any, str, str]:
    del factors
    if benchmark not in LIBERO_BENCHMARKS:
        raise KeyError(f"Unknown LIBERO benchmark {benchmark!r}. Known: {LIBERO_BENCHMARKS}")
    if task not in LIBERO_INDEX:
        _missing(task, LIBERO_INDEX, "LIBERO")
    if benchmark_module is None:
        from libero.libero import benchmark as benchmark_module
        from libero.libero import get_libero_path

        path_fn = get_libero_path
    if env_cls is None:
        from libero.libero.envs import OffScreenRenderEnv

        env_cls = OffScreenRenderEnv
    suite = benchmark_module.get_benchmark_dict()[benchmark]()
    count = suite.n_tasks() if callable(getattr(suite, "n_tasks", None)) else int(suite.n_tasks)
    index = LIBERO_INDEX[task] % count
    spec = suite.get_task(index)
    import os

    bddl = os.path.join(path_fn("bddl_files"), spec.problem_folder, spec.bddl_file)
    env = env_cls(bddl_file_name=bddl, camera_heights=render_size, camera_widths=render_size)
    seed_fn = getattr(env, "seed", None)
    if callable(seed_fn):
        seed_fn(seed)
    language = getattr(spec, "language", None) or f"{benchmark} task {index}"
    return env, f"{benchmark}:{index}", str(language)


def open_robocasa(task: str, seed: int, render_size: int, factors: dict, *, factory=None) -> tuple[Any, str, str]:
    del render_size, factors
    if task not in ROBOCASA_TASKS:
        _missing(task, ROBOCASA_TASKS, "RoboCasa")
    gym_id, short = ROBOCASA_TASKS[task]
    if factory is not None:
        env = factory(gym_id=gym_id, short=short, seed=seed)
        return env, gym_id, gym_id
    import robocasa  # noqa: F401
    import gymnasium as gym

    try:
        env = gym.make(gym_id, split="pretrain", seed=seed)
        return env, gym_id, gym_id
    except Exception:
        from robocasa.utils.env_utils import create_env

        env = create_env(env_name=short, render_onscreen=False, seed=seed)
        return env, short, short


class _RoboTwinSession:
    """Adapt Base_task.setup_demo / take_action / check_success to reset/step."""

    def __init__(self, task_env) -> None:
        self.task_env = task_env

    def reset(self, *, seed: int | None = None, options=None):
        del options
        self.task_env.setup_demo(now_ep_num=0, seed=0 if seed is None else int(seed), is_test=True)
        obs = self.task_env.get_obs()
        language = ""
        if hasattr(self.task_env, "get_instruction"):
            language = self.task_env.get_instruction() or ""
        if isinstance(obs, dict):
            obs = {**obs, "task": language}
        return obs, {}

    def step(self, action):
        self.task_env.take_action(action, action_type="qpos")
        obs = self.task_env.get_obs()
        success = bool(self.task_env.check_success())
        return obs, float(success), success, False, {"success": success}

    def close(self) -> None:
        self.task_env.close_env()


def open_robotwin(task: str, seed: int, render_size: int, factors: dict, *, module_loader=None) -> tuple[Any, str, str]:
    del seed, render_size, factors
    if task not in ROBOTWIN_TASKS:
        _missing(task, ROBOTWIN_TASKS, "RoboTwin")
    name = ROBOTWIN_TASKS[task]
    if module_loader is None:
        module = importlib.import_module(f"envs.{name}")
    else:
        module = module_loader(name)
    task_cls = getattr(module, name)
    return _RoboTwinSession(task_cls()), name, name


class _Backend:
    name = ""
    module = ""
    detail = ""
    upstream = ""
    upstream_url = ""
    opener = None

    def probe(self) -> dict:
        ok, detail = _installed(self.module)
        return {
            "name": self.name,
            "available": ok,
            "kind": "simulator",
            "support": "adapter",
            "detail": self.detail if not ok else f"{self.detail} 运行时 {detail}。",
            "upstream": self.upstream,
            "upstream_url": self.upstream_url,
        }

    def make(self, *, expose_privileged: bool = False, render_size: int = 160) -> BridgeEnv:
        ok, detail = _installed(self.module)
        if not ok:
            raise RuntimeError(f"{self.upstream} is not installed ({detail}). {self.detail}")
        return BridgeEnv(ExternalDriver(self.opener), expose_privileged=expose_privileged, render_size=render_size)


class IsaacLabBackend(_Backend):
    name = "isaac-lab"
    module = "isaaclab"
    upstream = "Isaac Lab"
    upstream_url = "https://github.com/isaac-sim/IsaacLab"
    opener = staticmethod(open_isaac)
    detail = (
        "gym.make 官方 id：Isaac-Lift-Cube-Franka-v0、Isaac-Stack-Cube-Franka-v0、Isaac-Open-Drawer-Franka-v0。"
        "push 和 sort 不在 Franka 任务表里。需要 Isaac Sim 的 GPU 镜像，CI 不跑这一项。"
    )


class ManiSkillBackend(_Backend):
    name = "maniskill"
    module = "mani_skill"
    upstream = "ManiSkill"
    upstream_url = "https://github.com/haosulab/ManiSkill"
    opener = staticmethod(open_maniskill)
    detail = "gym.make('PickCube-v1' | 'StackCube-v1' | 'PushCube-v1' | 'OpenCabinetDrawer-v1', obs_mode='rgb', control_mode='pd_ee_delta_pose')。"


class LiberoBackend(_Backend):
    name = "libero"
    module = "libero"
    upstream = "LIBERO"
    upstream_url = "https://github.com/Lifelong-Robot-Learning/LIBERO"
    opener = staticmethod(open_libero)
    detail = (
        "benchmark.get_benchmark_dict() 取 libero_object，再用 OffScreenRenderEnv(bddl_file_name=...)。"
        "任务 id 映射到 suite 里的第 0 到 4 个 task。默认基准是 libero_object。"
    )


class RoboCasaBackend(_Backend):
    name = "robocasa"
    module = "robocasa"
    upstream = "RoboCasa"
    upstream_url = "https://github.com/robocasa/robocasa"
    opener = staticmethod(open_robocasa)
    detail = "优先 gym.make('robocasa/PickPlaceCounterToCabinet' 等)。失败时回退到 create_env(env_name='PnPCounterToCab')。"


class RoboTwinBackend(_Backend):
    name = "robotwin"
    module = "envs"
    upstream = "RoboTwin"
    upstream_url = "https://github.com/RoboTwin-Platform/RoboTwin"
    opener = staticmethod(open_robotwin)
    detail = (
        "import envs.<task>，调用 setup_demo、get_obs、take_action(action, action_type='qpos')、check_success。"
        "映射：place_a2b_left、stack_blocks_two、open_microwave、pick_diverse_bottles。"
    )

    def probe(self) -> dict:
        # `envs` is a generic top-level name. Only treat it as RoboTwin when the
        # package exposes the task loader used by their eval client.
        ok = False
        detail = "ModuleNotFoundError"
        try:
            module = importlib.import_module("envs")
            ok = hasattr(module, "base_task") or hasattr(module, "beat_block_hammer") or hasattr(module, "place_a2b_left")
            detail = "installed" if ok else "module 'envs' is not RoboTwin"
        except Exception as exc:
            detail = exc.__class__.__name__
        row = super().probe()
        row["available"] = ok
        if not ok:
            row["detail"] = self.detail
        else:
            row["detail"] = f"{self.detail} 运行时 {detail}。"
        return row
