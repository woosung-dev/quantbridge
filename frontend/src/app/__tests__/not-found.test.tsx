// not-found 페이지 — 404 layout 통합 검증 (Sprint 43 W8)

import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import NotFound from "../not-found";

afterEach(() => cleanup());

describe("NotFound — 404 layout", () => {
  it("backdrop '404' + heading + 홈/대시보드 버튼 + 추천 카드 + 검색", () => {
    render(<NotFound />);

    expect(screen.getByTestId("error-illustration-backdrop")).toHaveTextContent("404");
    expect(screen.getByRole("heading", { name: "페이지를 찾을 수 없습니다" })).toBeInTheDocument();

    expect(screen.getByRole("link", { name: /홈으로 돌아가기/ })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /대시보드로/ })).toHaveAttribute("href", "/dashboard");

    // 404 recovery box 노출
    const box = screen.getByTestId("error-recovery-box");
    expect(box).toHaveAttribute("data-variant", "404");
    expect(screen.getByLabelText("원하는 기능을 검색하세요")).toBeInTheDocument();
  });
});
