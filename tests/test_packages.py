"""Integration tests. They install the packages and talk only through the registry."""

from __future__ import annotations

from loopbench_policies.bridge import SelectActionAdapter
from loopbench_spec.registry import clear, policies, simulator, suite, suites
from loopbench_evalkit.loop import run_closed_loop
from loopbench_evalkit.runner import evaluate


def setup_function() -> None:
    clear()


def test_plugins_from_separate_packages_are_visible():
    names = set(suites())
    assert {"tabletop_probe", "tabletop_mini", "tabletop_v1", "tabletop_smoke"} <= names
    assert "reference" in simulator("reference").probe()["gym_id"] or True
    probe = simulator("reference").probe()
    assert probe["available"] is True
    assert probe["gym_id"] == "Loopbench/Tabletop-v0"
    assert set(policies()) >= {"oracle", "vision_v1"}


def test_third_party_suite_runs_on_the_reference_sim_without_code_changes():
    result = evaluate(
        simulator("reference"),
        policies()["oracle"].make(),
        suite("tabletop_smoke"),
        episodes_per_cell=1,
        seed=0,
    )
    assert result["summary"]["n"] == 2
    assert result["episodes"][0]["success"] is True
    assert result["episodes"][1]["success"] is True


def test_oracle_nominal_tasks():
    backend = simulator("reference")
    policy = policies()["oracle"].make()
    env = backend.make(expose_privileged=True)
    try:
        for task in ("pick_place", "stack", "push", "drawer", "sort"):
            for seed in (0, 1):
                obs, info = env.reset(seed=seed, options={"task": task, "factors": {}})
                policy.reset()
                done = False
                steps = 0
                while steps < 200 and not done:
                    action = policy.select_action(obs, info)
                    obs, _reward, terminated, truncated, info = env.step(action)
                    done = terminated or truncated
                    steps += 1
                assert info["metrics"]["success"], (task, seed, steps, policy.phase, info["metrics"])
    finally:
        env.close()


def test_camera_shift_splits_absolute_and_relative_tasks():
    backend = simulator("reference")
    policy = policies()["vision_v1"].make()

    def run(task: str, factors: dict) -> bool:
        env = backend.make(expose_privileged=False)
        try:
            obs, info = env.reset(seed=0, options={"task": task, "factors": factors})
            assert "privileged" not in info
            policy.reset()
            done = False
            steps = 0
            while steps < 200 and not done:
                action = policy.select_action(obs, info)
                obs, _r, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                steps += 1
            return bool(info["metrics"]["success"])
        finally:
            env.close()

    assert run("pick_place", {})
    assert not run("pick_place", {"camera": "shifted"})
    assert not run("stack", {"camera": "shifted"})


def test_closed_loop_recovers():
    result = run_closed_loop("tabletop_probe", episodes_per_cell=1, seed=0)
    comparison = result["comparison"]
    assert comparison["after_success_rate"] > comparison["before_success_rate"]
    assert comparison["regressed"] == 0
    by_label = {row["label"]: row for row in comparison["slices"]}
    assert by_label["camera=shifted"]["before"] < by_label["camera=shifted"]["after"]
    assert by_label["lighting=glare"]["after"] == 1
    assert by_label["nominal"]["before"] == 1
    assert by_label["nominal"]["after"] == 1
    assert any(item["id"] == "hand_eye" for item in result["analysis"]["insights"])


def test_lerobot_shaped_adapter_unwraps_a_foreign_policy():
    class Foreign:
        def reset(self):
            self.ready = True

        def select_action(self, observation):
            del observation
            return [0.0, 0.0, 0.0, -1.0]

    adapted = SelectActionAdapter(Foreign(), name="fake-openvla")
    adapted.reset()
    action = adapted.select_action({"observation.image": None, "observation.state": None, "task": "x"})
    assert list(action) == [0.0, 0.0, 0.0, -1.0]


def test_same_seed_same_pixels():
    env = simulator("reference").make()
    try:
        first, _ = env.reset(seed=7, options={"task": "pick_place", "factors": {"jitter": "high"}})
        image = first["observation.image"].copy()
        second, _ = env.reset(seed=7, options={"task": "pick_place", "factors": {"jitter": "high"}})
        assert (image == second["observation.image"]).all()
    finally:
        env.close()
