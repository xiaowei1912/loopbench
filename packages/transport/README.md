# loopbench-transport

策略进程和仿真进程分开。线上是一行一个 JSON：

- `{"op":"reset"}`
- `{"op":"act","observation":{...},"info":{...}}` → `{"ok":true,"action":[...]}`
- `{"op":"close"}`

这是 XPolicyLab 那种策略适配器的最小合同：`reset` 和取动作。传输用标准库 TCP，这样策略环境不必安装仿真器。评测器只看见 `select_action`。
