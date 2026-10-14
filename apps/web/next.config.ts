import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev server is bound to 0.0.0.0, so the browser's 127.0.0.1 origin
  // is otherwise treated as cross-origin and the client never hydrates.
  allowedDevOrigins: ["127.0.0.1"],
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
