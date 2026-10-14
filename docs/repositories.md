# 仓库地图

这些包现在放在同一个 git 仓库里，是为了让 demo 能一次克隆就跑。依赖方向按多仓库来设计：每个包有自己的 `pyproject.toml`、README 和 entry point。拆出去的时候，把目录变成一个仓库，版本号照旧互相依赖即可。

## 谁拥有什么

| 目录 | 分发名 | 主人应该关心的事 |
| --- | --- | --- |
| `packages/spec` | loopbench-spec | 任务 id、因素名字、Suite、trace、注册表。改字段等于改所有仓库的合同。 |
| `packages/sim-reference` | loopbench-sim-reference | 桌面几何、颜色、相机平移、打滑。不拥有“什么叫一个好基准”。 |
| `packages/sim-mujoco` | loopbench-sim-mujoco | MuJoCo 桌面。接触和重力在这里，任务 id 仍用 spec。 |
| `packages/bridges` | loopbench-bridges | Isaac Lab、ManiSkill、LIBERO、RoboCasa、RoboTwin、ACT、OpenVLA、GR00T、π0、π0.5 的官方调用。不内置那些库。 |
| `packages/policies` | loopbench-policies | oracle、视觉伺服、标定、`SelectActionAdapter`。不拥有环境米制。 |
| `packages/evalkit` | loopbench-evalkit | 跑 episode、归因、场景生成、闭环。不拥有任何一个仿真的实现。 |
| `packages/adapters` | loopbench-adapters | 上游探测和接入说明。没有 `make()`。 |
| `packages/example-suite` | loopbench-example-suite | 给新基准仓库抄的最小例子。 |
| `packages/api` | loopbench-api | HTTP 和 JSON 落盘。 |
| `packages/cli` | loopbench-cli | `loopbench` 命令。 |
| `apps/web` | loopbench-web | 评测台。只说话给 HTTP。 |

## 安装顺序

spec → sim-reference、sim-mujoco、policies、adapters、bridges、example-suite → evalkit → api → cli。

`make install` 按这个顺序做 editable install。包之间用分发名依赖（`loopbench-spec>=0.1`），不写死磁盘路径，这样拆成多个 git 仓库之后 pyproject 不用改。

## 注册表

`loopbench_spec.registry` 读 `importlib.metadata.entry_points`：

- `loopbench.simulators`
- `loopbench.policies`
- `loopbench.suites`
- `loopbench.adapters`

类会被实例化，Suite 实例原样返回。`clear()` 给测试用。`public_info()` 丢掉 `privileged`。

这和 Gymnasium 注册环境、Isaac Lab 调用 `gymnasium.register` 是同一种发现方式：产品不维护一张写死的清单。

## 边界检查

`scripts/check_boundaries.py` 只看含 `import` 或 `import_module` 的代码行。注释和文档字符串里提到另一个包的名字是允许的，适配器的 glue 说明就靠这个。CLI 不在表里，它本来就要调用 API。
