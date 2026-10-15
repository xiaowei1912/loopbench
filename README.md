# Loopbench

物理智能的评测闭环。一次运行走完：

模型 → 仿真 → 基准 → 评测 → 结果

以及下一圈：

评测 → 读失败 → 生成场景和数据 → 改进策略 → 用同一套基准再评

参考桌面和 MuJoCo 桌面在 CI 里运行，不需要 GPU。Isaac Lab、ManiSkill、LIBERO、RoboCasa、RoboTwin，以及 ACT、OpenVLA、GR00T、π0、π0.5，由 `packages/bridges` 调用官方构造函数。库和权重不打进这个仓库。对照表在 `docs/coverage.md`。

界面是中文，代码和 API 用英文。

## 仓库怎么拆

每个目录都是一个可以单独 `pip install -e` 的包，靠 setuptools entry point 发现彼此，而不是互相 import。

| 包 | 可以依赖 | 不可以依赖 |
| --- | --- | --- |
| `packages/spec` | pydantic | 仿真、策略、评测 |
| `packages/sim-reference` | spec、Gymnasium、NumPy | 策略、评测 |
| `packages/sim-mujoco` | spec、Gymnasium、MuJoCo | 策略、评测、bridges |
| `packages/bridges` | spec、NumPy | 仿真、策略、评测 |
| `packages/policies` | spec、NumPy | 仿真、评测 |
| `packages/transport` | NumPy | 仿真、策略、评测 |
| `packages/evalkit` | spec、NumPy、Pillow、PyYAML | 仿真、策略、transport |
| `packages/adapters` | spec | 仿真、策略、评测 |
| `packages/example-suite` | spec | 其它一切 |
| `packages/api` | spec、evalkit（安装时带上插件，代码里不 import 仿真） | `loopbench_sim_reference`、`loopbench_policies` |
| `packages/cli` | api、evalkit、spec | 仿真内部 |

`packages/example-suite` 是第三方基准的模板。它注册 `tabletop_smoke`，评测器不用改一行。

边界由 `scripts/check_boundaries.py` 扫 import 行。

## 本地跑

需要 Python 3.11+ 和 Node 22。

```bash
make install
export PATH="$HOME/.local/bin:$PATH"
loopbench catalog
loopbench loop --suite tabletop_probe --policy vision_v1 --seed 0
loopbench experiment experiments/tabletop_smoke.yaml
```

策略也可以单独起一个进程，评测进程只连 `host:port`：

```bash
loopbench policy-serve --policy oracle --port 43126
```

开界面：

```bash
loopbench serve --port 43124
cd apps/web && npm install && npm run dev
```

- 界面：<http://127.0.0.1:43123>
- API：<http://127.0.0.1:43124/api/health>

`make install` 会按依赖顺序安装 `packages/` 下的包。MuJoCo 渲染需要本机有 `libosmesa6`（CI 会装）。这个环境没有 `python3-venv` 时，Makefile 使用 `--break-system-packages`。CI 里改用虚拟环境：`make install PIP=.venv/bin/pip BREAK=`。

Docker：

```bash
docker compose up --build
```

同样是 43123 和 43124。闭环数据放在 volume `loopbench-data`。

## 参考探针的一次实测

`tabletop_probe`，`vision_v1`，`reference`，seed 0，每格 1 条。改进前 25%（3/12），改进后 92%（11/12），找回 8 条，退步 0。

| 单因素 | 改进前 | 改进后 |
| --- | --- | --- |
| nominal | 100% | 100% |
| lighting=glare | 0% | 100% |
| lighting=dim | 0% | 100% |
| camera=shifted | 0% | 100% |
| clutter=2 | 0% | 50% |
| friction=low | 50% | 100% |

`clutter=2` 的 50% 要拆开看：抓取放置绕开了柱子，叠放仍然碰撞。绿色积木挡住黄块之后，侧向路点还会擦到柱子。这是还没补上的几何缺口，文档和界面都按这个结果写。

## 文档

- [计划](docs/plan.md)
- [需求](docs/requirements.md)
- [架构](docs/architecture.md)
- [企业评测平面](docs/platform.md)
- [仓库地图](docs/repositories.md)
- [平台覆盖](docs/coverage.md)
- [怎么扩展](docs/extending.md)
- [学习路径](docs/learning.md)
- [运行手册](docs/runbook.md)
- [ADR](docs/adr/0001-reference-simulator.md)

## 测试

```bash
make test
```

覆盖插件发现、第三方套件、oracle 名义工况、相机平移下视觉策略抓空、闭环不退步、MuJoCo 抓取放置，以及用假模块检查 Isaac、ManiSkill、LIBERO、RoboCasa、RoboTwin 和四类 VLA 的调用形状。API 会拒绝还没安装的仿真。企业平面另有一组测试：实验 YAML、组合拒绝、TCP 上的 oracle，以及 `POST /api/experiments`。
