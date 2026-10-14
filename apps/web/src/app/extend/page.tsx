import Link from "next/link";

const SNIPPET = `[project.entry-points."loopbench.suites"]
tabletop_smoke = "loopbench_example_suite:smoke"`;

const SIM = `class MujocoBackend:
    name = "mujoco"

    def probe(self):
        return {"name": self.name, "available": True, "kind": "simulator", "detail": "..."}

    def make(self, *, expose_privileged=False, render_size=160):
        return YourGymEnv(expose_privileged=expose_privileged)`;

export default function ExtendPage() {
  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">EXTEND</p>
      <h1 className="font-display mt-2 text-4xl">加一个仓库，不改评测器</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        评测器只认识 entry point。新的仿真、策略或基准装上之后，catalog 里就会出现，不用改 loopbench-evalkit。
        <Link href="/backends" className="ml-1 text-oxide underline underline-offset-4">
          tabletop_smoke
        </Link>
        就是这样进来的：它只依赖 spec。
      </p>

      <section className="mt-8">
        <h2 className="font-display text-2xl">四组入口</h2>
        <ul className="mt-3 space-y-2 text-sm leading-6">
          <li><span className="font-mono text-xs">loopbench.simulators</span> · probe() 和 make()，返回 Gymnasium Env</li>
          <li><span className="font-mono text-xs">loopbench.policies</span> · make() 和 improve()，动作从 select_action 来</li>
          <li><span className="font-mono text-xs">loopbench.suites</span> · 一个 Suite，任务 id 用 spec 里的词汇</li>
          <li><span className="font-mono text-xs">loopbench.adapters</span> · 只探测上游能不能 import</li>
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="font-display text-2xl">基准仓库</h2>
        <pre className="mt-3 overflow-x-auto border border-border bg-card p-4 font-mono text-xs leading-6">{SNIPPET}</pre>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Suite 的 tasks 写 pick_place、stack、push、drawer、sort。cells 用 Factors 的名字，不写米和颜色。每个仿真自己解释 camera=shifted 是多少。
        </p>
      </section>

      <section className="mt-8">
        <h2 className="font-display text-2xl">仿真仓库</h2>
        <pre className="mt-3 overflow-x-auto border border-border bg-card p-4 font-mono text-xs leading-6">{SIM}</pre>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          reset 接受 seed 和 options，options 里是 task 和 factors。观测字典带 observation.image、observation.state、task。info 公布 fixtures、materials、camera_model、control 和 metrics。privileged 只在 expose_privileged 为真时出现，视觉策略读不到它。
        </p>
      </section>

      <section className="mt-8">
        <h2 className="font-display text-2xl">依赖方向</h2>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          spec 不认识仿真和策略。仿真和策略互不 import。evalkit 不 import 它们，只通过 registry 取插件。API 同样不 import 仿真模块。scripts/check_boundaries.py 会扫 import 行。
        </p>
      </section>
    </div>
  );
}
