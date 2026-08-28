// [ADR-040] 전략 브리핑 — 결정론 층 계약.
//
// 이 파일이 잠그는 것은 둘이다.
//  ⑴ **판정어는 결정론 층이 독점한다** — 여기 그려지는 값에 LLM 산출물이 섞이면 안 된다.
//  ⑵ **없는 데이터는 그리지 않는다**(`_KIT.md` §4.9) — 특히 `signals` 는 Track S 에서
//     비는 것이 정상이고, 그때 「신호 없음」이라고 쓰면 거짓이다.

import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api-client";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { StrategyBriefPanel } from "@/features/strategy/components/brief/strategy-brief";
import type { StrategyBrief } from "@/features/strategy/schemas";

const mockUseStrategyBrief = vi.fn();
vi.mock("@/features/strategy/hooks", () => ({
  useStrategyBrief: (...args: unknown[]) => mockUseStrategyBrief(...args),
  // [ADR-040] 브리핑이 해설 패널을 품는다. 이 파일은 **결정론 층**을 재는 곳이라
  // 해설 본문은 대상이 아니다 — 열기 전 상태로 고정한다(그때는 서버를 안 부른다).
  // 해설 계약은 `narrative-panel.test.tsx` 가 잰다.
  useStrategyNarrative: () => ({ isPending: false, isError: false, data: undefined }),
}));

function makeBrief(overrides: Partial<StrategyBrief> = {}): StrategyBrief {
  return {
    strategy_id: "s-1",
    source_hash: "a".repeat(64),
    track: "S",
    parse: {
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 1,
      exit_count: 1,
      functions_used: ["ta.rsi", "ta.crossover"],
      unsupported_builtins: [],
      unsupported_calls: [],
      is_runnable: true,
      dogfood_only_warning: null,
      declaration: {
        kind: "strategy",
        title: "RSI",
        default_qty_type: null,
        default_qty_value: null,
        pyramiding: null,
      },
      inputs: [{ input_type: "int", var_name: "length", defval: "14", title: "RSI Length" }],
    },
    orders: [
      { name: "strategy.entry", line: 6, args: [{ name: null, value: "strategy.long" }] },
      { name: "strategy.close", line: 8, args: [] },
    ],
    signals: [],
    python_view: null,
    ...overrides,
  };
}

function ready(brief: StrategyBrief) {
  mockUseStrategyBrief.mockReturnValue({ isPending: false, isError: false, data: brief });
}

describe("StrategyBriefPanel — 결정론 층", () => {
  afterEach(() => {
    cleanup();
    mockUseStrategyBrief.mockReset();
  });

  it("실행 가능 판정 · 파라미터 · 지표 · 주문 줄번호를 그린다", () => {
    ready(makeBrief());
    render(<StrategyBriefPanel strategyId="s-1" />);

    expect(screen.getByTestId("brief-verdict").textContent).toBe("실행 가능");
    expect(screen.getByTestId("brief-params").textContent).toContain("length");
    expect(screen.getByTestId("brief-indicators").textContent).toContain("ta.rsi");

    const orders = screen.getByTestId("brief-orders").textContent ?? "";
    expect(orders).toContain("진입");
    expect(orders).toContain("L6"); // 소스 어디서 나오는지
    expect(orders).toContain("strategy.long"); // 어느 방향인지
  });

  it("★signals 가 비면 그 절을 아예 그리지 않는다", () => {
    // Track S 의 `if cond` 형태는 BE SignalExtractor 가 못 잡는다 — 비는 것이 정상이고
    // 「신호 없음」이라고 쓰면 거짓이다.
    ready(makeBrief({ signals: [] }));
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.queryByTestId("brief-signals")).toBeNull();
    expect(screen.queryByText(/신호 변수/)).toBeNull();
  });

  it("signals 가 있으면 그린다 (양성 대조)", () => {
    ready(makeBrief({ track: "A", signals: ["buySignal"] }));
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-signals").textContent).toContain("buySignal");
  });

  it("미지원이 있으면 무엇이 막았는지 줄번호와 함께 보여준다", () => {
    ready(
      makeBrief({
        parse: {
          ...makeBrief().parse,
          is_runnable: false,
          unsupported_builtins: ["ta.supertrend"],
          unsupported_calls: [
            {
              name: "ta.supertrend",
              line: 3,
              col: 9,
              workaround: "ta.atr 로 직접 구현",
              category: "data",
            },
          ],
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);

    expect(screen.getByTestId("brief-verdict").textContent).toBe("실행 불가");
    const blocked = screen.getByTestId("brief-blocked").textContent ?? "";
    expect(blocked).toContain("ta.supertrend");
    expect(blocked).toContain("L3");
    expect(blocked).toContain("ta.atr 로 직접 구현");
  });

  it("Trust Layer degraded 경고를 판정 줄에 노출한다", () => {
    ready(
      makeBrief({
        parse: {
          ...makeBrief().parse,
          dogfood_only_warning: "heikinashi 는 TV 와 달라질 수 있습니다",
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByText(/heikinashi/)).toBeTruthy();
  });

  it("사이징이 전부 미지정이면 그 절을 그리지 않는다", () => {
    ready(makeBrief());
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.queryByTestId("brief-sizing")).toBeNull();
  });

  it("로딩은 스켈레톤 하나 · 실패해도 화면이 산다", () => {
    mockUseStrategyBrief.mockReturnValue({ isPending: true, isError: false, data: undefined });
    const { unmount } = render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-skeleton")).toBeTruthy();
    unmount();

    mockUseStrategyBrief.mockReturnValue({ isPending: false, isError: true, data: undefined });
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-error")).toBeTruthy();
  });

  it("[ADR-042] python_view 가 있으면 「파이썬으로 보기」가 뜨고, 열면 실행 안 됨을 먼저 말한다", () => {
    ready(
      makeBrief({
        python_view: {
          code: "# 헤더\nlength = 14\nif close > open:\n    strategy.entry()\n",
          source_map: [
            [2, 3],
            [3, 5],
          ],
          unrendered: 0,
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);

    fireEvent.click(screen.getByRole("button", { name: "펼치기" }));

    // ★본문보다 먼저 「실행되는 코드가 아니다」가 나와야 한다.
    expect(screen.getByTestId("python-view-disclaimer").textContent).toContain(
      "실행되는 코드가 아닙니다",
    );
    const body = screen.getByTestId("python-view").textContent ?? "";
    expect(body).toContain("strategy.entry()");
    // 거터는 **원본 Pine 줄번호**다 — python 2번째 줄 → pine 3번째 줄.
    expect(body).toContain("3");
  });

  it("옮기지 못한 곳이 있으면 「지운 것이 아니다」를 말한다", () => {
    ready(
      makeBrief({
        python_view: { code: "# [원문 보존] for v in arr\n", source_map: [], unrendered: 2 },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "펼치기" }));

    expect(screen.getByTestId("python-view-preserved").textContent).toContain("2곳");
  });

  it("python_view 가 없으면 버튼 자체를 그리지 않는다", () => {
    ready(makeBrief({ python_view: null }));
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.queryByRole("button", { name: "펼치기" })).toBeNull();
  });

  // ── UI 감사 회귀 (2026-08-27) ────────────────────────────────────────────
  // ★★BE 는 파싱 실패 시 구조 추출 예외를 삼키고 빈 목록을 돌려준다(service.py 계약).
  //   그 빈 목록을 「없다」로 인쇄하면 **사용자가 자기 전략에 진입/청산이 없다고 믿고**
  //   그대로 백테스트를 제출한다. 이 제품의 핵심 가치(정직한 가정 표시) 정면 위반이다.
  it("★파싱이 실패하면 빈 목록을 「없다」로 단정하지 않는다", () => {
    ready(
      makeBrief({
        orders: [],
        parse: {
          ...makeBrief().parse,
          status: "error",
          is_runnable: false,
          errors: [{ code: "syntax", message: "예상치 못한 토큰", line: 4 }],
          inputs: [],
          functions_used: [],
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);

    // 확정 단정이 사라져야 한다.
    const body = screen.getByTestId("strategy-brief").textContent ?? "";
    expect(body).not.toContain("주문 호출이 없습니다");
    expect(body).not.toContain("조절할 파라미터를 선언하지 않았습니다");
    expect(body).toContain("읽지 못해");

    // ★그리고 「실행 불가」의 이유가 화면에 있어야 한다 — 종전에는 0줄이었다.
    const failed = screen.getByTestId("brief-parse-failed").textContent ?? "";
    expect(failed).toContain("예상치 못한 토큰");
    expect(failed).toContain("L4");
  });

  it("파싱이 성공했을 때는 「없다」가 정직한 단정이다 (음성 대조)", () => {
    ready(makeBrief({ orders: [], parse: { ...makeBrief().parse, inputs: [] } }));
    render(<StrategyBriefPanel strategyId="s-1" />);

    const body = screen.getByTestId("strategy-brief").textContent ?? "";
    expect(body).toContain("주문 호출이 없습니다");
    expect(screen.queryByTestId("brief-parse-failed")).toBeNull();
  });

  it("★서버의 내부 개발 메모를 판정 칩에 원문으로 박지 않는다", () => {
    const memo = "heikinashi() 사용 - Trust Layer 위반 (Sprint 29 ADR). dogfood-only 사용 권장.";
    ready(makeBrief({ parse: { ...makeBrief().parse, dogfood_only_warning: memo } }));
    render(<StrategyBriefPanel strategyId="s-1" />);

    // 칩은 사용자 언어로, 원문은 본문 절로 내려간다.
    expect(screen.getByTestId("brief-degraded").textContent).not.toContain("Sprint 29");
    expect(screen.getByTestId("brief-degraded-detail").textContent).toContain("Sprint 29");
  });

  it("★브리핑 로드 실패에 재시도와 상관 ID 가 있다", () => {
    const refetch = vi.fn();
    mockUseStrategyBrief.mockReturnValue({
      isPending: false,
      isError: true,
      data: undefined,
      error: new ApiError(502, "x", "실패", {
        detail: { code: "x", detail: "생성 실패", error_id: "abc123def456" },
      }),
      refetch,
    });
    render(<StrategyBriefPanel strategyId="s-1" />);

    // ★재시도가 없으면 유일한 탈출구가 새로고침이고, 백테스트 폼 안에서는 폼 값이 날아간다.
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(refetch).toHaveBeenCalled();
    // ★서버가 만든 상관 ID 를 버리면 문의를 추적할 수 없다.
    expect(screen.getByTestId("brief-error").textContent).toContain("abc123def456");
  });

  it("★파이썬 뷰 토글이 눌러도 사라지지 않는다 (포커스 유실 방지)", () => {
    ready(
      makeBrief({
        python_view: { code: "x = 1\n", source_map: [[1, 3]], unrendered: 0 },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);

    const btn = screen.getByRole("button", { name: "펼치기" });
    btn.focus();
    fireEvent.click(btn);

    // 같은 엘리먼트가 살아 있어야 포커스가 유지된다.
    expect(document.body.contains(btn)).toBe(true);
    expect(document.activeElement).toBe(btn);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
  });
});
