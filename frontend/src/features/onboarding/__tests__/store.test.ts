import { beforeEach, describe, expect, it } from "vitest";

import {
  createInitialState,
  isExpired,
  maybeExpireAndReset,
  nextStep,
  prevStep,
  selectBacktestId,
  selectStep,
  selectStrategyId,
  useOnboardingStore,
} from "@/features/onboarding/store";
import { ONBOARDING_TTL_MS } from "@/features/onboarding/types";

const FIXED_STRATEGY_ID = "11111111-2222-4333-8444-555555555555";
const FIXED_BACKTEST_ID = "66666666-7777-4888-9999-aaaaaaaaaaaa";

function resetStore() {
  useOnboardingStore.setState(createInitialState());
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("qb-onboarding-v1");
  }
}

describe("useOnboardingStore — step 전진/후진", () => {
  beforeEach(() => {
    resetStore();
  });

  it("초기 상태는 welcome step + null ids", () => {
    const s = useOnboardingStore.getState();
    expect(selectStep(s)).toBe("welcome");
    expect(selectStrategyId(s)).toBeNull();
    expect(selectBacktestId(s)).toBeNull();
  });

  it("setStep 으로 welcome → strategy → backtest → result 전진, reset 으로 welcome 복귀", () => {
    useOnboardingStore.getState().setStep("strategy");
    expect(selectStep(useOnboardingStore.getState())).toBe("strategy");

    useOnboardingStore.getState().setStep("backtest");
    expect(selectStep(useOnboardingStore.getState())).toBe("backtest");

    useOnboardingStore.getState().setStep("result");
    expect(selectStep(useOnboardingStore.getState())).toBe("result");

    useOnboardingStore.getState().reset();
    const s = useOnboardingStore.getState();
    expect(selectStep(s)).toBe("welcome");
    expect(selectStrategyId(s)).toBeNull();
    expect(selectBacktestId(s)).toBeNull();
    expect(s.startedAt).toBe(0);
  });

  it("setStrategy / setBacktest 가 id 를 저장하고 startedAt 을 1회만 찍는다", () => {
    const before = Date.now();
    useOnboardingStore.getState().setStrategy(FIXED_STRATEGY_ID);
    const firstStartedAt = useOnboardingStore.getState().startedAt;
    expect(firstStartedAt).toBeGreaterThanOrEqual(before);
    expect(selectStrategyId(useOnboardingStore.getState())).toBe(
      FIXED_STRATEGY_ID,
    );

    // 이후 호출은 startedAt 을 덮어쓰지 않는다 (세션 수명 기준).
    useOnboardingStore.getState().setBacktest(FIXED_BACKTEST_ID);
    expect(useOnboardingStore.getState().startedAt).toBe(firstStartedAt);
    expect(selectBacktestId(useOnboardingStore.getState())).toBe(
      FIXED_BACKTEST_ID,
    );
  });

  it("nextStep / prevStep 이 경계에서 clamp 된다", () => {
    expect(nextStep("welcome")).toBe("strategy");
    expect(nextStep("strategy")).toBe("backtest");
    expect(nextStep("backtest")).toBe("result");
    expect(nextStep("result")).toBe("result"); // clamp

    expect(prevStep("result")).toBe("backtest");
    expect(prevStep("backtest")).toBe("strategy");
    expect(prevStep("strategy")).toBe("welcome");
    expect(prevStep("welcome")).toBe("welcome"); // clamp
  });
});

describe("useOnboardingStore — 5분 TTL 만료 시 자동 reset", () => {
  beforeEach(() => {
    resetStore();
  });

  it("isExpired: startedAt=0 은 만료 아님 (세션 미시작)", () => {
    expect(isExpired(0, Date.now())).toBe(false);
  });

  it("isExpired: 5분 초과 시 true, 이내는 false", () => {
    const start = 1_000_000;
    expect(isExpired(start, start + ONBOARDING_TTL_MS - 1)).toBe(false);
    expect(isExpired(start, start + ONBOARDING_TTL_MS + 1)).toBe(true);
  });

  it("maybeExpireAndReset: TTL 초과면 store 를 welcome 으로 reset", () => {
    // 진행 중 상태 세팅
    useOnboardingStore.getState().setStep("backtest");
    useOnboardingStore.getState().setStrategy(FIXED_STRATEGY_ID);
    // startedAt 을 과거(6 분 전)로 강제 조정
    useOnboardingStore.setState({ startedAt: Date.now() - 6 * 60 * 1000 });

    const expired = maybeExpireAndReset();
    expect(expired).toBe(true);

    const s = useOnboardingStore.getState();
    expect(selectStep(s)).toBe("welcome");
    expect(selectStrategyId(s)).toBeNull();
    expect(selectBacktestId(s)).toBeNull();
    expect(s.startedAt).toBe(0);
  });

  it("maybeExpireAndReset: TTL 이내면 reset 하지 않음", () => {
    useOnboardingStore.getState().setStep("backtest");
    useOnboardingStore.getState().setStrategy(FIXED_STRATEGY_ID);

    const expired = maybeExpireAndReset();
    expect(expired).toBe(false);

    const s = useOnboardingStore.getState();
    expect(selectStep(s)).toBe("backtest");
    expect(selectStrategyId(s)).toBe(FIXED_STRATEGY_ID);
  });
});
