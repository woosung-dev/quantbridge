// ExchangeSupportTable — 공동 원장 5행: Bybit 2행 지원 + 로드맵 3행(무데이터 셀 title).
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ExchangeSupportTable } from "../exchange-support-table";

describe("ExchangeSupportTable", () => {
  afterEach(() => {
    cleanup();
  });

  it("5행 · 지원 2(chip done) · 로드맵 3", () => {
    const { container } = render(<ExchangeSupportTable ariaLabel="t" />);
    expect(container.querySelectorAll("tbody tr").length).toBe(5);
    expect(container.querySelectorAll(".chip.done").length).toBe(2);
    expect(screen.getAllByText("로드맵").length).toBe(3);
  });

  it("로드맵 행 — 환경/확인 범위 무데이터 셀 + title 사유", () => {
    const { container } = render(<ExchangeSupportTable />);
    const emptyEnv = container.querySelectorAll(
      'td[title="연결 작업을 시작하지 않아 환경을 정하지 않았습니다."]',
    );
    const emptyScope = container.querySelectorAll(
      'td[title="연결 코드가 없어 확인한 범위가 없습니다."]',
    );
    expect(emptyEnv.length).toBe(3);
    expect(emptyScope.length).toBe(3);
    emptyEnv.forEach((el) => expect(el.textContent).toBe("—"));
  });

  it("한글 표기 통일 — Demo/Mainnet 영문 미사용", () => {
    render(<ExchangeSupportTable />);
    expect(screen.getAllByText("데모").length).toBe(1);
    expect(screen.getAllByText("메인넷").length).toBe(1);
    expect(screen.queryByText("Demo")).not.toBeInTheDocument();
  });
});
