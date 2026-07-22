// LandingSupport (C 이식) — 거래소 지원 5행 표(무데이터 셀 title) + 로드맵 3문장 고지.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingSupport } from "../landing-support";

describe("LandingSupport", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=support + 거래소 표 5행", () => {
    const { container } = render(<LandingSupport />);
    expect(container.querySelector("#support")).not.toBeNull();
    const rows = container.querySelectorAll("table.trades tbody tr");
    expect(rows.length).toBe(5);
  });

  it("Bybit 2행 지원(chip done) + 로드맵 3행(무데이터 셀 title)", () => {
    const { container } = render(<LandingSupport />);
    const done = container.querySelectorAll("table.trades .chip.done");
    expect(done.length).toBe(2);
    expect(screen.getAllByText("로드맵").length).toBe(3);
    // 무데이터 셀 — 값이 EMPTY_CELL 하나뿐 + title 로 사유
    const emptyEnv = container.querySelector(
      'td[title="연결 작업을 시작하지 않아 환경을 정하지 않았습니다."]',
    );
    expect(emptyEnv?.textContent).toBe("—");
  });

  it("로드맵 3문장 고지 노출 (착수/완료 미약속)", () => {
    render(<LandingSupport />);
    expect(screen.getByText(/착수일이나 완료일을 약속하는 말이 아닙니다/)).toBeInTheDocument();
  });
});
