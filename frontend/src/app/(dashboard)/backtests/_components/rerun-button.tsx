"use client";

// W5 — Backtest 상세 페이지 헤더의 "재실행" 버튼.
// 동일 파라미터로 useCreateBacktest.mutate() 호출 → 성공 시 router.push 로
// 새 backtest 상세 페이지로 이동. LESSON-004: useEffect 사용 금지,
// router.push 는 click handler / mutation onSuccess 콜백 안에서만 호출.

import { useRouter } from "next/navigation";
import { Loader2, RefreshCcw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useCreateBacktest } from "@/features/backtest/hooks";
import type { BacktestDetail } from "@/features/backtest/schemas";

interface RerunButtonProps {
  backtest: BacktestDetail;
  /** terminal 상태 (completed/failed/cancelled) 일 때만 true */
  isEnabled: boolean;
}

export function RerunButton({ backtest, isEnabled }: RerunButtonProps) {
  const router = useRouter();
  const create = useCreateBacktest({
    onSuccess: (created) => {
      toast.success("재실행 시작");
      router.push(`/backtests/${created.backtest_id}`);
    },
    onError: (err) => {
      toast.error(`재실행 실패: ${err.message}`);
    },
  });

  const isPending = create.isPending;
  const isDisabled = !isEnabled || isPending;

  const handleClick = () => {
    // schema decimalString 이 응답을 number 로 transform 하므로 initial_capital
    // 은 이미 number. 안전을 위해 Number() 한 번 더 강제 + finite 가드.
    const capital = Number(backtest.initial_capital);
    if (!Number.isFinite(capital) || capital <= 0) {
      toast.error("재실행 실패: 유효하지 않은 초기 자본");
      return;
    }
    // Sprint 31 BL-162a — 재실행 시 동일 cost/margin 가정 보존 (사용자가 직전
    // backtest 와 동일 결과 기대). bt.config null (legacy) 시 Bybit 표준 default.
    const cfg = backtest.config ?? null;
    create.mutate({
      strategy_id: backtest.strategy_id,
      symbol: backtest.symbol,
      timeframe: backtest.timeframe as never, // schema enum 보장 (BE→FE)
      period_start: backtest.period_start,
      period_end: backtest.period_end,
      initial_capital: capital,
      leverage: cfg?.leverage ?? 1,
      fees_pct: cfg?.fees ?? 0.001,
      slippage_pct: cfg?.slippage ?? 0.0005,
      include_funding: cfg?.include_funding ?? true,
    });
  };

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={handleClick}
      disabled={isDisabled}
      aria-label="동일 파라미터로 재실행"
    >
      {isPending ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <RefreshCcw className="mr-2 h-4 w-4" />
      )}
      재실행
    </Button>
  );
}
