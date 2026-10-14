"use client";

import { useEffect, useState } from "react";

import { ErrorBlock, LoadingBlock } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Catalog } from "@/lib/types";

export default function BackendsPage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setError(null);
    api<Catalog>("/api/catalog")
      .then(setCatalog)
      .catch((exc: Error) => setError(exc.message));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="max-w-3xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">BACKENDS</p>
      <h1 className="font-display mt-2 text-4xl">后端目录</h1>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        已安装的仿真、策略和基准来自 entry point。上游栈只做探测：能 import 就标成可用，不能 import 就留下真实的接入点，不把 Isaac 或 LIBERO 的代码搬进来。
      </p>

      {error ? <div className="mt-6"><ErrorBlock detail={error} onRetry={load} /></div> : null}
      {!catalog && !error ? <div className="mt-6"><LoadingBlock /></div> : null}

      {catalog ? (
        <div className="mt-8 space-y-10">
          <Section title="仿真">
            {catalog.simulators.map((item) => (
              <Row
                key={item.name}
                title={item.name}
                available={item.available}
                meta={item.gym_id}
                body={item.detail}
                href={item.upstream_url}
                hrefLabel={item.upstream}
              />
            ))}
          </Section>
          <Section title="策略">
            {catalog.policies.map((item) => (
              <Row
                key={item.name}
                title={item.name}
                available={item.available}
                meta={item.needs_privileged ? "needs_privileged" : "deployable"}
                body={item.detail}
                href={item.upstream_url}
                hrefLabel={item.upstream}
              />
            ))}
          </Section>
          <Section title="基准">
            {catalog.suites.map((item) => (
              <Row
                key={item.name}
                title={`${item.label} · ${item.name}`}
                available
                meta={`${item.tasks.length} 任务 · ${item.cells.length} 格`}
                body={item.description}
                href={item.upstream_url}
                hrefLabel={item.upstream}
              />
            ))}
          </Section>
          <Section title="任务词汇">
            {catalog.tasks.map((item) => (
              <Row
                key={item.id}
                title={`${item.label} · ${item.id}`}
                available
                meta={item.family}
                body={item.instruction}
                href={item.upstream_url}
                hrefLabel={item.upstream}
              />
            ))}
          </Section>
          <Section title="上游栈">
            {catalog.adapters.map((item) => (
              <Row
                key={item.id}
                title={item.id}
                available={item.available}
                meta={item.available ? item.detail : item.role}
                body={item.glue}
                href={item.url}
                hrefLabel={item.module}
              />
            ))}
          </Section>
        </div>
      ) : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="font-display text-2xl">{title}</h2>
      <div className="mt-3 divide-y divide-border border-y border-border">{children}</div>
    </section>
  );
}

function Row({
  title,
  available,
  meta,
  body,
  href,
  hrefLabel,
}: {
  title: string;
  available: boolean;
  meta?: string;
  body: string;
  href?: string;
  hrefLabel?: string;
}) {
  return (
    <article className="py-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-medium">{title}</h3>
        <Badge variant={available ? "secondary" : "outline"}>{available ? "可用" : "未安装"}</Badge>
        {meta ? <span className="font-mono text-[11px] text-muted-foreground">{meta}</span> : null}
      </div>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{body}</p>
      {href ? (
        <a href={href} className="mt-1 inline-block text-xs text-oxide underline underline-offset-4" target="_blank" rel="noreferrer">
          {hrefLabel || href}
        </a>
      ) : null}
    </article>
  );
}
