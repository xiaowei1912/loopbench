"""Closed loop. Plugins come from the registry, not from imports of their repos."""

from __future__ import annotations

from loopbench_evalkit.analysis import analyze
from loopbench_evalkit.runner import evaluate, summarize
from loopbench_evalkit.scenarios import generate_scenarios
from loopbench_spec.registry import policy as policy_plugin
from loopbench_spec.registry import simulator, suite


def run_closed_loop(
    suite_name: str = "tabletop_probe",
    *,
    simulator_name: str = "reference",
    policy_name: str = "vision_v1",
    episodes_per_cell: int = 1,
    seed: int = 0,
    capture_frames: bool = False,
    on_progress=None,
) -> dict:
    bench = suite(suite_name)
    backend = simulator(simulator_name)
    plugin = policy_plugin(policy_name)
    before_policy = plugin.make()

    def phase(name: str, fraction: float, message: str) -> None:
        if on_progress:
            on_progress(name, fraction, message)

    phase("evaluate", 0.05, f"评测 {policy_name}")
    before = evaluate(
        backend,
        before_policy,
        bench,
        episodes_per_cell=episodes_per_cell,
        seed=seed,
        capture_frames=capture_frames,
        on_progress=(lambda i, n, msg: phase("evaluate", 0.05 + 0.35 * (i / max(n, 1)), msg)),
    )
    before["id"] = "before"
    report = analyze(before)
    scenarios = generate_scenarios(report)
    phase("improve", 0.5, "根据失败切片改进策略")
    improved, notes = plugin.improve(before_policy, report, backend.make)
    phase("re_evaluate", 0.55, "用同一套基准回评")
    after = evaluate(
        backend,
        improved,
        bench,
        episodes_per_cell=episodes_per_cell,
        seed=seed,
        capture_frames=capture_frames,
        on_progress=(lambda i, n, msg: phase("re_evaluate", 0.55 + 0.4 * (i / max(n, 1)), msg)),
    )
    after["id"] = "after"
    phase("done", 1.0, "闭环完成")
    return {
        "suite": bench.name,
        "simulator": simulator_name,
        "before": before,
        "after": after,
        "analysis": report,
        "scenarios": scenarios,
        "improve": notes,
        "comparison": compare_runs(before, after),
    }


def compare_runs(before: dict, after: dict) -> dict:
    def index(run: dict) -> dict:
        return {(ep["task"], tuple(sorted(ep["factors"].items())), ep["seed"]): ep for ep in run["episodes"]}

    left, right = index(before), index(after)
    recovered = regressed = 0
    pairs = []
    for key in left:
        if key not in right:
            continue
        a, b = left[key], right[key]
        recovered += int((not a["success"]) and b["success"])
        regressed += int(a["success"] and not b["success"])
        pairs.append(
            {
                "task": a["task"],
                "task_label": a["task_label"],
                "factors": a["factors"],
                "factor_label": a["factor_label"],
                "seed": a["seed"],
                "before": a["success"],
                "after": b["success"],
                "before_failure": a["failure"],
                "after_failure": b["failure"],
            }
        )
    labels: list[str] = []
    for episode in before["episodes"]:
        if episode["factor_label"] not in labels:
            labels.append(episode["factor_label"])
    slices = []
    for label in labels:
        b_eps = [ep for ep in before["episodes"] if ep["factor_label"] == label]
        a_eps = [ep for ep in after["episodes"] if ep["factor_label"] == label]
        if not b_eps or not a_eps:
            continue
        b_rate = sum(ep["success"] for ep in b_eps) / len(b_eps)
        a_rate = sum(ep["success"] for ep in a_eps) / len(a_eps)
        slices.append({"label": label, "before": b_rate, "after": a_rate, "delta": a_rate - b_rate, "n": len(b_eps)})
    b_sum, a_sum = summarize(before["episodes"]), summarize(after["episodes"])
    return {
        "before_success_rate": b_sum["success_rate"],
        "after_success_rate": a_sum["success_rate"],
        "delta": a_sum["success_rate"] - b_sum["success_rate"],
        "recovered": recovered,
        "regressed": regressed,
        "pairs": pairs,
        "slices": slices,
    }
