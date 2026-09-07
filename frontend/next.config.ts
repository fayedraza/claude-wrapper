import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root: the repo also has a root-level package.json
  // (the Playwright test suite, see ../tests/) with its own lockfile, which
  // Next.js would otherwise infer as the root and warn about.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
