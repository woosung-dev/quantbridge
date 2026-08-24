// LandingSupport (C 이식) — SSOT 거래소 지원표와 무데이터 셀 title을 렌더한다.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import {
  EMPTY_CELL,
  EXCHANGE_NO_ENV_TITLE,
  EXCHANGE_SUPPORT,
  ROADMAP_DISCLAIMER,
} from "@/lib/marketing-canon";

import { LandingSupport } from "../landing-support";

describe("LandingSupport", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=support + SSOT 거래소 표 행 수", () => {
    const { container } = render(<LandingSupport />);
    expect(container.querySelector("#support")).not.toBeNull();
    const rows = container.querySelectorAll("table.trades tbody tr");
    expect(rows.length).toBe(EXCHANGE_SUPPORT.length);
  });

  it("SSOT 지원·미지원 상태와 무데이터 셀 title", () => {
    const { container } = render(<LandingSupport />);
    const done = container.querySelectorAll("table.trades .chip.done");
    const supportedRows = EXCHANGE_SUPPORT.filter(({ status }) => status === "supported");
    const unsupportedRows = EXCHANGE_SUPPORT.filter(({ status }) => status === "unsupported");

    expect(done.length).toBe(supportedRows.length);
    expect(screen.getAllByText("지원하지 않음").length).toBe(unsupportedRows.length);
    // 무데이터 셀 — 값이 EMPTY_CELL 하나뿐 + title 로 사유
    const emptyEnv = container.querySelectorAll(`td[title="${EXCHANGE_NO_ENV_TITLE}"]`);
    expect(emptyEnv.length).toBe(unsupportedRows.length);
    expect([...emptyEnv].every((cell) => cell.textContent === EMPTY_CELL)).toBe(true);
  });

  it("SSOT 지원 범위 고지 노출", () => {
    render(<LandingSupport />);
    expect(screen.getByText(ROADMAP_DISCLAIMER)).toBeInTheDocument();
  });
});
