// LandingHowItWorks (C 이식) — 4 단계 카드 + section id=how.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingHowItWorks } from "../landing-how-it-works";

describe("LandingHowItWorks", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=how + 번호 아이브로우 없음 (BL-810)", () => {
    const { container } = render(<LandingHowItWorks />);
    expect(container.querySelector("#how")).not.toBeNull();
    expect(container.querySelector(".eyebrow .num")).toBeNull();
    expect(container.querySelector(".eyebrow")?.textContent).toBe("작동 방식");
  });

  it("4 단계 카드(.lp-step) — STEP 라벨 없음 (BL-810)", () => {
    const { container } = render(<LandingHowItWorks />);
    expect(container.querySelectorAll(".lp-step").length).toBe(4);
    // ★문자열을 쪼개 쓰지 않는다. 하네스 step 1 의 AC(`! grep -rq 'lp-step-num' src/`)가
    //   테스트 파일까지 덮는 바람에 생성자가 `".lp-step" + "-num"` 으로 우회했던 자리다.
    //   부재를 단언하는 테스트는 그 클래스 이름을 그대로 써야 읽힌다 (2026-08-19).
    expect(container.querySelector(".lp-step-num")).toBeNull();
    expect(screen.queryByText(/^STEP /)).toBeNull();
    expect(screen.getByText("전략 등록")).toBeInTheDocument();
    expect(screen.getByText("데모 실행")).toBeInTheDocument();
  });
});
