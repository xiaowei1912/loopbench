import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const origin = process.env.API_ORIGIN || "http://127.0.0.1:43124";
    return [{ source: "/api/:path*", destination: `${origin}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
