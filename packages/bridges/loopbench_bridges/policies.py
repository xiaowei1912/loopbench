"""Policy plugins. make() loads the upstream checkpoint; select_action calls the real method.

Weights are never downloaded here. Set the checkpoint env var on a machine
that already has the library and the files.
"""

from __future__ import annotations

import importlib
import os

import numpy as np

from loopbench_bridges.images import as_numpy


def _installed(module: str) -> tuple[bool, str]:
    try:
        loaded = importlib.import_module(module)
    except Exception as exc:
        return False, exc.__class__.__name__
    return True, str(getattr(loaded, "__version__", "installed"))


def action_rows(result) -> list[np.ndarray]:
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        if "actions" in result:
            result = result["actions"]
        else:
            result = next(iter(result.values()))
    if hasattr(result, "detach"):
        result = result.detach()
    if hasattr(result, "cpu"):
        result = result.cpu()
    array = as_numpy(result).astype(np.float64, copy=False)
    if array.ndim == 3:
        array = array[0]
    if array.ndim == 2:
        return [row.reshape(-1) for row in array]
    return [array.reshape(-1)]


class ChunkingPolicy:
    """Holds an action chunk and feeds the runner one row per step."""

    needs_privileged = False

    def __init__(self, inner, *, name: str, infer) -> None:
        self.inner = inner
        self.name = name
        self._infer = infer
        self._queue: list[np.ndarray] = []
        self.phase = name

    def reset(self) -> None:
        self._queue = []
        reset = getattr(self.inner, "reset", None)
        if reset is not None:
            reset()

    def select_action(self, observation: dict, info: dict | None = None) -> np.ndarray:
        del info
        if not self._queue:
            self._queue = action_rows(self._infer(self.inner, observation))
        if not self._queue:
            raise RuntimeError(f"{self.name} returned an empty action.")
        return np.asarray(self._queue.pop(0), dtype=np.float64)


def _openpi_example(observation: dict) -> dict:
    image = np.asarray(observation["observation.image"])
    state = np.asarray(observation.get("observation.state", np.zeros(8)), dtype=np.float64).reshape(-1)
    joints = state[:7] if state.size >= 7 else np.pad(state, (0, 7 - state.size))
    gripper = state[7:8] if state.size >= 8 else np.zeros(1)
    return {
        "observation/exterior_image_1_left": image,
        "observation/wrist_image_left": image,
        "observation/joint_position": joints,
        "observation/gripper_position": gripper,
        "prompt": str(observation.get("task", "")),
    }


def infer_openpi(policy, observation: dict):
    return policy.infer(_openpi_example(observation))


def infer_openvla(model, observation: dict):
    image = observation["observation.image"]
    instruction = str(observation.get("task", ""))
    processor = getattr(model, "loopbench_processor", None)
    if processor is not None:
        prompt = f"In: What action should the robot take to {instruction}?\nOut:"
        inputs = processor(prompt, image)
        return model.predict_action(**inputs, unnorm_key=getattr(model, "loopbench_unnorm_key", "bridge_orig"), do_sample=False)
    return model.predict_action(image, instruction)


def infer_act(policy, observation: dict):
    return policy.select_action(observation)


def infer_gr00t(policy, observation: dict):
    image = np.asarray(observation["observation.image"])
    state = np.asarray(observation.get("observation.state", np.zeros(8)), dtype=np.float32).reshape(-1)
    video = image[None, None]
    joints = state.astype(np.float32)[None, None]
    instruction = str(observation.get("task", ""))
    payload = {
        "video": {"ego_view": video},
        "state": {"joints": joints},
        "language": {"annotation.human.action.task_description": [[instruction]]},
    }
    return policy.get_action(payload)


class _WeightPlugin:
    name = ""
    module = ""
    env_var = ""
    upstream = ""
    upstream_url = ""
    detail = ""

    def probe(self) -> dict:
        ok, imported = _installed(self.module)
        checkpoint = os.environ.get(self.env_var, "").strip()
        available = ok and bool(checkpoint)
        if not ok:
            text = f"{self.detail} 当前没有安装 {self.module}（{imported}）。"
        elif not checkpoint:
            text = f"{self.detail} 库已安装，但没有 {self.env_var}，不会下载权重。"
        else:
            text = f"{self.detail} 将从 {self.env_var} 加载。"
        return {
            "name": self.name,
            "available": available,
            "kind": "policy",
            "support": "adapter",
            "needs_privileged": False,
            "detail": text,
            "upstream": self.upstream,
            "upstream_url": self.upstream_url,
        }

    def make(self, config: dict | None = None):
        config = config or {}
        checkpoint = (config.get("checkpoint") or os.environ.get(self.env_var) or "").strip()
        if not checkpoint:
            raise RuntimeError(f"{self.name} needs a checkpoint in {self.env_var} or make(config={{'checkpoint': ...}}).")
        inner = self.load(checkpoint, config)
        return ChunkingPolicy(inner, name=self.name, infer=self.infer)

    def improve(self, policy, report: dict, make_env):
        del report, make_env
        return policy, {"notes": [f"{self.name} 的权重在上游仓库训练，这一轮不更新参数。"], "levers": []}

    def load(self, checkpoint: str, config: dict):
        raise NotImplementedError

    infer = staticmethod(lambda inner, observation: inner)


class ActPlugin(_WeightPlugin):
    name = "act"
    module = "lerobot"
    env_var = "LOOPBENCH_ACT_CHECKPOINT"
    upstream = "LeRobot ACT"
    upstream_url = "https://github.com/huggingface/lerobot"
    detail = "ACTPolicy.from_pretrained(checkpoint).select_action(batch)。"
    infer = staticmethod(infer_act)

    def load(self, checkpoint: str, config: dict):
        del config
        from lerobot.policies.act.modeling_act import ACTPolicy

        return ACTPolicy.from_pretrained(checkpoint)


class OpenVLAPlugin(_WeightPlugin):
    name = "openvla"
    module = "transformers"
    env_var = "LOOPBENCH_OPENVLA_CHECKPOINT"
    upstream = "OpenVLA"
    upstream_url = "https://github.com/openvla/openvla"
    detail = "AutoModelForVision2Seq.from_pretrained(..., trust_remote_code=True).predict_action。"
    infer = staticmethod(infer_openvla)

    def load(self, checkpoint: str, config: dict):
        from transformers import AutoModelForVision2Seq, AutoProcessor

        processor = AutoProcessor.from_pretrained(checkpoint, trust_remote_code=True)
        model = AutoModelForVision2Seq.from_pretrained(checkpoint, trust_remote_code=True)
        model.loopbench_processor = processor
        model.loopbench_unnorm_key = config.get("unnorm_key", "bridge_orig")
        return model


class Gr00tPlugin(_WeightPlugin):
    name = "gr00t"
    module = "gr00t"
    env_var = "LOOPBENCH_GR00T_CHECKPOINT"
    upstream = "NVIDIA Isaac GR00T"
    upstream_url = "https://github.com/NVIDIA/Isaac-GR00T"
    detail = "Gr00tPolicy(embodiment_tag, model_path, device).get_action(observation)。"
    infer = staticmethod(infer_gr00t)

    def load(self, checkpoint: str, config: dict):
        from gr00t.data.embodiment_tags import EmbodimentTag
        from gr00t.policy.gr00t_policy import Gr00tPolicy

        tag = config.get("embodiment") or os.environ.get("LOOPBENCH_GR00T_EMBODIMENT", "GR1")
        device = config.get("device") or os.environ.get("LOOPBENCH_GR00T_DEVICE", "cuda:0")
        embodiment = EmbodimentTag[tag] if isinstance(tag, str) and tag in getattr(EmbodimentTag, "__members__", {}) else tag
        return Gr00tPolicy(embodiment_tag=embodiment, model_path=checkpoint, device=device)


class _OpenPIPlugin(_WeightPlugin):
    config_name = ""
    infer = staticmethod(infer_openpi)

    def load(self, checkpoint: str, config: dict):
        from openpi.policies import policy_config
        from openpi.training import config as openpi_config

        name = config.get("config") or self.config_name
        cfg = openpi_config.get_config(name)
        return policy_config.create_trained_policy(cfg, checkpoint)


class Pi0Plugin(_OpenPIPlugin):
    name = "pi0"
    module = "openpi"
    env_var = "LOOPBENCH_PI0_CHECKPOINT"
    config_name = "pi0_droid"
    upstream = "openpi π0"
    upstream_url = "https://github.com/Physical-Intelligence/openpi"
    detail = "config pi0_droid，policy.infer(example)['actions']。这不是 π0.5。"


class Pi05Plugin(_OpenPIPlugin):
    name = "pi05"
    module = "openpi"
    env_var = "LOOPBENCH_PI05_CHECKPOINT"
    config_name = "pi05_droid"
    upstream = "openpi π0.5"
    upstream_url = "https://github.com/Physical-Intelligence/openpi"
    detail = "config pi05_droid，同一个 infer 接口，另一套 checkpoint。LIBERO 微调对应 pi05_libero。"
