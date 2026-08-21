// 그리드서치 히트맵 축 계약 — 셀렉터의 「가로축」이 실제 열(thead th)을, 「세로축」이 행을 조작하는지 잠근다.
// 회귀 배경: 「가로축」 select 가 pair[0](행 변수)을 바꿔 사용자가 가로축으로 고른 변수가 세로에 나타났다.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GridSearchPairSelector } from "../grid-search-pair-selector";
import type { GridSearchResult } from "@/features/optimizer/schemas";

// 변수 3개 — 값 집합이 서로 겹치지 않게 두어 어느 변수가 어느 축에 렌더됐는지 판별한다.
const RESULT_3VAR: GridSearchResult = {
  schema_version: 1,
  kind: "grid_search",
  param_names: ["fastLength", "slowLength", "atrMult"],
  param_values: {
    fastLength: [10, 20],
    slowLength: [40, 50],
    atrMult: [1.5, 2.5],
  },
  cells: [
    {
      param_values: { fastLength: 10, slowLength: 40, atrMult: 1.5 },
      sharpe: 1.2,
      total_return: 80.1,
      max_drawdown: -12.3,
      num_trades: 120,
      is_degenerate: false,
      objective_value: 1.2,
    },
  ],
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  best_cell_index: 0,
};

/** thead 의 데이터 열 헤더(코너 th 제외) 텍스트 목록 */
function colHeaders(container: HTMLElement): string[] {
  return [...container.querySelectorAll("thead th")].slice(1).map((el) => el.textContent ?? "");
}

/** tbody 의 행 헤더(th[scope=row]) 텍스트 목록 */
function rowHeaders(container: HTMLElement): string[] {
  return [...container.querySelectorAll('tbody th[scope="row"]')].map((el) => el.textContent ?? "");
}

describe("GridSearchPairSelector — 축 셀렉터 ↔ 히트맵 렌더 방향 계약", () => {
  it("초기 상태 — 가로축 select 의 값이 열 헤더 변수와, 세로축 select 의 값이 행 헤더 변수와 일치한다", () => {
    const { container } = render(<GridSearchPairSelector result={RESULT_3VAR} />);
    const xSelect = screen.getByLabelText("히트맵 가로축 변수") as HTMLSelectElement;
    const ySelect = screen.getByLabelText("히트맵 세로축 변수") as HTMLSelectElement;
    // 초기 pair=[fastLength, slowLength] — 렌더는 행=fastLength, 열=slowLength.
    expect(colHeaders(container)).toEqual(["40", "50"]);
    expect(rowHeaders(container)).toEqual(["10", "20"]);
    // 셀렉터 라벨이 렌더와 같은 방향을 가리켜야 한다.
    expect(xSelect.value).toBe("slowLength");
    expect(ySelect.value).toBe("fastLength");
  });

  it("가로축 select 에서 변수 V 를 고르면 V 의 값들이 열 헤더(thead th)로 렌더된다", () => {
    const { container } = render(<GridSearchPairSelector result={RESULT_3VAR} />);
    fireEvent.change(screen.getByLabelText("히트맵 가로축 변수"), {
      target: { value: "atrMult" },
    });
    expect(colHeaders(container)).toEqual(["1.5", "2.5"]);
    // 세로축(행)은 그대로다.
    expect(rowHeaders(container)).toEqual(["10", "20"]);
  });

  it("세로축 select 에서 변수 V 를 고르면 V 의 값들이 행 헤더(tbody th[scope=row])로 렌더된다", () => {
    const { container } = render(<GridSearchPairSelector result={RESULT_3VAR} />);
    fireEvent.change(screen.getByLabelText("히트맵 세로축 변수"), {
      target: { value: "atrMult" },
    });
    expect(rowHeaders(container)).toEqual(["1.5", "2.5"]);
    // 가로축(열)은 그대로다.
    expect(colHeaders(container)).toEqual(["40", "50"]);
  });

  it("가로축에 세로축과 같은 변수를 고르면 세로축이 다른 변수로 스왑된다 (중복 축 금지)", () => {
    const { container } = render(<GridSearchPairSelector result={RESULT_3VAR} />);
    const ySelect = screen.getByLabelText("히트맵 세로축 변수") as HTMLSelectElement;
    // 세로축이 현재 fastLength — 가로축에도 fastLength 를 고른다.
    fireEvent.change(screen.getByLabelText("히트맵 가로축 변수"), {
      target: { value: "fastLength" },
    });
    expect(colHeaders(container)).toEqual(["10", "20"]);
    expect(ySelect.value).not.toBe("fastLength");
  });
});
