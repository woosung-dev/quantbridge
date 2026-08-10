// 앱 전역 Provider 체인 진입점 — ThemeProvider(다크/라이트 테마) 와 ClerkThemeBridge
// (Clerk 다국어·라우팅 + React Query) 를 조합한다.
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";
import { ClerkThemeBridge } from "./clerk-theme-bridge";

// 앱 레벨 Provider 체인 — ThemeProvider(최외곽) → ClerkThemeBridge(Clerk+Query) → children
//
// DESIGN.md §0: 앱 전체 라이트/다크 토글. next-themes attribute="class" 가 <html> 에
// .dark 를 토글하고 pre-paint 인라인 스크립트로 FOUC 를 차단한다 (layout.tsx 의
// suppressHydrationWarning 전제). disableTransitionOnChange 로 토글 시 전역 색 전환
// 애니메이션(transition-all/.qb-* )이 한꺼번에 깜빡이는 것을 방지.
//
// Precision Instrument: 다크가 기본 테마 (트레이딩 앱 표준, 차트 몰입).
// enableSystem 유지 — localStorage 에 명시 선택이 있는 기존 사용자는 그 값이 우선,
// 신규 방문자만 다크로 시작.
//
// Clerk 한국어 localization + 자체 도메인 routing 은 ClerkThemeBridge 로 이동 (BL-319/328).
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
    >
      <ClerkThemeBridge>{children}</ClerkThemeBridge>
    </ThemeProvider>
  );
}
