# ADR 0005：企业评测用五个平面，不内置上游实现

## 状态

接受。

## 背景

Isaac Lab-Arena、RoboVerse、XPolicyLab、vla-evaluation-harness、LeRobot、praxis-eval 都在解决同一件事：仿真、策略和基准不要焊死在一个进程里。把它们的源码拷进仓库，许可证和体积都会把 demo 拖死，而且 CI 跑不了 Isaac。

## 决定

- 场景、本体、任务是 `EnvironmentDefinition`。仿真器用 `accepts` 拒绝自己编译不了的一对。
- 实验是 YAML：共享的 rollout，加上一组具名 run。
- 策略传输是标准库 TCP 上的 JSON 行，操作只有 reset、act、close。
- 评测包不打开 socket，也不 import 仿真。CLI 和 API 把已经打开的对象传进去。
- 每条实验结果带协议号 `loopbench.experiment/1`。

## 后果

OSMO、上游 Docker 镜像、策略权重和第三方策略目录都不在这个仓库里。适配器仍然只在库和检查点都存在时报告可运行。换协议字段时升协议号，不悄悄改 `loopbench.experiment/1` 的含义。
