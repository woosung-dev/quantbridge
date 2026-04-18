"use client";

// Sprint 7c T4: wizard 입력 자동 저장 — localStorage v1 schema + 30일 TTL.
// Wizard 중단(새로고침/이탈) 시 pine_source + metadata 복원 → "이어서 작성" UX.

import { useEffect, useRef } from "react";

const DRAFT_KEY = "sprint7c:strategy-wizard-draft:v1";
const TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30일

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

export function loadWizardDraft(): WizardDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WizardDraft;
    if (parsed.version !== 1) return null;
    if (Date.now() - parsed.savedAt > TTL_MS) {
      window.localStorage.removeItem(DRAFT_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveWizardDraft(draft: Omit<WizardDraft, "version" | "savedAt">): void {
  if (typeof window === "undefined") return;
  const payload: WizardDraft = { version: 1, savedAt: Date.now(), ...draft };
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(payload));
  } catch {
    // quota exceeded 등 무시 — wizard는 draft 없이도 동작
  }
}

export function clearWizardDraft(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(DRAFT_KEY);
}

/**
 * 입력 state를 500ms debounce로 자동 저장.
 *
 * dep는 primitive value (method + pineSource)만 사용 — object literal을 그대로 dep에
 * 넣으면 매 render 새 참조라 debounce가 매번 리셋되어 사실상 무효화되고, 생략하면
 * exhaustive-deps 위반 + React Compiler 최적화 skip 경고가 나온다.
 *
 * React 공식 권장 패턴 대로 `useRef`에 최신 draft를 commit phase에 싱크하고,
 * 타임아웃 콜백은 실행 시점에 `draftRef.current`를 읽는다. ref를 render 중에
 * 직접 대입하면 React Compiler의 "Cannot access refs during render" rule 위반이므로,
 * sync 전용 useEffect(의존성 배열 없음 — 매 commit 후 실행)에서 수행한다.
 *
 * - 첫 effect: render commit 후 `draftRef.current = draft`로 최신 값 동기화
 * - 두 번째 effect: debounce 트리거용 scalar dep (method + pineSource)만
 * - metadata 변경은 debounce를 트리거하지 않지만, 발화 시점에 ref에서 최신 값을 가져가므로
 *   저장 payload에는 그대로 반영된다
 */
export function useAutoSaveDraft(draft: Omit<WizardDraft, "version" | "savedAt">): void {
  const draftRef = useRef(draft);

  useEffect(() => {
    draftRef.current = draft;
  });

  const { method, pineSource } = draft;
  useEffect(() => {
    const t = setTimeout(() => saveWizardDraft(draftRef.current), 500);
    return () => clearTimeout(t);
  }, [method, pineSource]);
}
