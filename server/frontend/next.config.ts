import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/backend/:path*',
        destination: 'http://backend:3001/api/:path*'
      }
    ]
  },
};

export default nextConfig;
