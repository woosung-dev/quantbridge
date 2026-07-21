// 새 백테스트 설정 C 디자인 언어 구조 + 상태 4종 렌더 테스트 — 이식 W3-A (screen-05).
// 시맨틱 구조(setup-grid · 번호 섹션 · calc-strip · side-rows)와 스켈레톤/에러/빈/무데이터 셀을 검증한다.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "@/app/(dashboard)/backtests/_components/forms/backtest-form";

// useStrategies 반환을 케이스별로 바꾼다 (로딩/에러/빈/로드).
type StrategiesReturn = {
  data?: { items: Array<{ id: string; name: string; parse_status: string }> };
  isLoading?: boolean;
  isError?: boolean;
  refetch?: () => void;
};
let mockStrategies: StrategiesReturn = {
  data: { items: [{ id: "abc", name: "MA Crossover Strategy", parse_status: "ok" }] },
};

let mockSearchParams = new URLSearchParams("strategy_id=abc");

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => mockStrategies,
  useStrategy: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

beforeEach(() => {
  mockSearchParams = new URLSearchParams("strategy_id=abc");
  mockStrategies = {
    data: { items: [{ id: "abc", name: "MA Crossover Strategy", parse_status: "ok" }] },
  };
});

afterEach(() => {
  cleanup();
});

describe("BacktestForm — C 디자인 언어 시맨틱 구조 (W3-A)", () => {
  it("셸: setup-grid 2단 + h1 동사형 + 헤더 칩 + 번호 섹션 01/02/03/04", () => {
    const { container } = render(<BacktestForm />);

    expect(container.querySelector("main.page")).not.toBeNull();
    // 헤더: report-title h1 은 5축 규약상 동사형
    expect(
      screen.getByRole("heading", { level: 1, name: "새 백테스트 실행" }),
    ).toBeInTheDocument();
    // 헤더 칩 + 요약 행에 엔진 문구 (accent 칩 포함). 내부 모듈명(pine_v2)은 UI 에 노출하지 않는다.
    expect(
      screen.getAllByText("바 단위 이벤트 루프").length,
    ).toBeGreaterThan(0);
    // 거래소는 Bybit 고정 (앱 화면 상한 §4.8)
    const bybitChips = screen.getAllByText("Bybit");
    expect(bybitChips.length).toBeGreaterThan(0);

    // 2단 레이아웃
    const layout = screen.getByTestId("backtest-form-layout");
    expect(layout.className).toMatch(/setup-grid/);
    expect(container.querySelector("form.setup-main")).not.toBeNull();
    expect(container.querySelector("aside.setup-side")).not.toBeNull();

    // 번호 아이브로 01~04 (03 진단은 unbacked API 라 드롭, 요약이 04)
    const eyebrows = Array.from(container.querySelectorAll(".eyebrow .num")).map(
      (e) => e.textContent,
    );
    expect(eyebrows).toEqual(["01", "02", "03", "04"]);
  });

  it("계산 요약(calc-strip): 기간과 봉 수를 순수 파생으로 렌더한다", () => {
    const { container } = render(<BacktestForm />);
    const strip = container.querySelector(".calc-strip");
    expect(strip).not.toBeNull();
    // 기본 기간(180일)과 1h 봉이 채워져 있어 두 셀 모두 값이 있다.
    const values = Array.from(strip!.querySelectorAll(".calc-value")).map(
      (e) => e.textContent,
    );
    expect(values[0]).toMatch(/일$/);
    expect(values[1]).toMatch(/개$/);
  });

  it("요약 사이드(side-rows): 엔진·심볼 등 백드 행 + 제출 버튼(form 연결)", () => {
    const { container } = render(<BacktestForm />);
    expect(container.querySelector(".side-rows")).not.toBeNull();
    expect(screen.getByTestId("summary-row-엔진")).toHaveTextContent(
      "바 단위 이벤트 루프",
    );
    const submit = screen.getByTestId("backtest-submit");
    expect(submit.getAttribute("form")).toBe("backtest-setup-form");
  });

  it("상태 1 · 스켈레톤: 전략 목록 로딩 중", () => {
    mockStrategies = { isLoading: true };
    render(<BacktestForm />);
    expect(screen.getByTestId("strategy-select-skeleton")).toBeInTheDocument();
  });

  it("상태 2 · 에러: 전략 목록 조회 실패 → role=alert + 실제 엔드포인트 + 재시도", () => {
    const refetch = vi.fn();
    mockStrategies = { isError: true, refetch };
    render(<BacktestForm />);
    const box = screen.getByTestId("strategy-select-error");
    expect(box).toBeInTheDocument();
    expect(box.getAttribute("role")).toBe("alert");
    expect(box).toHaveTextContent("GET /api/v1/strategies · 503");
    fireEvent.click(screen.getByText("다시 시도"));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("상태 3 · 빈 상태: 저장된 전략 없음 → 새 전략 만들기 CTA", () => {
    mockStrategies = { data: { items: [] } };
    render(<BacktestForm />);
    const box = screen.getByTestId("strategy-select-empty");
    expect(box).toBeInTheDocument();
    expect(box).toHaveTextContent("저장된 전략이 없습니다.");
    const cta = screen.getByText("새 전략 만들기");
    expect(cta.getAttribute("href")).toBe("/strategies/new");
  });

  it("상태 4 · 무데이터 셀: 종료일을 비우면 calc-strip 기간이 무데이터(—) + title", async () => {
    const { container } = render(<BacktestForm />);
    await act(async () => {
      fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "" } });
    });
    const emptyCell = container.querySelector(".calc-value.empty");
    expect(emptyCell).not.toBeNull();
    expect(emptyCell!.textContent).toBe("—");
    expect(emptyCell!.getAttribute("title")).toMatch(/기간을 계산/);
  });
});
