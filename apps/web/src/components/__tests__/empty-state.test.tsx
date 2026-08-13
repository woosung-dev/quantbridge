// EmptyState 공통 컴포넌트 단위 테스트 (headline / description / cta href).

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { EmptyState } from "@/components/empty-state";

describe("EmptyState", () => {
  afterEach(() => {
    cleanup();
  });

  it("headline 만 전달되면 description / cta 없이 렌더된다", () => {
    render(<EmptyState headline="아직 없습니다" />);

    expect(screen.getByTestId("empty-state-headline")).toHaveTextContent(
      "아직 없습니다",
    );
    expect(screen.queryByTestId("empty-state-description")).toBeNull();
    expect(screen.queryByTestId("empty-state-cta")).toBeNull();
  });

  it("description 추가 시 보조 문구가 노출된다", () => {
    render(
      <EmptyState
        headline="첫 백테스트를 시작하세요"
        description="전략을 선택하면 결과를 볼 수 있습니다"
      />,
    );

    expect(screen.getByTestId("empty-state-description")).toHaveTextContent(
      "전략을 선택하면 결과를 볼 수 있습니다",
    );
  });

  it("cta.onClick 가 클릭 시 호출된다", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        headline="작업이 필요합니다"
        cta={{ label: "시작하기", onClick }}
      />,
    );

    fireEvent.click(screen.getByTestId("empty-state-cta"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
