import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import {
  clearWizardDraft,
  loadWizardDraft,
  saveWizardDraft,
  useAutoSaveDraft,
  type WizardDraft,
} from "@/features/strategy/draft";

// localStorage key — draft.ts 내부 상수와 동기. 테스트 I/O 검증용 상수.
const DRAFT_KEY = "sprint7c:strategy-wizard-draft:v1";

type DraftInput = Omit<WizardDraft, "version" | "savedAt">;

const baseDraft: DraftInput = {
  method: "direct",
  pineSource: "//@version=5\nstrategy('t')",
  metadata: { name: "s1" },
};

describe("useAutoSaveDraft (draft debouncer)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("saves draft to localStorage after 500ms debounce", () => {
    renderHook(({ draft }) => useAutoSaveDraft(draft), {
      initialProps: { draft: baseDraft },
    });
    // 499ms 시점: 아직 save 호출 전
    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(window.localStorage.getItem(DRAFT_KEY)).toBeNull();

    // 500ms 경과: save 호출
    act(() => {
      vi.advanceTimersByTime(1);
    });
    const raw = window.localStorage.getItem(DRAFT_KEY);
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw as string) as WizardDraft;
    expect(parsed.version).toBe(1);
    expect(parsed.method).toBe("direct");
    expect(parsed.pineSource).toBe(baseDraft.pineSource);
    expect(parsed.metadata).toEqual(baseDraft.metadata);
  });

  it("resets debounce timer when pineSource changes within the window (last write wins)", () => {
    const { rerender } = renderHook(({ draft }) => useAutoSaveDraft(draft), {
      initialProps: { draft: baseDraft },
    });

    // 300ms 경과 (debounce 진행 중)
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(window.localStorage.getItem(DRAFT_KEY)).toBeNull();

    // pineSource 변경 — 기존 타이머 클리어되고 새 타이머 시작해야 함
    const next: DraftInput = {
      ...baseDraft,
      pineSource: "//@version=5\nstrategy('t2')",
    };
    rerender({ draft: next });

    // 원래라면 500ms 시점이었으나, reset 되었으므로 save 아직 안 됨
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(window.localStorage.getItem(DRAFT_KEY)).toBeNull();

    // 추가 200ms (총 변경 후 500ms) 후 save — 최신 값으로 덮어씀
    act(() => {
      vi.advanceTimersByTime(200);
    });
    const parsed = JSON.parse(
      window.localStorage.getItem(DRAFT_KEY) as string,
    ) as WizardDraft;
    expect(parsed.pineSource).toBe(next.pineSource);
  });

  it("triggers a separate debounce when method changes", () => {
    const { rerender } = renderHook(({ draft }) => useAutoSaveDraft(draft), {
      initialProps: { draft: baseDraft },
    });

    // 첫 번째 save 완료
    act(() => {
      vi.advanceTimersByTime(500);
    });
    const first = JSON.parse(
      window.localStorage.getItem(DRAFT_KEY) as string,
    ) as WizardDraft;
    expect(first.method).toBe("direct");

    // method 만 변경
    const switched: DraftInput = { ...baseDraft, method: "upload" };
    rerender({ draft: switched });

    // 500ms 뒤 method 반영된 payload 저장
    act(() => {
      vi.advanceTimersByTime(500);
    });
    const second = JSON.parse(
      window.localStorage.getItem(DRAFT_KEY) as string,
    ) as WizardDraft;
    expect(second.method).toBe("upload");
  });

  it("picks up metadata via ref when scalar deps trigger the debounce", () => {
    // metadata 는 dep가 아니므로 단독 변경만으론 debounce가 다시 트리거되지 않는다.
    // 그러나 save 실행 시점에 ref.current에서 최신 metadata를 읽어가야 한다.
    const { rerender } = renderHook(({ draft }) => useAutoSaveDraft(draft), {
      initialProps: { draft: baseDraft },
    });

    // 300ms 시점에 metadata만 변경 (scalar dep 동일)
    act(() => {
      vi.advanceTimersByTime(300);
    });
    const metaUpdated: DraftInput = {
      ...baseDraft,
      metadata: { name: "renamed" },
    };
    rerender({ draft: metaUpdated });

    // 원래 첫 렌더 기준 500ms 시점에 save 발화 — ref가 최신 metadata를 보고 있어야 함
    act(() => {
      vi.advanceTimersByTime(200);
    });
    const parsed = JSON.parse(
      window.localStorage.getItem(DRAFT_KEY) as string,
    ) as WizardDraft;
    expect(parsed.metadata).toEqual({ name: "renamed" });
  });
});

describe("saveWizardDraft / loadWizardDraft / clearWizardDraft", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips a draft via save → load", () => {
    saveWizardDraft(baseDraft);
    const loaded = loadWizardDraft();
    expect(loaded).not.toBeNull();
    expect(loaded?.method).toBe("direct");
    expect(loaded?.pineSource).toBe(baseDraft.pineSource);
  });

  it("clear removes the stored draft", () => {
    saveWizardDraft(baseDraft);
    expect(loadWizardDraft()).not.toBeNull();
    clearWizardDraft();
    expect(loadWizardDraft()).toBeNull();
  });

  it("loadWizardDraft returns null when version mismatches", () => {
    window.localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        version: 2,
        savedAt: Date.now(),
        method: "direct",
        pineSource: "",
        metadata: {},
      }),
    );
    expect(loadWizardDraft()).toBeNull();
  });
});
