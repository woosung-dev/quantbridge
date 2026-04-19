import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import {
  DRAFT_KEY_VERSION_PREFIX,
  clearOtherUsersDrafts,
  clearWizardDraft,
  draftKeyFor,
  loadWizardDraft,
  saveWizardDraft,
  useAutoSaveDraft,
  useDraftSnapshot,
  type WizardDraft,
} from "@/features/strategy/draft";

const USER_A = "user_A";
const USER_B = "user_B";

type DraftInput = Omit<WizardDraft, "version" | "savedAt">;

const baseDraft: DraftInput = {
  method: "direct",
  pineSource: "//@version=5\nstrategy('t')",
  metadata: { name: "s1" },
};

describe("useAutoSaveDraft (debounce + userId scoping)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("500ms 이후 현재 userId 키에 draft 를 저장한다", () => {
    renderHook(({ uid, draft }) => useAutoSaveDraft(uid, draft), {
      initialProps: { uid: USER_A, draft: baseDraft },
    });

    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    const raw = window.localStorage.getItem(draftKeyFor(USER_A));
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw as string) as WizardDraft;
    expect(parsed.method).toBe("direct");
    expect(parsed.pineSource).toBe(baseDraft.pineSource);
    expect(parsed.metadata).toEqual(baseDraft.metadata);
  });

  it("pineSource 변경 시 타이머가 리셋되고 최종 값이 저장된다", () => {
    const { rerender } = renderHook(
      ({ uid, draft }) => useAutoSaveDraft(uid, draft),
      { initialProps: { uid: USER_A, draft: baseDraft } },
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();

    const next: DraftInput = {
      ...baseDraft,
      pineSource: "//@version=5\nstrategy('t2')",
    };
    rerender({ uid: USER_A, draft: next });

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    const parsed = JSON.parse(
      window.localStorage.getItem(draftKeyFor(USER_A)) as string,
    ) as WizardDraft;
    expect(parsed.pineSource).toBe(next.pineSource);
  });

  it("metadata 는 ref 를 통해 최신 값이 저장 payload 에 반영된다", () => {
    const { rerender } = renderHook(
      ({ uid, draft }) => useAutoSaveDraft(uid, draft),
      { initialProps: { uid: USER_A, draft: baseDraft } },
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });
    const metaUpdated: DraftInput = {
      ...baseDraft,
      metadata: { name: "renamed" },
    };
    rerender({ uid: USER_A, draft: metaUpdated });

    act(() => {
      vi.advanceTimersByTime(200);
    });
    const parsed = JSON.parse(
      window.localStorage.getItem(draftKeyFor(USER_A)) as string,
    ) as WizardDraft;
    expect(parsed.metadata).toEqual({ name: "renamed" });
  });

  it("userId 가 null 이면 저장하지 않는다 (로그아웃 레이스)", () => {
    renderHook(({ uid, draft }) => useAutoSaveDraft(uid, draft), {
      initialProps: { uid: null as string | null, draft: baseDraft },
    });

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(window.localStorage.length).toBe(0);
  });

  it("userId 전환 시 이전 userId 의 draft 를 삭제한다", () => {
    // 선조건: user_A 키에 이미 draft 가 있음
    saveWizardDraft(USER_A, baseDraft);
    expect(window.localStorage.getItem(draftKeyFor(USER_A))).not.toBeNull();

    const { rerender } = renderHook(
      ({ uid, draft }) => useAutoSaveDraft(uid, draft),
      { initialProps: { uid: USER_A, draft: baseDraft } },
    );

    // sign-out 후 user_B 로 로그인
    rerender({ uid: USER_B, draft: baseDraft });

    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();
    // user_B 저장은 debounce 경과 후
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(window.localStorage.getItem(draftKeyFor(USER_B))).not.toBeNull();
  });
});

describe("save / load / clear — userId scoped", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("draft 는 userId 별 키에 저장된다", () => {
    saveWizardDraft(USER_A, baseDraft);
    const key = draftKeyFor(USER_A);
    expect(key).toBe(`${DRAFT_KEY_VERSION_PREFIX}:${USER_A}`);
    expect(window.localStorage.getItem(key)).not.toBeNull();
  });

  it("다른 userId 로는 해당 draft 가 보이지 않는다", () => {
    saveWizardDraft(USER_A, baseDraft);
    expect(loadWizardDraft(USER_B)).toBeNull();
    expect(loadWizardDraft(USER_A)).not.toBeNull();
  });

  it("load / clear 는 userId nullish 이면 no-op", () => {
    expect(loadWizardDraft(null)).toBeNull();
    expect(loadWizardDraft(undefined)).toBeNull();

    saveWizardDraft(USER_A, baseDraft);
    clearWizardDraft(null);
    expect(loadWizardDraft(USER_A)).not.toBeNull();

    clearWizardDraft(USER_A);
    expect(loadWizardDraft(USER_A)).toBeNull();
  });

  it("version 미일치 시 null 반환 + key 유지 (v2 migration 여지)", () => {
    window.localStorage.setItem(
      draftKeyFor(USER_A),
      JSON.stringify({
        version: 2,
        savedAt: Date.now(),
        method: "direct",
        pineSource: "",
        metadata: {},
      }),
    );
    expect(loadWizardDraft(USER_A)).toBeNull();
  });
});

describe("clearOtherUsersDrafts", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("현재 userId 를 제외한 모든 scoped draft 를 제거한다", () => {
    saveWizardDraft(USER_A, baseDraft);
    saveWizardDraft(USER_B, baseDraft);
    saveWizardDraft("user_C", baseDraft);

    clearOtherUsersDrafts(USER_B);

    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();
    expect(window.localStorage.getItem("user_C")).toBeNull();
    expect(window.localStorage.getItem(draftKeyFor(USER_B))).not.toBeNull();
  });

  it("prefix 가 다른 localStorage 키는 보존한다", () => {
    window.localStorage.setItem("other-app:settings", "{}");
    saveWizardDraft(USER_A, baseDraft);

    clearOtherUsersDrafts(USER_A);

    expect(window.localStorage.getItem("other-app:settings")).toBe("{}");
    expect(window.localStorage.getItem(draftKeyFor(USER_A))).not.toBeNull();
  });

  it("currentUserId 가 null 이면 모든 scoped draft 를 제거한다", () => {
    saveWizardDraft(USER_A, baseDraft);
    saveWizardDraft(USER_B, baseDraft);

    clearOtherUsersDrafts(null);

    expect(window.localStorage.getItem(draftKeyFor(USER_A))).toBeNull();
    expect(window.localStorage.getItem(draftKeyFor(USER_B))).toBeNull();
  });
});

describe("useDraftSnapshot (render-time localStorage derive)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("userId 가 null 이면 null 을 반환한다", () => {
    const { result } = renderHook(({ uid }) => useDraftSnapshot(uid), {
      initialProps: { uid: null as string | null },
    });
    expect(result.current).toBeNull();
  });

  it("해당 userId 로 저장된 draft 를 반영한다", () => {
    saveWizardDraft(USER_A, baseDraft);
    const { result } = renderHook(({ uid }) => useDraftSnapshot(uid), {
      initialProps: { uid: USER_A as string | null },
    });
    expect(result.current).not.toBeNull();
    expect(result.current?.pineSource).toBe(baseDraft.pineSource);
  });

  it("clearWizardDraft 후 useSyncExternalStore 가 null 로 업데이트된다", () => {
    saveWizardDraft(USER_A, baseDraft);
    const { result } = renderHook(({ uid }) => useDraftSnapshot(uid), {
      initialProps: { uid: USER_A as string | null },
    });
    expect(result.current).not.toBeNull();

    act(() => {
      clearWizardDraft(USER_A);
    });
    expect(result.current).toBeNull();
  });
});
