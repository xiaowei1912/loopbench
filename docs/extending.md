# 扩展

新能力是一个新的安装包，不是给 evalkit 加一个 if。

## 加一个基准

依赖只有 `loopbench-spec`。

```python
from loopbench_spec.schema import Factors, Suite

smoke = Suite(
    name="tabletop_smoke",
    label="Smoke",
    description="只依赖 spec 的示例基准。",
    tasks=("pick_place",),
    cells=(Factors(), Factors(camera="shifted")),
    upstream="example-suite",
)
```

```toml
[project.entry-points."loopbench.suites"]
tabletop_smoke = "loopbench_example_suite:smoke"
```

`tasks` 里的字符串必须是 spec 的任务 id。仿真器没实现这个任务时，在 `reset` 里抛错。不要为了一个仿真去改 suite 的词汇。

`Factors` 只接受名字。不要在 suite 里写 0.06 米或 RGB。

## 加一个仿真

```python
class MujocoBackend:
    name = "mujoco"

    def probe(self) -> dict:
        return {"name": self.name, "available": True, "kind": "simulator", "detail": "MuJoCo tabletop"}

    def make(self, *, expose_privileged: bool = False, render_size: int = 160):
        return YourEnv(expose_privileged=expose_privileged, render_size=render_size)
```

```toml
[project.entry-points."loopbench.simulators"]
mujoco = "my_mujoco.plugin:MujocoBackend"
```

Env 要满足：

- `reset(*, seed, options)`。`options["task"]` 是任务 id，`options["factors"]` 是因素字典。
- `step(action)` 返回五元组。
- 观测含 `observation.image`、`observation.state`、`task`。
- `info` 含 `fixtures`、`materials`、`camera_model`、`control`、`metrics`。
- `expose_privileged=False` 时 `info` 里没有 `privileged`。

`metrics` 的字段和 `EpisodeTrace` 一致，评测器用它分类，不再问仿真要第二种日志。

## 加一个策略

对象需要：

- `name`
- `needs_privileged`：真值策略设为 True
- `select_action(observation, info) -> np.ndarray`，至少 4 维
- 插件上的 `make()` 和 `improve(policy, report, make_env) -> (policy, notes)`

LeRobot、OpenVLA 或任何带 `select_action` 的对象：

```python
from loopbench_policies.bridge import SelectActionAdapter

policy = SelectActionAdapter(pretrained, name="openvla")
```

适配器会把 Tensor 收成 NumPy。它不读取 `privileged`。

`improve` 可以调用 `make_env(expose_privileged=True)` 做标定。返回的新策略在下一轮评测里必须自己能工作，不能再依赖那次特权 env。

## 加一个上游探测

`loopbench.adapters` 的 `probe()` 返回一组 `{id, module, role, glue, url, available, detail}`。不要在这里 import 仿真实现。glue 字符串写上游真实的函数名，方便人去那个仓库接。
