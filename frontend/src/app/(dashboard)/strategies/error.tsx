"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

// 전략 라우트 에러 바운더리 — Next.js App Router 규약.
// prefetch/streaming 중 throw된 에러를 이 경계에서 포착.
export default function StrategiesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[StrategiesError]", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-12">
      <div className="rounded-[var(--radius-lg)] border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-6 text-sm">
        <p className="font-medium text-[color:var(--destructive)]">
          전략 목록을 불러오지 못했습니다.
        </p>
        <p className="mt-1 text-xs text-[color:var(--text-secondary)]">
          네트워크 또는 인증 문제가 있을 수 있습니다.
          {error.digest ? (
            <span className="mt-1 block font-mono">ref: {error.digest}</span>
          ) : null}
        </p>
        <Button variant="outline" className="mt-4" onClick={reset}>
          다시 시도
        </Button>
      </div>
    </div>
  );
}
