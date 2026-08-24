// ExchangeSupportTable — 공동 원장 4행: Bybit 데모 1행 지원 + 미지원 3행(무데이터 셀 title).
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ExchangeSupportTable } from "../exchange-support-table";

describe("ExchangeSupportTable", () => {
  afterEach(() => {
    cleanup();
  });

  it("4행 · 지원 1(chip done) · 지원하지 않음 3", () => {
    const { container } = render(<ExchangeSupportTable ariaLabel="t" />);
    expect(container.querySelectorAll("tbody tr").length).toBe(4);
    expect(container.querySelectorAll(".chip.done").length).toBe(1);
    expect(screen.getAllByText("지원하지 않음").length).toBe(3);
  });

  it("미지원 행 — 환경/확인 범위 무데이터 셀 + title 사유", () => {
    const { container } = render(<ExchangeSupportTable />);
    const emptyEnv = container.querySelectorAll(
      'td[title="지원하지 않는 거래소라 환경을 정하지 않았습니다."]',
    );
    const emptyScope = container.querySelectorAll(
      'td[title="지원하지 않는 거래소라 확인한 범위가 없습니다."]',
    );
    expect(emptyEnv.length).toBe(3);
    expect(emptyScope.length).toBe(3);
    emptyEnv.forEach((el) => expect(el.textContent).toBe("—"));
  });

  it("한글 표기 통일 — Bybit 데모만 지원", () => {
    render(<ExchangeSupportTable />);
    expect(screen.getAllByText("데모").length).toBe(1);
    expect(screen.queryByText("메인넷")).not.toBeInTheDocument();
    expect(screen.queryByText("Demo")).not.toBeInTheDocument();
    expect(screen.queryByText("로드맵")).not.toBeInTheDocument();
  });
});
