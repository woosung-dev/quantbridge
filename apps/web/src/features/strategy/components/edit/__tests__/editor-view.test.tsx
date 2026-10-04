import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const prefetchBrief = vi.fn();
vi.mock("@/features/strategy/hooks", () => ({
  useStrategy: () => ({ data: undefined, isLoading: true, isError: false }),
  useUpdateStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  usePrefetchStrategyBrief: (id: string) => prefetchBrief(id),
}));

// 로딩 분기 테스트라 무거운 자식(Monaco 등)은 렌더에 안 닿지만, 모듈 import 자체를 끊는다.
vi.mock("../editor-monaco-wrapper", () => ({ EditorMonacoWrapper: () => null }));
vi.mock("../diagnostics-strip", () => ({ DiagnosticsStrip: () => null }));
vi.mock("../tab-metadata", () => ({ TabMetadata: () => null }));
vi.mock("../tab-webhook", () => ({ TabWebhook: () => null }));
vi.mock("../delete-dialog", () => ({ DeleteDialog: () => null }));

import { EditorView } from "../editor-view";

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

describe("EditorView 브리핑 병렬 조회", () => {
  it("전략 상세가 아직 로딩 중일 때 이미 브리핑 prefetch 를 건다 (상세 → 브리핑 직렬 왕복 방지)", () => {
    prefetchBrief.mockClear();
    render(<EditorView id="550e8400-e29b-41d4-a716-446655440000" />);

    expect(screen.getByTestId("strategy-editor-skeleton")).toBeTruthy();
    expect(prefetchBrief).toHaveBeenCalledWith("550e8400-e29b-41d4-a716-446655440000");
  });
});
