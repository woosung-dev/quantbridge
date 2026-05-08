// ParseResultPanel — loading / error / null / result 분기 + stagger className (Sprint 42-polish W3)

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ParseResultPanel } from "../parse-result-panel";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const baseResult: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 2,
  exit_count: 1,
  functions_used: ["ta.sma", "ta.crossover", "strategy.entry", "strategy.exit"],
  unsupported_builtins: [],
  is_runnable: true,
};

describe("ParseResultPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("loading=true → 파싱 중 텍스트 + skeleton 노출", () => {
    render(<ParseResultPanel result={null} loading={true} />);

    expect(screen.getByText("파싱 중...")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: /파싱 중/ })).toBeInTheDocument();
  });

  it("error 메시지 prop 있으면 alert 렌더", () => {
    render(<ParseResultPanel result={null} loading={false} error="네트워크 오류" />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("네트워크 오류");
  });

  it("result=null 이고 loading 아니면 empty hint 노출", () => {
    render(<ParseResultPanel result={null} loading={false} />);

    expect(
      screen.getByText("코드 입력 후 파싱 결과가 여기 표시됩니다."),
    ).toBeInTheDocument();
  });

  it("result 있으면 info row + 함수 + feature pills + stagger className 적용", () => {
    render(<ParseResultPanel result={baseResult} loading={false} />);

    // info rows 4개 (상태 / 버전 / 진입 / 청산)
    const infoRows = screen.getAllByTestId("parse-info-row");
    expect(infoRows).toHaveLength(4);
    // stagger animation class 적용 확인
    expect(infoRows[0]?.className).toMatch(/staggerIn/);

    // 함수 row (상위 4개)
    const fnRows = screen.getAllByTestId("parse-fn-row");
    expect(fnRows).toHaveLength(4);
    expect(fnRows[0]).toHaveTextContent("ta.sma");

    // feature pills — 진입 시그널 / 청산 시그널 / 실행 가능 모두 present
    expect(screen.getByText("진입 시그널")).toBeInTheDocument();
    expect(screen.getByText("청산 시그널")).toBeInTheDocument();
    expect(screen.getByText("실행 가능")).toBeInTheDocument();
  });
});
