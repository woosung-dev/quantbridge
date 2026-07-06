"use client";
// next-themes 의 현재 테마를 Clerk appearance.baseTheme 로 연결하는 클라이언트 브릿지
//
// ClerkProvider 는 provider 트리 최상단(ThemeProvider 안쪽)에서 useTheme() 를 호출할 수
// 없으므로, 본 client 컴포넌트가 ThemeProvider 내부에서 resolvedTheme 을 읽어 Clerk 위젯
// (SignIn/UserButton 등)의 다크/라이트를 앱 테마와 동기화한다. proxy.ts/clerkMiddleware 불변.
import { ClerkProvider } from "@clerk/nextjs";
import { koKR } from "@clerk/localizations";
import { dark } from "@clerk/themes";
import { useTheme } from "next-themes";
import type { ReactNode } from "react";
import { BRAND_PALETTE } from "@/lib/brand-palette";
import { QueryProvider } from "./query-provider";

export function ClerkThemeBridge({ children }: { children: ReactNode }) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <ClerkProvider
      localization={koKR}
      appearance={{
        baseTheme: isDark ? dark : undefined,
        // 코퍼는 테마별 등급이 다름(다크는 밝은 코퍼) — brand-palette SSOT 참조
        variables: {
          colorPrimary: isDark
            ? BRAND_PALETTE.dark.primary
            : BRAND_PALETTE.light.primary,
        },
      }}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/strategies"
      signUpFallbackRedirectUrl="/strategies"
    >
      <QueryProvider>{children}</QueryProvider>
    </ClerkProvider>
  );
}
