"use client";
// Equity 차트 + Compare 오버레이 컨트롤 — 다른 완료 백테스트를 골라 % 수익률로 오버레이
import { GitCompareArrows } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBacktest, useBacktests } from "@/features/backtest/hooks";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";
import { formatDate } from "@/features/backtest/utils";

import { EquityChartV2 } from "./equity-chart-v2";

interface Props {
  /** 현재 보고 있는 백테스트 id — 비교 후보에서 제외. */
  currentId: string;
  equityCurve: readonly EquityPoint[];
  trades?: readonly TradeItem[];
  initialCapital: number;
  timeframe: string;
  mddExceedsCapital?: boolean | null;
  buyAndHoldCurve?: readonly EquityPoint[] | null;
}

const NONE = "__none__";

export function EquityChartWithCompare({
  currentId,
  equityCurve,
  trades,
  initialCapital,
  timeframe,
  mddExceedsCapital,
  buyAndHoldCurve,
}: Props) {
  const [compareId, setCompareId] = useState<string>(NONE);

  // 완료된 백테스트 목록 (자기 자신 제외).
  const list = useBacktests({ limit: 50, offset: 0 });
  const candidates = useMemo(
    () =>
      (list.data?.items ?? []).filter(
        (b) => b.id !== currentId && b.status === "completed",
      ),
    [list.data?.items, currentId],
  );

  const selectedId = compareId === NONE ? undefined : compareId;
  const compareDetail = useBacktest(selectedId);
  const compareCurve = compareDetail.data?.equity_curve ?? null;
  const selectedSummary = candidates.find((b) => b.id === compareId);
  const compareLabel = selectedSummary
    ? `${selectedSummary.symbol} · ${selectedSummary.timeframe}`
    : undefined;

  return (
    <section className="rounded-xl border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium">수익률 · 단순보유 · 낙폭</h2>
        <div className="flex items-center gap-2">
          <GitCompareArrows
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Select
            value={compareId}
            onValueChange={(v) => setCompareId(v ?? NONE)}
          >
            <SelectTrigger
              className="h-9 w-[240px] text-sm"
              aria-label="비교할 백테스트 선택"
            >
              <SelectValue placeholder="다른 백테스트와 비교" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>비교 안 함</SelectItem>
              {candidates.map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.symbol} · {b.timeframe} ·{" "}
                  {formatDate(b.completed_at ?? b.created_at)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {selectedId && compareDetail.isError ? (
        <p className="mb-2 text-xs text-destructive">
          비교 백테스트를 불러오지 못했습니다.
        </p>
      ) : null}

      <EquityChartV2
        equityCurve={equityCurve}
        trades={trades}
        initialCapital={initialCapital}
        timeframe={timeframe}
        mddExceedsCapital={mddExceedsCapital}
        buyAndHoldCurve={buyAndHoldCurve}
        compareCurve={compareCurve}
        compareLabel={compareLabel}
      />
    </section>
  );
}
