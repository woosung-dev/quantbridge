// C 이식 S8 — LiveSessionTable 단위 테스트 (trading/_components 에서 이 도메인 폴더로 이동).
// - 빈 배열 → 안내 문구
// - 세션 → 상태 칩(BL-572 SSOT 라벨) + 심볼 / 인터벌 표시
// - sort toggle: 최신 시작순 ↔ 활성 우선

import { fireEvent, render, screen } from "@testing-library/react";

import { LiveSessionTable } from "../live-session-table";
import { LIVE_SESSION_STATUS_LABEL } from "@/features/live-sessions/labels";
import type { LiveSession } from "@/features/live-sessions/schemas";

const SESSION_A: LiveSession = {
  id: "10000000-0000-4000-a000-000000000001",
  user_id: "u0000000-0000-4000-a000-000000000001",
  strategy_id: "s0000000-0000-4000-a000-000000000001",
  exchange_account_id: "e0000000-0000-4000-a000-000000000001",
  symbol: "BTC/USDT",
  interval: "5m",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-05-08T10:00:00Z",
  deactivated_at: null,
};

const SESSION_B: LiveSession = {
  ...SESSION_A,
  id: "10000000-0000-4000-a000-000000000002",
  symbol: "ETH/USDT",
  interval: "15m",
  is_active: false,
  created_at: "2026-05-08T11:00:00Z",
};

describe("LiveSessionTable", () => {
  test("빈 배열 → 빈 상태 안내 문구", () => {
    render(<LiveSessionTable sessions={[]} />);
    // BL-423 — 이 표는 이제 종료 세션도 받는다. "활성 세션이 없습니다" 는 어긋난 문구다.
    expect(screen.getByText("세션이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-table")).not.toBeInTheDocument();
  });

  test("세션 2개 → 심볼 + 상태 칩 표시", () => {
    render(<LiveSessionTable sessions={[SESSION_A, SESSION_B]} />);
    expect(screen.getByTestId("live-session-table")).toBeInTheDocument();
    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByText("ETH/USDT")).toBeInTheDocument();
    // BL-572 — 표가 자체 문자열을 만들지 않고 목록 카드와 같은 SSOT 를 읽는다.
    expect(screen.getByText(LIVE_SESSION_STATUS_LABEL.active.label)).toBeInTheDocument();
    expect(screen.getByText(LIVE_SESSION_STATUS_LABEL.ended.label)).toBeInTheDocument();
    expect(screen.getByText("라이브 세션 (2)")).toBeInTheDocument();
  });

  // BL-572 — 종료된 세션을 "PAUSED" 로 부르면 재개 가능한 것처럼 읽힌다. 사유와 함께 죽은
  // 세션(position_divergence 등)까지 그렇게 나왔다. 영문 리터럴 자체가 회귀 신호다.
  test("한국어 UI 에 영문 상태 리터럴이 남지 않는다", () => {
    render(<LiveSessionTable sessions={[SESSION_A, SESSION_B]} />);
    expect(screen.queryByText("ACTIVE")).not.toBeInTheDocument();
    expect(screen.queryByText("PAUSED")).not.toBeInTheDocument();
  });

  test("sort toggle: 최신 시작순 ↔ 활성 우선", () => {
    render(<LiveSessionTable sessions={[SESSION_A, SESSION_B]} />);

    const toggle = screen.getByTestId("live-session-sort-toggle");
    expect(toggle).toHaveTextContent("최신 시작순");

    fireEvent.click(toggle);
    expect(toggle).toHaveTextContent("활성 우선");

    fireEvent.click(toggle);
    expect(toggle).toHaveTextContent("최신 시작순");
  });

  test("resolveStrategyName / resolveExchangeLabel 적용", () => {
    render(
      <LiveSessionTable
        sessions={[SESSION_A]}
        resolveStrategyName={(id) => `전략-${id.slice(0, 4)}`}
        resolveExchangeLabel={(id) => `Bybit-${id.slice(0, 4)}`}
      />,
    );
    expect(screen.getByText(/전략-s000/)).toBeInTheDocument();
    expect(screen.getByText(/Bybit-e000/)).toBeInTheDocument();
  });
});
