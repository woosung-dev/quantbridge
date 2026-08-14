// 온보딩 백테스트 제출 payload 의 비용 가정 — 낡은 미러를 잡는 회귀 ([BL-730]).
/**
 * ## 왜 이 파일이 있나
 *
 * 온보딩은 `fees_pct`/`slippage_pct` 를 **명시적으로 실어 보낸다**. 그래서 이 값이 낡으면
 * BE 기본값이 아예 안 쓰이고, 사용자가 처음 보는 백테스트가 **왕복 0.30%** 로 돈다 —
 * 실측 왕복은 0.138% 다. [BL-603] 이 2026-08-07 에 값을 좁혔을 때 이 경로가 안 따라왔다.
 *
 * ★**리터럴을 여기 다시 쓰지 않는다.** 이 항목의 원인이 FE 안에서만 리터럴 5벌이었는데,
 * 테스트가 여섯 번째 사본을 만들면 상수가 또 바뀔 때 이 테스트가 **틀린 값을 지킨다**.
 * 그래서 `cost-defaults` 를 import 해 「제출값 == 단일 상수」라는 **계약**을 잰다.
 */

import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_FEES_PCT,
  DEFAULT_SLIPPAGE_PCT,
} from "@/features/backtest/cost-defaults";

const mutate = vi.fn();

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: () => ({ mutate, isPending: false }),
  useBacktestProgress: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

import { Step3Backtest } from "../step-3-backtest";

describe("BL-730 — 온보딩 제출 payload 의 비용 가정", () => {
  beforeEach(() => {
    mutate.mockClear();
  });

  it("제출값이 FE 단일 상수와 같다 (리터럴 하드코딩 금지)", () => {
    render(
      <Step3Backtest
        strategyId="11111111-1111-4111-8111-111111111111"
        onBacktestReady={() => {}}
        onBack={() => {}}
      />,
    );

    expect(mutate).toHaveBeenCalledTimes(1);
    const payload = mutate.mock.calls[0]?.[0];
    expect(payload.fees_pct).toBe(DEFAULT_FEES_PCT);
    expect(payload.slippage_pct).toBe(DEFAULT_SLIPPAGE_PCT);
  });

  it("★음성 대조 — 종전의 낡은 값을 더 이상 보내지 않는다", () => {
    render(
      <Step3Backtest
        strategyId="11111111-1111-4111-8111-111111111111"
        onBacktestReady={() => {}}
        onBack={() => {}}
      />,
    );

    const payload = mutate.mock.calls[0]?.[0];
    // 0.001 / 0.0005 = 왕복 0.30%. 이 두 숫자는 **여기서만** 등장한다 — 「돌아오면 안 되는
    // 값」을 이름 붙여 고정하는 자리이고, 프로덕션 코드에는 남기지 않는다.
    expect(payload.fees_pct).not.toBe(0.001);
    expect(payload.slippage_pct).not.toBe(0.0005);
  });
});
