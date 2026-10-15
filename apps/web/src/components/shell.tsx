"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { cn } from "cn";

const NAV = [
  { href: "/", label: "工作台" },
  { href: "/evaluate", label: "评测" },
  { href: "/runs", label: "记录" },
  { href: "/backends", label: "后端" },
  { href: "/architecture", label: "架构" },
  { href: "/extend", label: "扩展" },
];

function active(href: string, path: string) {
  if (href === "/") return path === "/";
  if (href === "/runs") return path.startsWith("/runs") || path.startsWith("/loops");
  return path === href || path.startsWith(`${href}/`);
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [online, setOnline] = useState<"unknown" | "up" | "down">("unknown");

  useEffect(() => {
    let cancelled = false;
    api<{ ok: boolean }>("/api/health")
      .then(() => {
        if (!cancelled) setOnline("up");
      })
      .catch(() => {
        if (!cancelled) setOnline("down");
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-6xl">
        <aside className="sticky top-0 hidden h-screen w-52 shrink-0 flex-col border-r border-border px-5 py-8 md:flex">
          <Link href="/" className="group">
            <div className="font-mono text-[11px] tracking-[0.22em] text-oxide">LOOPBENCH</div>
            <div className="font-display mt-1 text-xl leading-none">评测闭环</div>
          </Link>
          <nav className="mt-10 flex flex-col gap-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  active(item.href, path) && "bg-muted text-foreground",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="mt-auto font-mono text-[11px] text-muted-foreground">
            <span
              className={cn(
                "mr-2 inline-block size-1.5 rounded-full",
                online === "up" && "bg-good",
                online === "down" && "bg-destructive",
                online === "unknown" && "bg-muted-foreground",
              )}
            />
            {online === "up" ? "API 在线" : online === "down" ? "API 未连接" : "正在探测 API"}
          </div>
        </aside>
        <div className="notebook-rule relative min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 py-3 backdrop-blur md:hidden">
            <div className="font-mono text-[11px] tracking-[0.18em] text-oxide">LOOPBENCH</div>
            <nav className="mt-2 flex gap-3 overflow-x-auto text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "shrink-0 text-muted-foreground",
                    active(item.href, path) && "text-foreground underline decoration-oxide underline-offset-4",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>
          <main className="px-4 py-8 md:px-12 md:py-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
