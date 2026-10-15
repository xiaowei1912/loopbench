# 10 两个仿真

读过 03 再读这一章。目标是分清「软件在环的简化桌面」和「带接触的 MuJoCo 桌面」，并知道 Gymnasium 这个契约为什么到处出现。

## Gymnasium 是环境的调用约定

[Gymnasium](https://gymnasium.farama.org/api/env/) 规定两个方法：

- `reset(*, seed, options) -> (obs, info)`
- `step(action) -> (obs, reward, terminated, truncated, info)`

Isaac Lab、ManiSkill、本仓库的两张桌面都按这个形状被 `gym.make` 创建。评测器多认一层：`options` 里有 `task` 和 `factors`，观测里有 `observation.image` 和 `observation.state`。

参考桌面的 gym id 是 `Loopbench/Tabletop-v0`。MuJoCo 桌面是 `Loopbench/MuJoCo-Tabletop-v0`。id 在 `register_gym()` 里登记。重复登记会被忽略。

## 参考桌面：准静态

代码在 `packages/sim-reference`。它不调用物理引擎。每一步把末端按动作挪一截，用几何判断抓取、碰撞和成功。

这样做的原因和你在 PC 上跑控制算法、被控对象用差分方程代替真电路一样：要快、要确定、要在 CI 里复现。同一种子得到同一张图。

抓取门限在 `constants.py`：

- 平面距离：低摩擦 0.024 米，名义 0.034 米，高摩擦 0.038 米
- 高度门限 `GRASP_Z = 0.035` 米
- 相机平移 `(0.06, -0.045)` 米，大于名义抓取门限，所以没标定时视觉会抓空

低摩擦的失败不是夹不住，是搬的时候滑。步长超过 0.022 米开始累计，累计超过 0.05 米则掉落，并把物体沿 x 再挪 0.08 米。后一步是为了避免「滑进箱子也算成功」。

光照：`dim` 是亮度乘 0.62，`glare` 往白色洗。没有黑色描边，避免暗光下把描边当成物体。

柱子的颜色是 `(72, 80, 90)`。视觉阈值是 40。这些数只属于这个仿真。

## MuJoCo：接触和关节

代码在 `packages/sim-mujoco`。步进调用 `mj_step`。头顶相机用 `mujoco.Renderer`。导入前要把 `MUJOCO_GL` 设成 `osmesa`，并且系统里有 `libosmesa6`。库没装时不要设这个环境变量，否则 `import mujoco` 会在 GL 函数上失败。

夹爪是三轴滑动关节加位置伺服，不是 mocap。mocap 会穿过物体，接触力推不动被抓的东西。父级滑动刚体要有惯性，质量低于 MuJoCo 的下限会在加载时直接报错。

抓取时夹爪几何的 `contype` 和 `conaffinity` 都要是 0。MuJoCo 在任一侧匹配时都会碰撞，只清一边仍会把方块推开，抓取落空。推动时两位置 1，让夹爪真正碰上冰球。

空闲刚体不能叠放在同一个坐标。叠在一起会爆出大量接触，把桌上的方块挤走。它们被停在彼此分开的位置。

伺服是软的。测试不能假设一个 0.04 米的指令在一步之内完成，要循环到测到的末端进入误差带。

CI 断言的是 `pick_place` 成功、不暴露 `privileged`、相机平移会改变像素。推动、叠放、抽屉在环境里有实现，没有全部写进断言。

`accepts()` 只接受场景 `tabletop`、本体 `planar_gripper`。厨房或 Franka 会在开跑前被拒绝。

## 和 Isaac 的距离

Isaac Lab 用 USD 场景和 GPU 物理，环境同样登记成 Gymnasium id，例如 `Isaac-Lift-Cube-Franka-v0`。本仓库的适配器在 `packages/bridges/loopbench_bridges/simulators.py` 的 `open_isaac`。调用 `gym.make` 之前要先 import `isaaclab` 和 `isaaclab_tasks`。

Franka 的官方任务里没有和本仓库 `push`、`sort` 对齐的 id。适配器会拒绝这两项，而不是随便映射到一个抬方块任务。

第一遍读 Isaac 时，只读他们的「注册一个 Gym 环境」教程：<https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/register_rl_env_gym.html>。先不要读渲染和传感器的全部页面。

## 读代码的顺序

1. `packages/sim-reference/loopbench_sim_reference/constants.py` 前 40 行。
2. 同目录 `env.py` 的 `reset`、`step`、`observe`。
3. `packages/sim-mujoco/loopbench_sim_mujoco/plugin.py` 的 `probe` 和 `accepts`。
4. 同目录 `env.py` 里夹爪碰撞位和抓取跟随。遇到 MJCF 字符串可以先跳过，知道它在描述刚体即可。

## 这一章不要求你做的事

不要求安装 Isaac Sim，不要求写 MJCF，不要求把参考桌面改成刚体仿真。两张桌面已经够把评测闭环和接触各看一遍。
