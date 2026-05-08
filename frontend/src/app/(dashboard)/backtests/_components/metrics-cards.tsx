// Sprint 32-D BL-156 — MDD 카드에 leverage 가정 inline 표시.
//
// dogfood Day 3 발견: KPI 카드 "MDD -132.96% / -343.15%" 표시. leverage=1
// (현물) 가정 하에서는 수학적으로 MDD ∈ [-100%, 0%] 범위. -100% 초과 시 자본
// 100% 초과 손실 = 사용자 신뢰 quality bar 미달 root cause.
//
// 본 fix: BE 응답의 metrics.mdd_exceeds_capital + config.leverage 를 사용해
// "MDD: -132.96% (leverage 1x · 자본 초과)" 또는 "MDD: -50% (leverage 5x 가정)"
// 형식으로 가정과 수치를 동시 표시. 사용자가 어떤 가정 하에서 어떤 수치인지
// 한 눈에 파악.

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  BacktestConfig,
  BacktestMetricsOut,
} from "@/features/backtest/schemas";
import { formatPercent } from "@/features/backtest/utils";

export interface MetricsCardsProps {
  metrics: BacktestMetricsOut;
  /** Sprint 32-D BL-156: leverage 가정 표시용. null/undefined 시 1x 현물 fallback. */
  config?: BacktestConfig | null;
}

export function MetricsCards({ metrics, config }: MetricsCardsProps) {
  const mddBelowCapital = metrics.max_drawdown < -1;
  const leverage = config?.leverage ?? 1;
  const mddCaption = buildMddCaption({
    leverage,
    mddBelowCapital,
    mddExceedsCapital: metrics.mdd_exceeds_capital ?? null,
  });

  const items = [
    {
      label: "총 수익률",
      value: formatPercent(metrics.total_return),
      caption: null as string | null,
      tone: metrics.total_return >= 0 ? "positive" : "negative",
    },
    {
      label: "Sharpe Ratio",
      value: Number.isFinite(metrics.sharpe_ratio)
        ? metrics.sharpe_ratio.toFixed(2)
        : "—",
      caption: null,
      tone: "neutral",
    },
    {
      label: "Max Drawdown",
      value: formatPercent(metrics.max_drawdown),
      caption: mddCaption,
      tone: "negative",
    },
    {
      label: "Profit Factor",
      value:
        metrics.profit_factor != null
          ? metrics.profit_factor.toFixed(2)
          : "—",
      caption: null,
      tone: "neutral",
    },
    {
      label: "승률 · 거래",
      value: `${formatPercent(metrics.win_rate)} · ${metrics.num_trades}`,
      caption: null,
      tone: "neutral",
    },
  ] as const;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {items.map((it) => {
        // Sprint 43 W7 — prototype 09 KPI tone 색 적용. positive=success / negative=destructive / neutral=text-primary.
        const valueClass =
          it.tone === "positive"
            ? "text-[color:var(--success)]"
            : it.tone === "negative"
              ? "text-[color:var(--destructive)]"
              : "text-[color:var(--text-primary)]";
        return (
          <Card key={it.label} size="sm">
            <CardHeader>
              <CardTitle className="text-xs font-normal uppercase tracking-wide text-muted-foreground">
                {it.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`font-mono text-2xl font-semibold tabular-nums ${valueClass}`}
                data-tone={it.tone}
              >
                {it.value}
              </div>
              {it.caption ? (
                <div
                  className="mt-1 text-[10px] text-muted-foreground"
                  data-testid={
                    it.label === "Max Drawdown" ? "mdd-leverage-caption" : undefined
                  }
                >
                  {it.caption}
                </div>
              ) : null}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

interface MddCaptionInput {
  readonly leverage: number;
  /** 클라이언트 계산: max_drawdown < -1 (= -100%). */
  readonly mddBelowCapital: boolean;
  /** BE 메타: 우선 신뢰 (Sprint 32-D 이후 응답). null 이면 클라이언트 fallback. */
  readonly mddExceedsCapital: boolean | null;
}

/**
 * MDD 카드 보조 caption 빌더.
 *
 * - leverage=1 + MDD ∈ [-100%, 0%] 범위 → 표시 없음 (정상).
 * - leverage>1 → "leverage Nx 가정" inline (자본 대비 손실 한계 N배).
 * - MDD < -100% → "leverage Nx · 자본 초과 손실" 강조 (수학 모순 사용자 인지).
 *
 * BE 의 mdd_exceeds_capital 메타가 있으면 우선 사용 (Sprint 32-D 이후 응답).
 * 없으면 클라이언트에서 max_drawdown 값으로 직접 판정 (legacy 응답 호환).
 */
export function buildMddCaption({
  leverage,
  mddBelowCapital,
  mddExceedsCapital,
}: MddCaptionInput): string | null {
  const exceedsCapital = mddExceedsCapital ?? mddBelowCapital;
  const leverageLabel =
    leverage === 1 ? "leverage 1x · 현물" : `leverage ${leverage.toFixed(1)}x`;

  if (exceedsCapital) {
    // 자본 초과 손실 — 사용자 신뢰 quality bar 의무 표시.
    return `${leverageLabel} · 자본 초과 손실`;
  }
  if (leverage !== 1) {
    return `${leverageLabel} 가정`;
  }
  return null;
}
