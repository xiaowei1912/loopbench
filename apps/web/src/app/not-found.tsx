import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";

export default function NotFound() {
  return (
    <div className="max-w-xl">
      <p className="font-mono text-[11px] tracking-[0.18em] text-oxide">404</p>
      <h1 className="font-display mt-2 text-4xl">这页不在实验记录里</h1>
      <p className="mt-3 text-sm text-muted-foreground">回到工作台，或者从评测页重新开一轮。</p>
      <Link href="/" className={cn(buttonVariants(), "mt-6 inline-flex")}>
        回工作台
      </Link>
    </div>
  );
}
