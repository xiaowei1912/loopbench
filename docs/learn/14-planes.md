# 14 企业评测平面

读过 06 和 07 再读。这一章讲的是把评测从「一个脚本跑一张桌子」收成可以交给别人的结构。来源和取舍在 [platform.md](../platform.md)，决定在 [ADR 0005](../adr/0005-experiment-planes.md)。

五个平面：

1. **组合。** 一个环境是场景 × 本体 × 任务，外加因素。类比板级支持包：同一份应用，声明它跑在哪块板、哪颗芯片、哪份测试固件上。
2. **仿真 handler。** 每个仿真一个插件，可选 `accepts(definition)`。参考桌面和 MuJoCo 只接受 `tabletop` × `planar_gripper`。对不上就在开跑前失败。
3. **策略进程。** 策略可以留在另一台机器。线上是 TCP，一行一个 JSON：`reset`、`act`、`close`。图像用 uint8 的 base64，不用巨大的嵌套数组。
4. **实验。** 一份 YAML 描述一次评测计划：共享的仿真、种子、每格条数，加上若干具名 run。
5. **协议。** 结果带 `loopbench.experiment/1`。种子、条数、策略、端点、场景、本体写在同一条记录里。以后改字段就升协议号，避免拿两种记录做对比。

## 实验文件

`experiments/tabletop_smoke.yaml`：

```yaml
name: tabletop_smoke
shared:
  simulator: reference
  seed: 0
  episodes_per_cell: 1
  continue_on_error: false
runs:
  - name: oracle
    suite: tabletop_smoke
    policy: oracle
  - name: vision
    suite: tabletop_smoke
    policy: vision_v1
```

每个 run 恰好有一个目标：`suite`，或一个 `environment`（场景、本体、任务三字段）。两个都写或都不写，加载时直接失败。

```bash
loopbench experiment experiments/tabletop_smoke.yaml
```

oracle 两格都成功。vision 的 run 也会正常结束，相机那一格失败写在 summary 里，不会让整个进程崩溃。`continue_on_error: false` 时，某个 run 抛错会停住后面的 run。设为 `true` 时，错误记在那一行，后面的 run 继续。这和 CI 里「一个 job 失败是否取消矩阵里的其它 job」是同一类开关。

HTTP 是 `POST /api/experiments`，正文就是这份结构的 JSON。仿真不可运行时返回 409，线程不会启动。`GET /api/platform` 返回协议号和六条上游来源，界面「架构」页读的就是它。

## 策略拆到另一个进程

```bash
loopbench policy-serve --policy oracle --host 127.0.0.1 --port 43126
```

实验 run 里增加：

```yaml
endpoint: 127.0.0.1:43126
needs_privileged: true
```

评测包自己不打开套接字。CLI 和 API 创建 `RemotePolicy`，把它交给 `run_experiment`。这样 evalkit 不必依赖传输库，传输库也不必依赖仿真。分层和 06 的表一致。

`needs_privileged: true` 只给远程 oracle 这种真值策略。视觉策略写 `false`。

## 故意留在上游的东西

OSMO 多机调度、XPolicyLab 的策略目录和 WebSocket、vla-eval 的基准 Docker 镜像、MetaSim 本体、模型权重。采用的是它们的边界，代码在本仓库重写。许可证和体积都不允许把那些实现拷进来。

## 读代码的顺序

1. `packages/spec/loopbench_spec/composition.py` 里的 `EnvironmentDefinition` 和 `RunSpec`。
2. `packages/evalkit/loopbench_evalkit/experiment.py` 的 `run_experiment`。
3. `packages/transport/loopbench_transport/wire.py` 的 `serve` 和 `RemotePolicy`。
4. `packages/api/loopbench_api/app.py` 里 `GET /api/platform` 和 `POST /api/experiments`。

读完用自己的话讲一次：谁决定「这张桌子能不能编译厨房」，谁负责把真值送过 TCP，协议号写在结果的哪个字段。
