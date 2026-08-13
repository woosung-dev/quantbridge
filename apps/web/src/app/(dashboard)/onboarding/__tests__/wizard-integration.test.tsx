import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type Mock,
} from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Hoisted mocks — vi.mock factories 가 module import 전에 평가되므로
// vi.hoisted 로 mock function 참조를 선공유.
// ---------------------------------------------------------------------------

const hoisted = vi.hoisted(() => {
  return {
    createMutate: vi.fn(),
    createIsPending: { value: false },
    backtestMutate: vi.fn(),
    backtestIsPending: { value: false },
    progressData: { value: null as unknown },
    backtestData: { value: null as unknown },
  };
});

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: "test-user",
    getToken: async () => "test-token",
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/features/strategy/hooks", () => ({
  useCreateStrategy: (opts?: {
    onSuccess?: (data: { id: string }) => void;
    onError?: (err: Error) => void;
  }) => ({
    mutate: (
      body: unknown,
      options?: {
        onSuccess?: (data: { id: string }) => void;
        onError?: (err: Error) => void;
      },
    ) => {
      hoisted.createMutate(body, options);
      // default: tests override via hoisted.createMutate.mockImplementation
    },
    isPending: hoisted.createIsPending.value,
    opts,
  }),
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: (opts?: {
    onSuccess?: (data: { backtest_id: string }) => void;
    onError?: (err: Error) => void;
  }) => ({
    mutate: (body: unknown) => {
      hoisted.backtestMutate(body);
      // 테스트에서 필요 시 hoisted.backtestMutate.mockImplementation 로 제어.
    },
    isPending: hoisted.backtestIsPending.value,
    opts,
  }),
  useBacktestProgress: () => ({
    data: hoisted.progressData.value,
    isError: false,
    isLoading: false,
  }),
  useBacktest: () => ({
    data: hoisted.backtestData.value,
    isError: false,
    isLoading: false,
  }),
}));

// fetch stub — public/samples/ema-crossover.pine 로드 시뮬레이션.
const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// ---------------------------------------------------------------------------
// Under-test imports — mocks 이후에 import 해야 replacement 적용.
// ---------------------------------------------------------------------------

import OnboardingPage from "../page";
import {
  createInitialState,
  useOnboardingStore,
} from "@/features/onboarding/store";

function resetStoreAndMocks() {
  useOnboardingStore.setState(createInitialState());
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("qb-onboarding-v1");
  }
  hoisted.createMutate.mockReset();
  hoisted.backtestMutate.mockReset();
  hoisted.progressData.value = null;
  hoisted.backtestData.value = null;
  hoisted.createIsPending.value = false;
  hoisted.backtestIsPending.value = false;
  fetchMock.mockReset();
}

describe("OnboardingPage — 4-step wizard integration", () => {
  beforeEach(() => {
    resetStoreAndMocks();
  });
  afterEach(() => {
    cleanup();
  });

  it("step 전진/후진: setStep 호출 시 렌더 패널이 바뀐다", () => {
    render(<OnboardingPage />);
    // 초기 welcome panel 이 렌더
    const panel = screen.getByTestId("onboarding-step-panel");
    expect(panel.getAttribute("data-step")).toBe("welcome");
    expect(screen.getByText(/QuantBridge 에 오신 것을 환영합니다/)).toBeInTheDocument();

    // 시작하기 → strategy step
    fireEvent.click(
      screen.getByRole("button", { name: /다음 단계로 진행/ }),
    );
    expect(
      screen.getByTestId("onboarding-step-panel").getAttribute("data-step"),
    ).toBe("strategy");

    // 뒤로 버튼 → welcome
    fireEvent.click(screen.getByRole("button", { name: /← 이전/ }));
    expect(
      screen.getByTestId("onboarding-step-panel").getAttribute("data-step"),
    ).toBe("welcome");
  });

  it("샘플 Pine load 성공 시 strategyId 를 store 에 저장하고 backtest step 으로 이동", async () => {
    // fetch 는 pine 원문을 반환.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: async () => "//@version=5\nstrategy('EMA Demo')",
    });

    // createStrategy mutate 가 호출되면 onSuccess 를 즉시 실행해 id 를 전달.
    const FIXED_STRATEGY_ID = "11111111-2222-4333-8444-555555555555";
    (hoisted.createMutate as Mock).mockImplementation(
      (
        _body: unknown,
        options?: { onSuccess?: (d: { id: string }) => void },
      ) => {
        options?.onSuccess?.({ id: FIXED_STRATEGY_ID });
      },
    );

    // welcome → strategy 로 진입시키고 시작
    useOnboardingStore.getState().setStep("strategy");
    render(<OnboardingPage />);

    const triggerBtn = screen.getByRole("button", {
      name: /샘플 전략 등록 및 다음 단계/,
    });

    // fetch → setState 체인이 React state 를 갱신하므로 act 로 감쌈.
    await act(async () => {
      fireEvent.click(triggerBtn);
      // fetch microtask + text() microtask flush
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/samples/ema-crossover.pine",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(hoisted.createMutate).toHaveBeenCalled();

    const state = useOnboardingStore.getState();
    expect(state.strategyId).toBe(FIXED_STRATEGY_ID);
    expect(state.step).toBe("backtest");
  });

  it("5분 TTL 만료 시 mount 시점에 welcome step 으로 reset", () => {
    // 진행 중 상태를 시뮬레이션 (strategy step, strategyId 세팅, startedAt 과거)
    useOnboardingStore.setState({
      step: "backtest",
      strategyId: "11111111-2222-4333-8444-555555555555",
      backtestId: null,
      startedAt: Date.now() - 6 * 60 * 1000, // 6분 전 → TTL 초과
    });

    render(<OnboardingPage />);

    const state = useOnboardingStore.getState();
    expect(state.step).toBe("welcome");
    expect(state.strategyId).toBeNull();
    expect(state.backtestId).toBeNull();
    // welcome panel 이 실제로 렌더되었는지도 확인
    expect(
      screen.getByTestId("onboarding-step-panel").getAttribute("data-step"),
    ).toBe("welcome");
  });
});
