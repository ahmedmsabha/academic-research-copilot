import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Keep tracing inside this app when parent directories contain other lockfiles.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
