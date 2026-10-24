import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  experimental: { cpus: 1, workerThreads: true, useTypeScriptCli: false },
  async headers() {
    return [{ source: "/:path*", headers: [
      {key: "X-Content-Type-Options", value: "nosniff"},
      {key: "Referrer-Policy", value: "no-referrer"},
      {key: "X-Frame-Options", value: "DENY"}
    ] }];
  }
};
export default nextConfig;
