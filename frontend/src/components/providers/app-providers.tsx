import { ClerkProvider } from "@clerk/nextjs";
import { koKR } from "@clerk/localizations";
import type { ReactNode } from "react";
import { QueryProvider } from "./query-provider";

// 앱 레벨 Provider 체인 — ClerkProvider가 바깥, React Query가 안쪽
//
// Sprint 61 T-3 (BL-319/328): Clerk widget 한국어 localization + 자체 도메인 routing.
// - localization=koKR: "Sign in / Email / Continue" 등 영어 form → 한국어 (BL-328).
// - signInUrl/signUpUrl 명시: dev instance 의 accounts.dev redirect 차단 → /sign-in,
//   /sign-up 자체 도메인 안에서 SignIn/SignUp 컴포넌트 호스팅 (BL-319).
// - signInFallbackRedirectUrl/signUpFallbackRedirectUrl: 인증 후 default redirect.
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ClerkProvider
      localization={koKR}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/strategies"
      signUpFallbackRedirectUrl="/strategies"
    >
      <QueryProvider>{children}</QueryProvider>
    </ClerkProvider>
  );
}
