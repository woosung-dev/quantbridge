// 앱 전역 Provider 체인 진입점 — ThemeProvider(다크/라이트 테마) 와 QueryProvider 를 조합한다.
// ★2026-08-17 ADR-034 — 사이에 있던 ClerkThemeBridge 가 사라졌다. Better Auth 는 provider
// 컴포넌트를 요구하지 않는다(세션은 nanostores 원자라 훅이 직접 구독한다).
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";
import { QueryProvider } from "./query-provider";

// 앱 레벨 Provider 체인 — ThemeProvider(최외곽) → QueryProvider → children
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
// ★종전에 여기 있던 「Clerk 한국어 localization + 자체 도메인 routing」(BL-319/328)은 위젯이
// 사라지면서 함께 없어졌다 — 로그인 화면이 우리 컴포넌트라 한국어가 기본이고, 라우팅은
// `proxy.ts` 가 `/sign-in` 으로 직접 보낸다.
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <QueryProvider>{children}</QueryProvider>
    </ThemeProvider>
  );
}
