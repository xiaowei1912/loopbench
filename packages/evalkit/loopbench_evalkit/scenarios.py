"""Turn a failure report into the next batch of scenes.

Three strategies, all deterministic:

- stress: more seeds on cells that already collapsed
- counterfactual: the same seed with one factor flipped back to nominal
- calibration: a lighting sweep used as labeled data collection, not as a score
"""

from __future__ import annotations

from loopbench_spec.schema import Factors


def generate_scenarios(report: dict, *, limit: int = 24) -> list[dict]:
    scenarios: list[dict] = []
    weak = [row for row in report.get("slices", []) if row.get("delta") is not None and row["delta"] <= -0.25]
    failed = [ep for ep in report.get("episodes", []) if not ep["success"]]

    for row in weak:
        examples = [
            ep
            for ep in failed
            if ep["factors"].get(row["factor"]) == row["level"]
        ][:2]
        for ep in examples:
            scenarios.append(
                {
                    "strategy": "stress",
                    "task": ep["task"],
                    "seed": int(ep["seed"]) + 101,
                    "factors": dict(ep["factors"]),
                    "reason": f"加种子复现 {row['label']}，当前单因素成功率 {row['success_rate']:.0%}",
                }
            )

    for ep in failed[:8]:
        factors = Factors.model_validate(ep["factors"])
        changed = factors.differs_from_nominal()
        if len(changed) != 1:
            continue
        scenarios.append(
            {
                "strategy": "counterfactual",
                "task": ep["task"],
                "seed": int(ep["seed"]),
                "factors": Factors().model_dump(),
                "reason": f"只把 {factors.label()} 拨回名义工况，用来确认这个因素是不是原因",
            }
        )

    for lighting in ("nominal", "dim", "glare"):
        for task in ("pick_place", "stack", "push", "drawer", "sort"):
            scenarios.append(
                {
                    "strategy": "calibration",
                    "task": task,
                    "seed": 1,
                    "factors": Factors(lighting=lighting).model_dump(),
                    "reason": f"数据采集：在 lighting={lighting} 下记录 {task} 的颜色，不计入得分",
                }
            )

    deduped = []
    seen = set()
    for item in scenarios:
        key = (item["strategy"], item["task"], item["seed"], tuple(sorted(item["factors"].items())))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped
