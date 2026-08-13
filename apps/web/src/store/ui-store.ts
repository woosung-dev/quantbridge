import { create } from "zustand";

// 전역 UI 상태 — 트리를 넓게 넘나드는 것만 유지 (frontend.md 3.2)
// C 이식 S3: 데스크톱 sidebar 접힘/펼침(sidebarOpen)은 순수 CSS 아이콘 레일(globals.css
// @media --sidebar-w)로 대체됐다. 런타임 상수 true 였고 호출자가 0이라 삭제했다.
// 모바일 nav drawer 상태만 전역으로 남는다.
interface UiState {
  // 모바일 nav drawer 열림 상태 — Sprint 60 S4 BL-300 (desktop sidebar 와 분리)
  mobileNavOpen: boolean;
  setMobileNavOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  mobileNavOpen: false,
  setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
}));
