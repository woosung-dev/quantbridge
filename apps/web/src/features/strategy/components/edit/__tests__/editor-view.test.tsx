import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const { strategyQuery, mutate, metadataRender, prefetchBrief } = vi.hoisted(() => ({
  strategyQuery: vi.fn(),
  mutate: vi.fn(),
  metadataRender: vi.fn(),
  prefetchBrief: vi.fn(),
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategy: strategyQuery,
  usePrefetchStrategyBrief: prefetchBrief,
  useUpdateStrategy: () => ({ mutate, isPending: false }),
}));

// 로딩 분기 테스트라 무거운 자식(Monaco 등)은 렌더에 안 닿지만, 모듈 import 자체를 끊는다.
vi.mock("../editor-monaco-wrapper", () => ({ EditorMonacoWrapper: () => null }));
vi.mock("../diagnostics-strip", () => ({ DiagnosticsStrip: () => null }));
vi.mock("../tab-metadata", () => ({
  TabMetadata: () => {
    metadataRender();
    return null;
  },
}));
vi.mock("../tab-webhook", () => ({ TabWebhook: () => null }));
vi.mock("../delete-dialog", () => ({ DeleteDialog: () => null }));

import { EditorView } from "../editor-view";
import { useEditStore } from "@/features/strategy/edit-store";
import { StrategyResponseSchema } from "@/features/strategy/schemas";

beforeEach(() => {
  strategyQuery.mockReturnValue({ data: undefined, isLoading: true, isError: false });
  useEditStore.setState({
    strategyId: null,
    pineSource: "",
    serverSnapshot: "",
    lastSavedAt: null,
  });
  mutate.mockReset();
  prefetchBrief.mockReset();
  metadataRender.mockReset();
});

afterEach(() => cleanup());

describe("EditorView 로딩 스켈레톤", () => {
  it("aria-busy 이고 주요 블록(헤더 칩 행 · 에디터 프레임 · 진단 · 설정) 자리를 예약한다", () => {
    render(<EditorView id="550e8400-e29b-41d4-a716-446655440000" />);

    const skeleton = screen.getByTestId("strategy-editor-skeleton");
    expect(skeleton.getAttribute("aria-busy")).toBe("true");

    // 헤더 카드 1 + 섹션 3(소스/진단/설정) = 주요 블록 4.
    expect(skeleton.querySelectorAll("section").length).toBe(4);

    // 헤더 — 칩 행 자리 5개.
    expect(skeleton.querySelectorAll(".report-meta .sk").length).toBe(5);

    // 에디터 프레임 — Monaco 본체 480 + 파일탭 toolbar 36 + 보더 2 ≈ 518px 자리.
    const frames = Array.from(skeleton.querySelectorAll<HTMLElement>(".sk")).filter(
      (el) => el.style.height === "518px",
    );
    expect(frames.length).toBe(1);
  });
});

describe("EditorView 타이핑 구독", () => {
  it("dirty 상태에서 추가 타이핑은 메타데이터를 다시 그리지 않고 저장은 최신 원문을 쓴다", () => {
    const strategy = StrategyResponseSchema.parse({
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Test",
      description: null,
      pine_source: "strategy('Test')",
      pine_version: "v5",
      parse_status: "ok",
      parse_errors: null,
      timeframe: "1h",
      symbol: "BTC/USDT",
      is_archived: false,
      created_at: "2026-10-21T00:00:00Z",
      updated_at: "2026-10-21T00:00:00Z",
    });
    strategyQuery.mockReturnValue({ data: strategy, isLoading: false, isError: false });
    render(<EditorView id={strategy.id} />);
    act(() => useEditStore.getState().setPineSource("first edit"));
    metadataRender.mockClear();
    act(() => useEditStore.getState().setPineSource("latest edit\nsecond line"));
    expect(metadataRender).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Pine 소스 2줄" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^저장$/ }));
    expect(mutate).toHaveBeenCalledWith({ pine_source: "latest edit\nsecond line" });
  });
});

describe("EditorView 브리핑 병렬 조회", () => {
  it("상세 로딩 중에도 브리핑 요청을 시작한다", () => {
    const id = "550e8400-e29b-41d4-a716-446655440000";
    render(<EditorView id={id} />);
    expect(screen.getByTestId("strategy-editor-skeleton")).toBeInTheDocument();
    expect(prefetchBrief).toHaveBeenCalledWith(id);
  });
});
