// 백테스트 설정 요약 카드 (우측 1fr) — 실시간 form watch
"use client";

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

function formatPct(n: number | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(2)}%`;
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

export function SetupSummaryAside({
  formValues,
  strategyName,
}: SetupSummaryAsideProps) {
  const days = diffDays(formValues.period_start, formValues.period_end);
  const runtime = estimateRuntimeSec(days);

  const rows: { label: string; value: string }[] = [
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
    { label: "포지션 사이즈", value: summarizePositionSize(formValues) },
    {
      label: "초기 자본",
      value: formatUsd(formValues.initial_capital),
    },
    { label: "수수료", value: formatPct(formValues.fees_pct) },
    { label: "슬리피지", value: formatPct(formValues.slippage_pct) },
  ];

  return (
    <aside
      className="sticky top-24 flex flex-col gap-4 rounded-xl border bg-card p-5"
      aria-label="백테스트 설정 요약"
      data-testid="setup-summary-aside"
    >
      <h2 className="font-display text-base font-semibold">백테스트 요약</h2>
      <dl className="flex flex-col gap-2">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex items-baseline justify-between gap-3 text-sm"
          >
            <dt className="text-muted-foreground">{r.label}</dt>
            <dd
              className="text-right font-medium"
              data-testid={`summary-row-${r.label}`}
            >
              {r.value}
            </dd>
          </div>
        ))}
      </dl>
      <div
        className="rounded-r-md border-l-4 border-[var(--accent-amber)] bg-[var(--accent-amber-light)] px-3 py-2.5"
        data-testid="summary-runtime-card"
      >
        <p className="text-xs text-muted-foreground">예상 실행 시간</p>
        <p className="font-mono text-base font-semibold text-[var(--accent-amber)]">
          {runtime}
        </p>
        <p className="text-xs text-muted-foreground">vectorbt 벡터화 엔진</p>
      </div>
    </aside>
  );
}
