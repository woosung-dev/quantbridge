// C 이식 S6 — TradeDetailTable 4상태(스켈레톤/에러/빈/데이터) + 페이저 + 방향 라벨 검증.

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";

import { TradeDetailTable } from "@/features/backtest/components/trades/trade-detail-table";

const tradeRangeChartMock = vi.hoisted(() => vi.fn());

vi.mock("@/features/backtest/components/trades/trade-range-chart", () => ({
  TradeRangeChart: tradeRangeChartMock,
}));

const ENDPOINT = "GET /api/v1/backtests/abcd1234/trades";

function mkTrade(idx: number, pnl = 10): TradeItem {
  return {
    trade_index: idx,
    direction: "long",
    status: "closed",
    entry_time: `2026-01-${String(idx).padStart(2, "0")}T00:00:00Z`,
    exit_time: `2026-01-${String(idx).padStart(2, "0")}T01:00:00Z`,
    entry_price: 100,
    exit_price: 110,
    size: 1,
    pnl,
    return_pct: 0.05,
    fees: 0.1,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

beforeEach(() => {
  tradeRangeChartMock.mockReset();
  tradeRangeChartMock.mockImplementation(() => (
    <div data-testid="trade-range-chart">구간 가격</div>
  ));
});

describe("TradeDetailTable — 4상태", () => {
  it("로딩 → 스켈레톤 렌더 (표 미노출)", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    expect(screen.getByTestId("trade-skeleton")).toBeInTheDocument();
    // 스켈레톤은 aria-hidden 이므로 a11y 트리에서 table 은 숨겨진다.
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByTestId("trade-empty")).not.toBeInTheDocument();
  });

  it("에러 → state-box(alert) + 메시지 + 엔드포인트", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading={false}
        isError
        errorMessage="500 server"
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    const box = screen.getByTestId("trade-error");
    expect(box).toHaveAttribute("role", "alert");
    expect(screen.getByText(/500 server/)).toBeInTheDocument();
    expect(screen.getByText(ENDPOINT)).toBeInTheDocument();
  });

  it("빈 상태(필터 없음) → trade-empty state-box(status)", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    const box = screen.getByTestId("trade-empty");
    expect(box).toHaveAttribute("role", "status");
    // 필터 없으면 초기화 버튼 미표시
    expect(screen.queryByTestId("trade-empty-reset")).not.toBeInTheDocument();
  });

  it("데이터 → 방향 셀은 S4 라벨(롱), 원시 enum(long) 미노출", () => {
    render(
      <TradeDetailTable
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    // side 칩은 한국어 라벨 (표 안에서). "롱" 은 방향 필터 option 에도 있으므로 표로 스코프.
    const table = screen.getByRole("table");
    expect(within(table).getByText("롱")).toBeInTheDocument();
    // 표 셀에 원시 enum "long" 이 노출되지 않는다 (data-direction 속성은 허용)
    expect(within(table).queryByText("long")).not.toBeInTheDocument();
  });

  it("행 expand 토글 — aria-expanded 변경 + 상세 3그룹 노출", () => {
    render(
      <TradeDetailTable
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    const expandBtn = screen.getByLabelText("거래 #1 상세 보기");
    expect(expandBtn).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("trade-detail-expanded")).not.toBeInTheDocument();

    fireEvent.click(expandBtn);

    const closeBtn = screen.getByLabelText("거래 #1 상세 닫기");
    expect(closeBtn).toHaveAttribute("aria-expanded", "true");
    const expanded = screen.getByTestId("trade-detail-expanded");
    expect(within(expanded).getByText("진입 정보")).toBeInTheDocument();
    expect(within(expanded).getByText("청산 정보")).toBeInTheDocument();
    expect(within(expanded).getByText("성과")).toBeInTheDocument();
  });

  it("backtestId가 있으면 확장 시 거래 구간 차트를 연결한다", () => {
    render(
      <TradeDetailTable
        backtestId="11111111-1111-4111-8111-111111111111"
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );

    fireEvent.click(screen.getByLabelText("거래 #1 상세 보기"));

    expect(screen.getByTestId("trade-range-chart")).toBeInTheDocument();
    expect(tradeRangeChartMock.mock.calls[0]?.[0]).toMatchObject({
      backtestId: "11111111-1111-4111-8111-111111111111",
      tradeIndex: 1,
    });
  });

  it("backtestId가 없으면 확장해도 거래 구간 차트를 만들지 않는다", () => {
    render(
      <TradeDetailTable
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );

    fireEvent.click(screen.getByLabelText("거래 #1 상세 보기"));

    expect(screen.queryByTestId("trade-range-chart")).not.toBeInTheDocument();
    expect(tradeRangeChartMock).not.toHaveBeenCalled();
  });

  it("row click → expand 토글 (button stopPropagation 으로 button 단독 클릭도 정상)", () => {
    render(
      <TradeDetailTable
        trades={[mkTrade(1, 100)]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    expect(screen.queryByTestId("trade-detail-expanded")).not.toBeInTheDocument();
    const cells = screen.getAllByRole("cell");
    fireEvent.click(cells[0]!); // 첫 행 첫 셀
    expect(screen.getByTestId("trade-detail-expanded")).toBeInTheDocument();
  });

  it("pageSize 50 — 60건 입력 시 페이저 노출 + 2페이지 이동", () => {
    const trades: TradeItem[] = Array.from({ length: 60 }, (_, i) => mkTrade(i + 1));
    render(
      <TradeDetailTable
        trades={trades}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    // 페이지 컨트롤 노출
    expect(screen.getByLabelText("이전 페이지")).toBeInTheDocument();
    const next = screen.getByLabelText("다음 페이지");
    expect(next).toBeInTheDocument();
    expect(screen.getByLabelText("이전 페이지")).toBeDisabled();

    // 다음 페이지로 이동 → "2" 버튼 활성 + 다음 disabled
    fireEvent.click(next);
    const page2 = screen.getByRole("button", { name: "2" });
    expect(page2).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("다음 페이지")).toBeDisabled();
  });

  it("CSV 버튼 — 0건이면 disabled", () => {
    render(
      <TradeDetailTable
        trades={[]}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
    expect(screen.getByLabelText("CSV 내보내기")).toBeDisabled();
  });
});

// --- BL-665 — 검색 디바운스 -------------------------------------------------
// ★착수 시점에 검색은 단위·e2e 어느 쪽에도 커버가 **0건**이었다. 디바운스를 넣기 전에
//   「검색이 여전히 거른다」와 「거르는 것이 늦춰진다」를 둘 다 못 재고 있었다.
describe("TradeDetailTable — 검색 디바운스 (BL-665)", () => {
  const trades = Array.from({ length: 3 }, (_, i) => mkTrade(i + 1));

  function renderTable() {
    render(
      <TradeDetailTable
        trades={trades}
        isLoading={false}
        isError={false}
        endpoint={ENDPOINT}
        filenamePrefix="bt-test"
      />,
    );
  }

  it("입력 직후에는 아직 안 거르고, 디바운스가 지나야 거른다", () => {
    vi.useFakeTimers();
    try {
      renderTable();
      const rows = () => within(screen.getByRole("table")).getAllByRole("row").length - 1;
      expect(rows()).toBe(3);

      fireEvent.change(screen.getByLabelText("거래 검색"), { target: { value: "2" } });
      // 입력값 자체는 즉시 반영된다 — 입력창이 굼떠지면 안 된다.
      expect(screen.getByLabelText("거래 검색")).toHaveValue("2");
      // 그러나 2000건 정렬·필터는 아직 안 돌았다.
      expect(rows()).toBe(3);

      // ★타이머 전진은 act 로 감싸야 debounce state 갱신이 커밋된다.
      // ★타이머 전진은 act 로 감싸야 debounce state 갱신이 커밋된다.
      act(() => {
        vi.advanceTimersByTime(250);
      });
      expect(rows()).toBe(1);
      expect(screen.getByRole("table")).toHaveTextContent("2");
    } finally {
      vi.useRealTimers();
    }
  });

  // codex 적대 리뷰 P1 — 배지가 즉시값을 세면 디바운스 창(200ms) 동안 표·CSV 와 어긋난다.
  // 「필터 1개」라고 말하면서 CSV 는 안 걸린 전량을 내보내는 상태가 실재했다.
  it("★활성 필터 배지가 표·CSV 와 같은 스냅샷을 센다 (디바운스 창 안에서도)", () => {
    vi.useFakeTimers();
    try {
      renderTable();
      // 배지는 activeCount>0 일 때만 렌더되고 `aria-label="활성 필터 N개"` 를 단다.
      const badge = () => screen.queryByLabelText(/^활성 필터 \d+개$/)?.textContent ?? null;
      const rows = () => within(screen.getByRole("table")).getAllByRole("row").length - 1;

      expect(badge()).toBeNull();
      fireEvent.change(screen.getByLabelText("거래 검색"), { target: { value: "2" } });
      // 디바운스 창 안 — 표가 아직 3건이면 배지도 아직 필터를 세면 안 된다.
      expect(rows()).toBe(3);
      expect(badge()).toBeNull();

      act(() => {
        vi.advanceTimersByTime(250);
      });
      expect(rows()).toBe(1);
      expect(badge()).toBe("필터 1개");
    } finally {
      vi.useRealTimers();
    }
  });
});
