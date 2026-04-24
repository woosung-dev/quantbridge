import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import { AppProviders } from "@/components/providers/app-providers";
import { LegalNoticeBanner } from "@/components/legal-notice-banner";
import { Toaster } from "@/components/ui/sonner";
import "@/styles/globals.css";

// DESIGN.md §3.1 — 3종 폰트 (Inter 본문 / Plus Jakarta 제목 / JetBrains Mono 숫자)
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-jakarta",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-mono-code",
  display: "swap",
});

export const metadata: Metadata = {
  title: "QuantBridge",
  description:
    "TradingView Pine Script 전략을 백테스트·데모·라이브 트레이딩으로 연결하는 퀀트 플랫폼",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="ko"
      className={`${inter.variable} ${jakarta.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <body>
        {/* Skip link (WCAG 2.4.1 bypass blocks) — Tab 첫 포커스 시 노출 */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-md focus:bg-[color:var(--primary)] focus:px-4 focus:py-2 focus:text-white"
        >
          본문으로 바로가기
        </a>
        {/* Sprint 11 Phase B — 법무 임시 고지 배너 (전 페이지 상단). H2 말 정식 변호사 교체 예정. */}
        <LegalNoticeBanner />
        <AppProviders>{children}</AppProviders>
        {/* Sonner Toaster — provider 체인 최하단 (z-index: modal 위) */}
        <Toaster position="top-center" richColors closeButton />
      </body>
    </html>
  );
}
