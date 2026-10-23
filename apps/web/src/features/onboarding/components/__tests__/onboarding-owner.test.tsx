import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  auth: { userId: "user-a" as string | null, isSignedIn: true as boolean | undefined },
  mutate: vi.fn(),
}));

vi.mock("@/hooks/use-auth-ctx", () => ({ useAuthCtx: () => mocks.auth }));
vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: () => ({ mutate: mocks.mutate, isPending: false }),
  useBacktestProgress: () => ({ data: undefined, isLoading: false }),
}));
vi.mock("../step-2-strategy", () => ({ Step2Strategy: () => null }));
vi.mock("../step-4-result", () => ({ Step4Result: () => null }));

import { createInitialState, useOnboardingStore } from "@/features/onboarding/store";
import { OnboardingView } from "../onboarding-view";

const STRATEGY_A = "11111111-1111-4111-8111-111111111111";
const requests: { userId: string | null; strategyId: string }[] = [];

function persistBacktest(ownerUserId?: string, startedAt = Date.now()) {
  window.localStorage.setItem(
    "qb-onboarding-v1",
    JSON.stringify({
      version: 1,
      state: {
        ...(ownerUserId ? { ownerUserId } : {}),
        step: "backtest",
        strategyId: STRATEGY_A,
        backtestId: null,
        startedAt,
      },
    }),
  );
}

beforeEach(() => {
  useOnboardingStore.setState(createInitialState());
  window.localStorage.removeItem("qb-onboarding-v1");
  mocks.auth.userId = "user-a";
  mocks.auth.isSignedIn = true;
  requests.length = 0;
  mocks.mutate.mockReset();
  mocks.mutate.mockImplementation((body: { strategy_id: string }) => {
    requests.push({ userId: mocks.auth.userId, strategyId: body.strategy_id });
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.removeItem("qb-onboarding-v1");
});

describe("온보딩 owner 렌더 경계", () => {
  it("A의 3단계는 복원하지만 B 전환 시 A ID를 요청하지 않고 초기화한다", async () => {
    persistBacktest("user-a");
    const view = render(<OnboardingView />);
    await waitFor(() => expect(requests).toEqual([{ userId: "user-a", strategyId: STRATEGY_A }]));

    mocks.auth.userId = "user-b";
    view.rerender(<OnboardingView />);
    await screen.findByText("QuantBridge 에 오신 것을 환영합니다");
    expect(useOnboardingStore.getState()).toMatchObject({
      ownerUserId: "user-b",
      step: "welcome",
      strategyId: null,
      backtestId: null,
    });
    expect(requests.filter((request) => request.userId === "user-b")).toEqual([]);
  });

  it.each(["user-a", undefined])(
    "B가 %s owner의 저장값으로 마운트해도 자동 요청은 없다",
    async (owner) => {
      persistBacktest(owner);
      mocks.auth.userId = "user-b";
      render(<OnboardingView />);
      await screen.findByText("QuantBridge 에 오신 것을 환영합니다");
      expect(mocks.mutate).not.toHaveBeenCalled();
      expect(useOnboardingStore.getState().ownerUserId).toBe("user-b");
      expect(useOnboardingStore.getState().strategyId).toBeNull();
    },
  );

  it("인증 조회 중 SSR 사용자 ID가 있어도 자동 실행 자식을 마운트하지 않는다", async () => {
    persistBacktest("user-a");
    mocks.auth.isSignedIn = undefined;
    const view = render(<OnboardingView />);
    await act(async () => {});
    expect(screen.queryByText("백테스트 실행")).not.toBeInTheDocument();
    expect(mocks.mutate).not.toHaveBeenCalled();
    mocks.auth.userId = "user-b";
    mocks.auth.isSignedIn = true;
    view.rerender(<OnboardingView />);
    await screen.findByText("QuantBridge 에 오신 것을 환영합니다");
    expect(mocks.mutate).not.toHaveBeenCalled();
  });

  it("같은 owner라도 만료한 3단계를 자동 요청 전에 비운다", async () => {
    persistBacktest("user-a", Date.now() - 6 * 60 * 1000);
    render(<OnboardingView />);
    await screen.findByText("QuantBridge 에 오신 것을 환영합니다");
    expect(mocks.mutate).not.toHaveBeenCalled();
  });

  it("저장소 복원 도중 B로 전환해도 뒤늦은 A 진행도를 실행하지 않는다", async () => {
    let finishHydration: () => void = () => {};
    vi.spyOn(useOnboardingStore.persist, "rehydrate").mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finishHydration = () => {
            useOnboardingStore.setState({
              ownerUserId: "user-a",
              step: "backtest",
              strategyId: STRATEGY_A,
              startedAt: Date.now(),
            });
            resolve();
          };
        }),
    );
    const view = render(<OnboardingView />);
    mocks.auth.userId = "user-b";
    view.rerender(<OnboardingView />);
    expect(mocks.mutate).not.toHaveBeenCalled();
    await act(async () => finishHydration());
    await screen.findByText("QuantBridge 에 오신 것을 환영합니다");
    expect(mocks.mutate).not.toHaveBeenCalled();
    expect(useOnboardingStore.getState().strategyId).toBeNull();
  });
});
