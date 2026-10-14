# ADR 0001：参考仿真，而不是把 Isaac 打进来

## 状态

接受。

## 背景

职位要求能跑 Isaac Lab、MuJoCo、RoboTwin、LIBERO。这些栈要 GPU、专有资产和各自的 Python 环境。一个 demo 仓库如果 vendoring 它们，CI 会变成镜像构建，评测逻辑也会和某一个仿真缠在一起。

## 决定

仓库里唯一可执行的仿真是准静态桌面，纯 NumPy，Gymnasium 接口，同一种子像素确定。Isaac、MuJoCo、ManiSkill、LIBERO、RoboCasa 只出现在适配器目录和文档里，写出真实的 import 和注册方式。

因素的物理含义属于仿真仓库。suite 只写 `camera=shifted` 这种名字。

## 后果

CI 不需要 GPU，闭环可以在一分钟内复现。代价是参考桌面没有接触求解器意义上的物理，打滑和碰撞是显式规则。接上 MuJoCo 或 Isaac 时，这些规则要由那个后端重做，trace 的字段保持不变。
