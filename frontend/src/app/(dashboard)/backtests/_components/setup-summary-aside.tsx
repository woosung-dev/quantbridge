// 백테스트 설정 요약 카드 (우측 1fr) — prototype 08 1:1 visual fidelity (Sprint 42-polish W4-fidelity)
"use client";

const TIMEFRAME_BARS_PER_DAY: Record<string, number> = {
  "1m": 1440,
  "5m": 288,
  "15m": 96,
  "1h": 24,
  "4h": 6,
  "1d": 1,
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
}

export interface SetupSummaryAsideProps {
  formValues: SetupSummaryValues;
  strategyName?: string;
}

function diffDays(start?: string, end?: string): number | null {
  if (!start || !end) return null;
  const s = new Date(`${start}T00:00:00Z`).getTime();
  const e = new Date(`${end}T00:00:00Z`).getTime();
  if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return null;
  return Math.round((e - s) / (1000 * 60 * 60 * 24));
}

function formatUsd(n: number | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `$${Math.round(n).toLocaleString()}`;
}

// 추정 runtime — durationDays 기반 단순 휴리스틱 (BE estimate API 부재 시 placeholder).
// vectorbt 벡터화 가정: ~100일당 0.3초.
function estimateRuntimeSec(days: number | null): string {
  if (days == null) return "~3.2초";
  const sec = Math.max(0.5, (days / 100) * 0.3);
  return `~${sec.toFixed(1)}초`;
}

function summarizePositionSize(v: SetupSummaryValues): string {
  if (v.sizing_source === "live" && v.position_size_pct != null) {
    return `${v.position_size_pct}% (Live)`;
  }
  if (v.default_qty_type === "strategy.percent_of_equity") {
    return `${v.default_qty_value ?? "—"}% (자기자본)`;
  }
  if (v.default_qty_type === "strategy.cash") {
    return `${formatUsd(v.default_qty_value)} (USDT)`;
  }
  if (v.default_qty_type === "strategy.fixed") {
    return `${v.default_qty_value ?? "—"} (수량)`;
  }
  return "—";
}

// 데이터 포인트 = days × bars/day. timeframe 미정 시 null.
function dataPoints(days: number | null, timeframe?: string): number | null {
  if (days == null || !timeframe) return null;
  const bpd = TIMEFRAME_BARS_PER_DAY[timeframe];
  if (bpd == null) return null;
  return days * bpd;
}

// 추정 수수료 = capital × fees_pct × 가정 trade 회전율 (대략 50회/년).
// prototype 의 "~$87" 와 같은 휴리스틱 estimate. capital, fees_pct, days 모두 있을 때만.
function estimateTotalFees(
  capital: number | undefined,
  feesPct: number | undefined,
  days: number | null,
): string {
  if (
    capital == null ||
    !Number.isFinite(capital) ||
    feesPct == null ||
    !Number.isFinite(feesPct) ||
    days == null
  ) {
    return "—";
  }
  // 평균 50 trade/년 가정 + 매 trade 진입+청산 = 2회 fee. capital 전액 회전 가정.
  const yearsApprox = days / 365;
  const tradesEstimate = Math.max(1, yearsApprox * 50);
  const totalFees = capital * feesPct * tradesEstimate * 2;
  return `~${formatUsd(totalFees)}`;
}

export function SetupSummaryAside({
  formValues,
  strategyName,
}: SetupSummaryAsideProps) {
  const days = diffDays(formValues.period_start, formValues.period_end);
  const runtime = estimateRuntimeSec(days);
  const dp = dataPoints(days, formValues.timeframe);
  const expectedFees = estimateTotalFees(
    formValues.initial_capital,
    formValues.fees_pct,
    days,
  );

  // prototype 7 row 정합: 전략 / 심볼 / 기간 / 데이터 포인트 / 초기 자본 / 포지션 사이즈 / 예상 수수료.
  // muted 플래그는 dim 스타일 (예상 수수료처럼 추정값).
  const rows: { label: string; value: string; muted?: boolean }[] = [
    { label: "전략", value: strategyName ?? "—" },
    { label: "심볼", value: formValues.symbol ?? "—" },
    {
      label: "기간",
      value:
        formValues.period_start && formValues.period_end
          ? `${formValues.period_start} ~ ${formValues.period_end}${
              days != null ? ` (${days}일)` : ""
            }`
          : "—",
    },
    {
      label: "데이터 포인트",
      value: dp != null ? dp.toLocaleString() : "—",
    },
    { label: "초기 자본", value: formatUsd(formValues.initial_capital) },
    { label: "포지션 사이즈", value: summarizePositionSize(formValues) },
    { label: "예상 수수료", value: expectedFees, muted: true },
  ];

  return (
    <aside
      className="qb-card-fade-in sticky top-24 flex flex-col gap-3 rounded-[14px] border bg-card p-6 shadow-[var(--card-shadow)]"
      aria-label="백테스트 설정 요약"
      data-testid="setup-summary-aside"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-display text-[1.05rem] font-semibold tracking-tight">
          백테스트 요약
        </h2>
        <span
          className="inline-flex items-center gap-1.5 font-mono text-[0.72rem] font-semibold text-[var(--success)]"
          aria-label="실시간 예상"
        >
          <span
            className="inline-block h-2 w-2 rounded-full bg-[var(--success)]"
            aria-hidden="true"
          />
          실시간 예상
        </span>
      </div>
      <div className="border-t" aria-hidden="true" />
      <dl className="flex flex-col gap-2">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex items-baseline justify-between gap-3"
          >
            <dt className="text-[0.82rem] font-medium text-muted-foreground">
              {r.label}
            </dt>
            <dd
              className={
                r.muted
                  ? "max-w-[60%] truncate text-right font-mono text-[0.85rem] font-medium text-muted-foreground"
                  : "max-w-[60%] truncate text-right font-mono text-[0.85rem] font-medium text-foreground"
              }
              data-testid={`summary-row-${r.label}`}
            >
              {r.value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="border-t" aria-hidden="true" />
      {/* prototype runtime amber 카드 — full bg + border + 큰 폰트 (1.5rem). */}
      <div
        className="flex flex-col gap-1 rounded-[10px] border border-[var(--accent-amber-light)] bg-[var(--accent-amber-light)] px-4 py-4"
        data-testid="summary-runtime-card"
      >
        <p className="text-[0.78rem] font-semibold text-[var(--accent-amber)]">
          예상 실행 시간
        </p>
        <p className="font-mono text-[1.5rem] font-bold leading-none tracking-tight text-[var(--accent-amber)]">
          {runtime}
        </p>
        <p className="text-[0.72rem] font-medium text-muted-foreground">
          vectorbt 벡터화 엔진 사용
        </p>
      </div>
    </aside>
  );
}
