// Sprint 54 — Grid Search N>2 변수쌍 선택 (heatmap 2D viz 강제, N-dim viz Sprint 55+).
"use client";

import { useState } from "react";

import { GridSearchHeatmap } from "./grid-search-heatmap";
import type { GridSearchResult } from "@/features/optimizer/schemas";

interface Props {
  result: GridSearchResult;
}

export function GridSearchPairSelector({ result }: Props) {
  const names = result.param_names;
  const initial: [string, string] = names.length >= 2
    ? [names[0]!, names[1]!]
    : ["", ""];
  const [pair, setPair] = useState<[string, string]>(initial);

  if (names.length < 2) {
    // 1D — 안내만 표시.
    return (
      <div className="rounded border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
        param_space 변수 1개 — 2D heatmap 미적용. 결과 표는 detail 페이지의 cells list 참고.
      </div>
    );
  }

  if (names.length === 2) {
    return <GridSearchHeatmap result={result} pair={[names[0]!, names[1]!]} />;
  }

  // N>2 — 변수쌍 선택 prompt.
  return (
    <div className="space-y-4">
      <div className="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/10 dark:text-amber-100">
        <strong className="block font-medium">N-dim 결과 ({names.length} 변수)</strong>
        heatmap 표시할 변수쌍 2개 선택 (best cell 의 나머지 변수 값으로 slice).
        Sprint 55+ N-dim viz (parallel-coord / surface) 확장 예정.
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-muted-foreground">X 축:</span>
          <select
            className="rounded border border-input bg-background px-2 py-1 text-sm"
            value={pair[0]}
            onChange={(e) => {
              const v = e.target.value;
              setPair(([_, y]) => (y === v ? [v, names.find((n) => n !== v) ?? y] : [v, y]));
            }}
          >
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-muted-foreground">Y 축:</span>
          <select
            className="rounded border border-input bg-background px-2 py-1 text-sm"
            value={pair[1]}
            onChange={(e) => {
              const v = e.target.value;
              setPair(([x, _]) => (x === v ? [names.find((n) => n !== v) ?? x, v] : [x, v]));
            }}
          >
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>
      <GridSearchHeatmap result={result} pair={pair} />
    </div>
  );
}
