// 그리드 탐색 N>2 변수쌍 선택 — C 디자인 언어 이식 (W3-C). heatmap 2D 표시용 축 2개 선택.
"use client";

import { useState } from "react";

import { GridSearchHeatmap } from "./grid-search-heatmap";
import type { GridSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: GridSearchResult;
}

export function GridSearchPairSelector({ result }: Props) {
  const names = result.param_names;
  const initial: [string, string] = names.length >= 2 ? [names[0]!, names[1]!] : ["", ""];
  const [pair, setPair] = useState<[string, string]>(initial);

  if (names.length < 2) {
    // 1D — 안내만 표시.
    return (
      <p className="chart-note" style={{ paddingLeft: 0, paddingRight: 0 }}>
        파라미터 공간이 변수 1개라 2D 히트맵을 그리지 않습니다. 위 리더보드가 전체 조합을
        순위로 보여 줍니다.
      </p>
    );
  }

  if (names.length === 2) {
    return <GridSearchHeatmap result={result} pair={[names[0]!, names[1]!]} />;
  }

  // N>2 — 변수쌍 선택 prompt.
  return (
    <div>
      <p className="notice-inline" style={{ marginBottom: 14 }} role="status">
        <span>
          변수 {names.length}개 결과입니다. 히트맵으로 볼 변수쌍 2개를 고르세요. 나머지 변수는
          최적 셀 값으로 고정한 단면을 그립니다.
        </span>
      </p>
      <div className="toolbar" style={{ marginBottom: 14 }}>
        <span className="field">
          <span className="field-label">가로축</span>
          <select
            className="select"
            aria-label="히트맵 가로축 변수"
            value={pair[0]}
            onChange={(e) => {
              const v = e.target.value;
              setPair(([, y]) => (y === v ? [v, names.find((n) => n !== v) ?? y] : [v, y]));
            }}
          >
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </span>
        <span className="field">
          <span className="field-label">세로축</span>
          <select
            className="select"
            aria-label="히트맵 세로축 변수"
            value={pair[1]}
            onChange={(e) => {
              const v = e.target.value;
              setPair(([x]) => (x === v ? [names.find((n) => n !== v) ?? x, v] : [x, v]));
            }}
          >
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </span>
      </div>
      <GridSearchHeatmap result={result} pair={pair} />
    </div>
  );
}
