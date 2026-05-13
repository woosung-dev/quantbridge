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

  // Sprint 37 BL-187a: leverage / include_funding row 제거 (사용자 명시 — 일단 빼기).
  // BE 응답에는 그대로 노출 (graceful upgrade 보존). FE 표시만 simplify.
  // BL-186 후속 풀 모델 (funding/mm rate/liquidation) 도래 시 두 row 재노출 검토.
  void leverage;
  void includeFunding;

  const items: readonly AssumptionRow[] = [
    {
      label: "초기 자본",
      value: `${initialCapital.toLocaleString("en-US", {
        maximumFractionDigits: 0,
      })} USDT`,
      title: "백테스트 시작 시점의 가용 자본",
      isDefault: false,
    },
    // Sprint 37 BL-185 → BL-187a: 라벨 simplify ("Spot-equivalent" → "1x · 롱/숏").
    // 사용자가 "Spot" 단어를 "현물 = 롱만" 으로 오해 — 실제는 롱/숏 모두 가능.
    {
      label: "포지션 모델",
      value: "1x · 롱/숏",
      title:
        "1x 비레버리지. 롱/숏 모두 가능 (자기자본 한도 내). " +
        "Pine strategy(default_qty_type=...) 3종 (percent_of_equity / cash / fixed) 사용. " +
        "funding rate / 강제 청산 / 유지 증거금 미반영.",
      isDefault: false,
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
  ];

  // BE config 응답 여부 판단: 초기 자본 (사용자 입력) + 포지션 모델 (Sprint 37 고정)
  // 외 2개 가정 (수수료 / 슬리피지) 모두 default = BE config 미응답.
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
