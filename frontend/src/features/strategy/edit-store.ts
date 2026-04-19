"use client";

// Sprint FE-03: Edit page 편집 버퍼 Zustand store.
// TabCode(Monaco) 와 TabParse(preview) 가 동일한 pineSource 를 공유하고,
// 서버 스냅샷과 비교해 isDirty 를 계산 → Save 버튼 + unload 경고가 이를 구독.
//
// Selector 계약:
// - 반드시 scalar selector (`useEditStore(s => s.xxx)`) 로만 사용.
// - 객체 selector (`s => ({...})`) 또는 전체 store 를 dep 로 넣으면 매 render 새 참조가 돼서
//   useEffect 가 무한 루프 또는 react-hooks/exhaustive-deps 위반을 유발한다 (LESSON-004).

import { create } from "zustand";

export interface EditState {
  strategyId: string | null;
  pineSource: string;
  serverSnapshot: string;
  lastSavedAt: Date | null;
  setPineSource: (source: string) => void;
  loadServerSnapshot: (strategyId: string, pineSource: string) => void;
  markSaved: (savedAt: Date) => void;
  resetDirty: () => void;
}

export const useEditStore = create<EditState>((set) => ({
  strategyId: null,
  pineSource: "",
  serverSnapshot: "",
  lastSavedAt: null,
  setPineSource: (source) => set({ pineSource: source }),
  loadServerSnapshot: (strategyId, pineSource) =>
    set({
      strategyId,
      pineSource,
      serverSnapshot: pineSource,
      lastSavedAt: null,
    }),
  markSaved: (savedAt) =>
    set((state) => ({
      serverSnapshot: state.pineSource,
      lastSavedAt: savedAt,
    })),
  resetDirty: () =>
    set((state) => ({
      pineSource: state.serverSnapshot,
    })),
}));

export const selectPineSource = (s: EditState): string => s.pineSource;
export const selectServerSnapshot = (s: EditState): string => s.serverSnapshot;
export const selectIsDirty = (s: EditState): boolean =>
  s.pineSource !== s.serverSnapshot;
export const selectLastSavedAt = (s: EditState): Date | null => s.lastSavedAt;
export const selectStrategyId = (s: EditState): string | null => s.strategyId;
