import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";

import { Shell } from "@/components/shell";

import "./globals.css";

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-newsreader",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Loopbench · 物理智能评测闭环",
  description: "仿真、基准、失败归因、场景生成、策略改进，然后用同一套基准再评一次。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`${plex.variable} ${newsreader.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full bg-background text-foreground">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
