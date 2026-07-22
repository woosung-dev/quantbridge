// not-found(404) — screen-13 §01 C 언어 구조 이식 검증(W3-H). 섹션 순서·핵심 시맨틱 클래스·
// 실경로 CTA·가짜 검색창 부재를 assert 한다.

import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import NotFound from "../not-found";

afterEach(() => cleanup());

describe("NotFound — 404 C 구조", () => {
  it("아이브로 404 + h1 + 상태 박스(err-hero, role=status) + 안내 노트", () => {
    const { container } = render(<NotFound />);

    // 아이브로 번호 뱃지
    expect(container.querySelector(".eyebrow .num")).toHaveTextContent("404");
    // 페이지 h1
    expect(
      screen.getByRole("heading", { level: 1, name: "요청한 페이지를 찾을 수 없습니다." }),
    ).toBeInTheDocument();

    // 상태 박스 — 무데이터/안내라 neutral(role=status) + err-hero 폭
    const stateBox = screen.getByTestId("not-found-state");
    expect(stateBox).toHaveClass("state-box", "err-hero");
    expect(stateBox).toHaveAttribute("role", "status");
    expect(stateBox.querySelector(".state-title")).toBeInTheDocument();

    // 카드 head 의 상태 칩 + 안내 노트
    expect(container.querySelector(".card .card-head .chip")).toHaveTextContent("404");
    expect(container.querySelector(".chart-note")).toBeInTheDocument();
  });

  it("CTA 3벌 — 권장 카드가 첫째, 전부 실제 워크스페이스 경로로 연결", () => {
    render(<NotFound />);
    const row = screen.getByTestId("not-found-cta-row");
    const cards = row.querySelectorAll(":scope > article");
    expect(cards).toHaveLength(3);

    // 첫 카드 = 권장(백테스트 목록)
    const first = cards.item(0);
    expect(first).toHaveClass("cta", "recommended");
    expect(first?.querySelector(".cta-badge")).toHaveTextContent("권장");

    expect(screen.getByRole("link", { name: "백테스트 목록 열기" })).toHaveAttribute(
      "href",
      "/backtests",
    );
    expect(screen.getByRole("link", { name: "전략 목록 열기" })).toHaveAttribute(
      "href",
      "/strategies",
    );
    expect(screen.getByRole("link", { name: "대시보드 열기" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
  });

  it("가짜 검색창을 그리지 않는다(동작하지 않는 검색 입력 금지)", () => {
    render(<NotFound />);
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
