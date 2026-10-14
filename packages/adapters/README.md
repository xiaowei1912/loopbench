# loopbench-adapters

上游适配仓库。不实现 Isaac、MuJoCo、ManiSkill、LIBERO。

它只回答两件事：那个包现在能不能 import，以及一个独立仓库要调用的真实入口。
新的仿真仓库自己注册 `loopbench.simulators`，不要把物理引擎拷进这里。
