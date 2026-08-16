// 파싱 결과 패널(C 이식 screen-07 §03) 시맨틱 구조 테스트 — 상태 4종 + backed 값만 렌더 확인.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ParseResultPanel } from "@/features/strategy/components/new/parse-result-panel";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

function makeResult(overrides: Partial<ParsePreviewResponse> = {}): ParsePreviewResponse {
  return {
    status: "ok",
    pine_version: "v5",
    warnings: [],
    errors: [],
    entry_count: 1,
    exit_count: 1,
    functions_used: ["ta.sma", "ta.crossover"],
    unsupported_builtins: [],
    unsupported_calls: [],
    is_runnable: true,
    ...overrides,
  };
}

describe("ParseResultPanel — C 이식 시맨틱 구조", () => {
  afterEach(cleanup);

  it("지원됨: .parse-kpi + chip done '지원됨' + 감지 함수 목록 + 저장 버튼", () => {
    render(
      <ParseResultPanel result={makeResult()} loading={false} canSave onSave={vi.fn()} />,
    );
    expect(screen.getByTestId("parse-supported")).toBeTruthy();
    expect(screen.getByText("지원됨").className).toBe("chip done");
    expect(screen.getByText("ta.sma")).toBeTruthy();
    // 지원 판정 2/2 (functions_used 2, unsupported 0)
    expect(screen.getByText("2 / 2")).toBeTruthy();
    const save = screen.getByTestId("parse-save") as HTMLButtonElement;
    expect(save.disabled).toBe(false);
    // 심볼 기본값 무데이터 셀
    expect(screen.getByTitle(/Pine 스크립트에는 심볼이 없습니다/)).toBeTruthy();
  });

  it("canSave 가 false 면 저장 버튼이 비활성화된다", () => {
    render(<ParseResultPanel result={makeResult()} loading={false} canSave={false} />);
    expect((screen.getByTestId("parse-save") as HTMLButtonElement).disabled).toBe(true);
  });

  it("미지원: state-box.failed + 미지원 함수 목록 + 전체 미지원 정책 문구", () => {
    render(
      <ParseResultPanel
        result={makeResult({ status: "unsupported", unsupported_builtins: ["request.security"] })}
        loading={false}
      />,
    );
    const box = screen.getByTestId("parse-unsupported");
    expect(box.className).toContain("state-box failed");
    expect(screen.getByText("request.security")).toBeTruthy();
    expect(screen.getByText(/부분 실행 없이 전체를 지원되지 않음으로 처리/)).toBeTruthy();
  });

  it("미지원: BE가 보낸 줄번호와 우회안을 렌더한다", () => {
    render(
      <ParseResultPanel
        result={makeResult({
          status: "unsupported",
          unsupported_builtins: ["ta.alma"],
          unsupported_calls: [
            {
              name: "ta.alma",
              line: 12,
              col: null,
              workaround: "ta.sma() 또는 ta.ema()로 바꾸세요.",
              category: "math",
            },
          ],
        })}
        loading={false}
      />,
    );

    expect(screen.getByText(/L12/)).toBeTruthy();
    expect(screen.getByText(/우회안: ta\.sma\(\) 또는 ta\.ema\(\)로 바꾸세요/)).toBeTruthy();
  });

  it("로딩: .sk 스켈레톤", () => {
    render(<ParseResultPanel result={null} loading />);
    expect(screen.getByTestId("parse-skeleton")).toBeTruthy();
  });

  it("빈 상태: 코드 없음 안내 state-box", () => {
    render(<ParseResultPanel result={null} loading={false} />);
    expect(screen.getByTestId("parse-empty")).toBeTruthy();
  });

  it("요청 실패: state-box.failed + 파싱 엔드포인트 코드", () => {
    render(<ParseResultPanel result={null} loading={false} error="Network error" />);
    const box = screen.getByTestId("parse-request-error");
    expect(box.className).toContain("state-box failed");
    expect(screen.getByText("POST /api/v1/strategies/parse")).toBeTruthy();
  });
});
