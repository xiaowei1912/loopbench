"""Failure taxonomy and one-factor attribution.

Modes are assigned from the episode trace, not from a second model. Attribution
uses the one-factor slice: the cell that changes a single scene factor, compared
with the all-nominal cell. Confounded interaction cells stay out of that delta.
"""

from __future__ import annotations

from loopbench_spec.schema import EpisodeTrace, Factors

FAILURE_LABELS = {
    "grasp_miss": "抓空",
    "wrong_object": "抓错物体",
    "slip": "滑落",
    "collision": "碰撞卡住",
    "placement_error": "放置偏差",
    "push_miss": "推动未入区",
    "timeout": "超时",
}


def classify(trace: EpisodeTrace) -> str | None:
    if trace.success:
        return None
    if trace.slips > 0:
        return "slip"
    if trace.wrong_grasps > 0 and not trace.ever_grasped_target:
        return "wrong_object"
    if trace.collisions >= 8 and not trace.ever_grasped_target:
        return "collision"
    if trace.needs_grasp and not trace.ever_grasped_target:
        return "grasp_miss"
    if trace.needs_grasp and trace.ever_grasped_target:
        return "placement_error"
    if trace.task == "push":
        if trace.collisions >= 8:
            return "collision"
        return "push_miss"
    return "timeout"


def analyze(run: dict) -> dict:
    episodes = run["episodes"]
    baseline = _rate(episodes, lambda ep: Factors.model_validate(ep["factors"]).differs_from_nominal() == {})
    slices = _one_factor_slices(episodes, baseline)
    annotated = []
    for ep in episodes:
        factors = Factors.model_validate(ep["factors"])
        attribution = _attribute(factors, slices)
        annotated.append({**ep, "attribution": attribution})
    failure_counts: dict[str, int] = {}
    for ep in annotated:
        if ep["failure"]:
            failure_counts[ep["failure"]] = failure_counts.get(ep["failure"], 0) + 1
    cross = _task_factor(annotated, "camera", "shifted")
    insights = _insights(slices, cross, failure_counts, len(episodes), baseline)
    recommendations = _recommendations(slices, failure_counts)
    return {
        "baseline_success_rate": baseline["rate"],
        "baseline_n": baseline["n"],
        "slices": slices,
        "failures": [
            {"mode": mode, "label": FAILURE_LABELS.get(mode, mode), "count": count}
            for mode, count in sorted(failure_counts.items(), key=lambda item: -item[1])
        ],
        "task_camera": cross,
        "insights": insights,
        "recommendations": recommendations,
        "episodes": annotated,
    }


def _one_factor_slices(episodes: list[dict], baseline: dict) -> list[dict]:
    levels = {
        "lighting": ["dim", "glare"],
        "camera": ["shifted"],
        "clutter": [1, 2],
        "friction": ["low", "high"],
        "jitter": ["high"],
    }
    rows = []
    for factor, options in levels.items():
        for level in options:
            matched = [ep for ep in episodes if _is_one_factor(ep["factors"], factor, level)]
            if not matched:
                continue
            rate = sum(1 for ep in matched if ep["success"]) / len(matched)
            delta = None if baseline["n"] == 0 else rate - baseline["rate"]
            rows.append(
                {
                    "factor": factor,
                    "level": level,
                    "n": len(matched),
                    "success_rate": rate,
                    "delta": delta,
                    "label": f"{factor}={level}",
                }
            )
    rows.sort(key=lambda row: (row["delta"] is None, row["delta"] if row["delta"] is not None else 0))
    return rows


def _is_one_factor(factors: dict, factor: str, level) -> bool:
    current = Factors.model_validate(factors)
    nominal = Factors().model_dump()
    data = current.model_dump()
    if data[factor] != level:
        return False
    for key, value in nominal.items():
        if key == factor:
            continue
        if data[key] != value:
            return False
    return True


def _attribute(factors: Factors, slices: list[dict]) -> dict | None:
    changed = factors.differs_from_nominal()
    if not changed:
        return None
    ranked = []
    for key, level in changed.items():
        row = next((item for item in slices if item["factor"] == key and item["level"] == level), None)
        delta = row["delta"] if row and row["delta"] is not None else 0.0
        ranked.append((delta, key, level))
    ranked.sort()
    delta, key, level = ranked[0]
    return {"factor": key, "level": level, "delta": delta, "label": f"{key}={level}"}


def _task_factor(episodes: list[dict], factor: str, level) -> list[dict]:
    seen: list[str] = []
    for ep in episodes:
        if ep["task"] not in seen:
            seen.append(ep["task"])
    rows = []
    for task in seen:
        matched = [ep for ep in episodes if ep["task"] == task and _is_one_factor(ep["factors"], factor, level)]
        if not matched:
            continue
        rows.append(
            {
                "task": task,
                "label": matched[0]["task_label"],
                "n": len(matched),
                "success_rate": sum(1 for ep in matched if ep["success"]) / len(matched),
            }
        )
    return rows


def _insights(slices, cross, failure_counts, n, baseline) -> list[dict]:
    del n, cross
    insights = []
    by_label = {row["label"]: row for row in slices}

    def drop(label: str) -> float | None:
        row = by_label.get(label)
        if row is None or row["delta"] is None:
            return None
        return row["delta"]

    camera = drop("camera=shifted")
    if camera is not None and camera <= -0.4:
        insights.append(
            {
                "id": "hand_eye",
                "title": "手眼平移直接写进了物体的世界坐标",
                "body": (
                    f"camera=shifted 的单因素成功率比名义工况低 {abs(camera):.0%}。"
                    "末端的本体感觉在真实桌面坐标系里，视觉却把每个物体都平移了一截，"
                    "偏差大于抓取门限，夹具目标和看着另一块积木的目标都会抓空。"
                    "地标圆点每个 episode 都能把这个平移解出来，不需要重训抓取。"
                ),
            }
        )
    glare = drop("lighting=glare")
    dim = drop("lighting=dim")
    if (glare is not None and glare <= -0.4) or (dim is not None and dim <= -0.4):
        worst = "glare" if (glare or 0) <= (dim or 0) else "dim"
        insights.append(
            {
                "id": "color_constancy",
                "title": "光照变了，颜色原型还停在名义工况",
                "body": (
                    f"lighting={worst} 让物体颜色离开了出厂原型，检测直接丢失。"
                    "闭环要补的不是更大的策略网络，而是在这个光照下采一小组带位姿标签的图像，把原型库补上。"
                ),
            }
        )
    clutter = drop("clutter=2")
    if clutter is None:
        clutter = drop("clutter=1")
    if clutter is not None and clutter <= -0.4:
        insights.append(
            {
                "id": "clearance",
                "title": "杂乱失败是几何的，柱子挡在直线上",
                "body": (
                    "柱子被放在起点和目标的连线上。没有避障技能时末端停在柱子前，碰撞计数一直涨。"
                    "打开 clearance 之后，抓取放置会改走柱子侧面。叠放时绿色积木挡住黄块，侧向路点仍可能擦到第二根柱子，这一格不会一次回到满分。"
                ),
            }
        )
    slips = failure_counts.get("slip", 0)
    friction = drop("friction=low")
    if friction is not None and friction <= -0.3 and slips > 0:
        insights.append(
            {
                "id": "transport",
                "title": "低摩擦下抓得住，搬得快就会掉",
                "body": (
                    f"slip 出现了 {slips} 次，friction=low 的成功率变化是 {friction:+.0%}。"
                    "抓取门限本身够用。失败发生在搬运：步长超过接触能跟上的速度。把搬运步长降下来即可。"
                ),
            }
        )
    jitter = drop("jitter=high")
    if jitter is not None and jitter > -0.2:
        insights.append(
            {
                "id": "jitter_robust",
                "title": "闭环视觉对位姿抖动是稳的",
                "body": (
                    f"jitter=high 的成功率变化是 {jitter:+.0%}。物体每步都被重新看见，"
                    "随机化位姿几乎不伤这个伺服。它会伤的是开环或只在名义分布上模仿的策略。"
                ),
            }
        )
    if not insights and baseline["n"]:
        insights.append(
            {
                "id": "flat",
                "title": "这一轮没有明显的单因素塌陷",
                "body": (
                    f"名义工况成功率 {baseline['rate']:.0%}，各单因素切片没有跌过归因阈值。"
                    "可以加大 episode 数再看交互项。"
                ),
            }
        )
    return insights


def _recommendations(slices: list[dict], failure_counts: dict[str, int]) -> list[dict]:
    recs = []
    weak = {row["label"] for row in slices if row["delta"] is not None and row["delta"] <= -0.25}

    def add(lever: str, title: str, detail: str) -> None:
        recs.append({"lever": lever, "title": title, "detail": detail})

    if any(label.startswith("lighting=") for label in weak):
        add("prototypes", "补光照原型", "用带位姿日志的一小撮标定场景，为 dim / glare 采集颜色原型。评测时不再读取真值。")
    if "camera=shifted" in weak:
        add("landmarks", "打开地标手眼标定", "每个 episode 开始时用地标圆点解出相机平移，修正像素到桌面的映射。")
    if any(label.startswith("clutter=") for label in weak):
        add("clearance", "打开避障", "把深色柱子当作障碍，直线撞上就改走侧向路点。抓取放置会回来；叠放在遮挡下仍可能擦到柱子。")
    if failure_counts.get("slip", 0) > 0 or "friction=low" in weak:
        add("careful_transport", "降低搬运步长", "抓住之后把平面步长限制在接触跟得上的范围内，避免低摩擦滑落。")
    return recs


def _rate(episodes: list[dict], predicate) -> dict:
    matched = [ep for ep in episodes if predicate(ep)]
    if not matched:
        return {"n": 0, "rate": 0.0}
    return {"n": len(matched), "rate": sum(1 for ep in matched if ep["success"]) / len(matched)}
