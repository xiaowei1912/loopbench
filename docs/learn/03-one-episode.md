# 03 一条 episode

把 `tabletop_smoke` 里名义工况的 `pick_place` 想成一次抓取。仿真里没有微秒级中断。评测器在一个普通的 for 循环里调用你的「控制律」。

## 时间顺序

`evaluate` 在 `packages/evalkit/loopbench_evalkit/runner.py`。

1. 按策略的 `needs_privileged` 创建环境。`oracle` 为真，`vision_v1` 为假。
2. 基准展开成若干 `EpisodeSpec`：任务、因素、种子。
3. `env.reset(seed=..., options={"task", "factors"})`，得到观测和 `info`。
4. `policy.reset()`。策略自己的相位清掉，例如「正在接近」。
5. 循环，最多到仿真自己的步数上限：
   - 策略不需要真值时，`public_info` 删掉 `privileged`。
   - `action = policy.select_action(observation, info)`。
   - `env.step(action)`，得到新的观测、奖励、是否结束、是否截断、新的 `info`。
6. 结束时读 `info["metrics"]`，收成 `EpisodeTrace`，`classify` 给出失败模式。
7. 环境 `close()`。

这和「上电初始化、然后在主循环里读传感器、写执行器、直到完成或看门狗咬」是同一件事。`terminated` 是做完了。`truncated` 是步数用尽，任务还没完成。

## 观测里有什么

对齐 LeRobot 里常见的键，这样以后换一个预训练策略时键不用重起一套。

| 键 | 含义 | 固件类比 |
| --- | --- | --- |
| `observation.image` | uint8，高 × 宽 × 3，参考仿真默认 160×160 | 相机 DMA 缓冲 |
| `observation.state` | 末端 xy、高度、夹爪 | 关节编码器或末端位姿 |
| `task` | 这句任务的语言，例如把红块放进箱子 | 工单文本 |

动作至少 4 个数：x 增量、y 增量、z、夹爪开合。参考仿真和 MuJoCo 吃这 4 维。大模型常常一次吐出未来很多步、每一行更宽。那种截断只发生在接到这两张桌面的适配器上，实验协议本身不把动作砍成 4 维。

## info 里有什么

仿真必须公布策略和渲染都要用、但又不该写死在策略仓库里的量：

- `fixtures`：箱子、区域、抽屉、地标的位置
- `materials`：物体在没打光时的颜色
- `assets`：尺寸
- `camera_model`：像素和桌面坐标怎么换算
- `control`：工作空间和碰撞半径
- `metrics`：这一步的 trace 字段

`privileged` 只有调试口打开时才在。里面是物体真值、相机偏移、当前抓着谁。

策略可以读 `fixtures` 和 `materials`。这相当于读公开的机械图纸。读 `privileged` 相当于读仿真器内存里的答案。

## 参考桌面上这一抓在做什么

名义 `pick_place` 的布局在 `packages/sim-reference/loopbench_sim_reference/constants.py`：

- 红块大约在 `(0.34, 0.42)`
- 箱子在 `(0.76, 0.42)`，半宽 0.09 米
- 末端从 `(0.50, 0.14, 0.18)` 出发
- 工作空间 x 从 0.08 到 0.92，y 从 0.08 到 0.74，z 从 0.02 到 0.22

`oracle` 用真值走到红块上方，下降，闭合夹爪，抬起，移到箱子，松开。`vision_v1` 在图像里找红色像素，换成桌面坐标，交给同一个控制器。名义光照下两种都能放进箱子。

参考仿真是准静态的：它不积分牛顿定律。夹爪到了门限内就认为抓住。这是软件在环的简化模型，用来把评测闭环跑通。带接触的版本在 MuJoCo 那一章。

## 建议的阅读顺序

只读这些，别通读整个仓库：

1. `packages/spec/loopbench_spec/schema.py` 里的 `Factors`、`Suite`、`EpisodeTrace`。
2. `packages/evalkit/loopbench_evalkit/runner.py` 的 `evaluate` 和 `_run`。
3. `packages/sim-reference/loopbench_sim_reference/env.py` 的 `reset` 和 `step` 签名。
4. `packages/policies/loopbench_policies/vision.py` 的 `select_action`。先看它不读 `privileged`，再看它怎么从图像找颜色。

## 做完再往下

在 `runner.py` 里指出三行：创建环境的地方、调用 `select_action` 的地方、调用 `classify` 的地方。然后读 04，看失败是怎么被命名的。
