// 인증 페이지 split-screen shell — 좌 brand-panel + 우 Clerk 폼
// design source: docs/prototypes/04-login.html (1:1 visual fidelity)

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
 * prototype 04 정합:
 * - md+ (≥768px): 50/50 grid — 좌 BrandPanel (다크 그라디언트) + 우 Clerk children
 * - mobile (<768px): BrandPanel 미노출, children 만 stack 표시
 * - 우측 form-panel: 흰색 배경(`#fff`) + padding 80px 40px (md+) — prototype 의 `.form-panel`
 * - max-w 400px — prototype 의 `.form-wrapper`
 */
export function SplitScreenShell({ mode, children }: SplitScreenShellProps) {
  return (
    <div className="grid min-h-dvh grid-cols-1 md:grid-cols-2">
      <BrandPanel mode={mode} />
      <main
        className="flex min-h-dvh items-center justify-center bg-white px-6 py-12 md:px-10 md:py-20"
      >
        <div className="w-full max-w-[400px]">{children}</div>
      </main>
    </div>
  );
}
