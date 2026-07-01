// 여러 라이브 세션의 누적 실현-PnL 곡선을 하나의 포트폴리오 곡선으로 병합하는 순수 헬퍼

export interface CurvePoint {
  time: number; // epoch seconds
  value: number;
}

/**
 * N개 세션의 누적(cumulative) PnL 곡선을 합산 병합.
 *
 * 각 곡선은 그 세션의 시각별 누적 실현손익이다. 서로 timestamp 가 다르므로
 * 전체 timestamp 합집합을 오름차순으로 훑으며, 각 곡선의 "그 시점까지의 마지막
 * 누적값"(carry-forward)을 더해 포트폴리오 누적 곡선을 만든다.
 *
 * 순수 함수. 입력 곡선은 time 오름차순 가정(정렬 안 돼 있어도 내부에서 정렬).
 */
export function mergeCumulativeCurves(
  curves: readonly (readonly CurvePoint[])[],
): CurvePoint[] {
  const sorted = curves
    .map((c) => [...c].sort((a, b) => a.time - b.time))
    .filter((c) => c.length > 0);
  if (sorted.length === 0) return [];

  const allTimes = Array.from(
    new Set(sorted.flatMap((c) => c.map((p) => p.time))),
  ).sort((a, b) => a - b);

  const cursor = sorted.map(() => 0);
  const lastValue = sorted.map(() => 0);
  const out: CurvePoint[] = [];

  for (const t of allTimes) {
    let sum = 0;
    for (let i = 0; i < sorted.length; i++) {
      const curve = sorted[i]!;
      while (cursor[i]! < curve.length && curve[cursor[i]!]!.time <= t) {
        lastValue[i] = curve[cursor[i]!]!.value;
        cursor[i]!++;
      }
      sum += lastValue[i]!;
    }
    out.push({ time: t, value: sum });
  }
  return out;
}
