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

// PRD `BacktestConfig` dataclass + Bybit Perpetual taker 표준값.
const DEFAULT_FEES = 0.001; // 0.10%
const DEFAULT_SLIPPAGE = 0.0005; // 0.05%

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
}: AssumptionsCardProps) {
  const fees = config?.fees ?? DEFAULT_FEES;
  const slippage = config?.slippage ?? DEFAULT_SLIPPAGE;

  // 실행 가정 열 (variant-c 좌열).
  const execRows: readonly AssumptionRow[] = [
    { label: "엔진", value: ENGINE_LABEL, isDefault: false },
    {
      label: "포지션 모델",
      value: "1x · 롱/숏",
      title: config?.include_funding
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
      value: formatPercent(fees, 2),
      title: "Bybit Perpetual 표준 taker 수수료 (0.10%) 가정",
      isDefault: config?.fees == null,
    },
    {
      label: "슬리피지",
      value: formatPercent(slippage, 3),
      title: "주문 체결 시점 호가창 슬리피지 (평균 0.05%) 가정",
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
