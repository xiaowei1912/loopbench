"""Policy entry points. A new repository registers another class in this group."""

from __future__ import annotations

from loopbench_policies.improve import improve_vision
from loopbench_policies.oracle import OraclePolicy
from loopbench_policies.vision import VisionConfig, VisionPolicy


class OraclePlugin:
    name = "oracle"

    def probe(self) -> dict:
        return {
            "name": self.name,
            "available": True,
            "kind": "policy",
            "support": "runnable",
            "needs_privileged": True,
            "detail": "特权上界。评测器只在策略声明 needs_privileged 时交出真值。",
            "upstream": "privileged baseline",
        }

    def make(self, config: dict | None = None):
        del config
        return OraclePolicy()

    def improve(self, policy, report: dict, make_env):
        del policy, report, make_env
        return self.make(), {"notes": ["oracle 不需要改进"], "levers": []}


class VisionPlugin:
    name = "vision_v1"

    def probe(self) -> dict:
        return {
            "name": self.name,
            "available": True,
            "kind": "policy",
            "support": "runnable",
            "needs_privileged": False,
            "detail": "颜色伺服。接口与 LeRobot PreTrainedPolicy.select_action 同名。",
            "upstream": "LeRobot select_action",
            "upstream_url": "https://huggingface.co/docs/lerobot/bring_your_own_policies",
        }

    def make(self, config: dict | None = None) -> VisionPolicy:
        if config is None:
            return VisionPolicy(VisionConfig(name="vision_v1"))
        return VisionPolicy(VisionConfig.from_dict(config))

    def improve(self, policy, report: dict, make_env):
        return improve_vision(policy, report, make_env)
