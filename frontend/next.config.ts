// Next.js production config — Sprint 60 S5 BL-245/246/274 (P1-13 안전헤더 최소 gate)
import type { NextConfig } from "next";

// Multi-Agent QA 2026-05-13 발견 — landing/dashboard 모든 페이지 보안 헤더 0개.
// Beta 외부 노출 시 즉시 audit fail. P1-13 채택: 최소 gate (CSP report-only / X-Frame / Referrer-Policy / HSTS)
// 적용 후 Sprint 61 polish 시 CSP strict 로 단계적 강화.
const securityHeaders = [
  {
    // Clickjacking 차단 — dashboard 페이지 iframe embed 금지
    key: "X-Frame-Options",
    value: "DENY",
  },
  {
    // Referrer 정보 노출 최소화 (cross-origin 시 origin only)
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    // MIME type sniffing 차단
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    // HSTS — production HTTPS 강제 (Sprint 61 production deploy 시 enforce)
    // Beta 단계 max-age 짧게 (6 months) — preload list 미진입
    key: "Strict-Transport-Security",
    value: "max-age=15552000; includeSubDomains",
  },
  {
    // Permissions-Policy — 미사용 brower API 차단 (geolocation/camera/microphone)
    key: "Permissions-Policy",
    value: "geolocation=(), camera=(), microphone=(), payment=()",
  },
];

const nextConfig: NextConfig = {
  // 2026-08-07 fe-oracle-deploy — 오라클 A1(aarch64) 배포용 최소 런타임 산출물.
  // 서버에 Node 가 없어 `next start` 를 쓸 수 없다 — standalone 의 `server.js` 를
  // node:22-alpine 이미지에 얹는다 (빌드는 맥, 서버는 실행만).
  output: "standalone",
  // ★루트에 husky/prettier 용 `pnpm-lock.yaml` 이 있어 Next 가 workspace root 를
  // 레포 루트로 추론한다. 그대로 두면 file tracing 이 루트 `node_modules` 까지 훑는다.
  // 이 레포는 pnpm workspace 가 아니므로(`pnpm-workspace.yaml` 없음) frontend 로 고정한다.
  outputFileTracingRoot: __dirname,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
