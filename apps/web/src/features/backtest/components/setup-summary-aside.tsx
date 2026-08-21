// 백테스트 설정 요약 사이드 (우측 340px) — C 디자인 언어 이식(W3-A, screen-05 §05).
// 요약 행은 폼 값과 그 폼 값에서 순수 파생 가능한 값(기간 일수·봉 수)만 담는다. 서버가 주지 않는
// 추정 소요 시간·추정 수수료·실시간 배지는 그리지 않는다(§4.9 인쇄 금지 — 가짜 데이터 방지).
"use client";

import { EMPTY_CELL } from "@/lib/labels";

const FILL_TIMING_LABEL: Record<string, string> = {
  next_bar_open: "시그널 다음 봉 시가",
  bar_close: "시그널 봉 종가",
};

export interface SetupSummaryValues {
  symbol?: string;
  timeframe?: string;
  period_start?: string;
  period_end?: string;
  initial_capital?: number;
  position_size_pct?: number | null;
  default_qty_type?: string;
  default_qty_value?: number;
  sizing_source?: string;
  leverage?: number;
  fees_pct?: number;
  slippage_pct?: number;
  fill_timing?: string;
}

export interface SetupSummaryAsideProps {
  formValues: SetupSummaryValues;
  strategyName?: string;
  /** 우측 요약의 주 액션 버튼이 제출할 폼 id. */
  formId: string;
  /** 제출/요청 진행 중이면 버튼 비활성화. */
  submitting?: boolean;
  /** 폼 검증 오류 수. 1건 이상이면 실행 전 경고 문구를 띄운다. */
  errorCount?: number;
}

// 기간 일수 = (종료 - 시작) / 하루. 두 날짜가 순서대로 있을 때만. 순수 파생값(검산 가능).
export function diffDays(start?: string, end?: string): number | null {
  if (!start || !end) return null;
  const s = new Date(`${start}T00:00:00Z`).getTime();
  const e = new Date(`${end}T00:00:00Z`).getTime();
  if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return null;
  return Math.round((e - s) / (1000 * 60 * 60 * 24));
}

/** 하루당 봉 수. 24시간 시장 기준 (결측 없음 가정 = 상한 추정치). */
export const TIMEFRAME_BARS_PER_DAY: Record<string, number> = {
  "1m": 1440,
  "5m": 288,
  "15m": 96,
  "1h": 24,
  "4h": 6,
  "1d": 1,
};

// 봉 수 = days × bars/day. 순수 파생값(검산 가능). timeframe 미정 시 null.
export function barCount(days: number | null, timeframe?: string): number | null {
  if (days == null || !timeframe) return null;
  const bpd = TIMEFRAME_BARS_PER_DAY[timeframe];
  if (bpd == null) return null;
  return days * bpd;
}

function formatUsd(n: number | undefined): string {
  if (n == null || !Number.isFinite(n)) return EMPTY_CELL;
  return Math.round(n).toLocaleString();
}

function formatPct(n: number | undefined): string {
  if (n == null || !Number.isFinite(n)) return EMPTY_CELL;
  // 소수 저장값(0.001)을 백분율(0.10%)로. 뒤 0 은 다듬는다.
  const pct = n * 100;
  return `${Number(pct.toFixed(4))}%`;
}

function summarizePositionSize(v: SetupSummaryValues): string {
  if (v.sizing_source === "live" && v.position_size_pct != null) {
    return `${v.position_size_pct}% · Live 미러`;
  }
  if (v.default_qty_type === "strategy.percent_of_equity") {
    return `${v.default_qty_value ?? EMPTY_CELL}% · 자기자본`;
  }
  if (v.default_qty_type === "strategy.cash") {
    return `${formatUsd(v.default_qty_value)} USDT`;
  }
  if (v.default_qty_type === "strategy.fixed") {
    return `${v.default_qty_value ?? EMPTY_CELL} 수량`;
  }
  return EMPTY_CELL;
}

interface SummaryRow {
  label: string;
  value: string;
  /** 무데이터 셀일 때 이유. */
  title?: string;
}

export function SetupSummaryAside({
  formValues,
  strategyName,
  formId,
  submitting = false,
  errorCount = 0,
}: SetupSummaryAsideProps) {
  const days = diffDays(formValues.period_start, formValues.period_end);
  const bars = barCount(days, formValues.timeframe);
  const feesPct = formValues.fees_pct;

  const rows: SummaryRow[] = [
    { label: "전략", value: strategyName ?? EMPTY_CELL },
    { label: "심볼", value: formValues.symbol ?? EMPTY_CELL },
    { label: "주기", value: formValues.timeframe ?? EMPTY_CELL },
    {
      label: "기간",
      value:
        formValues.period_start && formValues.period_end
          ? `${formValues.period_start} ~ ${formValues.period_end}${
              days != null ? ` (${days}일)` : ""
            }`
          : EMPTY_CELL,
    },
    {
      label: "봉 수",
      value: bars != null ? `${bars.toLocaleString()}개` : EMPTY_CELL,
      title: bars == null ? "기간과 타임프레임이 정해져야 봉 수를 계산합니다." : undefined,
    },
    { label: "초기 자본", value: formatUsd(formValues.initial_capital) },
    { label: "포지션 사이징", value: summarizePositionSize(formValues) },
    {
      label: "수수료",
      value:
        feesPct != null && Number.isFinite(feesPct)
          ? `테이커 ${formatPct(feesPct)} · 양방향`
          : EMPTY_CELL,
    },
    { label: "슬리피지", value: formatPct(formValues.slippage_pct) },
    {
      label: "체결 시점",
      value: formValues.fill_timing
        ? (FILL_TIMING_LABEL[formValues.fill_timing] ?? EMPTY_CELL)
        : EMPTY_CELL,
    },
    { label: "엔진", value: "바 단위 이벤트 루프" },
  ];

  return (
    <div className="card" data-testid="setup-summary-aside">
      <div className="side-rows">
        {rows.map((r) => (
          <div className="trust-row" key={r.label}>
            <span className="trust-key">{r.label}</span>
            <span className="trust-val" title={r.title} data-testid={`summary-row-${r.label}`}>
              {r.value}
            </span>
          </div>
        ))}
      </div>

      {errorCount > 0 ? (
        <p className="side-warn" role="status" data-testid="summary-validation-warn">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
            <line x1="12" y1="9" x2="12" y2="13.5" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          입력값 {errorCount}건을 확인해야 실행할 수 있습니다.
        </p>
      ) : null}

      <div className="side-actions">
        <button
          className="btn btn-primary btn-block"
          type="submit"
          form={formId}
          disabled={submitting}
          data-testid="backtest-submit"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polygon points="7 4 20 12 7 20 7 4" />
          </svg>
          {submitting ? "요청 중" : "백테스트 실행"}
        </button>
      </div>

      <p className="disclaimer">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="11" x2="12" y2="16" />
          <line x1="12" y1="7.5" x2="12.01" y2="7.5" />
        </svg>
        <span>
          이 요약은 지금 폼에 입력한 값 그대로입니다. 위 가정 중 하나만 바뀌어도 결과는 달라지므로,
          리포트를 읽기 전에 이 목록부터 확인하세요.
        </span>
      </p>
    </div>
  );
}
