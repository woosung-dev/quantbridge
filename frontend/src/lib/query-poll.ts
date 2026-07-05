// React Query refetchInterval 순수 함수 팩토리 — LESSON-004(error→false 폴링 중단) 가드의 SSOT.

import type { Query } from "@tanstack/react-query";

export type RefetchIntervalFn<TData> = (q: Query<TData, Error>) => number | false;

/**
 * refetchInterval 함수 생성 — error 상태면 무조건 false(LESSON-004 CPU 루프 방지 가드 내장),
 * 그 외에는 `compute(data)` 결과를 그대로 반환한다.
 * 상수 간격 폴링은 `makeRefetchInterval(() => MS)`, 데이터 의존 간격은 compute 에 순수 함수를 전달.
 */
export function makeRefetchInterval<TData>(
  compute: (data: TData | undefined) => number | false,
): RefetchIntervalFn<TData> {
  return (q) => {
    if (q.state.status === "error") return false;
    return compute(q.state.data);
  };
}

/**
 * status 폴링용 refetchInterval 생성 — terminal status 도달 시 폴링 중단.
 * - error 상태 → false (makeRefetchInterval 가드)
 * - data 미도착 → intervalMs 유지 (첫 응답 전 폴링 지속)
 * - `getStatus(data)` ∈ terminalStatuses → false
 * - 그 외 → intervalMs
 */
export function makeStatusPoll<TData>(
  getStatus: (data: TData) => string,
  terminalStatuses: ReadonlySet<string>,
  intervalMs: number,
): RefetchIntervalFn<TData> {
  return makeRefetchInterval((data) => {
    if (data == null) return intervalMs;
    return terminalStatuses.has(getStatus(data)) ? false : intervalMs;
  });
}
