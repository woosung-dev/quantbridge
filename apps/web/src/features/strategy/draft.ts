"use client";

// Sprint 7c T4 / Sprint FE-C: wizard 입력 자동 저장 — localStorage v1 schema + 30일 TTL.
// Sprint FE-C: Clerk userId 별 스코핑. 같은 기기에서 계정 전환 시 이전 계정 draft 누출 방지.
// Key 스키마: `${DRAFT_KEY_VERSION_PREFIX}:${userId}`.

import { useEffect, useRef, useSyncExternalStore } from "react";

export const DRAFT_KEY_VERSION_PREFIX = "sprint7c:strategy-wizard-draft:v1";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30일

export function draftKeyFor(userId: string): string {
  return `${DRAFT_KEY_VERSION_PREFIX}:${userId}`;
}

export interface WizardDraft {
  version: 1;
  savedAt: number;
  method: "direct" | "upload" | "url";
  pineSource: string;
  metadata: {
    name?: string;
    description?: string;
    symbol?: string;
    timeframe?: string;
    tags?: string[];
  };
}

export function loadWizardDraft(userId: string | null | undefined): WizardDraft | null {
  if (typeof window === "undefined") return null;
  if (!userId) return null;
  try {
    const key = draftKeyFor(userId);
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WizardDraft;
    if (parsed.version !== 1) return null;
    if (Date.now() - parsed.savedAt > TTL_MS) {
      window.localStorage.removeItem(key);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveWizardDraft(
  userId: string | null | undefined,
  draft: Omit<WizardDraft, "version" | "savedAt">,
): void {
  if (typeof window === "undefined") return;
  if (!userId) return;
  const payload: WizardDraft = { version: 1, savedAt: Date.now(), ...draft };
  try {
    window.localStorage.setItem(draftKeyFor(userId), JSON.stringify(payload));
    snapshotCache.delete(snapshotKey(userId));
    notifyDraftChanged();
  } catch {
    // quota exceeded 등 무시 — wizard는 draft 없이도 동작
  }
}

export function clearWizardDraft(userId: string | null | undefined): void {
  if (typeof window === "undefined") return;
  if (!userId) return;
  window.localStorage.removeItem(draftKeyFor(userId));
  snapshotCache.delete(snapshotKey(userId));
  notifyDraftChanged();
}

// Render-time localStorage 읽기 캐시. useSyncExternalStore 가 동일 참조를 반환하도록 보장.
// key: userId | "__anon__". value: { stamp: 직렬화된 원본, parsed: 파싱 결과 }.
// stamp 비교로 외부 storage event 없이도 로컬 mutation (save/clear) 후 stale 방지.
const snapshotCache = new Map<
  string,
  { stamp: string | null; parsed: WizardDraft | null }
>();

function snapshotKey(userId: string | null | undefined): string {
  return userId ?? "__anon__";
}

function readSnapshot(userId: string | null | undefined): WizardDraft | null {
  if (typeof window === "undefined") return null;
  if (!userId) return null;
  const key = draftKeyFor(userId);
  const stamp = window.localStorage.getItem(key);
  const cached = snapshotCache.get(snapshotKey(userId));
  if (cached && cached.stamp === stamp) return cached.parsed;
  const parsed = loadWizardDraft(userId);
  snapshotCache.set(snapshotKey(userId), { stamp, parsed });
  return parsed;
}

// 모듈 단위 subscriber — same-window mutation 을 useSyncExternalStore 가 알아차리도록
// save/clear 계열이 호출될 때 수동으로 emit.
const draftListeners = new Set<() => void>();

function subscribeDraft(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  draftListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    draftListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function notifyDraftChanged(): void {
  for (const listener of draftListeners) listener();
}

// 현재 userId 의 draft 존재 여부를 reactive 하게 반영. setState-in-effect 없이
// render-time 에 localStorage 를 derive 하려는 목적 (LESSON-004 정책 호환).
export function useDraftSnapshot(userId: string | null | undefined): WizardDraft | null {
  return useSyncExternalStore(
    subscribeDraft,
    () => readSnapshot(userId),
    () => null,
  );
}

// 현재 userId 를 제외한 모든 wizard draft 제거 — 계정 전환/공유 기기 대비.
export function clearOtherUsersDrafts(currentUserId: string | null | undefined): void {
  if (typeof window === "undefined") return;
  const storage = window.localStorage;
  const prefix = `${DRAFT_KEY_VERSION_PREFIX}:`;
  const keepKey = currentUserId ? draftKeyFor(currentUserId) : null;
  const toRemove: string[] = [];
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (!key) continue;
    if (!key.startsWith(prefix)) continue;
    if (key === keepKey) continue;
    toRemove.push(key);
  }
  if (toRemove.length === 0) return;
  for (const key of toRemove) {
    storage.removeItem(key);
  }
  snapshotCache.clear();
  notifyDraftChanged();
}

/**
 * 입력 state를 500ms debounce로 자동 저장.
 *
 * - userId 변경 감지: 이전 userId 의 draft 를 best-effort 로 삭제 (signout 후 다른 계정 로그인 대비).
 * - dep는 primitive value (method + pineSource + userId)만 사용 — object literal을 그대로 dep에
 *   넣으면 매 render 새 참조라 debounce가 매번 리셋.
 * - ref를 render 중에 직접 대입하면 React Compiler의 "Cannot access refs during render" rule 위반
 *   (LESSON-006). 따라서 sync 전용 useEffect (deps 없음) 에서 수행.
 */
export function useAutoSaveDraft(
  userId: string | null | undefined,
  draft: Omit<WizardDraft, "version" | "savedAt">,
): void {
  const draftRef = useRef(draft);
  const prevUserIdRef = useRef<string | null | undefined>(userId);

  useEffect(() => {
    draftRef.current = draft;
  });

  useEffect(() => {
    const prev = prevUserIdRef.current;
    if (prev && prev !== userId) {
      clearWizardDraft(prev);
    }
    prevUserIdRef.current = userId;
  }, [userId]);

  const { method, pineSource } = draft;
  useEffect(() => {
    if (!userId) return;
    const t = setTimeout(() => saveWizardDraft(userId, draftRef.current), 500);
    return () => clearTimeout(t);
  }, [method, pineSource, userId]);
}
