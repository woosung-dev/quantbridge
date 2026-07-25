"use client";

// 05 거래 내역 — variant-c "거래 목록" 이식. 공용 table.trades/.toolbar/.pager 를 소비한다.
// 프로토타입 variant-c.html:1447-1575 의 단일행 10열 구조(번호/방향/진입·청산 시각·가/수량/손익/
// 수익률/청산 사유). 방향 라벨은 용어 SSOT(TRADE_DIRECTION_LABEL), 무데이터 셀은 EMPTY_CELL.
// 런업/드로다운/누적 등 확장 열과 정렬은 전용 /trades 원장(S6)이 담당하고, 여기서는 미리보기다.

import { useMemo, useState } from "react";
import { DownloadIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { TRADE_DIRECTION_LABEL } from "@/features/backtest/labels";
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
import { EMPTY_CELL } from "@/lib/labels";

// 리포트 미리보기 상한. 전체 원장은 /backtests/[id]/trades 가 담당한다.
const PREVIEW_LIMIT = 25;

// 청산 사유 표기 — 원시 enum 노출 금지(labels 경유 관례). exit_kind 없으면 시그널 청산.
const EXIT_REASON_LABEL: Record<string, string> = {
  take_profit: "익절",
  stop_loss: "손절",
  trailing_stop: "추적 손절",
  liquidation: "강제청산",
};

interface TradeLedgerTableProps {
  trades: readonly TradeItem[];
  filenamePrefix?: string;
}

export function TradeLedgerTable({
  trades,
  filenamePrefix = "trades",
}: TradeLedgerTableProps) {
  const [directionFilter, setDirectionFilter] =
    useState<TradeFilters["direction"]>("all");
  const [resultFilter, setResultFilter] =
    useState<TradeFilters["result"]>("all");

  // 최신 거래가 위(번호 내림차순) — variant-c 는 186 이 맨 위다.
  const sorted = useMemo(
    () =>
      applyTradeFilterSort(
        trades,
        { direction: directionFilter, result: resultFilter },
        "entry_time",
        "desc",
      ),
    [trades, directionFilter, resultFilter],
  );
  const shown = useMemo(() => sorted.slice(0, PREVIEW_LIMIT), [sorted]);

  const handleExport = () => {
    const csv = tradesToCsv(sorted);
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadCsv(`${filenamePrefix}-${ts}.csv`, csv);
  };

  if (trades.length === 0) {
    return (
      <div className="card">
        <div className="card-body">
          <StateBox
            testId="trade-ledger-empty"
            title="기록된 거래가 없습니다."
            body="이 실행에서 체결된 거래가 없습니다. 진입 조건을 만족한 신호가 없었을 수 있습니다."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="card" data-testid="trade-ledger-table">
      <div className="card-head">
        <div>
          <h3 className="card-title">거래 목록</h3>
          <p className="card-sub">
            최근 순 · {shown.length}건 표시{sorted.length > shown.length ? ` · 전체 ${sorted.length}건 중` : ""}
          </p>
        </div>
        <div className="toolbar">
          <select
            className="select"
            aria-label="방향 필터"
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value as TradeFilters["direction"])}
          >
            <option value="all">방향 전체</option>
            <option value="long">롱</option>
            <option value="short">숏</option>
          </select>
          <select
            className="select"
            aria-label="결과 필터"
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value as TradeFilters["result"])}
          >
            <option value="all">결과 전체</option>
            <option value="win">수익</option>
            <option value="loss">손실</option>
          </select>
          <button className="btn btn-ghost" type="button" onClick={handleExport}>
            <DownloadIcon aria-hidden="true" />
            CSV
          </button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="trades" aria-label={`거래 목록 ${shown.length}건`}>
          <thead>
            <tr>
              <th scope="col" className="num">번호</th>
              <th scope="col">방향</th>
              <th scope="col">진입 시각</th>
              <th scope="col" className="num">진입가</th>
              <th scope="col">청산 시각</th>
              <th scope="col" className="num">청산가</th>
              <th scope="col" className="num">수량</th>
              <th scope="col" className="num">손익</th>
              <th scope="col" className="num">수익률</th>
              <th scope="col">청산 사유</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 ? (
              <tr>
                <td colSpan={10} className="mono-l dim">
                  필터 조건에 맞는 거래가 없습니다.
                </td>
              </tr>
            ) : (
              shown.map((t) => <TradeRow key={t.trade_index} trade={t} />)
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span>
          전체 {sorted.length}건 중 1번부터 {shown.length}번까지
        </span>
      </div>
    </div>
  );
}

function TradeRow({ trade: t }: { trade: TradeItem }) {
  const isClosed = t.status === "closed" && t.exit_time !== null;
  const pnlTone = t.pnl >= 0 ? "num pos" : "num neg";
  const returnTone = t.return_pct >= 0 ? "num pos" : "num neg";
  const exitReason = isClosed
    ? (t.exit_kind != null ? EXIT_REASON_LABEL[t.exit_kind] : undefined) ?? "시그널 청산"
    : "보유 중";

  return (
    <tr data-testid={`trade-row-${t.trade_index}`} data-direction={t.direction}>
      <td className="num">{t.trade_index + 1}</td>
      <td>
        <span className={t.direction === "long" ? "side long" : "side short"}>
          {TRADE_DIRECTION_LABEL[t.direction]}
        </span>
      </td>
      <td className="mono-l">{formatDateTime(t.entry_time)}</td>
      <td className="num">{formatCurrency(t.entry_price)}</td>
      <td className="mono-l">{isClosed ? formatDateTime(t.exit_time) : EMPTY_CELL}</td>
      <td className="num">
        {t.exit_price !== null ? formatCurrency(t.exit_price) : EMPTY_CELL}
      </td>
      <td className="num">{formatCurrency(t.size, 4)}</td>
      <td className={pnlTone}>
        {t.pnl >= 0 ? "+" : ""}
        {formatCurrency(t.pnl)}
      </td>
      <td className={returnTone}>
        {t.return_pct >= 0 ? "+" : ""}
        {formatPercent(t.return_pct)}
      </td>
      <td>{exitReason}</td>
    </tr>
  );
}
