"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

// Dashboard 라우트 그룹 에러 바운더리 — app/error.tsx보다 좁은 scope.
// 대시보드 shell은 유지하고 콘텐츠 영역만 에러 UI로 대체.
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[DashboardError]", error);
  }, [error]);

  return (
    <div className="mx-auto flex max-w-[520px] flex-col items-start gap-4 px-6 py-12">
      <h2 className="font-display text-xl font-bold">
        대시보드를 불러오지 못했습니다
      </h2>
      <p className="text-sm text-[color:var(--text-secondary)]">
        네트워크 또는 인증 상태를 확인한 뒤 다시 시도해 주세요.
        {error.digest ? (
          <span className="mt-1 block font-mono text-xs text-[color:var(--text-muted)]">
            ref: {error.digest}
          </span>
        ) : null}
      </p>
      <Button onClick={reset}>다시 시도</Button>
    </div>
  );
}
