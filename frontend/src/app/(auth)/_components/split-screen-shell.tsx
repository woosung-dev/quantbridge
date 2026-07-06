// 인증 페이지 split-screen shell — 좌 brand-panel + 우 Clerk 폼
// Precision Instrument W5 PR-12 (원 레이아웃: docs/prototypes/04-login.html)

import type { ReactNode } from "react";
import { BrandPanel } from "./brand-panel";

type SplitMode = "sign-in" | "sign-up";

interface SplitScreenShellProps {
  mode: SplitMode;
  children: ReactNode;
}

/**
 * 인증 라우트 그룹 `(auth)` 전용 split-screen shell.
 *
 * - md+ (≥768px): 50/50 grid — 좌 BrandPanel (항상 카본+코퍼) + 우 Clerk children
 * - mobile (<768px): BrandPanel 미노출, children 만 stack 표시
 * - 우측 form-panel: `bg-card` 토큰 (라이트 화이트 / 다크 스틸 flip)
 * - form wrapper max-w 400px
 */
export function SplitScreenShell({ mode, children }: SplitScreenShellProps) {
  return (
    <div className="grid min-h-dvh grid-cols-1 md:grid-cols-2">
      <BrandPanel mode={mode} />
      <main
        className="flex min-h-dvh items-center justify-center bg-card px-6 py-12 md:px-10 md:py-20"
      >
        <div className="w-full max-w-[400px]">{children}</div>
      </main>
    </div>
  );
}
