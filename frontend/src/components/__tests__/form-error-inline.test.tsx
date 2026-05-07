// FormErrorInline — null / 422+unsupported / 422 fallback / 5xx 분기 테스트.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { FormErrorInline } from "@/components/form-error-inline";
import { ApiError } from "@/lib/api-client";

describe("FormErrorInline", () => {
  afterEach(() => {
    cleanup();
  });

  it("error=null 이면 아무것도 렌더하지 않는다", () => {
    const { container } = render(<FormErrorInline error={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("422 + unsupported_builtins → 카드 + hints + edit link 렌더", () => {
    const apiErr = new ApiError(
      422,
      "strategy_not_runnable",
      "Strategy contains unsupported Pine built-ins",
      {
        detail: {
          code: "strategy_not_runnable",
          detail: "unsupported builtins",
          unsupported_builtins: ["heikinashi", "security"],
          friendly_message:
            "이 strategy 는 다른 timeframe 데이터에 의존해 backtest 결과가 부정확할 수 있습니다.",
        },
      },
    );
    render(
      <FormErrorInline
        error={apiErr}
        editStrategyHref="/strategies/abc/edit?tab=parse"
        testIdPrefix="backtest-form"
      />,
    );

    expect(screen.getByTestId("backtest-form-unsupported-card")).toBeInTheDocument();
    expect(screen.getByTestId("backtest-form-friendly-message")).toHaveTextContent(
      "다른 timeframe 데이터",
    );
    expect(screen.getByTestId("backtest-form-edit-strategy-link")).toHaveAttribute(
      "href",
      "/strategies/abc/edit?tab=parse",
    );
    expect(screen.queryByTestId("backtest-form-server-error")).toBeNull();
  });

  it("422 + unsupported_builtins 빈 list → fallback server-error 렌더", () => {
    const apiErr = new ApiError(422, "validation_error", "입력값 오류", {
      detail: {
        code: "validation_error",
        detail: "fields",
        unsupported_builtins: [],
      },
    });
    render(<FormErrorInline error={apiErr} testIdPrefix="backtest-form" />);

    expect(screen.queryByTestId("backtest-form-unsupported-card")).toBeNull();
    expect(screen.getByTestId("backtest-form-server-error")).toBeInTheDocument();
  });

  it("5xx ApiError → server-error 단순 alert 렌더", () => {
    const apiErr = new ApiError(503, "service_unavailable", "백엔드 일시 장애");
    render(<FormErrorInline error={apiErr} />);

    const el = screen.getByTestId("form-error-server-error");
    expect(el).toHaveTextContent("백엔드 일시 장애");
  });
});
