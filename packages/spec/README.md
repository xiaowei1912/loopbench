# loopbench-spec

仓库边界：评测闭环的契约。不含仿真器，不含策略。

其它仓库只依赖这个包，通过 entry point 注册自己：

- `loopbench.simulators`
- `loopbench.policies`
- `loopbench.suites`

`composition` 里还有企业评测的合同：`EnvironmentDefinition`（场景 × 本体 × 任务）、`Experiment`（shared + runs）、协议号 `loopbench.experiment/1`。仿真器自己决定能不能编译某一对场景和本体。

环境步进对齐 Gymnasium 的 `reset` / `step`。策略动作对齐 LeRobot 的 `select_action`。
