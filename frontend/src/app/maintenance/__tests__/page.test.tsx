// maintenance(503) — screen-13 §03 C 언어 구조 이식 검증(W3-H). 섹션 순서·핵심 시맨틱 클래스·
// 무데이터 ETA 셀·정직성 고지를 assert 한다. 재시도 버튼은 window.location.reload 라 클릭하지
// 않고 렌더만 확인한다.

import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import MaintenancePage from "../page";

afterEach(() => cleanup());

describe("MaintenancePage — 503 C 구조", () => {
  it("아이브로 503 + h1 + 상태 박스(failed, role=alert, state-code) + 트러스트 그리드", () => {
    const { container } = render(<MaintenancePage />);

    expect(container.querySelector(".eyebrow .num")).toHaveTextContent("503");
    expect(
      screen.getByRole("heading", { level: 1, name: "서비스를 일시적으로 사용할 수 없습니다." }),
    ).toBeInTheDocument();

    const stateBox = screen.getByTestId("maintenance-503-state");
    expect(stateBox).toHaveClass("state-box", "failed", "err-hero");
    expect(stateBox).toHaveAttribute("role", "alert");
    expect(stateBox.querySelector(".state-code")).toHaveTextContent("GET /health · 503");

    expect(container.querySelector(".trust-grid")).toBeInTheDocument();
  });

  it("예상 복구 시간은 무데이터 셀로 두고 추정치를 인쇄하지 않는다", () => {
    const { container } = render(<MaintenancePage />);
    const emptyCell = container.querySelector(".trust-val.empty");
    expect(emptyCell).toBeInTheDocument();
    expect(emptyCell).toHaveAttribute("title");
    // 재시도 권장 간격(30초)은 HTTP 재시도 정책이고 트레이딩 주문 재시도 문구는 섞지 않는다
    expect(container.textContent).toContain("Retry-After");
    expect(container.textContent).not.toContain("지수 백오프");
  });

  it("재시도 버튼 + 홈 링크 + 자동 갱신 없음 고지", () => {
    const { container } = render(<MaintenancePage />);
    expect(screen.getByTestId("maintenance-retry-button")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "홈으로" })).toHaveAttribute("href", "/");
    expect(container.querySelector(".disclaimer")).toHaveTextContent("자동으로 갱신하지 않습니다");
  });
});
