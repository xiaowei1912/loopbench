# ADR 0002：环境用 Gymnasium，策略用 select_action

## 状态

接受。

## 背景

Isaac Lab、ManiSkill、Gym 系环境都走 `reset` / `step`。LeRobot、以及很多 VLA 微调仓库，策略侧的方法叫 `select_action`。XPolicyLab 用 websocket 把这两边拆开，但方法本身还是「观测进，动作出」。

## 决定

仿真插件返回 Gymnasium 1.0 的 Env。观测字典使用 `observation.image`、`observation.state`、`task`。策略实现 `select_action(observation, info)`。已有 `select_action` 的对象用 `SelectActionAdapter` 包一层，Tensor 在边界上变成 NumPy。

不发明第三套 step API。

## 后果

评测器可以同时跑参考桌面和任何一个 Gym 环境。LeRobot 策略不用改训练代码。代价是参考桌面的 4 维增量动作和 Franka 的关节动作不是同一个向量，那个映射属于具体仿真，不属于 spec。
