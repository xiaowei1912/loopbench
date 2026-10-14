"""JSON run store. The API process is the only writer."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

_LOCK = threading.Lock()


def data_root() -> Path:
    root = Path(os.environ.get("LOOPBENCH_DATA", "data"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


# Closed-loop comparison labels. They are not durable ids.
_RESERVED_RUN_IDS = {"before", "after"}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def save_run(run: dict) -> dict:
    raw = run.get("id")
    run_id = raw if isinstance(raw, str) and raw and raw not in _RESERVED_RUN_IDS else new_id("run")
    run = {**run, "id": run_id}
    with _LOCK:
        _write(data_root() / "runs" / run_id / "run.json", run)
        summary = {key: value for key, value in run.items() if key != "episodes"}
        summary["episodes"] = len(run.get("episodes", []))
        _write(data_root() / "runs" / run_id / "summary.json", summary)
    return run


def list_runs() -> list[dict]:
    folder = data_root() / "runs"
    if not folder.exists():
        return []
    rows = []
    for path in sorted(folder.glob("*/summary.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    rows.sort(key=lambda item: item.get("id", ""), reverse=True)
    return rows


def get_run(run_id: str) -> dict | None:
    path = data_root() / "runs" / run_id / "run.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_loop(payload: dict) -> dict:
    loop_id = payload.get("id") or new_id("loop")
    payload = {**payload, "id": loop_id}
    with _LOCK:
        _write(data_root() / "loops" / f"{loop_id}.json", payload)
    return payload


def get_loop(loop_id: str) -> dict | None:
    path = data_root() / "loops" / f"{loop_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_loops() -> list[dict]:
    folder = data_root() / "loops"
    if not folder.exists():
        return []
    rows = []
    for path in folder.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        comparison = payload.get("comparison") or {}
        rows.append(
            {
                "id": payload.get("id"),
                "suite": payload.get("suite"),
                "simulator": payload.get("simulator"),
                "before_id": payload.get("before_id"),
                "after_id": payload.get("after_id"),
                "before_success_rate": comparison.get("before_success_rate"),
                "after_success_rate": comparison.get("after_success_rate"),
                "delta": comparison.get("delta"),
                "recovered": comparison.get("recovered"),
                "regressed": comparison.get("regressed"),
            }
        )
    rows.sort(key=lambda item: item.get("id") or "", reverse=True)
    return rows
