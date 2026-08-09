// BacktestReportShell — variant-c 번호 섹션 IA (01~10) 존재/순서 + metrics null 방어 검증
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BacktestDetail } from "@/features/backtest/schemas";

vi.mock("@/features/backtest/hooks", () => ({
  useAllBacktestTrades: () => ({
    data: { items: [], total: 0, truncated: false },
    isLoading: false,
    isError: false,
    error: null,
  }),
  useBacktest: () => ({ data: undefined, isLoading: false, isError: false }),
  useBacktests: () => ({ data: undefined, isLoading: false, isError: false }),
  useStressTest: () => ({ data: undefined, isLoading: false, isError: false, error: null }),
  useLatestStressTest: () => ({ data: undefined }),
  useCreateMonteCarlo: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateWalkForward: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateCostAssumption: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateParamStability: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/components/charts/trading-chart", () => ({
  TradingChart: () => <div data-testid="mock-trading-chart" />,
}));

import { BacktestReportShell } from "@/app/(dashboard)/backtests/_components/report/backtest-report-shell";

const BT = {
  id: "11111111-2222-3333-4444-555555555555",
  strategy_id: "s",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2025-01-01T00:00:00Z",
  period_end: "2026-07-05T00:00:00Z",
  status: "completed",
  created_at: "2026-07-05T00:00:00Z",
  completed_at: "2026-07-05T00:00:00Z",
  initial_capital: 1000000,
  error: null,
  config: null,
  metrics: {
    total_return: 0.189,
    sharpe_ratio: 1.154,
    max_drawdown: -0.0252,
    win_rate: 0.9898,
    num_trades: 295,
    profit_factor: 21.3,
  },
  equity_curve: [
    { timestamp: "2025-01-01T00:00:00Z", value: 1000000 },
    { timestamp: "2025-01-02T00:00:00Z", value: 1010000 },
  ],
} as unknown as BacktestDetail;

describe("BacktestReportShell (variant-c 번호 섹션 IA)", () => {
  it("핵심 섹션 프리미티브(요약/차트/지표/거래/다음 단계)가 시맨틱 클래스로 렌더", () => {
    render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(screen.getByTestId("backtest-report-shell")).toBeInTheDocument();
    expect(screen.getByTestId("key-stats-strip")).toBeInTheDocument();
    expect(screen.getByTestId("performance-chart")).toBeInTheDocument();
    expect(screen.getByTestId("metric-groups-section")).toBeInTheDocument();
    expect(screen.getByTestId("report-next-steps")).toBeInTheDocument();
  });

  it("01~10 아이브로 번호가 순서대로 존재 (상단→하단 단일 스크롤)", () => {
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    const nums = Array.from(container.querySelectorAll(".eyebrow .num")).map(
      (el) => el.textContent,
    );
    expect(nums).toEqual([
      "01",
      "02",
      "03",
      "04",
      "05",
      "06",
      "07",
      "08",
      "09",
      "10",
    ]);
  });

  it("실행 조건 섹션에 AssumptionsCard(초기 자본) 가 1회만 렌더", () => {
    render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(screen.getAllByText("초기 자본")).toHaveLength(1);
  });

  it("스트레스 테스트 섹션 앵커 id 가 CTA 링크와 일치", () => {
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(container.querySelector("#stress-test")).not.toBeNull();
    const cta = screen.getByTestId("report-next-steps");
    expect(within(cta).getByText("스트레스 테스트 열기").getAttribute("href")).toBe(
      "#stress-test",
    );
  });

  // ── BL-397 앵커 계약 ──────────────────────────────────────────────────────
  //
  // `/backtests/<id>#<앵커>` 로 리포트의 특정 섹션을 공유할 수 있어야 한다. 기존 선례는
  // 08 스트레스 테스트 하나뿐이었고(위 테스트가 그것을 지킨다) 나머지 아홉은 링크 불가였다.
  //
  // 순서까지 동결하는 이유: 하나를 지우고 다른 하나를 더해도 배열 비교는 잡지만
  // "존재하는가" 만 개별로 물으면 못 잡는다. 중복 id 도 배열 비교로만 드러난다.
  const SECTION_ANCHORS = [
    "key-stats",
    "benchmark",
    "metrics",
    "trades",
    "distributions",
    "profit-structure",
    "runup-drawdown",
    "stress-test",
    "assumptions",
    "next-steps",
  ] as const;

  it("열 개 섹션 전부에 안정적인 앵커 id 를 단다", () => {
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    const ids = Array.from(container.querySelectorAll("section.section")).map((el) => el.id);
    expect(ids).toEqual([...SECTION_ANCHORS]);
  });

  it("앵커 스크롤이 상단바에 가리지 않게 scroll-margin 을 준다", () => {
    // ★이것은 대리 지표다. jsdom 은 레이아웃을 계산하지 않으므로 "제목이 실제로 안 가린다" 를
    //   여기서 잴 수 없다. 진짜 판정은 e2e (`report-section-anchors.spec.ts`) 의
    //   boundingBox().y 어서션이고, 이 테스트는 값이 바뀌거나 빠지는 회귀를 막는다.
    //
    // ★값을 정확히 동결하는 이유 (codex G1 발견 3): 접두사만 검사하면 `scroll-mt-[60px]` 로
    //   바뀌어도 e2e 의 `y >= 60` 과 함께 통과한다. 그러면 여유 16px 계약이 아무 데서도
    //   지켜지지 않는다. sticky `.topbar` 60px (`globals.css` 의 `--topbar-h`) + 여유 16 = 76.
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    const sections = Array.from(container.querySelectorAll("section.section"));
    expect(sections).toHaveLength(SECTION_ANCHORS.length);
    for (const el of sections) {
      expect(el.className.split(/\s+/)).toContain("scroll-mt-[76px]");
    }
  });

  it("자산 곡선이 비면 02 를 빼고 나머지 아홉 앵커를 그대로 단다", () => {
    // ★codex G1 발견 4. 02 는 `equity_curve` 가 있을 때만 렌더된다. 그 조건이 거짓일 때
    //   나머지 앵커가 밀리거나 사라지지 않는지, 그리고 화면이 깨지지 않는지를 본다.
    //   (`#benchmark` 로 들어온 링크는 그때 "없는 fragment" 와 같은 처리로 떨어진다.)
    const { container } = render(
      <BacktestReportShell
        backtest={{ ...BT, equity_curve: [] } as unknown as BacktestDetail}
        currentId={BT.id}
      />,
    );
    const ids = Array.from(container.querySelectorAll("section.section")).map((el) => el.id);
    expect(ids).toEqual(SECTION_ANCHORS.filter((anchor) => anchor !== "benchmark"));
  });

  // ── 마운트 시 해시 재조정 ────────────────────────────────────────────────
  //
  // ★2026-08-10 실측으로 확정된 계약이다. `id` 프롭만 넣은 판에서 e2e
  //   `#trades 로 진입하면...` 가 `viewport ratio 0` 으로 red 였다 — 엘리먼트는 DOM 에
  //   있는데 브라우저가 스크롤하지 않았다. 원인: `/backtests/[id]/page.tsx` 는 prefetch 를
  //   하지 않아 리포트가 React Query 완료 뒤에 삽입되는데, 네이티브 fragment 위치결정은
  //   문서 로드 시점에 이미 끝나고 다시 시도하지 않는다.
  //
  //   백로그 [BL-397] 의 「프롭 하나를 9곳에 넘긴다」는 이 실측으로 반증됐다.
  //
  // jsdom 은 레이아웃이 없어 `scrollIntoView` 를 아예 구현하지 않는다. 그래서 프로토타입에
  // 심어 두고 **어떤 엘리먼트로** 불렸는지만 본다. 위치는 e2e 가 잰다.
  function withScrollSpy(hash: string, run: (scrolled: Element[]) => void) {
    const scrolled: Element[] = [];
    const had = Object.prototype.hasOwnProperty.call(Element.prototype, "scrollIntoView");
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function scrollIntoViewSpy(this: Element) {
      scrolled.push(this);
    };
    window.location.hash = hash;
    try {
      run(scrolled);
    } finally {
      window.location.hash = "";
      if (had) Element.prototype.scrollIntoView = original;
      else delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
    }
  }

  it("해시를 달고 들어오면 마운트 직후 그 섹션으로 스크롤한다", () => {
    withScrollSpy("#trades", (scrolled) => {
      const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
      expect(scrolled).toEqual([container.querySelector("#trades")]);
    });
  });

  it("모르는 해시로 들어오면 아무 것도 스크롤하지 않는다", () => {
    // ★음성 대조. 재조정이 "해시만 있으면 무조건 움직인다" 로 번지지 않는지 본다.
    withScrollSpy("#nope", (scrolled) => {
      render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
      expect(scrolled).toEqual([]);
    });
  });

  it("metrics 없으면 null 렌더 (방어)", () => {
    const { container } = render(
      <BacktestReportShell
        backtest={{ ...BT, metrics: null } as unknown as BacktestDetail}
        currentId={BT.id}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
