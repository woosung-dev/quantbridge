"use client";

// TV "거래목록" 원장 — 거래당 진입/청산 2행(rowSpan), 방향 badge, 크기(qty+명목가),
// 순손익 abs+%, 런업/드로다운(MFE/MAE, bar 근사)/누적 PnL 컬럼.
// 신규 컬럼은 전 trade null(구 백테스트) 시 자동 hide (Surface Trust).

import { ChevronDown, ChevronUp, Download } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TradeItem } from "@/features/backtest/schemas";
import {
  type TradeFilters,
  applyTradeFilterSort,
  downloadCsv,
  formatCurrency,
  formatDateTime,
  formatPercent,
  tradesToCsv,
} from "@/features/backtest/utils";
import { cn } from "@/lib/utils";

const LEDGER_LIMIT = 200;

const EXIT_KIND_LABEL: Record<string, string> = {
  take_profit: "청산 · TP",
  stop_loss: "청산 · SL",
  trailing_stop: "청산 · 트레일링",
};

interface TradeLedgerTableProps {
  trades: readonly TradeItem[];
  filenamePrefix?: string;
}

export function TradeLedgerTable({
  trades,
  filenamePrefix = "trades",
}: TradeLedgerTableProps) {
  const visible = trades.slice(0, LEDGER_LIMIT);
  const truncated = trades.length > LEDGER_LIMIT;

  // TV 기본 = 거래 번호 내림차순 (최신 거래 위).
  const [indexDesc, setIndexDesc] = useState(true);
  const [directionFilter, setDirectionFilter] =
    useState<TradeFilters["direction"]>("all");
  const [resultFilter, setResultFilter] =
    useState<TradeFilters["result"]>("all");

  const filtered = useMemo(() => {
    const base = applyTradeFilterSort(
      visible,
      { direction: directionFilter, result: resultFilter },
      "entry_time",
      indexDesc ? "desc" : "asc",
    );
    return base;
  }, [visible, directionFilter, resultFilter, indexDesc]);

  // 신규 컬럼 — 전 trade null 이면 컬럼 자체 hide.
  const hasExcursion = useMemo(
    () => filtered.some((t) => t.runup_abs != null || t.drawdown_abs != null),
    [filtered],
  );
  const hasCumulative = useMemo(
    () => filtered.some((t) => t.cumulative_pnl != null),
    [filtered],
  );

  const handleExport = () => {
    const csv = tradesToCsv(filtered);
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadCsv(`${filenamePrefix}-${ts}.csv`, csv);
  };

  if (visible.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        기록된 거래가 없습니다
      </div>
    );
  }

  const colCount = 6 + (hasExcursion ? 2 : 0) + (hasCumulative ? 1 : 0);

  return (
    <div className="space-y-3" data-testid="trade-ledger-table">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={directionFilter}
            onValueChange={(v) =>
              setDirectionFilter(v as TradeFilters["direction"])
            }
          >
            <SelectTrigger className="w-32" aria-label="방향 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">방향: 전체</SelectItem>
              <SelectItem value="long">롱만</SelectItem>
              <SelectItem value="short">숏만</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={resultFilter}
            onValueChange={(v) => setResultFilter(v as TradeFilters["result"])}
          >
            <SelectTrigger className="w-32" aria-label="결과 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">결과: 전체</SelectItem>
              <SelectItem value="win">승리만</SelectItem>
              <SelectItem value="loss">패배만</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground">
            {filtered.length} / {visible.length} 건
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={filtered.length === 0}
          aria-label="CSV 내보내기"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          CSV
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-muted/50 text-xs tracking-wide text-muted-foreground uppercase">
            <tr>
              <th scope="col" className="px-3 py-2 text-left">
                <button
                  type="button"
                  onClick={() => setIndexDesc((prev) => !prev)}
                  className="inline-flex items-center gap-1 hover:text-foreground"
                  aria-label={`거래 번호 ${indexDesc ? "내림차순" : "오름차순"} 정렬`}
                >
                  거래 번호
                  {indexDesc ? (
                    <ChevronDown className="h-3 w-3" aria-hidden="true" />
                  ) : (
                    <ChevronUp className="h-3 w-3" aria-hidden="true" />
                  )}
                </button>
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                타입
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                날짜 및 시간 (UTC)
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                가격
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                크기
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                순손익
              </th>
              {hasExcursion ? (
                <>
                  <th scope="col" className="px-3 py-2 text-right">
                    런업
                    <span className="ml-1 normal-case">(bar 근사)</span>
                  </th>
                  <th scope="col" className="px-3 py-2 text-right">
                    드로다운
                    <span className="ml-1 normal-case">(bar 근사)</span>
                  </th>
                </>
              ) : null}
              {hasCumulative ? (
                <th scope="col" className="px-3 py-2 text-right">
                  누적 PnL
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={colCount}
                  className="px-3 py-8 text-center text-sm text-muted-foreground"
                >
                  필터 조건에 일치하는 거래가 없습니다
                </td>
              </tr>
            ) : (
              filtered.map((t) => (
                <LedgerRows
                  key={t.trade_index}
                  trade={t}
                  hasExcursion={hasExcursion}
                  hasCumulative={hasCumulative}
                />
              ))
            )}
          </tbody>
        </table>
        {truncated ? (
          <p className="border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            최대 {LEDGER_LIMIT}건만 표시됩니다. 전체 결과는 CSV 내보내기로 확인하세요.
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** 거래 1건 = 청산/진입 2행 (open 은 진입 1행). rowSpan 셀은 첫 행에만. */
function LedgerRows({
  trade: t,
  hasExcursion,
  hasCumulative,
}: {
  trade: TradeItem;
  hasExcursion: boolean;
  hasCumulative: boolean;
}) {
  const isClosed = t.status === "closed" && t.exit_time !== null;
  const rowSpan = isClosed ? 2 : 1;
  const notional = t.entry_price * t.size;
  const pnlTone = t.pnl >= 0 ? "text-bullish" : "text-bearish";
  const exitLabel =
    (t.exit_kind != null ? EXIT_KIND_LABEL[t.exit_kind] : undefined) ?? "청산";

  const spanCells = (
    <>
      <td rowSpan={rowSpan} className="px-3 py-2 align-middle text-right tabular-nums">
        <div>{formatCurrency(t.size, 4)}</div>
        <div className="text-xs text-muted-foreground">
          {formatCurrency(notional, 0)} USDT
        </div>
      </td>
      <td
        rowSpan={rowSpan}
        className={cn("px-3 py-2 align-middle text-right font-mono tabular-nums", pnlTone)}
      >
        <div>
          {t.pnl >= 0 ? "+" : ""}
          {formatCurrency(t.pnl)} USDT
        </div>
        <div className="text-xs opacity-80">
          {t.return_pct >= 0 ? "+" : ""}
          {formatPercent(t.return_pct)}
        </div>
      </td>
      {hasExcursion ? (
        <>
          <td
            rowSpan={rowSpan}
            className="px-3 py-2 align-middle text-right font-mono text-xs tabular-nums text-bullish"
          >
            {t.runup_abs != null ? (
              <>
                <div>{formatCurrency(t.runup_abs)}</div>
                <div className="opacity-70">
                  {t.runup_pct != null ? formatPercent(t.runup_pct) : ""}
                </div>
              </>
            ) : (
              "—"
            )}
          </td>
          <td
            rowSpan={rowSpan}
            className="px-3 py-2 align-middle text-right font-mono text-xs tabular-nums text-bearish"
          >
            {t.drawdown_abs != null ? (
              <>
                <div>{formatCurrency(t.drawdown_abs)}</div>
                <div className="opacity-70">
                  {t.drawdown_pct != null ? formatPercent(t.drawdown_pct) : ""}
                </div>
              </>
            ) : (
              "—"
            )}
          </td>
        </>
      ) : null}
      {hasCumulative ? (
        <td
          rowSpan={rowSpan}
          className={cn(
            "px-3 py-2 align-middle text-right font-mono tabular-nums",
            (t.cumulative_pnl ?? 0) >= 0 ? "text-bullish" : "text-bearish",
          )}
        >
          {t.cumulative_pnl != null ? (
            <>
              {t.cumulative_pnl >= 0 ? "+" : ""}
              {formatCurrency(t.cumulative_pnl)}
            </>
          ) : (
            "—"
          )}
        </td>
      ) : null}
    </>
  );

  const numberCell = (
    <td rowSpan={rowSpan} className="px-3 py-2 align-middle">
      <span className="font-mono tabular-nums">{t.trade_index + 1}</span>
      <span
        className={cn(
          "ml-2 rounded px-1.5 py-0.5 text-[11px] font-semibold",
          t.direction === "long"
            ? "bg-[color:var(--success-subtle)] text-[color:var(--bullish)]"
            : "bg-[color:var(--destructive-subtle)] text-[color:var(--bearish)]",
        )}
        data-dir={t.direction}
      >
        {t.direction === "long" ? "롱" : "숏"}
      </span>
      {t.comment ? (
        <div className="mt-0.5 text-[11px] text-muted-foreground">{t.comment}</div>
      ) : null}
    </td>
  );

  if (!isClosed) {
    return (
      <tr className="border-t" data-direction={t.direction}>
        {numberCell}
        <td className="px-3 py-2 text-xs">진입 (보유 중)</td>
        <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
          {formatDateTime(t.entry_time)}
        </td>
        <td className="px-3 py-2 text-right tabular-nums">
          {formatCurrency(t.entry_price)} USDT
        </td>
        {spanCells}
      </tr>
    );
  }

  return (
    <>
      <tr className="border-t" data-direction={t.direction}>
        {numberCell}
        <td className="px-3 py-2 text-xs">{exitLabel}</td>
        <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
          {formatDateTime(t.exit_time)}
        </td>
        <td className="px-3 py-2 text-right tabular-nums">
          {t.exit_price !== null ? `${formatCurrency(t.exit_price)} USDT` : "—"}
        </td>
        {spanCells}
      </tr>
      <tr data-direction={t.direction}>
        <td className="px-3 py-2 text-xs text-muted-foreground">진입</td>
        <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
          {formatDateTime(t.entry_time)}
        </td>
        <td className="px-3 py-2 text-right text-muted-foreground tabular-nums">
          {formatCurrency(t.entry_price)} USDT
        </td>
      </tr>
    </>
  );
}
