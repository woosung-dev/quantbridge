// 대시보드 자산 곡선 축 계약 단위 테스트 (S7) — BL-407 실증 부류.
// 못박는 것 둘.
//   1. y축 라벨 포매터가 값에 배율을 곱이지 않는다 (percent 함정 회피 — 절대 USDT 값).
//   2. 축 모드가 로그·백분율이 아니다 (절대값 곡선은 선형 Normal 고정).
// lightweight-charts v4 는 percent 타입을 써도 ×100 하지 않고 minMove 를 무시한 채 precision
// 을 양자화한다. 이 곡선은 반대로 어떤 배율도 곱이면 안 되므로 custom formatter 로 못박는다.

import { describe, expect, it } from "vitest";

import { CHART_PALETTE_FALLBACK } from "@/lib/chart-tokens";

import {
  EQUITY_LINE_OPTIONS,
  EQUITY_PRICE_SCALE_MODE,
  FORBIDDEN_EQUITY_SCALE_MODES,
  PRICE_SCALE_MODE,
  formatEquityAxis,
} from "../equity-chart-config";

// priceFormat 은 union 타입이라 테스트용으로 좁혀 읽는다.
interface CustomPriceFormatShape {
  type?: string;
  formatter?: (value: number) => string;
  minMove?: number;
}

describe("자산 곡선 축 포매터 — 배율을 곱이지 않는다", () => {
  it("입력값을 그대로 소수 2자리로 찍는다 (×100 하지 않는다)", () => {
    expect(formatEquityAxis(1)).toBe("1.00");
    expect(formatEquityAxis(100)).toBe("100.00");
    expect(formatEquityAxis(10412.66)).toBe("10,412.66");
  });

  it("음수와 0 도 배율 없이 찍는다", () => {
    expect(formatEquityAxis(-142.18)).toBe("-142.18");
    expect(formatEquityAxis(0)).toBe("0.00");
  });

  it("반증 — percent 함정(×100)이 있었다면 100 이 '10,000.00' 이 됐을 것이다", () => {
    // ×100 배율이 스며들면 100 → 10000. 그렇지 않음을 확인한다.
    expect(formatEquityAxis(100)).not.toBe("10,000.00");
    // 1 → "1.00" 이지 "100.00" 이 아니다 (백분율 재정규화 부재).
    expect(formatEquityAxis(1)).not.toBe("100.00");
  });

  it("비유한값은 '0.00' 폴백 (NaN/Infinity 라벨 오염 차단)", () => {
    expect(formatEquityAxis(Number.NaN)).toBe("0.00");
    expect(formatEquityAxis(Number.POSITIVE_INFINITY)).toBe("0.00");
  });
});

describe("자산 곡선 라인 series 옵션 — percent 아님", () => {
  const pf = EQUITY_LINE_OPTIONS.priceFormat as CustomPriceFormatShape;

  it("priceFormat.type 이 'custom' 이고 'percent' 가 아니다", () => {
    expect(pf.type).toBe("custom");
    expect(pf.type).not.toBe("percent");
  });

  it("formatter 가 배율 없는 포매터(formatEquityAxis)와 동일 출력을 낸다", () => {
    expect(typeof pf.formatter).toBe("function");
    expect(pf.formatter?.(10412.66)).toBe("10,412.66");
    expect(pf.formatter?.(100)).toBe("100.00");
  });

  it("색은 chart-tokens SSOT(equity 폴백)에서 온다", () => {
    expect(EQUITY_LINE_OPTIONS.color).toBe(CHART_PALETTE_FALLBACK.equity);
    expect(EQUITY_LINE_OPTIONS.lineWidth).toBe(2);
  });
});

describe("자산 곡선 축 모드 계약 — 로그·백분율 금지", () => {
  it("계약 모드가 Normal(=0) 이다", () => {
    expect(EQUITY_PRICE_SCALE_MODE).toBe(PRICE_SCALE_MODE.NORMAL);
    expect(EQUITY_PRICE_SCALE_MODE).toBe(0);
  });

  it("계약 모드가 로그도 백분율도 아니다", () => {
    expect(EQUITY_PRICE_SCALE_MODE).not.toBe(PRICE_SCALE_MODE.LOGARITHMIC);
    expect(EQUITY_PRICE_SCALE_MODE).not.toBe(PRICE_SCALE_MODE.PERCENTAGE);
  });

  it("금지 모드 집합이 로그·백분율·IndexedTo100 을 담고 Normal 은 담지 않는다", () => {
    expect(FORBIDDEN_EQUITY_SCALE_MODES).toContain(PRICE_SCALE_MODE.LOGARITHMIC);
    expect(FORBIDDEN_EQUITY_SCALE_MODES).toContain(PRICE_SCALE_MODE.PERCENTAGE);
    expect(FORBIDDEN_EQUITY_SCALE_MODES).toContain(PRICE_SCALE_MODE.INDEXED_TO_100);
    expect(FORBIDDEN_EQUITY_SCALE_MODES).not.toContain(EQUITY_PRICE_SCALE_MODE);
  });
});
