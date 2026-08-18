// 활성 세션 계정 잔고 카드의 계약 상태를 검증한다.
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAccountBalances } from "@/features/trading/hooks";

vi.mock("@/features/trading/hooks", () => ({
  useAccountBalances: vi.fn(),
}));

import { AccountBalanceSection } from "../account-balance-section";

const account = {
  id: "a0000000-0000-4000-8000-000000000001",
  label: "Bybit Demo",
};
const mockBalances = vi.mocked(useAccountBalances);

function query(data: unknown, overrides: Record<string, unknown> = {}) {
  return { data, isLoading: false, isError: false, ...overrides } as never;
}

beforeEach(() => {
  mockBalances.mockReturnValue([]);
});

describe("AccountBalanceSection", () => {
  it("활성 세션 계정이 없으면 빈 상태를 표시한다", () => {
    render(<AccountBalanceSection accounts={[]} />);
    expect(screen.getByTestId("account-balance-empty")).toHaveTextContent("활성 라이브 세션이 없습니다.");
  });

  it("총 자산·사용 가능 값과 0~100으로 clamp된 미터를 표시한다", () => {
    mockBalances.mockReturnValue([
      query({
        account_id: account.id,
        asset: "USDT",
        supported: true,
        reason: null,
        total: "100",
        free: "150",
        fetched_at: "2026-07-24T12:00:00Z",
      }),
    ]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.getByTestId(`balance-total-${account.id}`)).toHaveTextContent("100 USDT");
    expect(screen.getByTestId(`balance-free-${account.id}`)).toHaveTextContent("150 USDT");
    expect(screen.getByTestId(`balance-meter-${account.id}`)).toHaveAttribute(
      "aria-label",
      "사용 가능 잔고 100%",
    );
  });

  it("total이 null이면 미터 대신 확인 불가를 표시한다", () => {
    mockBalances.mockReturnValue([
      query({
        account_id: account.id,
        asset: "USDT",
        supported: true,
        reason: null,
        total: null,
        free: "10",
        fetched_at: null,
      }),
    ]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.queryByTestId(`balance-meter-${account.id}`)).not.toBeInTheDocument();
    expect(screen.getAllByText("확인 불가")).toHaveLength(2);
  });

  it("total이 0이면 0% 미터를 표시한다", () => {
    mockBalances.mockReturnValue([
      query({
        account_id: account.id,
        asset: "USDT",
        supported: true,
        reason: null,
        total: "0",
        free: "0",
        fetched_at: null,
      }),
    ]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.getByTestId(`balance-meter-${account.id}`)).toHaveAttribute(
      "aria-label",
      "사용 가능 잔고 0%",
    );
  });

  it("미지원 계정은 백엔드 사유를 표시한다", () => {
    mockBalances.mockReturnValue([
      query({
        account_id: account.id,
        asset: "USDT",
        supported: false,
        reason: "Bybit 계정만 지원합니다.",
        total: null,
        free: null,
        fetched_at: null,
      }),
    ]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.getByText("Bybit 계정만 지원합니다.")).toBeInTheDocument();
  });

  it("로딩 중에는 미지원 문구 대신 불러오는 중만 표시한다", () => {
    mockBalances.mockReturnValue([query(undefined, { isLoading: true })]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.getAllByText("불러오는 중")).toHaveLength(2);
    expect(screen.queryByText("잔고 조회를 지원하지 않습니다.")).not.toBeInTheDocument();
  });

  // 2026-08-18 — 프로토타입 screen-01:1171-1197 의 1카드-1지표 관례.
  it("계정 잔고와 사용 가능은 각각의 .card.kpi 로 분리해 그린다", () => {
    mockBalances.mockReturnValue([
      query({
        account_id: account.id,
        asset: "USDT",
        supported: true,
        reason: null,
        total: "100",
        free: "80",
        fetched_at: null,
      }),
    ]);
    const { container } = render(<AccountBalanceSection accounts={[account]} />);

    const cards = container.querySelectorAll(".card.kpi");
    expect(cards).toHaveLength(2);
    // 한 카드에 label→value 쌍이 하나씩만 있다.
    expect(cards[0]!.querySelectorAll(".kpi-label")).toHaveLength(1);
    expect(cards[1]!.querySelectorAll(".kpi-label")).toHaveLength(1);
    expect(cards[0]!.querySelector(".kpi-label")?.textContent).toBe("계정 잔고");
    expect(cards[1]!.querySelector(".kpi-label")?.textContent).toBe("사용 가능");
  });

  // 로딩은 본문 텍스트가 아니라 §01 형제 KPI 들과 같은 StatValue(.kpi-na) 규율이다.
  it("로딩 표기는 StatValue 관례(.kpi-na)를 쓴다", () => {
    mockBalances.mockReturnValue([query(undefined, { isLoading: true })]);
    render(<AccountBalanceSection accounts={[account]} />);

    for (const el of screen.getAllByText("불러오는 중")) {
      expect(el).toHaveClass("kpi-na");
    }
  });

  it("조회 실패는 미지원이 아니라 실패 문구로 표시한다", () => {
    mockBalances.mockReturnValue([query(undefined, { isError: true })]);
    render(<AccountBalanceSection accounts={[account]} />);

    expect(screen.getByText("잔고를 불러오지 못했습니다.")).toBeInTheDocument();
    expect(screen.queryByText("잔고 조회를 지원하지 않습니다.")).not.toBeInTheDocument();
  });
});
