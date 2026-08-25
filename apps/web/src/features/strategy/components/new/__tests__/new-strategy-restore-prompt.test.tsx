// BL-823 회귀 테스트 — 복원 모달은 **이전 세션의** 초안에만 뜬다.
// `useDraftSnapshot` 이 useSyncExternalStore 라이브 구독이라 `useAutoSaveDraft`(500ms debounce)가
// 방금 쓴 「지금 세션의」 초안을 즉시 되읽는다. 세션 안에서 입력이 시작되면 프롬프트 게이트가
// 닫혀 있어야 한다. ★draft 모듈은 mock 하지 않는다 — 실모듈 + jsdom localStorage + fake timers 로
// auto-save → 되읽기 경로를 실제로 태운다 (diagnostics 테스트와 달리 이 파일의 주제가 그 경로다).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { draftKeyFor, type WizardDraft } from "@/features/strategy/draft";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Monaco 에디터는 무겁고 브라우저 API 를 요구하므로 textarea 로 대체.
vi.mock("@/components/monaco/pine-editor", () => ({
  PineEditor: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea data-testid="pine-editor" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

// 파싱 결과 패널은 이 테스트 범위 밖 — 스텁으로 대체.
vi.mock("@/features/strategy/components/new/parse-result-panel", () => ({
  ParseResultPanel: () => <div data-testid="parse-result-panel" />,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useCreateStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useParseStrategy: () => ({ mutate: vi.fn(), data: null, isPending: false, error: null }),
  usePreviewParse: () => ({ data: null, isFetching: false, error: null }),
}));

import { NewStrategyWizard } from "@/features/strategy/components/new/new-strategy-wizard";

// 전역 auth mock(`tests/setup.ts`)의 기본 userId — draft key 스코핑이 이 값을 쓴다.
const USER_ID = "user-1";
const DIALOG_TITLE = "이어서 작성하시겠어요?";

function renderWizard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NewStrategyWizard />
    </QueryClientProvider>,
  );
}

function seedPriorDraft(): void {
  const draft: WizardDraft = {
    version: 1,
    savedAt: Date.now(),
    method: "direct",
    pineSource: "//@version=5\nstrategy('prior')",
    metadata: { name: "이전 세션 전략" },
  };
  window.localStorage.setItem(draftKeyFor(USER_ID), JSON.stringify(draft));
}

describe("NewStrategyWizard — 복원 프롬프트 게이트 (BL-823)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("이 세션의 auto-save 초안에는 모달이 뜨지 않는다 (타이핑 → 500ms 경과)", () => {
    renderWizard();
    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();

    fireEvent.change(screen.getByTestId("pine-editor"), {
      target: { value: "//@version=5\nstrategy('now')" },
    });
    act(() => {
      vi.advanceTimersByTime(600);
    });

    // 경로 도달 가드 — auto-save 가 실제로 썼는지 먼저 확인한다. 이것이 없으면
    // 「저장 자체가 안 돼서」 모달이 안 뜬 구현도 초록으로 통과한다.
    const stored = window.localStorage.getItem(draftKeyFor(USER_ID));
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored!).pineSource).toContain("strategy('now')");

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("진짜 이전 세션 초안(마운트 전 존재)에는 모달이 뜬다 — 음성 대조", () => {
    seedPriorDraft();
    renderWizard();
    expect(screen.getByText(DIALOG_TITLE)).toBeTruthy();
  });

  it("수동 「초안 저장」 직후에도 모달이 뜨지 않는다", () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("전략 이름"), {
      target: { value: "지금 세션 전략" },
    });
    fireEvent.click(screen.getByText("초안 저장"));

    expect(window.localStorage.getItem(draftKeyFor(USER_ID))).not.toBeNull();
    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });
});
