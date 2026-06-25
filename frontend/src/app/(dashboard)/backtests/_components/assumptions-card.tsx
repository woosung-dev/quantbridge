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
  /**
   * C14 (정직성) — metrics.total_fees / total_slippage 절대 총비용 (USDT).
   * 헤드라인 수치가 net 임을 숨길 수 없는 line item 으로 노출. 구 백테스트
   * (totals 미저장) 는 null/undefined → 행 미렌더 (backward-compat).
   */
  readonly totalFees?: number | null;
  readonly totalSlippage?: number | null;
  /**
   * C6 (정직성) — metrics.funding_data_incomplete. perp funding 차감 시 보유 구간
   * 일부가 funding 데이터 가용 범위(인제스션 forward-only — 최근 Bybit BTC/ETH) 밖이면
   * true → "펀딩 비용 미반영 구간 있음" 정직 고지. false=전 구간 반영, null/undefined=
   * funding 미반영(include_funding=false / 구 백테스트) → 둘 다 미렌더.
   */
  readonly fundingDataIncomplete?: boolean | null;
}

function formatUsdt(v: number): string {
  return `${v.toLocaleString("en-US", { maximumFractionDigits: 2 })} USDT`;
}

export function AssumptionsCard({
  initialCapital,
  config,
  totalFees,
  totalSlippage,
  fundingDataIncomplete,
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

  // C14 (정직성) — 절대 총비용 행. metrics totals 가 있을 때만 노출 (구 백테스트 호환).
  const costItems: { label: string; value: string }[] = [];
  if (totalFees != null) {
    costItems.push({ label: "총 수수료", value: formatUsdt(totalFees) });
  }
  if (totalSlippage != null) {
    costItems.push({ label: "총 슬리피지", value: formatUsdt(totalSlippage) });
  }

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
        {costItems.map((it) => (
          <div key={it.label} className="flex flex-col gap-0.5">
            <dt className="text-muted-foreground">{it.label}</dt>
            <dd className="font-mono text-sm font-medium tabular-nums">
              {it.value}
            </dd>
          </div>
        ))}
      </dl>
      {/* C14 (정직성) — 가설적 결과 + 순(net) + 체결 가정 상시 고지. */}
      <p
        data-testid="backtest-honesty-note"
        className="mt-2 border-t pt-2 text-[11px] leading-relaxed text-muted-foreground"
      >
        ⚠ 가설적 결과입니다. 후행 데이터로 계산되며 위 수수료·슬리피지가 차감된 순(net)
        수치입니다. 체결 가정 — 시장가는 현재 봉 종가, 지정가·스톱은 다음 봉 이후
        트리거가에 체결됩니다.
      </p>
      {/* C6 (정직성) — funding 데이터가 보유 구간 일부를 못 덮을 때만 표시. "결측"
          (혼란) 대신 *왜* 미반영인지 설명. include_funding=false / 미반영 시 미렌더. */}
      {fundingDataIncomplete === true ? (
        <p
          data-testid="backtest-funding-incomplete-note"
          className="mt-2 text-[11px] leading-relaxed text-amber-600 dark:text-amber-500"
        >
          ⚠ 펀딩 비용 미반영 구간 있음 — funding 데이터 가용 범위(최근 Bybit
          BTC/ETH) 밖의 보유 구간은 펀딩비가 차감되지 않았습니다. 해당 구간 손익은
          펀딩 비용만큼 낙관 편향일 수 있습니다.
        </p>
      ) : null}
    </section>
  );
}
