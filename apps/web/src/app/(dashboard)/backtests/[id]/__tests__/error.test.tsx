// Sprint 32 E (BL-163) — backtest detail error.tsx 액셔너블 UX 검증.
//
// 1) error.message 노출 (사용자가 root cause 일부 파악 가능)
// 2) "다시 시도" / "백테스트 목록" / "ADR-003 supported list 참조" 3 액션 버튼
// 3) digest (Next.js sentry-style) 표시 — observability 보조

import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import BacktestDetailError from "../error";

// next/link 는 vitest 환경에서 children 그대로 렌더 — anchor href 가 그대로 노출되므로 OK.

afterEach(() => {
  cleanup();
});

describe("BacktestDetailError — Sprint 32 E (BL-163)", () => {
  it("기본 렌더 — 헤더 + reset 버튼 + ADR-003 supported list 링크 노출", () => {
    const reset = vi.fn();
    render(
      <BacktestDetailError
        error={Object.assign(new Error("Network failed"), {
          digest: "ref-abc-123",
        })}
        reset={reset}
      />,
    );

    expect(screen.getByTestId("backtest-detail-error")).toBeInTheDocument();
    expect(screen.getByText(/백테스트를 불러오지 못했습니다/)).toBeInTheDocument();
    // error.message 노출 (root cause 파악 보조)
    expect(
      screen.getByTestId("backtest-detail-error-message"),
    ).toHaveTextContent("Network failed");
    // digest 노출 (observability)
    expect(screen.getByText(/ref: ref-abc-123/)).toBeInTheDocument();
    // ADR-003 supported list 참조 링크 (actionable CTA)
    const supportedLink = screen.getByTestId(
      "backtest-detail-error-supported-link",
    );
    expect(supportedLink).toBeInTheDocument();
    expect(supportedLink.closest("a")?.getAttribute("href")).toBe(
      "/strategies",
    );
  });

  it("다시 시도 버튼 클릭 → reset 호출", () => {
    const reset = vi.fn();
    render(
      <BacktestDetailError
        error={new Error("transient")}
        reset={reset}
      />,
    );

    fireEvent.click(screen.getByText("다시 시도"));
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("error.message 가 빈 문자열이면 message 노출 element 미렌더", () => {
    const reset = vi.fn();
    render(<BacktestDetailError error={new Error("")} reset={reset} />);

    expect(
      screen.queryByTestId("backtest-detail-error-message"),
    ).not.toBeInTheDocument();
  });

  it("digest 미설정 시 ref 노출 안 함", () => {
    const reset = vi.fn();
    render(<BacktestDetailError error={new Error("oops")} reset={reset} />);

    expect(screen.queryByText(/ref:/)).not.toBeInTheDocument();
  });
});
