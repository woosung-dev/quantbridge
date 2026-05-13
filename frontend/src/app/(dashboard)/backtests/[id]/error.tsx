"use client";

// Sprint 32 E (BL-163) — actionable error UX for backtest detail route.
//
// fullstack.md 패턴 차용 + 도메인 특화: backtest detail 로딩 실패 시 (네트워크 / 5xx /
// strategy_not_runnable 422) 사용자에게 (1) 무엇이 실패했는지 (2) 어떻게 복구할지
// (3) ADR-003 supported list 안내 링크 노출.
//
// 본 파일은 React render-time 예외만 catch (mutation onError 는 backtest-form.tsx
// + backtest-detail-view.tsx 의 inline 처리). dashboard error.tsx (한 단계 위) 보다
// 좁은 scope — 백테스트 상세 화면 컨텍스트 유지.

import Link from "next/link";
import { useEffect } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface BacktestDetailErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function BacktestDetailError({
  error,
  reset,
}: BacktestDetailErrorProps) {
  useEffect(() => {
    // Sprint 32 E (BL-163): error.message 는 일반 message — sensitive
    // payload 노출 risk 적음 (backend unhandled_exc_handler 가 sanitize).
    console.error("[BacktestDetailError]", error);
  }, [error]);

  return (
    <div
      className="mx-auto flex max-w-[640px] flex-col items-start gap-4 px-6 py-12"
      role="alert"
      data-testid="backtest-detail-error"
    >
      <h2 className="font-display text-xl font-bold">
        백테스트를 불러오지 못했습니다
      </h2>
      <p className="text-sm text-[color:var(--text-secondary)]">
        네트워크 또는 서버 상태 일시적 오류일 수 있습니다. 다시 시도하거나 잠시
        후 새로고침해 주세요.
      </p>
      {error.message ? (
        <p
          className="text-xs font-mono text-[color:var(--text-muted)] break-all"
          data-testid="backtest-detail-error-message"
        >
          {error.message}
        </p>
      ) : null}
      {error.digest ? (
        <p className="text-xs font-mono text-[color:var(--text-muted)]">
          ref: {error.digest}
        </p>
      ) : null}

      {/* Sprint 32 E (BL-163): actionable CTA — strategy_not_runnable 케이스 대비
          ADR-003 supported list 진입 경로 노출 (Coverage Analyzer pre-flight).
          Button 컴포넌트가 asChild 미지원 → Link 에 buttonVariants 직접 적용. */}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button onClick={reset}>다시 시도</Button>
        <Link
          href="/backtests"
          className={cn(buttonVariants({ variant: "outline" }))}
        >
          백테스트 목록으로
        </Link>
        <Link
          href="/strategies"
          className={cn(buttonVariants({ variant: "ghost" }))}
          data-testid="backtest-detail-error-supported-link"
        >
          지원 함수 목록 참조 (전략 목록)
        </Link>
      </div>
    </div>
  );
}
