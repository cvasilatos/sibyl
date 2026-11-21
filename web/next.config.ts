import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // Links from before each tab had its own route (/?tab=library&review=…). Other query parameters are kept.
      { source: "/", has: [{ type: "query", key: "tab", value: "(?<tab>review|library|models|gpu)" }], destination: "/:tab", permanent: false },
      { source: "/", destination: "/review", permanent: false },
    ];
  },
};

export default nextConfig;
