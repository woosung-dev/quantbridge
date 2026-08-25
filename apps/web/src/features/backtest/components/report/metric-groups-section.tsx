// 03 상세 지표 — variant-c 지표 묶음 이식. 공용 .metric-groups 를 소비한다.
// 프로토타입 variant-c.html:1280-1324 의 4묶음(수익성/위험/거래 통계/실행 품질) 구조를
// 그대로 옮기되, 값은 BacktestMetricsOut 스키마가 받치는 것만 그린다. 스키마에 필드가 없는
// 연환산 변동성·베타는 무데이터 셀(.metric-value.empty + title) 로 정직하게 남긴다 (§4.9).

"use client";

import { useMemo } from "react";

import { deriveBuyAndHoldMetrics } from "@/features/backtest/analytics";
import { deriveTradeCounts } from "@/features/backtest/trade-counts";
import type { BacktestMetricsOut, EquityPoint } from "@/features/backtest/schemas";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";
import { EMPTY_CELL } from "@/lib/labels";

interface MetricGroupsSectionProps {
  metrics: BacktestMetricsOut;
  /** 벤치마크 초과 파생용 — 없으면 그 셀만 무데이터. */
  buyAndHoldCurve?: readonly EquityPoint[] | null;
  /** 구 실행의 청산 모델 부재와 1배 실행을 구분하는 입력. */
  leverage?: number | null;
}

type Tone = "pos" | "neg" | "neutral";

interface MetricSpec {
  label: string;
  /** null = 스키마 미제공 → 무데이터 셀. */
  value: string | null;
  tone?: Tone;
  /** 무데이터 셀의 사유 (title 속성). */
  emptyTitle?: string;
  /** 값이 있는 셀의 부연. */
  valueTitle?: string;
}

const NOT_COMPUTED = "이 실행에서는 계산되지 않았습니다.";

function signedPct(v: number | null | undefined, digits = 2): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  const sign = v > 0 ? "+" : "";
  return `${sign}${formatPercent(v, digits)}`;
}

function signedCurrency(v: number | null | undefined): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  const sign = v > 0 ? "+" : "";
  return `${sign}${formatCurrency(v)}`;
}

/** avg_holding_hours(시간) → "N일 M시간". 하루 미만이면 "M시간". */
function formatHoldingDuration(hours: number | null | undefined): string | null {
  if (hours == null || !Number.isFinite(hours)) return null;
  const totalHours = Math.round(hours);
  const days = Math.floor(totalHours / 24);
  const rem = totalHours % 24;
  if (days === 0) return `${rem}시간`;
  return `${days}일 ${rem}시간`;
}

function fixed(v: number | null | undefined, digits = 2): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  return v.toFixed(digits);
}

export function MetricGroupsSection({
  metrics: m,
  buyAndHoldCurve,
  leverage,
}: MetricGroupsSectionProps) {
  // 벤치마크 초과(%p) = 전략 총 수익률 - 매수 후 보유 수익률. BH 커브가 있어야 파생 가능.
  const excessPct = useMemo(() => {
    if (!buyAndHoldCurve || buyAndHoldCurve.length < 2) return null;
    const bh = deriveBuyAndHoldMetrics(buyAndHoldCurve.map((p) => p.value));
    if (bh === null) return null;
    return m.total_return - bh.returnPct;
  }, [buyAndHoldCurve, m.total_return]);
  const sharpe = describeSharpe(m.sharpe_convention, m.sharpe_ratio);

  const profitability: MetricSpec[] = [
    {
      label: "총 수익률",
      value: signedPct(m.total_return),
      tone: m.total_return >= 0 ? "pos" : "neg",
    },
    {
      label: "연환산 수익률",
      value: signedPct(m.annual_return_pct),
      tone: (m.annual_return_pct ?? 0) >= 0 ? "pos" : "neg",
    },
    {
      label: "순손익",
      value: signedCurrency(m.net_profit_abs),
      tone: (m.net_profit_abs ?? 0) >= 0 ? "pos" : "neg",
    },
    { label: "총 이익", value: signedCurrency(m.gross_profit_abs), tone: "pos" },
    {
      label: "총 손실",
      value: signedCurrency(m.gross_loss_abs != null ? -Math.abs(m.gross_loss_abs) : null),
      tone: "neg",
    },
    {
      label: "수익 팩터",
      value: fixed(m.profit_factor),
      emptyTitle: "손실 거래가 없어 수익 팩터를 계산할 수 없습니다.",
    },
  ];

  const risk: MetricSpec[] = [
    { label: "최대 낙폭", value: signedPct(m.max_drawdown), tone: "neg" },
    {
      label: "최대 낙폭 지속",
      value: m.drawdown_duration != null ? `${m.drawdown_duration} bars` : null,
    },
    {
      label: "샤프 지수",
      value: sharpe.display,
      valueTitle: sharpe.foot,
    },
    { label: "소르티노 지수", value: fixed(m.sortino_ratio) },
    { label: "칼마 지수", value: fixed(m.calmar_ratio) },
    // 연환산 변동성은 응답 스키마에 대응 필드가 없다 → 항상 무데이터 셀 (§4.9).
    { label: "연환산 변동성", value: null, emptyTitle: NOT_COMPUTED },
  ];

  // BL-822 — 「거래 수」(미청산 포함)와 「완료 거래」(승률 분모)를 각각의 이름으로 인쇄한다.
  // 한 이름을 둘이 쓰던 동안 「총 거래 수 13 · 승률 16.67%」가 곱해서 정수가 안 나왔다.
  const counts = deriveTradeCounts(m);
  const tradeStats: MetricSpec[] = [
    {
      label: "총 거래 수",
      value: String(counts.total),
      valueTitle:
        counts.open > 0
          ? `미청산 ${counts.open}건을 포함한 수입니다. 거래 목록의 행 수와 같습니다.`
          : undefined,
    },
    {
      label: "완료 거래",
      value: String(counts.completed),
      valueTitle: "진입·청산이 모두 끝난 거래입니다. 아래 승률의 분모입니다.",
    },
    {
      label: "승률",
      value: formatPercent(m.win_rate),
      valueTitle: `완료 거래 ${counts.completed}건 기준입니다.`,
    },
    { label: "평균 수익", value: signedCurrency(m.avg_win_abs), tone: "pos" },
    {
      label: "평균 손실",
      value: signedCurrency(m.avg_loss_abs != null ? -Math.abs(m.avg_loss_abs) : null),
      tone: "neg",
    },
    { label: "손익비", value: fixed(m.ratio_avg_win_loss) },
    { label: "평균 보유 기간", value: formatHoldingDuration(m.avg_holding_hours) },
  ];

  const execution: MetricSpec[] = [
    {
      label: "최대 연속 승",
      value: m.consecutive_wins_max != null ? String(m.consecutive_wins_max) : null,
    },
    {
      label: "최대 연속 패",
      value: m.consecutive_losses_max != null ? String(m.consecutive_losses_max) : null,
    },
    {
      label: "총 수수료",
      value: signedCurrency(m.total_fees != null ? -Math.abs(m.total_fees) : null),
      tone: "neg",
    },
    {
      label: "슬리피지 비용",
      value: signedCurrency(m.total_slippage != null ? -Math.abs(m.total_slippage) : null),
      tone: "neg",
    },
    {
      label: "벤치마크 초과",
      value: excessPct != null ? `${signedPct(excessPct)}p` : null,
      tone: (excessPct ?? 0) >= 0 ? "pos" : "neg",
      emptyTitle: "매수 후 보유 곡선이 없어 초과 수익을 계산할 수 없습니다.",
    },
    {
      label: "강제청산",
      value: m.liquidation_count != null ? `${m.liquidation_count}건` : null,
      emptyTitle:
        leverage != null && leverage > 1
          ? "이 실행 시점에는 청산 모델이 없었습니다(구 실행)."
          : "레버리지 1배 실행에는 마진 모델이 적용되지 않습니다.",
      valueTitle: "플랫 유지증거금률 0.5% · 단일 tier · 격리마진 · Bybit 기준.",
    },
    // 베타는 이 실행에서 계산하지 않는다 → 무데이터 셀 (variant-c.html:1320 과 동일).
    { label: "베타", value: null, emptyTitle: NOT_COMPUTED },
  ];

  const groups: ReadonlyArray<{ title: string; rows: MetricSpec[] }> = [
    { title: "수익성", rows: profitability },
    { title: "위험", rows: risk },
    { title: "거래 통계", rows: tradeStats },
    { title: "실행 품질", rows: execution },
  ];

  return (
    <div className="card" data-testid="metric-groups-section">
      <div className="metric-groups">
        {groups.map((g) => (
          <div className="metric-group" key={g.title}>
            <p className="metric-group-title">{g.title}</p>
            {g.rows.map((row) => (
              <MetricRow key={row.label} spec={row} />
            ))}
          </div>
        ))}
      </div>
      <p className="metric-note">
        총수익률은 기말 미청산 평가손익·펀딩을 반영하고, 순손익은 실현분만 집계합니다.
      </p>
    </div>
  );
}

function MetricRow({ spec }: { spec: MetricSpec }) {
  const toneClass =
    spec.value == null
      ? "metric-value empty"
      : spec.tone === "pos"
        ? "metric-value pos"
        : spec.tone === "neg"
          ? "metric-value neg"
          : "metric-value";
  return (
    <div className="metric">
      <span className="metric-label">{spec.label}</span>
      <span className={toneClass} title={spec.value == null ? spec.emptyTitle : spec.valueTitle}>
        {spec.value ?? EMPTY_CELL}
      </span>
    </div>
  );
}
