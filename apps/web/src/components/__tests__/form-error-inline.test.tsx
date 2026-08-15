// FormErrorInline — null / 422+unsupported / 422 fallback / 5xx 분기 테스트.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

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

  it("422 + degraded_calls → TradingView 차이를 고지한 동의 체크박스", () => {
    const onDegradedConsentChange = vi.fn();
    const apiErr = new ApiError(422, "strategy_degraded", "API 422 /api/v1/backtests", {
      detail: {
        code: "strategy_degraded",
        detail: "Strategy uses degraded Pine functions: heikinashi",
        degraded_calls: ["heikinashi"],
        friendly_message: "일부 함수가 근사 처리됩니다.",
      },
    });
    render(
      <FormErrorInline
        error={apiErr}
        testIdPrefix="backtest-form"
        onDegradedConsentChange={onDegradedConsentChange}
      />,
    );

    const card = screen.getByTestId("backtest-form-degraded-card");
    expect(card).toHaveTextContent("TradingView와 다를 수 있습니다");
    const checkbox = screen.getByTestId("backtest-form-degraded-consent");
    fireEvent.click(checkbox);
    expect(onDegradedConsentChange).toHaveBeenCalledWith(true);
  });

  it("degraded_calls 없는 422는 동의 체크박스를 렌더하지 않는다", () => {
    const apiErr = new ApiError(422, "validation_error", "입력값 오류", {
      detail: { code: "validation_error", detail: "fields" },
    });
    render(<FormErrorInline error={apiErr} testIdPrefix="backtest-form" />);

    expect(screen.queryByTestId("backtest-form-degraded-consent")).toBeNull();
  });

  // BL-485 — `friendly_message` 는 BE 화이트리스트 2종(`StrategyNotRunnable` /
  // `StrategyDegraded`)에만 붙는다(`apps/api/src/main.py:51,56`). 나머지 422 는 그 필드가
  // 없어 `err.message` 로 떨어지는데, 그 값은 프로덕션에서 **언제나** `API 422 <path>` 다
  // (`lib/api-client.ts:57`). 즉 사용자는 서버가 준 문장 대신 HTTP 잡음을 본다.
  it("422 + friendly_message 없음 → detail.detail 을 렌더하고 'API 422' 를 안 보여준다", () => {
    const apiErr = new ApiError(422, "live_session_conflict", "API 422 /api/v1/live-sessions", {
      detail: {
        code: "live_session_conflict",
        detail: "이미 같은 전략·심볼로 실행 중인 세션이 있습니다.",
      },
    });
    render(<FormErrorInline error={apiErr} />);

    const el = screen.getByTestId("form-error-server-error");
    expect(el).toHaveTextContent("이미 같은 전략·심볼로 실행 중인 세션이 있습니다.");
    expect(el).not.toHaveTextContent("API 422");
  });

  // 음성 대조 — 폴백이 기존 경로를 **가로채면 안 된다**. `friendly_message` 가 있으면
  // `detail.detail` 이 함께 있어도 여전히 `friendly_message` 가 이긴다.
  it("422 + friendly_message 있음 → detail.detail 이 있어도 friendly_message 가 이긴다", () => {
    const apiErr = new ApiError(422, "strategy_degraded", "API 422 /api/v1/backtests", {
      detail: {
        code: "strategy_degraded",
        detail: "raw degraded detail",
        friendly_message: "일부 함수가 근사 처리됩니다.",
      },
    });
    render(<FormErrorInline error={apiErr} />);

    const el = screen.getByTestId("form-error-server-error");
    expect(el).toHaveTextContent("일부 함수가 근사 처리됩니다.");
    expect(el).not.toHaveTextContent("raw degraded detail");
  });

  it("5xx ApiError → server-error 단순 alert 렌더", () => {
    const apiErr = new ApiError(503, "service_unavailable", "백엔드 일시 장애");
    render(<FormErrorInline error={apiErr} />);

    const el = screen.getByTestId("form-error-server-error");
    expect(el).toHaveTextContent("백엔드 일시 장애");
  });
});
