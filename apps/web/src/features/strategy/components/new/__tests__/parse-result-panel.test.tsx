// 파싱 결과 패널(C 이식 screen-07 §03) 시맨틱 구조 테스트 — 상태 4종 + backed 값만 렌더 확인.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

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
    declaration: null,
    inputs: [],
    dogfood_only_warning: null,
    ...overrides,
  };
}

describe("ParseResultPanel — C 이식 시맨틱 구조", () => {
  afterEach(cleanup);

  it("지원됨: .parse-kpi + chip done '지원됨' + 감지 함수 목록 + 저장 버튼", () => {
    render(<ParseResultPanel result={makeResult()} loading={false} canSave onSave={vi.fn()} />);
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
    expect(screen.queryByText("Pine 구문을 확인해 주세요.")).toBeNull();
    expect(screen.queryByText(/서버 진단 보기/)).toBeNull();
  });

  it("구문 오류는 한국어 복구 안내와 구조화된 위치를 보이고 원본 진단은 접어 보존한다", () => {
    const messages = ["SyntaxError: no viable alternative", "unexpected token 'end'"];
    render(
      <ParseResultPanel
        result={makeResult({
          status: "error",
          errors: [
            { code: "SYNTAX_ERROR", message: messages[0]!, line: 2 },
            { code: "UNEXPECTED_TOKEN", message: messages[1]!, line: 7 },
          ],
        })}
        loading={false}
        canSave
      />,
    );
    expect(screen.getByText("Pine 구문을 확인해 주세요.")).toBeVisible();
    expect(screen.getByText(/괄호와 들여쓰기, Pine 버전 선언/)).toHaveTextContent(
      "파싱 검사를 다시 실행",
    );
    expect(screen.getByText("서버가 보고한 위치: 2행, 7행.")).toBeVisible();
    const summary = screen.getByText("서버 진단 보기 (2건)");
    const details = summary.closest("details")!;
    expect(details).not.toHaveAttribute("open");
    expect(within(details).getAllByRole("listitem", { hidden: true })).toHaveLength(2);
    for (const message of messages) {
      expect(within(details).getByText(message)).not.toBeVisible();
    }
    fireEvent.click(summary);
    for (const message of messages) {
      expect(within(details).getByText(message)).toBeVisible();
    }
    expect(within(details).getByText("L2 · SYNTAX_ERROR")).toBeVisible();
    expect(within(details).getByText("L7 · UNEXPECTED_TOKEN")).toBeVisible();
    expect(screen.queryByTestId("parse-save")).toBeNull();
    expect(screen.queryByText(/부분 실행 없이 전체를 지원되지 않음으로 처리/)).toBeNull();
  });

  it("구조화된 위치가 없으면 서버 문자열의 line 숫자를 추출하지 않는다", () => {
    const message = 'SyntaxError: File "<unknown>", line 98';
    render(
      <ParseResultPanel
        result={makeResult({
          status: "error",
          errors: [{ code: "SYNTAX_ERROR", message, line: null }],
        })}
        loading={false}
      />,
    );
    expect(screen.queryByText(/서버가 보고한 위치/)).toBeNull();
    expect(screen.getByText(message)).toHaveTextContent(message);
    expect(screen.getByText("서버 진단 보기 (1건)").closest("details")).not.toHaveAttribute("open");
  });

  it("세부 진단이 없는 오류도 복구 안내를 유지하고 저장하지 못한다", () => {
    render(<ParseResultPanel result={makeResult({ status: "error" })} loading={false} canSave />);
    expect(screen.getByText("Pine 구문을 확인해 주세요.")).toBeVisible();
    expect(screen.queryByText(/서버 진단 보기/)).toBeNull();
    expect(screen.queryByTestId("parse-save")).toBeNull();
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

  // [ADR-040] Stage 1 — 종전 이 패널은 「서버 응답에 파라미터 필드가 없어 표시하지
  // 않습니다」를 인쇄했다. `inputs` 가 열린 뒤 그 문장은 거짓이 되므로 실개수로 바꿨다.
  it("파라미터 개수와 스윕 가능 수를 실데이터로 그린다", () => {
    render(
      <ParseResultPanel
        result={makeResult({
          inputs: [
            { input_type: "int", var_name: "length", defval: "14", title: null },
            { input_type: "generic", var_name: "legacy", defval: "7", title: null },
          ],
        })}
        onSave={vi.fn()}
        canSave
        loading={false}
      />,
    );
    expect(screen.getByText("파라미터")).toBeTruthy();
    // 2개 중 int 하나만 최적화가 스윕할 수 있다(BE `_validate_grid_search_pre`).
    expect(screen.getByText(/스윕할 수 있는 것은 1개/)).toBeTruthy();
  });
});
