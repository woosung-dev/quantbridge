// 주기적으로 갱신되는 현재 시각(ms). 「N분 전」 같은 상대 시간 문구가 부모 재렌더에 기대지 않고
// 스스로 흐르게 한다 — React Compiler 가 켜진 뒤로는 부모 재렌더가 자식까지 내려가지 않는다(2026-11-04).
"use client";

import { useEffect, useState } from "react";

export function useNowTick(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}
