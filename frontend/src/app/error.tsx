"use client";
// 루트 에러 바운더리 — prototype 11 의 500 layout (요청ID + clipboard + 시스템 상태) 1:1 visual fidelity

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ErrorIllustration } from "@/app/_components/error-illustration";
import { ErrorRecoveryBox } from "@/app/_components/error-recovery-box";

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

  // digest 가 있으면 요청 ID 로 노출 (Next.js sentry-style)
  const requestId = error.digest ?? "";
  // 발생 시각 — render 시점 1회 고정 (hydration 일치)
  const occurredAt = useMemo(() => formatNowKst(), []);
  // "다시 시도" 버튼 inline loading state — Next.js reset() 은 즉시 컴포넌트를 unmount 할 수도 있고
  // 외부 fetch 가 다시 실패할 수도 있어 1.2s timeout 으로 spinner 자동 해제 (UX 안전판).
  const [isRetrying, setIsRetrying] = useState(false);
  const handleRetry = () => {
    if (isRetrying) return;
    setIsRetrying(true);
    try {
      reset();
    } finally {
      window.setTimeout(() => setIsRetrying(false), 1200);
    }
  };

  return (
    <section
      aria-labelledby="err-500-heading"
      className="relative flex min-h-[calc(100vh-60px)] flex-col items-center justify-center overflow-hidden px-6 py-14 sm:py-20"
    >
      <ErrorIllustration variant="500" />

      <div className="relative z-[2] w-full max-w-[560px] text-center">
        <h1
          id="err-500-heading"
          className="mb-3.5 font-display text-2xl font-bold tracking-tight text-[color:var(--text-primary)] sm:text-[2rem]"
        >
          일시적인 문제가 발생했습니다
        </h1>
        <p className="mx-auto mb-8 max-w-[480px] whitespace-pre-line text-base leading-relaxed text-[color:var(--text-secondary)]">
          {`서버에서 요청을 처리하지 못했습니다.\n잠시 후 다시 시도해주세요. 문제가 계속되면 고객센터로 문의 바랍니다.`}
        </p>

        <ErrorRecoveryBox
          variant="500"
          requestId={requestId}
          occurredAt={occurredAt}
        />

        <div role="group" aria-label="복구 동작" className="relative z-[2] flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={handleRetry}
            disabled={isRetrying}
            data-testid="error-retry-button"
            data-loading={isRetrying || undefined}
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] bg-[color:var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)] transition-all duration-200 hover:-translate-y-px hover:bg-[color:var(--primary-hover)] hover:shadow-[0_12px_28px_rgba(37,99,235,0.36)] disabled:cursor-not-allowed disabled:opacity-80"
          >
            {isRetrying ? (
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                aria-hidden="true"
                className="motion-safe:animate-spin"
              >
                <path d="M21 12a9 9 0 1 1-6.22-8.55" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
            )}
            {isRetrying ? "다시 시도 중…" : "다시 시도"}
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-[10px] border border-[color:var(--border-dark)] bg-white px-5 py-2.5 text-sm font-semibold text-[color:var(--text-primary)] transition-colors hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M3 12l9-9 9 9" />
              <path d="M5 10v10h14V10" />
            </svg>
            홈으로
          </Link>
        </div>

        {/* 시스템 상태 pill bar */}
        <div
          role="status"
          aria-live="polite"
          className="relative z-[2] mt-8 inline-flex flex-wrap items-center justify-center gap-2.5 rounded-full border border-[color:var(--border)] bg-white px-4 py-2.5 text-[13px] shadow-sm"
        >
          <span aria-hidden="true" className="relative h-2 w-2 rounded-full bg-[color:var(--success)]">
            <span className="absolute -inset-1 rounded-full bg-[color:var(--success)] opacity-35 motion-safe:animate-ping" />
          </span>
          <span className="font-medium text-[color:var(--text-secondary)]">시스템 상태:</span>
          <span className="inline-flex items-center rounded-full bg-[color:var(--success-light)] px-2.5 py-0.5 text-xs font-semibold text-[#166534]">
            정상 운영 중
          </span>
        </div>
      </div>
    </section>
  );
}

// 발생 시각 포맷 — KST 고정 표시
function formatNowKst(): string {
  const now = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} KST`;
}
