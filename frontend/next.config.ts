import type { NextConfig } from "next";

// Dev CPU 부하 최소화:
// - typedRoutes: build 타임에만 활성. dev에선 파일 변경마다 route 재스캔 → CPU 누수.
// - reactStrictMode: true 유지 (double-render는 bug 조기 탐지 가치).
//   Monaco/Clerk의 이중 mount로 체감 큰 경우 dev 한정 false 고려.
const isBuild = process.env.NEXT_PHASE === "phase-production-build";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: isBuild,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  },
};

export default nextConfig;
