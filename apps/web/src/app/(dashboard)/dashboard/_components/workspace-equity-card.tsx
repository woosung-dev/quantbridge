"use client";

// 워크스페이스 자산 곡선 카드 (대시보드 §02) — C 디자인 언어 이식.
// 프로토타입 screen-02 §02 "데모 계좌 자산 곡선" 의 카드 골격(card-head/legend/chart-wrap/
// chart-note)을 소비하되, 데이터는 활성 세션 합산 누적 실현 손익(agg.mergedEquityCurve)만
// 그린다. 입금 기준선(프로토타입의 "10,000")은 우리 데이터에 없어 그리지 않는다(정직성 §4.9).
// 차트 축은 equity-chart-config.ts 의 계약을 따른다(선형 축 + 배율 없는 포매터).

import type { ChartPoint } from "@/components/charts/trading-chart";
import { TradingChart } from "@/components/charts/trading-chart";
import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";

import { EQUITY_LINE_OPTIONS, formatEquityAxis } from "./equity-chart-config";

interface WorkspaceEquityCardProps {
  /** 합산 누적 실현 손익 곡선 (epoch seconds, USDT). */
  data: readonly ChartPoint[];
  /** 세션 state 팬아웃이 아직 로딩 중인지. */
  isLoading: boolean;
  /** 활성 세션 수 — 카드 부제·빈 상태 문구에 쓴다. */
  activeSessionCount: number;
  /** 최신 누적 손익 값 (범례 표기용). */
  latestValue: number;
  /**
   * BL-458 — 출처 소계를 신뢰할 수 있는지. `true` 일 때만 "구간별 출처는 여기 표시하지
   * 않는다" 는 고지를 붙인다. 소계 자체가 없으면 그 고지도 근거가 없다.
   */
  hasProvenanceSplit?: boolean;
}

export function WorkspaceEquityCard({
  data,
  isLoading,
  activeSessionCount,
  latestValue,
  hasProvenanceSplit = false,
}: WorkspaceEquityCardProps) {
  // 곡선은 최소 2점 이상이어야 의미가 있다. 1점 이하는 "아직 없음" 으로 본다.
  const hasSeries = data.length >= 2;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">합산 실현 손익 추이</h3>
          <p className="card-sub">
            활성 세션 {activeSessionCount}건의 누적 실현 손익을 시간순으로 합쳐 그립니다. 단위는
            USDT 이며, 세션이 보고한 자산 곡선 지점만 사용합니다.
          </p>
        </div>
      </div>

      <div className="legend">
        <span className="legend-item">
          <span className="legend-key eq" aria-hidden="true" />
          누적 실현 손익{" "}
          <span className="legend-val">{formatEquityAxis(latestValue)}</span>
        </span>
      </div>

      {hasSeries ? (
        <div className="chart-wrap" data-testid="equity-chart">
          <TradingChart
            data={data}
            height={260}
            options={EQUITY_LINE_OPTIONS}
            ariaLabel="활성 세션 합산 누적 실현 손익 곡선. 단위는 USDT, 시작은 0 근방입니다."
          />
        </div>
      ) : isLoading ? (
        <div className="card-body" data-testid="equity-loading">
          <div className="sk-bars" aria-hidden="true">
            {SK_BAR_HEIGHTS.map((h, i) => (
              <span key={i} className="sk" style={{ height: `${h}%` }} />
            ))}
          </div>
          <div className="sk sk-line" style={{ width: "58%" }} aria-hidden="true" />
          <p className="state-note" role="status">
            <ClockIcon />
            세션 자산 곡선을 불러오고 있습니다.
          </p>
        </div>
      ) : (
        <div className="card-body">
          <StateBox
            testId="equity-empty"
            icon={<ChartIcon />}
            title="아직 그릴 손익 곡선이 없습니다."
            body="활성 라이브 세션이 거래를 시작하면 합산 실현 손익 곡선이 여기에 그려집니다."
          />
        </div>
      )}

      <p className="chart-note">
        <InfoIcon />
        세션이 보고한 누적 실현 손익 지점을 시간순으로 병합한 값입니다. 데모 계좌는 Bybit 데모
        환경의 주문 결과이며 실자금이 아닙니다.
        {/* BL-458 — ★포인트별 출처는 이 곡선에 표시할 수 없다. 병합은 각 세션의 마지막
            누적값을 carry-forward 해 더하므로, 한 지점의 값은 대부분 과거 거래에서
            실려온 값의 합이다. 그걸 "이 시점의 출처" 로 칠하면 적극적으로 틀린다.
            그래서 곡선은 집계 수준으로만 고지하고, 구간별 표시는 세션 상세에서 한다. */}
        {hasProvenanceSplit ? (
          <>
            {" "}
            구간별 출처는 이 곡선에 표시하지 않습니다. 병합 지점의 값은 여러 세션의 과거 누적이
            합쳐진 값이라 한 시점의 출처로 칠할 수 없습니다. 확정·추정 구분은 세션 상세에서
            봅니다.
          </>
        ) : null}
      </p>
    </div>
  );
}

// 스켈레톤 막대 높이 — 프로토타입 screen-02 §05 sk-bars 관례(고정 패턴).
const SK_BAR_HEIGHTS = [52, 34, 80, 61, 43, 74, 29, 66];

function ClockIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15.5 14" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="6" y1="20" x2="6" y2="14" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="18" y1="20" x2="18" y2="10" />
    </svg>
  );
}
