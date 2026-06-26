import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Strict mode catches common React bugs during development
  reactStrictMode: true,

  // Standalone output bundles only the files needed to run in production,
  // dramatically reducing the Docker image size. Next.js traces imports and
  // includes only what's actually used — no full node_modules in the runtime
  // layer. Enabled when NEXT_STANDALONE=true (set in the Dockerfile).
  // https://nextjs.org/docs/app/api-reference/config/next-config-js/output
  output: process.env.NEXT_STANDALONE === "true" ? "standalone" : undefined,

  // Security headers for production
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },

  // Redirect bare /app paths to /dashboard
  async redirects() {
    return [
      {
        source: "/app",
        destination: "/dashboard",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
