"use client";

import { useEffect, useState } from "react";

/** 값이 바뀐 뒤 지정한 시간이 지나면 최신 값을 반환한다. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
