"""Run a named experiment.

An experiment is the Arena shape: shared rollout settings plus a list of runs.
Each run is one installed suite, or one scene × embodiment × task cell.
The runner does not import a simulator or a policy. The caller opens both.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from loopbench_evalkit.runner import evaluate, summarize
from loopbench_spec.composition import PROTOCOL, Experiment, RunSpec
from loopbench_spec.registry import suite as load_suite

PolicyOpener = Callable[[RunSpec], Any]
SimulatorOpener = Callable[[str], Any]


def load_experiment(path: str | Path) -> Experiment:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Experiment.model_validate(raw)


def run_experiment(
    experiment: Experiment,
    *,
    open_simulator: SimulatorOpener,
    open_policy: PolicyOpener,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for run in experiment.runs:
        resolved = experiment.resolved(run)
        policy = None
        try:
            if run.suite:
                bench = load_suite(run.suite)
            else:
                if run.environment is None:
                    raise ValueError(f"Run {run.name!r} has no suite and no environment.")
                bench = run.environment.to_suite()
            backend = open_simulator(resolved["simulator"])
            accept = getattr(backend, "accepts", None)
            if run.environment is not None and accept is not None:
                accept(run.environment)
            policy = open_policy(run)
            result = evaluate(
                backend,
                policy,
                bench,
                episodes_per_cell=resolved["episodes_per_cell"],
                seed=resolved["seed"],
            )
            rows.append(
                {
                    "name": run.name,
                    "status": "succeeded",
                    "simulator": resolved["simulator"],
                    "policy": run.policy,
                    "endpoint": run.endpoint,
                    "suite": bench.name,
                    "scene": None if run.environment is None else run.environment.scene,
                    "embodiment": None if run.environment is None else run.environment.embodiment,
                    "seed": resolved["seed"],
                    "episodes_per_cell": resolved["episodes_per_cell"],
                    "summary": result["summary"],
                    "error": None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "name": run.name,
                    "status": "failed",
                    "simulator": resolved["simulator"],
                    "policy": run.policy,
                    "endpoint": run.endpoint,
                    "suite": run.suite,
                    "scene": None if run.environment is None else run.environment.scene,
                    "embodiment": None if run.environment is None else run.environment.embodiment,
                    "seed": resolved["seed"],
                    "episodes_per_cell": resolved["episodes_per_cell"],
                    "summary": summarize([]),
                    "error": str(exc),
                }
            )
            if not experiment.shared.continue_on_error:
                break
        finally:
            closer = getattr(policy, "close", None)
            if closer is not None:
                try:
                    closer()
                except Exception:
                    pass
    episodes_n = sum(row["summary"]["n"] for row in rows)
    episodes_ok = sum(row["summary"]["success"] for row in rows)
    return {
        "name": experiment.name,
        "protocol": PROTOCOL,
        "continue_on_error": experiment.shared.continue_on_error,
        "runs": rows,
        "summary": {
            "runs": len(rows),
            "failed": sum(1 for row in rows if row["status"] == "failed"),
            "n": episodes_n,
            "success": episodes_ok,
            "success_rate": 0.0 if episodes_n == 0 else episodes_ok / episodes_n,
        },
    }
