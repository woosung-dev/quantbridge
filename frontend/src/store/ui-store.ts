import { create } from "zustand";

// 전역 UI 상태 — 트리를 넓게 넘나드는 것만 유지 (frontend.md 3.2)
type Theme = "light" | "dash";

interface UiState {
  sidebarOpen: boolean;
  // 모바일 nav drawer 열림 상태 — Sprint 60 S4 BL-300 (desktop sidebar 와 분리)
  mobileNavOpen: boolean;
  theme: Theme;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setMobileNavOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  mobileNavOpen: false,
  theme: "light",
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
  setTheme: (theme) => set({ theme }),
}));
