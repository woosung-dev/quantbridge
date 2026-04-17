"use client";

// Sprint 7c T4: wizard 입력 자동 저장 — localStorage v1 schema + 30일 TTL.
// Wizard 중단(새로고침/이탈) 시 pine_source + metadata 복원 → "이어서 작성" UX.

import { useEffect } from "react";

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
 * deps는 primitive value (method + pineSource)로 분해 — object literal re-render 무한 루프 회피.
 */
export function useAutoSaveDraft(draft: Omit<WizardDraft, "version" | "savedAt">): void {
  const { method, pineSource } = draft;
  useEffect(() => {
    const t = setTimeout(() => saveWizardDraft(draft), 500);
    return () => clearTimeout(t);
    // metadata는 Sprint 7c에서 persist하지 않음 — pine_source + method만 primitive deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [method, pineSource]);
}
