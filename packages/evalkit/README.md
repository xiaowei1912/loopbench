# loopbench-evalkit

评测仓库。只依赖 `loopbench-spec`。

仿真器和策略通过 entry point 注入。本仓库负责：跑 episode、单因素归因、生成下一批场景、调用策略自己的 `improve()`，以及按实验 YAML 连续跑多个 run。打开仿真、打开策略、打开 socket 都是调用方的事。
