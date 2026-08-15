// 트레이딩 코크핏의 WS 미실현 손익 KPI 상태를 검증한다.
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useLiveSessionsMock = vi.fn();
const useUnrealizedPnlEstimateMock = vi.fn();
const useStrategiesMock = vi.fn();
const useExchangeAccountsMock = vi.fn();
const useKillSwitchEventsMock = vi.fn();
const liveSessionFormProps = vi.fn();

// BL-664 — 종전 mock 은 렌더마다 **새 객체**를 돌려줘서 무엇으로 무효화했는지 검증할 수 없었다.
// 모듈 레벨 안정 spy 로 바꾼다.
const invalidateQueriesMock = vi.fn();
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: invalidateQueriesMock }),
}));
// BL-551 — 세션 선택이 useState 가 아니라 `?session=<id>` 다. 선례는 같은 레포의
// `backtest-list.tsx` 의 `pushStatus`/`pushSort`(URLSearchParams 복사 → set → router.replace).
//
// ★이 하네스는 쓰기를 읽기로 되먹인다. `replace` 가 쿼리 문자열을 갱신하고, 시험은 `rerender`
//   로 다음 렌더를 요청한다 — 실제 라우터가 하는 일과 같은 순서다. 클릭 직후 같은 렌더에서
//   상세가 열리기를 기대하면 안 된다. 그것은 종전 useState 판의 동작이다.
let queryString = "";
const replaceMock = vi.fn((url: string) => {
  const idx = url.indexOf("?");
  queryString = idx === -1 ? "" : url.slice(idx + 1);
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  usePathname: () => "/trading",
  useSearchParams: () => new URLSearchParams(queryString),
}));
// ★키 팩토리는 흉내내지 않고 **진짜**를 쓴다 — query-keys 는 의존성 없는 leaf 라 배럴을 끌지 않는다.
// 흉내내면 팩토리가 바뀌어도 이 시험이 초록이 된다.
vi.mock("@/features/live-sessions", async () => ({
  liveSessionKeys: (await import("@/features/live-sessions/query-keys")).liveSessionKeys,
  LiveSessionDetail: () => <div data-testid="mock-detail" />,
  // BL-551 — 선택을 쓰는 지점은 목록 클릭과 **여기** 둘이다. 종전 `() => null` mock 은
  // `onSuccess` 경로를 한 번도 태우지 않아 한쪽만 URL 로 옮겨도 초록이었다.
  LiveSessionForm: ({
    onSuccess,
    ...props
  }: {
    onSuccess?: (session: { id: string }) => void;
    exchangeAccounts: readonly unknown[];
  }) => {
    liveSessionFormProps(props);
    return (
      <button
        type="button"
        data-testid="mock-live-session-created"
        onClick={() => onSuccess?.({ id: "created-session" })}
      >
        세션 생성됨
      </button>
    );
  },
  LiveSessionList: ({
    onSelect,
  }: {
    onSelect?: (session: { id: string; is_active?: boolean }) => void;
  }) => (
    <>
      <button
        type="button"
        data-testid="mock-live-session-select"
        onClick={() => onSelect?.({ id: "session-1", is_active: true })}
      >
        세션 선택
      </button>
      <button
        type="button"
        data-testid="mock-inactive-live-session-select"
        onClick={() => onSelect?.({ id: "inactive-session", is_active: false })}
      >
        종료 세션 선택
      </button>
    </>
  ),
  LiveSessionTable: () => null,
  useLiveSessions: () => useLiveSessionsMock(),
  useUnrealizedPnlEstimate: () => useUnrealizedPnlEstimateMock(),
}));
vi.mock("@/features/strategy/hooks", async () => ({
  strategyKeys: (await import("@/features/strategy/query-keys")).strategyKeys,
  useStrategies: () => useStrategiesMock(),
}));
vi.mock("@/features/trading", async () => ({
  tradingKeys: (await import("@/features/trading/query-keys")).tradingKeys,
  ExchangeAccountsPanel: () => null,
  KillSwitchPanel: () => null,
  OrdersPanel: () => null,
  useExchangeAccounts: () => useExchangeAccountsMock(),
  useKillSwitchEvents: () => useKillSwitchEventsMock(),
}));
vi.mock("../kill-switch-banner", () => ({ KillSwitchBanner: () => null }));
vi.mock("../account-balance-section", () => ({ AccountBalanceSection: () => null }));
vi.mock("../open-positions-table", () => ({ OpenPositionsTable: () => null }));
const accountPositionsProps = vi.fn();
vi.mock("../account-positions-table", () => ({
  AccountPositionsTable: (props: { accounts: readonly { id: string }[] }) => {
    accountPositionsProps(props);
    return null;
  },
}));
vi.mock("../session-diagnostics", () => ({ SessionDiagnostics: () => null }));

import { TradingCockpit } from "../trading-cockpit";

function setDefaults() {
  // BL-533 — 코크핏은 `useLiveSessions(true)` 를 쓴다. 그 응답에는 **비활성 세션도 들어 있다**.
  // 종전 mock 은 활성 1건만 돌려줘서 `include_inactive=false` 를 흉내내고 있었고, 그래서
  // 「종료 세션 선택」테스트가 `selectedInactiveSession` 미러 state 덕에만 통과했다.
  // 미러를 지우려면 mock 이 먼저 실제 쿼리를 닮아야 한다.
  useLiveSessionsMock.mockReturnValue({
    data: {
      items: [
        { id: "session-1", is_active: true },
        { id: "inactive-session", is_active: false },
      ],
    },
    isError: false,
    isFetching: false,
    isPending: false,
  });
  useStrategiesMock.mockReturnValue({ data: { items: [] } });
  useExchangeAccountsMock.mockReturnValue({ data: [], isError: false, isPending: false });
  useKillSwitchEventsMock.mockReturnValue({
    data: { items: [] },
    isError: false,
    isPending: false,
  });
  useUnrealizedPnlEstimateMock.mockReturnValue({
    total: null,
    isEstimating: true,
    latestTs: null,
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-24T00:00:20.000Z"));
  vi.clearAllMocks();
  queryString = "";
  setDefaults();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("TradingCockpit — 미실현 손익 추정 KPI", () => {
  it("계정 응답의 read_only를 라이브 세션 폼 옵션까지 보존한다", () => {
    useExchangeAccountsMock.mockReturnValue({
      data: [
        {
          id: "account-read-only",
          exchange: "bybit",
          mode: "demo",
          label: "read-only-demo",
          read_only: true,
        },
      ],
      isError: false,
      isPending: false,
    });

    render(<TradingCockpit />);

    expect(liveSessionFormProps).toHaveBeenLastCalledWith(
      expect.objectContaining({
        exchangeAccounts: [
          expect.objectContaining({
            id: "account-read-only",
            read_only: true,
          }),
        ],
      }),
    );
  });

  it("mark 미수신이면 시세 수신 대기를 그린다", () => {
    render(<TradingCockpit />);

    expect(screen.getByText("미실현 손익 · 추정")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("시세 수신 대기");
    expect(screen.queryByText("총 세션")).not.toBeInTheDocument();
  });

  it("추정값을 부호·소수 두 자리 USDT로 그린다", () => {
    useUnrealizedPnlEstimateMock.mockReturnValue({
      total: 12.3,
      isEstimating: false,
      latestTs: Date.now(),
    });
    render(<TradingCockpit />);

    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("+12.30 USDT");
  });

  it("15초를 초과한 epoch-ms ticker에 시세 지연 배지를 그린다", () => {
    useUnrealizedPnlEstimateMock.mockReturnValue({
      total: -4.5,
      isEstimating: false,
      latestTs: Date.now() - 15_001,
    });
    render(<TradingCockpit />);

    expect(screen.getByTestId("kpi-unrealized-pnl")).toHaveTextContent("-4.50 USDT");
    expect(screen.getByText("시세 지연")).toBeInTheDocument();
  });

  it("새 §02·§03을 넣고 기존 섹션을 §08까지 순서대로 번호 매긴다", () => {
    render(<TradingCockpit />);

    expect(screen.getByRole("region", { name: "계좌 잔고" })).toHaveTextContent("02 계좌 잔고");
    expect(screen.getByRole("region", { name: "열린 포지션" })).toHaveTextContent("03 열린 포지션");
    expect(screen.getByRole("region", { name: "리스크 가드" })).toHaveTextContent("04 리스크 가드");
    expect(screen.getByRole("region", { name: "진단" })).toHaveTextContent("08 진단");
  });

  it("선택한 세션이 목록에서 사라지면 중단 안내를 보여준다", () => {
    const { rerender } = render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-select"));
    useLiveSessionsMock.mockReturnValue({
      data: { items: [] },
      isError: false,
      isPending: false,
    });
    rerender(<TradingCockpit />);

    expect(screen.getByTestId("live-session-stopped-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-detail")).not.toBeInTheDocument();
  });

  // BL-551 — 아래 세 시험의 `rerender` 는 어서션이 아니라 **경로**의 변화다. 선택이 URL 로
  // 옮겨갔으므로 클릭은 `router.replace` 를 부르고, 화면은 그 다음 렌더에서 바뀐다.
  // 어서션 집합은 종전과 같다.
  it("목록에 남아 있으면 상세를 보여준다", () => {
    const { rerender } = render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-select"));
    rerender(<TradingCockpit />);

    expect(screen.getByTestId("mock-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  it("최근 종료 세션을 선택해도 같은 상세 패널을 보여준다", () => {
    const { rerender } = render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-inactive-live-session-select"));
    rerender(<TradingCockpit />);

    expect(screen.getByTestId("mock-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  // BL-533 — 위 테스트가 **무엇 덕에** 통과하는지 못 박는다.
  // 미러 state 를 지운 뒤로 종료 세션 상세는 오직 `useLiveSessions(true)` 가 비활성을
  // 실어 오기 때문에 열린다. 쿼리가 활성만 돌려주도록 되돌아가면(=`useLiveSessions()`)
  // 같은 클릭이 상세가 아니라 중단 안내로 떨어진다. 이 대조가 없으면 위 테스트는
  // 「종료 세션이 목록에 있든 없든 통과」로 읽혀 판별력이 사라진다.
  it("쿼리가 활성만 실어 오면 같은 클릭이 중단 안내로 떨어진다 (미러 없음의 증거)", () => {
    useLiveSessionsMock.mockReturnValue({
      data: { items: [{ id: "session-1", is_active: true }] },
      isError: false,
      isPending: false,
    });
    const { rerender } = render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-inactive-live-session-select"));
    rerender(<TradingCockpit />);

    expect(screen.getByTestId("live-session-stopped-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-detail")).not.toBeInTheDocument();
  });

  // --- BL-551 — 세션 상세를 링크로 열 수 있어야 한다 -------------------------
  //
  // 착수 시점 실측: 선택은 `trading-cockpit.tsx:67` 의 `useState` 가 쥐고 있었고 trading 트리
  // 전체에 `useSearchParams` 가 0건이었다. 새로고침하면 선택이 사라지고 특정 세션으로 링크할
  // 수단이 없었다.
  //
  // ★목록 밖 세션은 원리상 열 수 없다 — `GET /live-sessions/{id}` 단건 엔드포인트가 없고,
  //   목록은 활성 전체 + 최근 종료 20건뿐이다. 그래서 그 경우는 이미 있는
  //   `live-session-stopped-notice` 로 떨어지는 것이 정답이고, 그것이 아래 음성 대조다.
  it("?session=<id> 로 진입하면 그 세션 상세가 열린다", () => {
    queryString = "session=session-1";

    render(<TradingCockpit />);

    expect(screen.getByTestId("mock-detail")).toBeInTheDocument();
    // 읽기만으로 열려야 한다. 진입이 URL 을 다시 쓰면 히스토리를 흔든다.
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("목록에 없는 id 로 진입하면 중단 안내가 뜬다", () => {
    // ★음성 대조. 딥링크가 "무슨 id 든 상세를 연다" 로 번지지 않는지 본다.
    useLiveSessionsMock.mockReturnValue({
      data: { items: [{ id: "session-1", is_active: true }] },
      isError: false,
      isFetching: false,
      isPending: false,
    });
    queryString = "session=gone-forever";

    render(<TradingCockpit />);

    expect(screen.getByTestId("live-session-stopped-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-detail")).not.toBeInTheDocument();
  });

  it("캐시가 있는 refetch 중에는 목록 밖 선택을 불러오는 중으로 보인다", () => {
    useLiveSessionsMock.mockReturnValue({
      data: { items: [{ id: "session-1", is_active: true }] },
      isError: false,
      isFetching: true,
      isPending: false,
    });
    queryString = "session=created-session";

    render(<TradingCockpit />);

    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
    expect(screen.getByText("세션 목록을 불러오는 중입니다.")).toBeInTheDocument();
  });

  it("목록을 불러오는 중에는 중단 안내를 띄우지 않는다", () => {
    // ★딥링크가 생기면서 **처음 도달 가능해진** 경로다. 종전에는 마운트 시 선택이 언제나
    //   비어 있어 이 분기가 열리지 않았다. `?session=` 을 달고 들어오면 목록 응답이 오기 전
    //   한 프레임 동안 "밀려났습니다" 가 번쩍인다.
    useLiveSessionsMock.mockReturnValue({ data: undefined, isError: false, isPending: true });
    queryString = "session=session-1";

    render(<TradingCockpit />);

    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  it("목록 조회가 실패했을 때는 중단 안내로 오진하지 않는다", () => {
    // ★codex G1 발견 2. 목록 요청이 실패하면 `sessionItems` 가 비어 목록 밖 id 와 구분되지
    //   않는다. 그대로 두면 네트워크 실패를 "종료 이력 20건에서 밀려났다" 로 잘못 설명한다.
    //   목록 자체의 실패 표시는 `LiveSessionList` 가 이미 한다.
    useLiveSessionsMock.mockReturnValue({ data: undefined, isError: true, isPending: false });
    queryString = "session=session-1";

    render(<TradingCockpit />);

    expect(screen.queryByTestId("live-session-stopped-notice")).not.toBeInTheDocument();
  });

  // ★`{ scroll: false }` 는 장식이 아니다 (codex G1 발견 1). Next 16 의 `router.replace` 는
  //   기본으로 페이지 최상단으로 스크롤한다 (`node_modules/next/dist/docs/.../use-router.md`
  //   의 "Disabling scroll to top"). 세션 목록은 화면 §07 이므로, 그냥 두면 상세를 열려던
  //   사용자가 매 클릭마다 페이지 꼭대기로 튕긴다. 종전 useState 판에는 없던 부작용이다.
  it("세션을 클릭하면 URL 에 session 파라미터를 replace 로 싣는다", () => {
    render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-select"));

    expect(replaceMock).toHaveBeenCalledTimes(1);
    expect(replaceMock).toHaveBeenCalledWith("/trading?session=session-1", { scroll: false });
  });

  it("기존 쿼리 파라미터를 지우지 않는다", () => {
    // `?tab=live-sessions` 는 읽는 코드가 없는 유물이지만 e2e 3종이 아직 goto 에 쓴다.
    // 선택이 그것을 날려버리면 링크를 공유받은 쪽에서 경로가 달라진다.
    queryString = "tab=live-sessions";

    render(<TradingCockpit />);
    fireEvent.click(screen.getByTestId("mock-live-session-select"));

    expect(replaceMock).toHaveBeenCalledWith("/trading?tab=live-sessions&session=session-1", {
      scroll: false,
    });
  });

  it("새 세션을 만들면 그 세션도 같은 경로로 URL 에 실린다", () => {
    // ★codex G1 발견(D9). 쓰기 지점은 둘인데 종전 mock 이 `LiveSessionForm: () => null` 이라
    //   `onSuccess` 경로가 한 번도 검증되지 않았다. 한쪽만 URL 로 옮기면 새로 만든 세션이
    //   새로고침에서 사라진다.
    render(<TradingCockpit />);

    fireEvent.click(screen.getByTestId("mock-live-session-created"));

    expect(replaceMock).toHaveBeenCalledWith("/trading?session=created-session", {
      scroll: false,
    });
  });

  it("★계정 잔여 포지션 표에 활성 세션이 아니라 **등록된 모든 계정**을 넘긴다", () => {
    // BL-498 의 핵심 배선. 활성 세션 기준으로 좁히면 세션 0건일 때 잔여 노출이
    // 다시 화면에서 사라진다 — 그게 이 기능이 존재하는 이유다.
    useLiveSessionsMock.mockReturnValue({
      data: { items: [] },
      isError: false,
      isPending: false,
    });
    useExchangeAccountsMock.mockReturnValue({
      data: [
        { id: "acc-1", mode: "demo", label: "데모 1" },
        { id: "acc-2", mode: "demo", label: "데모 2" },
      ],
      isError: false,
      isPending: false,
    });
    accountPositionsProps.mockClear();

    render(<TradingCockpit />);

    const last = accountPositionsProps.mock.calls.at(-1)?.[0];
    expect(last.accounts.map((a: { id: string }) => a.id)).toEqual(["acc-1", "acc-2"]);
  });

  // --- BL-663 — 5초 틱의 재조정 범위 ---------------------------------------
  // `AccountPositionsTable` 은 memo 가 없으므로 코크핏이 재렌더되면 반드시 다시 호출된다.
  // ⇒ 그 호출 수가 곧 「코크핏이 재조정됐나」의 대리 측정이다.
  it("★5초 틱이 코크핏 §01~§08 을 재조정하지 않는다 (KPI leaf 안에 갇혔다)", () => {
    render(<TradingCockpit />);
    const before = accountPositionsProps.mock.calls.length;
    expect(before).toBeGreaterThan(0); // 대리 측정이 살아 있음을 먼저 확인한다

    act(() => {
      vi.advanceTimersByTime(15_000); // 5초 틱 3회분
    });

    expect(accountPositionsProps.mock.calls.length).toBe(before);
    // 그러면서 KPI 자체는 계속 그려진다.
    expect(screen.getByTestId("kpi-unrealized-pnl")).toBeInTheDocument();
  });

  // --- BL-664 — 새로고침의 무효화 범위 ------------------------------------
  // ★네 번째 도메인 `alert-rules` 는 codex 적대 리뷰가 잡았다 — 첫 판은 셋만 무효화했고
  //   §08 `SessionDiagnostics` 의 `useAlertRules`(`alert-rules/hooks.ts`)가 빠져 있었다.
  //   종전 무필터 호출은 그것도 갱신했으므로 빠뜨리면 **기능이 깨진다**. 도메인이 늘면 여기에 더해라.
  it("★새로고침이 이 화면의 네 도메인만 무효화한다 (앱 전체 캐시가 아니라)", async () => {
    const { liveSessionKeys } = await import("@/features/live-sessions/query-keys");
    const { tradingKeys } = await import("@/features/trading/query-keys");
    const { strategyKeys } = await import("@/features/strategy/query-keys");
    const { alertRuleKeys } = await import("@/features/alert-rules/query-keys");

    render(<TradingCockpit />);
    invalidateQueriesMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: /새로고침/ }));

    // ⑴ 무필터 호출이 0회여야 한다 — 이것이 [BL-664] 의 결함 자체다.
    expect(invalidateQueriesMock.mock.calls.every((c) => c[0]?.queryKey !== undefined)).toBe(true);

    // ⑵ 정확히 세 도메인 루트. 팩토리 출력과 대조하므로 키가 바뀌면 이 시험이 깨진다.
    const keys = invalidateQueriesMock.mock.calls.map((c) => c[0].queryKey);
    expect(keys).toEqual([
      tradingKeys.all("user-1"),
      liveSessionKeys.all("user-1"),
      strategyKeys.all("user-1"),
      alertRuleKeys.all("user-1"),
    ]);

    // ⑶ 음성 대조 — 백테스트·옵티마이저 루트는 어느 호출에도 안 걸린다.
    const roots = keys.map((k) => k[0]);
    expect(roots).not.toContain("backtests");
    expect(roots).not.toContain("optimizations");
  });
});
