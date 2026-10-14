import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";

const MEASURED = [
  { label: "nominal", before: "100%", after: "100%" },
  { label: "lighting=glare", before: "0%", after: "100%" },
  { label: "lighting=dim", before: "0%", after: "100%" },
  { label: "camera=shifted", before: "0%", after: "100%" },
  { label: "clutter=2", before: "0%", after: "50%" },
  { label: "friction=low", before: "50%", after: "100%" },
];

export default function HomePage() {
  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">PHYSICAL AI · MODEL TO RESULT</p>
      <h1 className="font-display mt-3 text-4xl leading-[1.15] tracking-tight md:text-5xl">
        从一次失败读出该改哪一层
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
        普通工程师要在几分钟里走完模型、仿真、基准、评测和结果，并且把失败变成下一轮的场景和数据。Loopbench
        把这条闭环拆成可以单独安装的包。参考桌面和 MuJoCo 桌面在这个进程里就能跑。Isaac Lab、ManiSkill、LIBERO、RoboCasa、RoboTwin，以及 ACT、OpenVLA、GR00T、π0、π0.5，都有调用官方构造函数的适配器；库和权重不打进仓库。
      </p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Link href="/evaluate" className={cn(buttonVariants({ size: "lg" }), "h-10 px-4")}>
          跑一轮 Probe
        </Link>
        <Link href="/backends" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-4")}>
          看后端目录
        </Link>
      </div>

      <section className="mt-12 border-t border-border pt-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl">参考探针</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              tabletop_probe · vision_v1 · reference · seed 0 · 每格 1 条。光照、手眼和低摩擦回来了。杂乱只回来一半。
            </p>
          </div>
          <div className="font-mono text-sm">
            <span className="text-muted-foreground">25%</span>
            <span className="mx-2 text-oxide">→</span>
            <span>92%</span>
            <span className="ml-3 text-muted-foreground">找回 8 · 退步 0</span>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <thead className="font-mono text-[11px] tracking-wide text-muted-foreground">
              <tr className="border-b border-border">
                <th className="py-2 font-normal">单因素</th>
                <th className="py-2 font-normal">改进前</th>
                <th className="py-2 font-normal">改进后</th>
              </tr>
            </thead>
            <tbody>
              {MEASURED.map((row) => (
                <tr key={row.label} className="border-b border-border/70">
                  <td className="py-2 font-mono text-xs">{row.label}</td>
                  <td className="py-2 tabular-nums text-muted-foreground">{row.before}</td>
                  <td className="py-2 tabular-nums">{row.after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          clutter=2 的 50% 来自任务拆开：抓取放置绕开了柱子，叠放时绿色积木挡住黄块，侧向路点仍会擦到柱子。这一格是刻意留下的几何缺口，不是已经修好的指标。
        </p>
      </section>

      <section className="mt-10 grid gap-6 md:grid-cols-3">
        <article>
          <h3 className="font-display text-xl">评测</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            环境走 Gymnasium 的 reset / step。策略走 LeRobot 的 select_action。观测键是 observation.image、observation.state 和 task。
          </p>
        </article>
        <article>
          <h3 className="font-display text-xl">归因</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            只拿单因素格子和全名义工况比。光照乘相机、杂乱乘摩擦这种交互格留在记录里，不写进 delta。
          </p>
        </article>
        <article>
          <h3 className="font-display text-xl">改进</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            标定可以看真值。第二轮评测把 privileged 收回去：颜色原型、地标、避障和更短的搬运步长都要自己从图像里用。
          </p>
        </article>
      </section>
    </div>
  );
}
