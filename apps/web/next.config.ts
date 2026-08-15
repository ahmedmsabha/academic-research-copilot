import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone is for Docker/VPS only. Vercel uses its own Next.js builder.
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" as const } : {}),
  // Keep tracing inside this app when parent directories contain other lockfiles.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
