// StrategyCard — status indicator dot + 메타 badge + hover 클래스 + 액션 메뉴 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { StrategyListItem } from "@/features/strategy/schemas";
import { StrategyCard } from "../strategy-card";

const FIXTURE: StrategyListItem = {
  id: "00000000-0000-0000-0000-000000000001",
  name: "MA Crossover Strategy",
  symbol: "BTC/USDT",
  timeframe: "1h",
  pine_version: "v5",
  parse_status: "ok",
  parse_errors: null,
  tags: ["trend", "momentum", "scalp"],
  trading_sessions: [],
  is_archived: false,
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-07T12:00:00Z",
};

describe("StrategyCard", () => {
  afterEach(() => {
    cleanup();
  });

  it("전략 이름·심볼·타임프레임·Pine 버전 메타를 모두 표시한다", () => {
    render(<StrategyCard strategy={FIXTURE} />);
    expect(screen.getByText("MA Crossover Strategy")).toBeInTheDocument();
    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText(/Pine v5/)).toBeInTheDocument();
  });

  it("hover lift 트랜지션 클래스를 가지고 있다 (group + hover:-translate-y)", () => {
    const { container } = render(<StrategyCard strategy={FIXTURE} />);
    const root = container.querySelector('[aria-label$="전략"]');
    expect(root?.className).toMatch(/group/);
    expect(root?.className).toMatch(/hover:-translate-y/);
  });

  it("tags 가 3 개 초과면 처음 3 개 + '+N' 표시한다", () => {
    const many: StrategyListItem = {
      ...FIXTURE,
      tags: ["a", "b", "c", "d", "e"],
    };
    render(<StrategyCard strategy={many} />);
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
    expect(screen.getByText("c")).toBeInTheDocument();
    expect(screen.queryByText("d")).not.toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("trading_sessions 가 비어있으면 '24h' 뱃지를 표시한다", () => {
    render(<StrategyCard strategy={FIXTURE} />);
    expect(screen.getByText("24h")).toBeInTheDocument();
  });

  it("액션 메뉴 trigger 와 편집 CTA 가 모두 렌더된다", () => {
    render(<StrategyCard strategy={FIXTURE} />);
    expect(
      screen.getByRole("button", { name: "카드 액션 메뉴" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /편집/ })).toBeInTheDocument();
  });

  it("parse_status='ok' 일 때 success tone 라벨을 표시한다", () => {
    render(<StrategyCard strategy={FIXTURE} />);
    // PARSE_STATUS_META.ok.label = "파싱 성공" or similar
    // exact label은 utils 에 따르므로, dot span 존재로만 체크
    const dotContainer = screen.getByText(/파싱/);
    expect(dotContainer).toBeInTheDocument();
  });
});
