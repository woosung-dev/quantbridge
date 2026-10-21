"use client";

import { useCallback, useState } from "react";

// 실제 DOM이 연결될 때 측정한다. 빈 데이터→차트 전환과 숨김→표시도 감지한다.
// React 19 callback ref의 cleanup으로 관찰자를 해제한다.
export function useChartWidth() {
  const [hasWidth, setHasWidth] = useState(false);
  const wrapperRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    const ready = node.getBoundingClientRect().width > 0;
    setHasWidth(ready);
    if (ready || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      if (entries.some((entry) => entry.contentRect.width > 0)) {
        setHasWidth(true);
        observer.disconnect();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return { wrapperRef, hasWidth };
}
