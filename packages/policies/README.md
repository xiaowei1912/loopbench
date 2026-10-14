# loopbench-policies

策略仓库。只依赖 `loopbench-spec`。

`select_action(observation, info)` 对齐 LeRobot 的 `PreTrainedPolicy.select_action`。
OpenVLA、ACT、GR00T、π0 不在这里重写；用 `SelectActionAdapter` 包住已经实现该方法的对象即可。
