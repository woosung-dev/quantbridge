// 인증 페이지 split-screen shell — 좌 brand-panel + 우 Clerk 폼
// design source: docs/prototypes/04-login.html

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
 * - md+ (≥768px): 50/50 grid — 좌 BrandPanel (다크 그라디언트) + 우 Clerk children
 * - mobile (<768px): BrandPanel 미노출, children 만 stack 표시
 * - 우측 children wrapper: 라이트 배경(--bg-alt) + center align + min-h-dvh
 */
export function SplitScreenShell({ mode, children }: SplitScreenShellProps) {
  return (
    <div className="grid min-h-dvh grid-cols-1 md:grid-cols-2">
      <BrandPanel mode={mode} />
      <main
        className="flex min-h-dvh items-center justify-center p-6 md:p-10"
        style={{ background: "var(--bg-alt)" }}
      >
        <div className="w-full max-w-[440px]">{children}</div>
      </main>
    </div>
  );
}
