const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: served by FastAPI (dashboard/out) or GitHub Pages.
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: { root: import.meta.dirname },
};

export default nextConfig;
