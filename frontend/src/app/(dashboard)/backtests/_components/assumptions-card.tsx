// Sprint 30-α (Surface Hardening): 백테스트 가정 박스.
// PRD `backtests.config` JSONB 5 필드 (initial_capital / leverage / fees / slippage /
// include_funding) 를 결과 페이지 Overview 탭 상단에 노출. 차별화 (현실적 시뮬레이션)
// 의 시각적 대표 — 사용자가 결과 수치가 어떤 가정으로 계산되었는지 즉각 인지.
//
// 본 sprint 30-α scope: BE 응답에 `config` 필드 미포함 시 표준 가정값으로 graceful
// degrade. Sprint 30-γ-BE 에서 BacktestDetail.config JSONB 노출 후 자동 upgrade.
//
// Sprint 31 BL-162a — 사용자 입력 활성화 (TradingView strategy 속성 패턴). 사용자가
// BacktestForm 에서 leverage/fees/slippage/include_funding 입력 시 BE 가 그 값을
// 그대로 응답 → AssumptionsCard 가 (기본) 마크 자동 제거 (graceful upgrade).
//
// LESSON-004: render body 에서 ref/state 변경 없음. props → 파생값만 계산.

import type { BacktestConfig } from "@/features/backtest/schemas";
import { formatPercent } from "@/features/backtest/utils";

// PRD `BacktestConfig` dataclass + Bybit Perpetual taker 표준값.
const DEFAULT_LEVERAGE = 1.0;
const DEFAULT_FEES = 0.001; // 0.10%
const DEFAULT_SLIPPAGE = 0.0005; // 0.05%
const DEFAULT_INCLUDE_FUNDING = true;

interface AssumptionRow {
  readonly label: string;
  readonly value: string;
  readonly title: string;
  readonly isDefault: boolean;
}

export interface AssumptionsCardProps {
  /** BE 응답 `initial_capital` 을 number 로 (Decimal → str → transform 후). */
  readonly initialCapital: number;
  /**
   * BE `BacktestDetail.config` JSONB. Sprint 30-α 시점 BE 미응답 → null/undefined.
   * Sprint 30-γ-BE 에서 BE 가 응답에 포함하면 graceful upgrade.
   */
  readonly config?: BacktestConfig | null;
}

export function AssumptionsCard({
  initialCapital,
  config,
}: AssumptionsCardProps) {
  const leverage = config?.leverage ?? DEFAULT_LEVERAGE;
  const fees = config?.fees ?? DEFAULT_FEES;
  const slippage = config?.slippage ?? DEFAULT_SLIPPAGE;
  const includeFunding = config?.include_funding ?? DEFAULT_INCLUDE_FUNDING;

  const items: readonly AssumptionRow[] = [
    {
      label: "초기 자본",
      value: `${initialCapital.toLocaleString("en-US", {
        maximumFractionDigits: 0,
      })} USDT`,
      title: "백테스트 시작 시점의 가용 자본",
      isDefault: false,
    },
    // Sprint 37 BL-185: Spot-equivalent visible row. tooltip 만으론 사용자가
    // 못 봄 → 결과 해석 시 가장 먼저 인지하도록 visible row 로 노출 (codex 권장).
    {
      label: "포지션 모델",
      value: "Spot-equivalent",
      title:
        "Sprint 37 BL-185: Pine strategy(default_qty_type=...) 3종 (percent_of_equity / cash / fixed) " +
        "사용. 레버리지 효과는 초기 자본 배수로 우회 가능 (예: 5x ≈ initial_capital × 5). " +
        "funding rate / 강제 청산 / 유지 증거금 미반영 (BL-186 후속).",
      isDefault: false,
    },
    {
      label: "레버리지",
      value: leverage === 1 ? "1x · 현물" : `${leverage.toFixed(1)}x`,
      // Sprint 32-D BL-156: MDD 수학 정합 — leverage 는 *명시적 가정* 으로 노출.
      // Sprint 37 BL-185: Spot-equivalent 모델 채택 — leverage 는 PnL 엔진 계산에
      // 미반영 (응답 노출만). 사용자가 5x 효과를 보려면 initial_capital × 5 우회.
      // BL-186 후속 풀 모델에서 funding/mm rate/liquidation 정확 시뮬레이션 예정.
      title:
        "Spot-equivalent 가정. 현재 PnL 엔진 미반영 (응답 노출만). " +
        "레버리지 효과 시뮬레이션은 initial_capital 배수로 우회 가능. " +
        "BL-186 후속 풀 모델에서 funding/유지 증거금/강제 청산 정확 반영 예정.",
      isDefault: config?.leverage == null,
    },
    {
      label: "수수료",
      value: formatPercent(fees, 2),
      title: "Bybit/OKX Perpetual 표준 taker 수수료 (0.10%) 가정",
      isDefault: config?.fees == null,
    },
    {
      label: "슬리피지",
      value: formatPercent(slippage, 3),
      title: "주문 체결 시점 호가창 슬리피지 (평균 0.05%) 가정",
      isDefault: config?.slippage == null,
    },
    {
      label: "펀딩비 반영",
      value: includeFunding ? "ON" : "OFF",
      // Sprint 37 BL-185: 현재 미반영 (Spot-equivalent). BL-186 후속 풀 모델에서
      // 8h 주기 funding rate 정확 시뮬레이션 예정.
      title:
        "현재 미반영 (Spot-equivalent 가정). BL-186 후속 풀 모델에서 8h 주기 " +
        "funding rate 정확 시뮬레이션 예정.",
      isDefault: config?.include_funding == null,
    },
  ];

  // BE config 응답 여부 판단: 초기 자본 (사용자 입력) + 포지션 모델 (Sprint 37 고정)
  // 외 4개 가정 (레버리지/수수료/슬리피지/펀딩) 모두 default = BE config 미응답.
  const allAssumptionsDefaulted = items
    .slice(2)
    .every((it) => it.isDefault);

  return (
    <section
      aria-label="백테스트 가정"
      className="rounded-xl border bg-muted/30 px-4 py-3"
    >
      <header className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium">백테스트 가정</h2>
        {allAssumptionsDefaulted ? (
          <span
            className="text-xs text-muted-foreground"
            data-testid="assumptions-default-notice"
          >
            ⓘ 표준 가정값 (BE config 미응답)
          </span>
        ) : null}
      </header>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3 lg:grid-cols-5">
        {items.map((it) => (
          <div key={it.label} className="flex flex-col gap-0.5">
            <dt
              className="flex items-center gap-1 text-muted-foreground"
              title={it.title}
            >
              <span>{it.label}</span>
              {it.isDefault ? (
                <span
                  className="text-[10px] text-muted-foreground/60"
                  aria-label="기본 가정값"
                >
                  (기본)
                </span>
              ) : null}
            </dt>
            <dd className="font-mono text-sm font-medium tabular-nums">
              {it.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
