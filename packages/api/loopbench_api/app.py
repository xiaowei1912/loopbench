"""HTTP surface. Imports the harness and the registry, never a simulator module."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loopbench_api import store
from loopbench_evalkit.analysis import analyze
from loopbench_evalkit.loop import run_closed_loop
from loopbench_evalkit.runner import evaluate
from loopbench_evalkit.scenarios import generate_scenarios
from loopbench_spec.registry import adapters, policies, simulator, simulators, suite, suites, tasks

app = FastAPI(title="Loopbench", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_JOBS: dict[str, dict[str, Any]] = {}
_JOB_LOCK = threading.Lock()


class JobRequest(BaseModel):
    kind: str = Field(pattern="^(eval|loop)$")
    suite: str = "tabletop_probe"
    policy: str = "vision_v1"
    simulator: str = "reference"
    episodes_per_cell: int = 1
    seed: int = 0
    capture_frames: bool = False


def _job(job_id: str, **fields: Any) -> None:
    with _JOB_LOCK:
        current = _JOBS.get(job_id, {"id": job_id})
        current.update(fields)
        _JOBS[job_id] = current


def _run_job(job_id: str, request: JobRequest) -> None:
    try:
        _job(job_id, status="running", progress=0.02, message="开始")

        def on_progress(phase: str, fraction: float, message: str) -> None:
            _job(job_id, status="running", progress=fraction, message=f"{phase}: {message}")

        if request.kind == "eval":
            backend = simulator(request.simulator)
            plugin = policies()[request.policy]
            run = evaluate(
                backend,
                plugin.make(),
                suite(request.suite),
                episodes_per_cell=request.episodes_per_cell,
                seed=request.seed,
                capture_frames=request.capture_frames,
                on_progress=lambda index, total, message: _job(
                    job_id,
                    status="running",
                    progress=index / max(total, 1),
                    message=message,
                ),
            )
            report = analyze(run)
            run["analysis"] = {key: value for key, value in report.items() if key != "episodes"}
            run["scenarios"] = generate_scenarios(report)
            saved = store.save_run(run)
            _job(job_id, status="succeeded", progress=1, message="完成", run_id=saved["id"])
            return
        result = run_closed_loop(
            request.suite,
            simulator_name=request.simulator,
            policy_name=request.policy,
            episodes_per_cell=request.episodes_per_cell,
            seed=request.seed,
            capture_frames=request.capture_frames,
            on_progress=on_progress,
        )
        before_payload = dict(result["before"])
        before_payload["analysis"] = {key: value for key, value in result["analysis"].items() if key != "episodes"}
        before_payload["scenarios"] = result["scenarios"]
        before = store.save_run(before_payload)
        after = store.save_run(dict(result["after"]))
        result["before_id"] = before["id"]
        result["after_id"] = after["id"]
        result["policy"] = before.get("policy")
        result["seed"] = before.get("seed")
        result["episodes_per_cell"] = before.get("episodes_per_cell")
        # The loop document keeps the comparison and the analysis, not a second copy of every frame.
        result["before"] = {"id": before["id"], "summary": before["summary"]}
        result["after"] = {"id": after["id"], "summary": after["summary"]}
        saved = store.save_loop(result)
        _job(job_id, status="succeeded", progress=1, message="闭环完成", loop_id=saved["id"], run_id=after["id"])
    except Exception as exc:  # surface the message to the product, keep the server up
        _job(job_id, status="failed", message=str(exc), progress=1)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "loopbench"}


@app.get("/api/catalog")
def catalog() -> dict:
    def dump_suite(item) -> dict:
        data = item.model_dump()
        data["cells"] = [{**cell, "label": suite_cell.label()} for cell, suite_cell in zip(data["cells"], item.cells, strict=False)]
        return data

    adapter_rows: list[dict] = []
    for plugin in adapters().values():
        adapter_rows.extend(plugin.probe())
    return {
        "simulators": [item.probe() for item in simulators().values()],
        "policies": [item.probe() for item in policies().values()],
        "suites": [dump_suite(item) for item in suites().values()],
        "tasks": [task.model_dump() for task in tasks().values()],
        "adapters": adapter_rows,
    }


@app.post("/api/jobs")
def create_job(request: JobRequest) -> dict:
    if request.simulator not in simulators():
        raise HTTPException(404, f"unknown simulator {request.simulator}")
    if request.policy not in policies():
        raise HTTPException(404, f"unknown policy {request.policy}")
    if request.suite not in suites():
        raise HTTPException(404, f"unknown suite {request.suite}")
    job_id = store.new_id("job")
    _job(job_id, status="queued", progress=0, message="排队", kind=request.kind)
    threading.Thread(target=_run_job, args=(job_id, request), daemon=True).start()
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@app.get("/api/runs")
def list_runs() -> dict:
    return {"runs": store.list_runs()}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run


@app.get("/api/loops")
def list_loops() -> dict:
    return {"loops": store.list_loops()}


@app.get("/api/loops/{loop_id}")
def get_loop(loop_id: str) -> dict:
    payload = store.get_loop(loop_id)
    if payload is None:
        raise HTTPException(404, "loop not found")
    return payload
