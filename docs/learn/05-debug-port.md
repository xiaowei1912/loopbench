# 05 真值是调试口

固件可以在调试版本里把内部状态打到串口。量产版本把这路关掉。如果量产版本只有插着 JTAG 才能工作，这个测试没有测到你要交付的东西。

机器人仿真里的「真值」就是物体在仿真器内存里的位姿。策略如果能读到它，评测测的是控制器，不是感知。

## 两道闸

1. 环境只有 `expose_privileged=True` 时才把 `privileged` 放进 `info`。
2. 评测器只有在 `policy.needs_privileged` 为真时才这样创建环境，并用 `public_info` 再滤一次。

两道都在，是为了防止策略对象忘了声明、调用方却把真值传进去。决定写在 [ADR 0003](../adr/0003-privileged.md)。

`oracle.needs_privileged` 是 `True`。它没有图像也能抓，因为它直接读 `privileged["bodies"]`。它是上界：基准和控制器是通的。它不是要部署的策略。

`vision_v1.needs_privileged` 是 `False`。`select_action` 只看图像、图纸（`fixtures`、`materials`、`camera_model`）和自己的控制器状态。

## 标定是单独一道工序

暗光和眩光下，固定的 RGB 阈值对不上被打光之后的颜色。手眼平移下，像素换算出来的桌面坐标是偏的。这两件事都修得了，但修的时候需要知道「这个像素本来是红块」。

`improve_vision` 在 `packages/policies/loopbench_policies/improve.py`：

1. `make_env(expose_privileged=True)`，自己打开调试口。
2. 对三种光照、每个任务采一张图，用真值知道该采样哪个像素。
3. 把采到的颜色冻进原型库。
4. 打开地标标定、柱子避障、慢速搬运。
5. 返回一个新策略，名字是 `vision_v2`。

下一轮 `evaluate` 看到的是 `vision_v2`，它的 `needs_privileged` 仍是 `False`。调试口再次关掉。原型是标定结果，像产线把颜色传感器的增益写进 EEPROM 之后，线上不再接标定治具。

地标是桌面上两个品红圆点，像素位置在 `FIDUCIALS`。每个 episode 都能从它们解出相机平移。这不是重训一个网络。

## 远程策略也要声明

策略可以跑在另一个进程里，动过 TCP 传过来。评测进程看不到那个进程的源码，所以 `needs_privileged` 要写在实验 run 上。远程 oracle 必须写 `true`。写了 `false` 的话，真值不会过线，oracle 会直接报错。视觉策略保持 `false`。

传输格式在 `packages/transport`。入门阶段知道这件事即可，14 再看协议。

## 做完再往下

用一句话区分三次看真值的机会：

- 评测 `oracle`：整段 episode 都开着调试口。
- 评测 `vision_v1` 或 `vision_v2`：不开。
- `improve()`：只在采集原型时开，返回之后关掉。
