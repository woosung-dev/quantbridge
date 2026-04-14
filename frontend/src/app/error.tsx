"use client";

import { useEffect } from "react";

// 루트 에러 바운더리 — fullstack.md 패턴 차용
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="mx-auto flex max-w-[520px] flex-col items-start gap-4 px-6 py-20">
      <h2 className="font-display text-2xl font-bold">문제가 발생했습니다</h2>
      <p className="text-sm text-[color:var(--text-secondary)]">
        일시적인 오류일 수 있습니다. 다시 시도하거나 잠시 후 새로고침해 주세요.
      </p>
      <button
        type="button"
        onClick={reset}
        className="inline-flex min-h-[48px] items-center gap-2 rounded-[10px] bg-[color:var(--primary)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[color:var(--primary-hover)]"
      >
        다시 시도
      </button>
    </div>
  );
}
