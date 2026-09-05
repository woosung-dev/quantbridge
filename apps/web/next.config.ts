// Next.js production config — Sprint 60 S5 BL-245/246/274 (P1-13 안전헤더 최소 gate)
import bundleAnalyzer from "@next/bundle-analyzer";
import type { NextConfig } from "next";

// Multi-Agent QA 2026-05-13 발견 — landing/dashboard 모든 페이지 보안 헤더 0개.
// Beta 외부 노출 시 즉시 audit fail. P1-13 채택: 최소 gate (CSP report-only / X-Frame / Referrer-Policy / HSTS)
// 적용 후 Sprint 61 polish 시 CSP strict 로 단계적 강화.
// ★2026-09-06 실측 — CSP 는 report-only 로도 **적용된 적이 없다**(아래 5종에 `Content-Security-Policy*` 없음).
//   위 두 줄은 계획이지 현황이 아니다. 넣으려면 인라인 스크립트·Monaco·차트 CDN 표면을 먼저 재라.
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
  // ★2026-08-08 — 위 한 줄은 **빌드 시 file tracing 만** 고정했다. 같은 workspace-root
  // 오추론이 Turbopack 에도 걸려 `next dev` 의 **해석 뿌리가 레포 루트**였고, 그 증거가
  // `Can't resolve 'tailwindcss' in '<레포 루트>'` 였다(루트 node_modules 엔 없다).
  // 고정 후 실측: 그 에러 2건 → **0건**.
  // ★★**이것은 CPU 문제의 해가 아니다.** 같은 회차에 `next dev` 가 요청 0건에서 417% CPU 를
  // 태우는 사고가 있었는데, 이 고정을 넣고 A/B 로 재니 **415% → 415% 로 불변**이었다.
  // 진범은 `.next/dev` Turbopack 영속 캐시(1.99GB)였고 그것을 치우자 417% → **0.1%** 였다.
  // 두 결함을 한 줄로 묶어 적지 마라 — 이 주석의 초안이 정확히 그 실수를 했다.
  turbopack: { root: __dirname },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

// 2026-08-09 fe-perf-quartet [BL-662] — 번들 계측 전용. `ANALYZE=1` 일 때만 켜지므로
// 평시 빌드는 이 래퍼를 통과만 한다. [BL-662] 의 근거는 「줄 수와 모듈 도달성」이지
// 측정된 KB 가 아니었다 — 이 래퍼가 그 숫자를 만든다.
const withBundleAnalyzer = bundleAnalyzer({ enabled: process.env.ANALYZE === "1" });

export default withBundleAnalyzer(nextConfig);
