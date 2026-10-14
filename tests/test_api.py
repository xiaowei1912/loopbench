"""API smoke tests. The loop case uses the third-party suite so it stays small."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from loopbench_api.app import app


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


def test_uninstalled_simulator_is_rejected_before_a_job_starts():
    client = TestClient(app)
    response = client.post(
        "/api/jobs",
        json={"kind": "eval", "suite": "isaac_franka", "policy": "oracle", "simulator": "isaac-lab"},
    )
    assert response.status_code == 409
    assert "Isaac" in response.json()["detail"]


def test_catalog_lists_the_example_suite():
    client = TestClient(app)
    response = client.get("/api/catalog")
    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["suites"]}
    assert "tabletop_smoke" in names
    assert any(item["name"] == "reference" and item["available"] for item in payload["simulators"])
    assert any(item["id"] == "isaac-lab" and item["available"] is False for item in payload["adapters"])


def test_eval_job_on_the_plugin_suite():
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={"kind": "eval", "suite": "tabletop_smoke", "policy": "oracle", "episodes_per_cell": 1, "seed": 0},
    )
    assert created.status_code == 200
    job = _wait(client, created.json()["id"])
    assert job["status"] == "succeeded", job
    run = client.get(f"/api/runs/{job['run_id']}")
    assert run.status_code == 200
    assert run.json()["summary"]["success_rate"] == 1


def test_loop_job_persists_distinct_runs():
    client = TestClient(app)
    created = client.post(
        "/api/jobs",
        json={"kind": "loop", "suite": "tabletop_smoke", "policy": "oracle", "episodes_per_cell": 1, "seed": 0},
    )
    assert created.status_code == 200
    job = _wait(client, created.json()["id"])
    assert job["status"] == "succeeded", job
    loop = client.get(f"/api/loops/{job['loop_id']}")
    assert loop.status_code == 200
    payload = loop.json()
    assert payload["before_id"] != payload["after_id"]
    assert payload["before_id"] not in {"before", "after"}
    assert client.get(f"/api/runs/{payload['before_id']}").status_code == 200
    assert client.get(f"/api/runs/{payload['after_id']}").status_code == 200
    listed = client.get("/api/loops").json()["loops"]
    assert any(item["id"] == payload["id"] for item in listed)
