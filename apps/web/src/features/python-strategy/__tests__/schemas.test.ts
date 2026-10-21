import { describe, expect, it } from "vitest";
import { backtestDraft, strategyDraft } from "../defaults";
import {
  PythonBacktestRequestSchema,
  PythonStrategyBodySchema,
  PythonResultSchema,
} from "../schemas";

describe("Python 실험실 입력 계약", () => {
  it("파라미터 JSON을 변환하고 워밍업 입력을 정수로 정규화한다", () => {
    const result = PythonStrategyBodySchema.parse({
      ...strategyDraft(null),
      params_json: '{"period":20,"enabled":true,"label":"EMA","optional":null}',
      warmup_bars: "100",
    });
    expect(result.params).toEqual({ period: 20, enabled: true, label: "EMA", optional: null });
    expect(result.warmup_bars).toBe(100);
    expect(result).not.toHaveProperty("params_json");
  });

  it.each(["{", "[]", "null", '{"period":[20]}', '{"period":{"value":20}}'])(
    "객체의 스칼라 값이 아닌 JSON %s를 거절한다",
    (params_json) => {
      const result = PythonStrategyBodySchema.safeParse({ ...strategyDraft(null), params_json });
      expect(result.success).toBe(false);
      if (!result.success) expect(result.error.issues[0]?.path).toEqual(["params_json"]);
    },
  );

  it("날짜를 UTC 자정으로 변환하고 비용은 소수 문자열을 보존한다", () => {
    const request = PythonBacktestRequestSchema.parse(
      backtestDraft(new Date("2026-10-21T08:00:00Z")),
    );
    expect(request.period_start).toBe("2026-04-21T00:00:00Z");
    expect(request.period_end).toBe("2026-10-21T00:00:00Z");
    expect(request.initial_capital).toBe("10000");
    expect(request.fees).toBe("0.00055");
  });

  it("뒤바뀐 기간·음수 비용·잘못된 자본·비허용 시간봉을 거절한다", () => {
    const draft = backtestDraft();
    for (const change of [
      { period_end: draft.period_start },
      { fees: "-0.001" },
      { fees: "0.02" },
      { initial_capital: "0" },
      { slippage: "NaN" },
      { timeframe: "5m" },
    ]) {
      expect(PythonBacktestRequestSchema.safeParse({ ...draft, ...change }).success).toBe(false);
    }
  });

  it("엔진의 지수 표기 Decimal을 거절하거나 0으로 바꾸지 않는다", () => {
    const result = PythonResultSchema.parse({
      metrics: {
        total_return: "1E-8",
        max_drawdown: "-0.1",
        profit_factor: null,
        num_trades: 0,
        sharpe_ratio: "0",
        total_fees: "0E-8",
        total_slippage: "2E-8",
      },
      trades: [],
      equity_curve: [{ timestamp: "2026-01-01T00:00:00Z", value: "1E4" }],
      provenance: {},
    });
    expect(result.metrics.total_return).toBe("1E-8");
    expect(result.metrics.total_fees).toBe("0E-8");
    expect(result.equity_curve[0]?.value).toBe("1E4");
  });
});
