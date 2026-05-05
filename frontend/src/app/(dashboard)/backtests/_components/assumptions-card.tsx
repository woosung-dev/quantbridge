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
    {
      label: "레버리지",
      value: leverage === 1 ? "1x · 현물" : `${leverage.toFixed(1)}x`,
      // Sprint 32-D BL-156: MDD 수학 정합 — leverage 는 *명시적 가정* 으로
      // 노출. pine_v2 엔진은 leverage 를 PnL 에 직접 적용 안 함 (qty=절대
      // 수량). 사용자가 자본 대비 손실 한계 (-100%) 를 초과하는 MDD 를
      // 해석할 때 참고 (>1x 시 자연스럽게 설명 가능).
      title:
        "1x = 현물 매매 가정. >1x = Perpetual 선물 (Bybit/OKX) 가정. " +
        "MDD 가 -100% 초과 시 leverage 가정으로 해석 가능.",
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
      title: "8시간마다 발생하는 무기한 선물 펀딩비 반영 여부",
      isDefault: config?.include_funding == null,
    },
  ];

  // 초기 자본 외 4개 가정 모두 default = BE config 미응답 상태.
  const allAssumptionsDefaulted = items
    .slice(1)
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
