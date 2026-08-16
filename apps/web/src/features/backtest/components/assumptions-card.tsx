"use client";

// 08 실행 조건 — variant-c "가정과 데이터 출처" 이식. 공용 .trust-grid/.trust-row/.disclaimer 를 소비한다.
// 프로토타입 variant-c.html:1587-1609 의 2열(실행 가정 / 데이터·비용) 구조. 봉 개수·결측 봉·소요 시간은
// BacktestDetail 스키마에 대응 필드가 없어 그리지 않는다(§4.9). 고지 문구는 프로토타입의 "샘플 데이터"
// 카피가 아니라 실데이터 화면의 정직한 가설적 결과 고지를 유지한다(카피 재설계 아님, 도메인 정합).
//
// LESSON-004: render body 에서 ref/state 변경 없음. props → 파생값만 계산.

import { AlertTriangle } from "lucide-react";

import { InfoIcon } from "@/components/info-icon";
import type { BacktestConfig } from "@/features/backtest/schemas";
import { formatDate, formatDateTime, formatPercent } from "@/features/backtest/utils";
import { DEFAULT_FEES_PCT, DEFAULT_SLIPPAGE_PCT } from "@/features/backtest/cost-defaults";

// PRD `BacktestConfig` dataclass 기본값의 거울이다. ★BL-603(2026-08-07) — 종전 값은
// 거래소 공시 표준가에서 온 추정치였고, 라이브 원장 실측(taker 0.055%/leg · 진입가 잔차
// 중앙 0.014%)으로 교체했다. 백엔드 `engine/types.py` + `backtest/schemas.py` 와 **셋이
// 같이 움직여야 한다** — 여기만 낡으면 화면이 반증된 가정을 계속 주장한다.
// ★[BL-730] — 값은 `features/backtest/cost-defaults.ts` 가 갖는다. 여기서 베끼지 않는다.
const DEFAULT_FEES = DEFAULT_FEES_PCT;
const DEFAULT_SLIPPAGE = DEFAULT_SLIPPAGE_PCT;

// 엔진은 도메인 상수 — 바 단위 이벤트 루프 (ADR-011, 벡터화 아님). 내부 모듈명(pine_v2)은
// no-internal-ids 가드에 따라 노출 카피에서 제외하고, backtest-list/코크핏 칩과 같은 문구를 쓴다.
const ENGINE_LABEL = "바 단위 이벤트 루프";

interface AssumptionRow {
  readonly label: string;
  readonly value: string;
  readonly title?: string;
  readonly isDefault: boolean;
}

export interface AssumptionsCardProps {
  readonly initialCapital: number;
  readonly config?: BacktestConfig | null;
  readonly totalFees?: number | null;
  readonly totalSlippage?: number | null;
  readonly totalFunding?: number | null;
  readonly fundingDataIncomplete?: boolean | null;
  /** 데이터·기간 열 파생용 (BacktestDetail 에서 shell 이 전달). 없으면 그 행 미렌더. */
  readonly periodStart?: string | null;
  readonly periodEnd?: string | null;
  readonly ranAt?: string | null;
  /**
   * 엔진이 이 실행에 대해 남긴 경고 (2026-08-15 surface-truth · U8).
   *
   * ★서버는 이 값을 **계산하고 있었는데** 아무도 받지 않았다 — 엔진 주석이 스스로
   * 「사용자가 silent success 받지 않도록 노출」이라 적어 뒀는데 소비자가 0건이었다.
   * 지정가 진입처럼 **백테스트와 라이브가 다르게 행동하는** 경우가 여기로 나온다.
   *
   * ★`null`(이 컬럼 이전 실행 = 모른다)과 `[]`(경고 없이 돌았다)는 다른 값이다.
   * 둘 다 아무것도 그리지 않지만, 「모른다」를 「없다」로 바꿔 말하지 않기 위해 구분을 유지한다.
   */
  readonly warnings?: readonly string[] | null;
}

function formatUsdt(v: number): string {
  return `${v.toLocaleString("en-US", { maximumFractionDigits: 2 })} USDT`;
}

function daysBetween(startIso: string, endIso: string): number | null {
  const s = new Date(startIso).getTime();
  const e = new Date(endIso).getTime();
  if (!Number.isFinite(s) || !Number.isFinite(e) || e < s) return null;
  return Math.round((e - s) / (24 * 60 * 60 * 1000));
}

export function AssumptionsCard({
  initialCapital,
  config,
  totalFees,
  totalSlippage,
  totalFunding,
  fundingDataIncomplete,
  periodStart,
  periodEnd,
  ranAt,
  warnings,
}: AssumptionsCardProps) {
  const fees = config?.fees ?? DEFAULT_FEES;
  const slippage = config?.slippage ?? DEFAULT_SLIPPAGE;
  const leverage = config?.leverage ?? 1;
  const hasMarginModel = leverage > 1;

  // 실행 가정 열 (variant-c 좌열).
  const execRows: readonly AssumptionRow[] = [
    { label: "엔진", value: ENGINE_LABEL, isDefault: false },
    {
      label: "포지션 모델",
      value: hasMarginModel ? `${leverage}x · 롱/숏 · 격리마진` : "1x · 롱/숏",
      title: hasMarginModel
        ? "플랫 유지증거금률 0.5% · 단일 tier · Bybit 기준 강제청산 반영. tier 계단·파산수수료 미반영. 펀딩 비용은 8시간 정산 주기로 차감."
        : config?.include_funding
          ? "강제 청산 / 유지 증거금 미반영. 펀딩 비용은 8시간 정산 주기로 차감 (총 펀딩 행 참조)."
          : "1x 비레버리지. 롱/숏 모두 가능 (자기자본 한도 내). " +
            "전략의 수량 지정 3종 (자본 비율 / 현금 / 고정 수량) 사용. " +
            "펀딩 비용 / 강제 청산 / 유지 증거금 미반영.",
      isDefault: false,
    },
    {
      label: "체결 타이밍",
      value:
        (config?.fill_timing ?? "bar_close") === "next_bar_open"
          ? "다음 봉 시가 (TV 정합)"
          : "신호 봉 종가",
      title:
        "시장가 주문 체결 시점. TradingView 기본은 다음 봉 시가 " +
        "(process_orders_on_close=false), QuantBridge 기본은 신호 봉 종가.",
      isDefault: config?.fill_timing == null,
    },
    {
      label: "수수료",
      // ★소수 2자리로는 0.055% 가 "0.06%" 로 반올림돼 실측값이 화면에서 사라진다.
      value: formatPercent(fees, 3),
      title: "Bybit demo 원장 실측 taker 수수료 (leg 당 0.055%) 가정",
      isDefault: config?.fees == null,
    },
    {
      label: "슬리피지",
      value: formatPercent(slippage, 3),
      title: "체결 진입가 잔차 실측 (매칭쌍 중앙 0.014%) 가정",
      isDefault: config?.slippage == null,
    },
  ];

  // 데이터·비용 열 (variant-c 우열). 스키마가 받치는 값만.
  const dataRows: AssumptionRow[] = [
    {
      label: "초기 자본",
      value: `${initialCapital.toLocaleString("en-US", { maximumFractionDigits: 0 })} USDT`,
      isDefault: false,
    },
  ];
  if (periodStart != null && periodEnd != null) {
    const d = daysBetween(periodStart, periodEnd);
    dataRows.push({
      label: "기간",
      value: `${formatDate(periodStart)} ~ ${formatDate(periodEnd)}${d != null ? ` (${d}일)` : ""}`,
      isDefault: false,
    });
  }
  if (ranAt != null) {
    dataRows.push({ label: "실행 시각", value: formatDateTime(ranAt), isDefault: false });
  }
  if (totalFees != null) {
    dataRows.push({ label: "총 수수료", value: formatUsdt(totalFees), isDefault: false });
  }
  if (totalSlippage != null) {
    dataRows.push({ label: "총 슬리피지", value: formatUsdt(totalSlippage), isDefault: false });
  }
  if (totalFunding != null) {
    dataRows.push({
      label: "총 펀딩",
      value: formatUsdt(totalFunding),
      title: "8시간 정산 주기 무기한 선물 펀딩비 순액. 양수 = 지불, 음수 = 수취 (Bybit 실측 rate 기반)",
      isDefault: false,
    });
  }

  // 수수료 + 슬리피지 모두 default = BE config 미응답.
  const allAssumptionsDefaulted = execRows
    .slice(3)
    .every((it) => it.isDefault);

  return (
    <section className="card" aria-label="백테스트 가정">
      {allAssumptionsDefaulted ? (
        <div className="card-head">
          <span
            className="card-sub assumptions-notice"
            data-testid="assumptions-default-notice"
          >
            <InfoIcon />
            표준 가정값 (BE config 미응답)
          </span>
        </div>
      ) : null}

      <div className="trust-grid">
        <div className="trust-col">
          {execRows.map((row) => (
            <TrustRow key={row.label} row={row} />
          ))}
        </div>
        <div className="trust-col">
          {dataRows.map((row) => (
            <TrustRow key={row.label} row={row} />
          ))}
        </div>
      </div>

      <p className="disclaimer" data-testid="backtest-honesty-note">
        <InfoIcon />
        <span>
          가설적 결과입니다. 후행 데이터로 계산되며 위 수수료·슬리피지가 차감된 순(net)
          수치입니다. 체결 가정. 시장가는 현재 봉 종가, 지정가·스톱은 다음 봉 이후 트리거가에
          체결됩니다.
        </span>
      </p>

      {fundingDataIncomplete === true ? (
        <p className="disclaimer report-note-warn" data-testid="backtest-funding-incomplete-note">
          <AlertTriangle aria-hidden="true" />
          <span>
            펀딩 비용 미반영 구간이 있습니다. funding 데이터 가용 범위(최근 Bybit BTC/ETH)
            밖의 보유 구간은 펀딩비가 차감되지 않았습니다. 해당 구간 손익은 펀딩 비용만큼 낙관
            편향일 수 있습니다.
          </span>
        </p>
      ) : null}

      {warnings != null && warnings.length > 0 ? (
        <div className="disclaimer report-note-warn" data-testid="backtest-engine-warnings">
          <AlertTriangle aria-hidden="true" />
          <div>
            <p>
              이 실행에서 엔진이 남긴 알림입니다. 숫자를 읽기 전에 먼저 보세요.
            </p>
            {/*
             * ★건수를 세지 않는다 (2026-08-15 적대 리뷰 P3). 서버는 서로 다른 경고가 상한
             * (50건)을 넘으면 **합성 요약 한 줄**("… N건이 더 있습니다")을 배열 끝에 붙인다.
             * 그 배열 길이를 「엔진이 남긴 알림 수」로 말하면 **51건**이라 거짓이다(실제 60).
             * 잘렸다는 사실은 그 마지막 줄이 스스로 말하므로, 화면은 세지 말고 그대로 인쇄한다.
             */}
            <ul>
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </section>
  );
}

/** trust-key 는 라벨 텍스트 노드 + (기본) 마크를 함께 담고 title 을 갖는다. */
function TrustRow({ row }: { row: AssumptionRow }) {
  return (
    <div className="trust-row">
      <span className="trust-key" title={row.title}>
        <span>{row.label}</span>
        {row.isDefault ? (
          <span className="dim" aria-label="기본 가정값">
            {" "}
            (기본)
          </span>
        ) : null}
      </span>
      <span className="trust-val">{row.value}</span>
    </div>
  );
}
