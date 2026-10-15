"""Enterprise seams: composition, experiment YAML, and a policy process."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from loopbench_api.app import app
from loopbench_evalkit.experiment import load_experiment, run_experiment
from loopbench_policies.oracle import OraclePolicy
from loopbench_sim_reference.plugin import ReferenceBackend
from loopbench_spec.composition import PROTOCOL, EnvironmentDefinition, Experiment, Rollout, RunSpec
from loopbench_spec.registry import policies, simulator
from loopbench_transport.codec import from_jsonable, to_jsonable
from loopbench_transport.wire import RemotePolicy, serve

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("LOOPBENCH_DATA", str(tmp_path))


def _wait(client: TestClient, job_id: str, timeout: float = 90) -> dict:
    deadline = time.monotonic() + timeout
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.05)
    return job


def _open_policy(run: RunSpec):
    if run.endpoint:
        return RemotePolicy(run.endpoint, name=run.policy, needs_privileged=bool(run.needs_privileged))
    return policies()[run.policy].make()


def test_reference_rejects_a_scene_it_cannot_compile():
    definition = EnvironmentDefinition(
        name="kitchen",
        scene="kitchen",
        embodiment="franka",
        task="drawer",
    )
    with pytest.raises(ValueError, match="tabletop"):
        ReferenceBackend().accepts(definition)


def test_image_codec_roundtrip():
    image = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
    payload = to_jsonable({"observation.image": image, "n": np.int64(3)})
    assert payload["observation.image"]["__image__"] is True
    restored = from_jsonable(payload)
    assert restored["observation.image"].dtype == np.uint8
    assert np.array_equal(restored["observation.image"], image)
    assert restored["n"] == 3


def test_shipped_experiment_runs_both_policies():
    experiment = load_experiment(ROOT / "experiments" / "tabletop_smoke.yaml")
    assert experiment.name == "tabletop_smoke"
    result = run_experiment(experiment, open_simulator=simulator, open_policy=_open_policy)
    assert result["protocol"] == PROTOCOL
    assert result["summary"]["failed"] == 0
    assert result["summary"]["n"] == 4
    by_name = {row["name"]: row for row in result["runs"]}
    assert by_name["oracle"]["summary"]["success_rate"] == 1
    assert by_name["vision"]["status"] == "succeeded"


def test_remote_oracle_solves_one_composed_cell():
    ready = threading.Event()
    stop = threading.Event()
    bound: list[int] = []
    thread = threading.Thread(
        target=serve,
        args=(OraclePolicy(), "127.0.0.1", 0, stop),
        kwargs={"ready": ready, "bound": bound},
        daemon=True,
    )
    thread.start()
    assert ready.wait(2)
    definition = EnvironmentDefinition(
        name="nominal-pick",
        scene="tabletop",
        embodiment="planar_gripper",
        task="pick_place",
    )
    experiment = Experiment(
        name="remote-oracle",
        shared=Rollout(simulator="reference", seed=0, episodes_per_cell=1),
        runs=(
            RunSpec(
                name="oracle-tcp",
                policy="oracle",
                environment=definition,
                endpoint=f"127.0.0.1:{bound[0]}",
                needs_privileged=True,
            ),
        ),
    )
    try:
        result = run_experiment(experiment, open_simulator=simulator, open_policy=_open_policy)
    finally:
        stop.set()
        thread.join(timeout=2)
    assert result["summary"]["failed"] == 0
    assert result["runs"][0]["summary"]["success_rate"] == 1
    assert result["runs"][0]["scene"] == "tabletop"
    assert result["runs"][0]["endpoint"]


def test_bad_composition_fails_the_run_and_can_continue():
    bad = EnvironmentDefinition(name="nope", scene="kitchen", embodiment="franka", task="pick_place")
    good = EnvironmentDefinition(
        name="ok",
        scene="tabletop",
        embodiment="planar_gripper",
        task="pick_place",
    )
    experiment = Experiment(
        name="continue",
        shared=Rollout(continue_on_error=True, episodes_per_cell=1, seed=0),
        runs=(
            RunSpec(name="rejected", policy="oracle", environment=bad),
            RunSpec(name="accepted", policy="oracle", environment=good),
        ),
    )
    result = run_experiment(experiment, open_simulator=simulator, open_policy=_open_policy)
    assert result["summary"]["failed"] == 1
    assert result["summary"]["runs"] == 2
    assert result["runs"][0]["status"] == "failed"
    assert "tabletop" in result["runs"][0]["error"]
    assert result["runs"][1]["summary"]["success_rate"] == 1


def test_platform_catalog_and_experiment_job():
    client = TestClient(app)
    platform = client.get("/api/platform")
    assert platform.status_code == 200
    body = platform.json()
    assert body["protocol"] == "loopbench.experiment/1"
    ids = {item["id"] for item in body["sources"]}
    assert ids == {
        "isaaclab-arena",
        "roboverse",
        "xpolicylab",
        "vla-evaluation-harness",
        "lerobot",
        "praxis-eval",
    }

    rejected = client.post(
        "/api/experiments",
        json={
            "name": "gpu",
            "shared": {"simulator": "isaac-lab"},
            "runs": [{"name": "a", "policy": "oracle", "suite": "isaac_franka"}],
        },
    )
    assert rejected.status_code == 409

    invalid = client.post(
        "/api/experiments",
        json={
            "name": "both",
            "runs": [
                {
                    "name": "a",
                    "policy": "oracle",
                    "suite": "tabletop_smoke",
                    "environment": {
                        "name": "cell",
                        "scene": "tabletop",
                        "embodiment": "planar_gripper",
                        "task": "pick_place",
                    },
                }
            ],
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/experiments",
        json={
            "name": "cell",
            "shared": {"simulator": "reference", "seed": 0, "episodes_per_cell": 1},
            "runs": [
                {
                    "name": "oracle",
                    "policy": "oracle",
                    "environment": {
                        "name": "nominal-pick",
                        "scene": "tabletop",
                        "embodiment": "planar_gripper",
                        "task": "pick_place",
                    },
                }
            ],
        },
    )
    assert created.status_code == 200
    job = _wait(client, created.json()["id"])
    assert job["status"] == "succeeded", job
    assert job["experiment"]["protocol"] == "loopbench.experiment/1"
    assert job["experiment"]["summary"]["success_rate"] == 1
