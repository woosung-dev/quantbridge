// 브랜드 팔레트 hex 상수 SSOT — CSS 변수를 읽을 수 없는 소비자 전용 (Precision Instrument)
//
// 소비자 3곳: chart-tokens.ts SSR 폴백 / Monaco defineTheme(pine-language.ts) /
// OG 이미지(opengraph-image.tsx). CSS 변수 라이브 해석이 가능한 곳은 이 모듈이 아니라
// globals.css 토큰을 직접 소비할 것.
//
// 동기화 계약: 이 파일과 src/styles/globals.css 의 :root/.dark 값은 항상 같은
// 커밋에서 함께 변경한다 (desync = 차트 SSR 플래시 / 에디터·OG 구팔레트 잔존).

export const BRAND_PALETTE = {
  light: {
    bg: "#f6f7f8",
    bgAlt: "#edeff1",
    card: "#ffffff",
    cardRaised: "#ffffff",
    border: "#e2e5e9",
    borderDark: "#cbd1d7",
    textPrimary: "#171a1e",
    textSecondary: "#4b535c",
    textMuted: "#656e78",
    primary: "#b45309",
    primaryHover: "#9a4507",
    bullish: "#0b7a55",
    bearish: "#c93a31",
    success: "#047857",
    destructive: "#c22a2a",
    warning: "#a16207",
    chartEquity: "#b45309",
    chartBenchmark: "#2563eb",
    chartCompare: "#7c3aed",
    chartGrid: "rgba(23, 26, 30, 0.07)",
    ddLine: "rgba(201, 58, 49, 0.55)",
    ddTop: "rgba(201, 58, 49, 0.3)",
    ddBottom: "rgba(201, 58, 49, 0.02)",
  },
  dark: {
    bg: "#0b0d0f",
    bgAlt: "#101214",
    card: "#141619",
    cardRaised: "#1a1d21",
    border: "#22262b",
    borderDark: "#31363d",
    textPrimary: "#e8eaed",
    textSecondary: "#a6adb5",
    textMuted: "#7a828c",
    primary: "#f08c2e",
    primaryHover: "#f79d4d",
    bullish: "#2dd4a7",
    bearish: "#f6685e",
    success: "#34d399",
    destructive: "#f6685e",
    warning: "#e5a93d",
    chartEquity: "#f08c2e",
    chartBenchmark: "#6aa2f7",
    chartCompare: "#a78bfa",
    chartGrid: "rgba(232, 234, 237, 0.07)",
    ddLine: "rgba(246, 104, 94, 0.55)",
    ddTop: "rgba(246, 104, 94, 0.28)",
    ddBottom: "rgba(246, 104, 94, 0.02)",
  },
} as const;

export type BrandPaletteTheme = keyof typeof BRAND_PALETTE;
