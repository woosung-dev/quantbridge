import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppProviders } from "@/components/providers/app-providers";
import { LegalNoticeBanner } from "@/components/legal-notice-banner";
import { Toaster } from "@/components/ui/sonner";
import { archivo, ibmPlexMono } from "@/lib/fonts";
import "@/styles/globals.css";

// DESIGN.md §3.1 — Precision Instrument 타이포 3종.
// 본문 Pretendard Variable 은 globals.css 의 dynamic-subset @import 로 로드
// (next/font 아님 — 한글 2.3MB 단일 preload 회피). Archivo/IBM Plex Mono 는
// lib/fonts.ts 의 next/font 로더 SSOT.

export const metadata: Metadata = {
  title: "QuantBridge",
  description:
    "TradingView Pine Script 전략을 백테스트·데모·라이브 트레이딩으로 연결하는 퀀트 플랫폼",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="ko"
      className={`${archivo.variable} ${ibmPlexMono.variable}`}
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
        {/* Sprint 11 Phase B — Beta 단계 고지 배너 (전 페이지 상단). H2 말 정식 변호사 교체 예정. */}
        <LegalNoticeBanner />
        <AppProviders>{children}</AppProviders>
        {/* Sonner Toaster — provider 체인 최하단 (z-index: modal 위) */}
        <Toaster position="top-center" richColors closeButton />
      </body>
    </html>
  );
}
