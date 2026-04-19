"use client";

import { useCallback, useSyncExternalStore } from "react";

// SSR-safe media query 훅. 서버에서는 false (desktop 기본) 를 반환하여 hydration mismatch 를 피하고,
// 클라이언트 mount 시 실제 matchMedia 결과로 동기화된다. useSyncExternalStore 를 사용해
// LESSON-004 (useEffect + setState 케스케이드) 를 원천 차단.
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
        return () => {};
      }
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onStoreChange);
      return () => mql.removeEventListener("change", onStoreChange);
    },
    [query],
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(query).matches;
  }, [query]);

  const getServerSnapshot = useCallback(() => false, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
