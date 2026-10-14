"""MuJoCo runs here. The other platforms are checked against fake upstream modules."""

from __future__ import annotations

import numpy as np

from loopbench_bridges.policies import ChunkingPolicy, action_rows, infer_act, infer_gr00t, infer_openpi, infer_openvla
from loopbench_bridges.session import BridgeEnv
from loopbench_bridges.simulators import (
    ISAAC_TASKS,
    MANISKILL_TASKS,
    ROBOCASA_TASKS,
    ROBOTWIN_TASKS,
    ExternalDriver,
    IsaacLabBackend,
    open_isaac,
    open_libero,
    open_maniskill,
    open_robocasa,
    open_robotwin,
)
from loopbench_spec.registry import clear, simulator


def setup_function() -> None:
    clear()


class _FakeEnv:
    def __init__(self) -> None:
        self.actions = []
        self.closed = False
        self.seed = None

    def reset(self, *, seed=None, options=None):
        del options
        self.seed = seed
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        image[0, 0, 0] = 9
        return {"rgb": image, "state": np.arange(4, dtype=np.float32)}, {}

    def step(self, action):
        self.actions.append(np.asarray(action))
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        return {"rgb": image, "state": np.zeros(4)}, 1.0, True, False, {"success": True}

    def close(self) -> None:
        self.closed = True


class _FakeGym:
    def __init__(self) -> None:
        self.made = []
        self.env = _FakeEnv()

    def make(self, gym_id, **kwargs):
        self.made.append((gym_id, kwargs))
        return self.env


def _run(opener) -> _FakeGym:
    gym = _FakeGym()
    env = BridgeEnv(ExternalDriver(lambda task, seed, size, factors: opener(task, seed, size, factors, gym_module=gym)), expose_privileged=False, render_size=16)
    obs, info = env.reset(seed=3, options={"task": "pick_place", "factors": {"camera": "shifted"}})
    assert obs["observation.image"].shape == (16, 16, 3)
    assert obs["observation.image"][0, 0, 0] == 9
    assert "privileged" not in info
    assert "factors_recorded_not_applied" in info["metrics"]["events"]
    obs, reward, terminated, truncated, info = env.step(np.ones(7))
    assert terminated and info["metrics"]["success"]
    assert reward == 1
    env.close()
    assert gym.env.closed
    assert gym.env.seed == 3
    return gym


def test_isaac_and_maniskill_call_official_ids():
    isaac = _run(open_isaac)
    assert isaac.made[0][0] == ISAAC_TASKS["pick_place"]
    skill = _run(open_maniskill)
    assert skill.made[0][0] == MANISKILL_TASKS["pick_place"]
    assert skill.made[0][1]["obs_mode"] == "rgb"
    assert skill.made[0][1]["control_mode"] == "pd_ee_delta_pose"
    assert IsaacLabBackend().probe()["available"] is False


def test_libero_builds_offscreen_env_from_the_benchmark_task():
    class Task:
        problem_folder = "libero_object"
        bddl_file = "pick_the_alphabet_soup.bddl"
        language = "pick the alphabet soup"

    class Suite:
        n_tasks = 10

        def get_task(self, index):
            assert index == 0
            return Task()

    class Benchmark:
        def get_benchmark_dict(self):
            return {"libero_object": lambda: Suite()}

    created = {}

    def env_cls(**kwargs):
        created.update(kwargs)
        return _FakeEnv()

    driver = ExternalDriver(
        lambda task, seed, size, factors: open_libero(
            task,
            seed,
            size,
            factors,
            benchmark_module=Benchmark(),
            env_cls=env_cls,
            path_fn=lambda kind: f"/libero/{kind}",
        )
    )
    env = BridgeEnv(driver, expose_privileged=False, render_size=16)
    obs, info = env.reset(seed=1, options={"task": "pick_place", "factors": {}})
    assert created["bddl_file_name"] == "/libero/bddl_files/libero_object/pick_the_alphabet_soup.bddl"
    assert created["camera_heights"] == 16
    assert obs["task"] == "pick the alphabet soup"
    assert info["fixtures"]["upstream_id"] == "libero_object:0"
    env.close()


def test_robocasa_prefers_the_gym_id():
    seen = {}

    def factory(*, gym_id, short, seed):
        seen.update(gym_id=gym_id, short=short, seed=seed)
        return _FakeEnv()

    driver = ExternalDriver(lambda task, seed, size, factors: open_robocasa(task, seed, size, factors, factory=factory))
    env = BridgeEnv(driver, expose_privileged=False, render_size=16)
    env.reset(seed=4, options={"task": "drawer", "factors": {}})
    assert seen["gym_id"] == ROBOCASA_TASKS["drawer"][0]
    assert seen["short"] == "OpenDrawer"
    env.close()


def test_robotwin_uses_setup_demo_and_take_action():
    class Task:
        def __init__(self) -> None:
            self.calls = []

        def setup_demo(self, **kwargs):
            self.calls.append(("setup", kwargs))

        def get_obs(self):
            image = np.zeros((8, 8, 3), dtype=np.uint8)
            return {"head_camera": image}

        def get_instruction(self):
            return "place the object"

        def take_action(self, action, action_type="qpos"):
            self.calls.append(("act", action_type, list(np.asarray(action))))

        def check_success(self):
            return True

        def close_env(self):
            self.calls.append(("close",))

    task = Task()

    def loader(name):
        from types import SimpleNamespace

        assert name == ROBOTWIN_TASKS["stack"]
        return SimpleNamespace(**{name: (lambda: task)})

    driver = ExternalDriver(lambda t, seed, size, factors: open_robotwin(t, seed, size, factors, module_loader=loader))
    env = BridgeEnv(driver, expose_privileged=False, render_size=8)
    obs, _info = env.reset(seed=2, options={"task": "stack", "factors": {}})
    assert obs["task"] == "place the object"
    assert task.calls[0][0] == "setup"
    assert task.calls[0][1]["is_test"] is True
    _obs, _reward, terminated, _truncated, info = env.step(np.zeros(14))
    assert task.calls[1][0] == "act"
    assert task.calls[1][1] == "qpos"
    assert terminated and info["metrics"]["success"]
    env.close()
    assert task.calls[-1] == ("close",)


def test_policy_wrappers_call_the_upstream_method():
    class Act:
        def select_action(self, observation):
            assert "observation.image" in observation
            return np.arange(7)

    class Vla:
        def predict_action(self, image, instruction):
            assert instruction == "put the red cube into the bin"
            return np.ones(7)

    class Gr00t:
        def get_action(self, observation):
            assert observation["language"]["annotation.human.action.task_description"] == [["pick"]]
            return {"joint_positions": np.ones((1, 2, 8))}, {}

    class Pi:
        def infer(self, example):
            assert example["prompt"] == "pick"
            assert example["observation/exterior_image_1_left"].shape[0] == 4
            return {"actions": np.arange(16, dtype=np.float64).reshape(2, 8)}

    obs = {
        "observation.image": np.zeros((4, 4, 3), dtype=np.uint8),
        "observation.state": np.arange(8),
        "task": "put the red cube into the bin",
    }
    act = ChunkingPolicy(Act(), name="act", infer=infer_act)
    assert act.select_action(obs).shape == (7,)
    vla = ChunkingPolicy(Vla(), name="openvla", infer=infer_openvla)
    assert np.allclose(vla.select_action(obs), 1)
    gr00t = ChunkingPolicy(Gr00t(), name="gr00t", infer=infer_gr00t)
    obs["task"] = "pick"
    first = gr00t.select_action(obs)
    second = gr00t.select_action(obs)
    assert first.shape == (8,) and second.shape == (8,)
    pi = ChunkingPolicy(Pi(), name="pi0", infer=infer_openpi)
    assert pi.select_action(obs).shape == (8,)
    assert pi.select_action(obs)[0] == 8
    assert action_rows(np.zeros(4))[0].shape == (4,)


def test_mujoco_pick_place_succeeds_and_hides_privileged():
    backend = simulator("mujoco")
    assert backend.probe()["available"] is True
    assert backend.probe()["gym_id"] == "Loopbench/MuJoCo-Tabletop-v0"
    hidden = backend.make(expose_privileged=False, render_size=32)
    obs, info = hidden.reset(seed=0, options={"task": "pick_place", "factors": {}})
    assert "privileged" not in info
    assert obs["observation.image"].shape == (32, 32, 3)
    hidden.close()

    env = backend.make(expose_privileged=True, render_size=32)
    obs, info = env.reset(seed=0, options={"task": "pick_place", "factors": {}})
    nominal = obs["observation.image"].copy()
    shifted, _ = env.reset(seed=0, options={"task": "pick_place", "factors": {"camera": "shifted"}})
    assert not np.array_equal(nominal, shifted["observation.image"])
    obs, info = env.reset(seed=0, options={"task": "pick_place", "factors": {}})
    target = next(body for body in info["privileged"]["bodies"] if body["role"] == "target")
    dest = np.array([target["x"], target["y"], 0.03])
    info = _servo(env, info, dest, -1)
    for _ in range(3):
        obs, _reward, terminated, _truncated, info = env.step([0, 0, 0, 1])
        if terminated:
            break
    assert info["privileged"]["holding"] == "red"
    info = _servo(env, info, np.array([info["privileged"]["ee"][0], info["privileged"]["ee"][1], 0.16]), 1)
    info = _servo(env, info, np.array([0.76, 0.42, 0.14]), 1)
    for _ in range(6):
        obs, _reward, terminated, _truncated, info = env.step([0, 0, -0.04, -1])
    for _ in range(20):
        obs, _reward, terminated, _truncated, info = env.step([0, 0, 0, -1])
        if terminated:
            break
    assert info["metrics"]["success"] is True
    env.close()


def _servo(env, info, dest, grip, limit=90):
    for _ in range(limit):
        ee = np.asarray(info["privileged"]["ee"][:3], dtype=np.float64)
        if np.linalg.norm(ee - dest) < 0.02:
            return info
        delta = np.clip(dest - ee, -0.045, 0.045)
        _obs, _reward, terminated, _truncated, info = env.step([*delta, grip])
        if terminated:
            return info
    return info
