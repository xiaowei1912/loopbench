# loopbench-spec

仓库边界：评测闭环的契约。不含仿真器，不含策略。

其它仓库只依赖这个包，通过 entry point 注册自己：

- `loopbench.simulators`
- `loopbench.policies`
- `loopbench.suites`

环境步进对齐 Gymnasium 的 `reset` / `step`。策略动作对齐 LeRobot 的 `select_action`。
