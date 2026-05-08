// 파싱 결과 하단 패널 — 3 탭 / problem count / aria-live (Sprint 43 W9-fidelity)
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ParsePanel } from "../parse-panel";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const okResult: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 2,
  exit_count: 1,
  functions_used: ["ta.sma", "ta.crossover", "strategy.entry"],
  unsupported_builtins: [],
  is_runnable: true,
};

const unsupportedResult: ParsePreviewResponse = {
  ...okResult,
  status: "unsupported",
  is_runnable: false,
  unsupported_builtins: ["ta.foobar", "strategy.barbaz"],
};

describe("ParsePanel", () => {
  it("loading 시 '파싱 중...' 안내", () => {
    render(<ParsePanel result={null} loading />);
    expect(screen.getByText("파싱 중...")).toBeInTheDocument();
  });

  it("result 가 있으면 stagger 항목들이 렌더링됨", () => {
    render(<ParsePanel result={okResult} />);
    expect(screen.getAllByTestId("parse-panel-item").length).toBeGreaterThanOrEqual(3);
    // status 라벨이 제목 항목에 포함
    expect(
      screen.getByText(/Pine Script v5 감지/),
    ).toBeInTheDocument();
  });

  it("미지원 함수가 있으면 '문제' 탭에 count badge + 항목 표시", () => {
    render(<ParsePanel result={unsupportedResult} />);

    // 탭 라벨에 count 2 노출
    const problemTab = screen.getByRole("tab", { name: /문제/ });
    expect(problemTab).toHaveTextContent("2");

    fireEvent.click(problemTab);

    expect(screen.getByText(/미지원 함수: ta.foobar/)).toBeInTheDocument();
    expect(screen.getByText(/미지원 함수: strategy.barbaz/)).toBeInTheDocument();
  });

  it("aria-live='polite' 로 결과 변경을 announce", () => {
    render(<ParsePanel result={okResult} />);
    expect(screen.getByTestId("parse-panel")).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });
});
