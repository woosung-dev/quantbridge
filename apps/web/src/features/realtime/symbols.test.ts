// Bybit ticker 심볼 변환의 백엔드 쌍둥이 계약을 검증한다.
import { describe, expect, it } from "vitest";

import { toBybitTickerSymbol } from "./symbols";

describe("toBybitTickerSymbol", () => {
  it.each([
    ["BTC/USDT", "BTCUSDT"],
    ["BTC/USDT:USDT", "BTCUSDT"],
    ["SOL/USDT", "SOLUSDT"],
  ])("%s를 %s로 변환한다", (symbol, expected) => {
    expect(toBybitTickerSymbol(symbol)).toBe(expected);
  });
});
