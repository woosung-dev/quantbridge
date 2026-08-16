import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";

// 전략 hooks 는 Clerk/react-query 체인을 통해 호출되므로 이 레이어에서 고정.
const deleteMutate = vi.fn();
const updateMutate = vi.fn();

vi.mock("@/features/strategy/hooks", () => ({
  useDeleteStrategy: () => ({
    mutate: deleteMutate,
    isPending: false,
  }),
  useUpdateStrategy: () => ({
    mutate: updateMutate,
    isPending: false,
  }),
}));

vi.mock("@/features/strategy/utils", () => ({
  isStrategyHasBacktestsError: () => false,
}));

import { DeleteDialog } from "../delete-dialog";

type Listener = (event: MediaQueryListEvent) => void;

/** 이 하네스가 흉내 낼 수 있는 유일한 형태. 다른 형태가 오면 던진다(조용한 통과 금지). */
const MAX_WIDTH_RE = /^\(\s*max-width:\s*(\d+(?:\.\d+)?)px\s*\)$/;

/** 컴포넌트가 `window.matchMedia` 에 실제로 넘긴 query 문자열 (호출 순, 중복 포함). */
let observedQueries: string[] = [];

/**
 * **뷰포트 폭 하나**를 흉내 내는 matchMedia.
 *
 * ★★★왜 boolean 이 아니라 폭인가 (2026-08-08 `/code-review` 지적).
 *   종전 판은 `installMatchMedia(mobile: boolean)` 이었고, 넘어온 **query 문자열을 한 번도
 *   보지 않은 채** 어떤 query 에도 같은 mql 을 돌려줬다(`media` 필드는 `(max-width: 767px)` 로
 *   박혀 있었지만 아무도 읽지 않았다). 그래서 `matches` 를 시험이 직접 정했고, 컴포넌트가 쓰는
 *   경계가 767 이든 768 이든 **모든 테스트가 똑같이 초록**이었다 — [BL-644] 가 고친 그 1픽셀을
 *   누가 되돌려도 어느 게이트도 물지 않는 상태였다.
 *   이제 query 를 **파싱해서** 이 폭이 조건에 드는지로 `matches` 를 만든다. `max-width` 는
 *   경계값을 **포함**하므로 `matches = width <= N` 이다. ⇒ 폭 768 시험 하나가 767/768 을 가른다.
 */
function installMatchMedia(viewportWidth: number) {
  observedQueries = [];
  const listeners = new Set<Listener>();
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      observedQueries.push(query);
      const m = MAX_WIDTH_RE.exec(query);
      if (!m) {
        throw new Error(
          `이 하네스는 "(max-width: Npx)" 만 흉내 낸다 — 받은 query: ${query}. ` +
            `축이 바뀌었다면 하네스를 먼저 고쳐라 (조용히 통과시키면 오라클이 죽는다).`,
        );
      }
      return {
        matches: viewportWidth <= Number(m[1]),
        media: query,
        onchange: null,
        addEventListener: (_type: string, listener: Listener) => {
          listeners.add(listener);
        },
        removeEventListener: (_type: string, listener: Listener) => {
          listeners.delete(listener);
        },
        addListener: (listener: Listener) => listeners.add(listener),
        removeListener: (listener: Listener) => listeners.delete(listener),
        dispatchEvent: () => true,
      };
    }),
  });
}

const baseProps = {
  open: true,
  onOpenChange: vi.fn(),
  strategyId: "strat-1",
  strategyName: "테스트 전략",
  onDone: vi.fn(),
  onArchived: vi.fn(),
};

describe("DeleteDialog — responsive branch", () => {
  beforeEach(() => {
    deleteMutate.mockReset();
    updateMutate.mockReset();
    baseProps.onOpenChange.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders bottom Sheet on mobile viewport (≤768px)", () => {
    installMatchMedia(375);
    render(<DeleteDialog {...baseProps} />);
    expect(document.querySelector('[data-slot="sheet-content"]')).not.toBeNull();
    expect(document.querySelector('[data-slot="dialog-content"]')).toBeNull();
    // drag handle (시각적 afformance)
    expect(document.querySelector('[data-slot="sheet-handle"]')).not.toBeNull();
  });

  it("renders centered Dialog on desktop viewport (>768px)", () => {
    installMatchMedia(1440);
    render(<DeleteDialog {...baseProps} />);
    expect(document.querySelector('[data-slot="dialog-content"]')).not.toBeNull();
    expect(document.querySelector('[data-slot="sheet-content"]')).toBeNull();
  });

  // ── 경계 고정 ([BL-644] 오라클) ──────────────────────────────────────────
  //
  // ★★이 세 검사가 이 파일에서 유일하게 **숫자를 고정**한다. 위 375/1440 시험은 767 로
  //   되돌려도 통과한다(둘 다 경계에서 멀다). 판별하는 것은 768 과 그 이웃뿐이다.
  //   음성 대조(2026-08-08): `delete-dialog.tsx` 를 `(max-width: 767px)` 로 되돌리면
  //   아래 「768px 은 모바일」과 「query 문자열 고정」이 red 가 된다.

  it("경계 768px 은 모바일이다 — CSS `@media (max-width: 768px)` 와 같은 축 ([BL-644])", () => {
    installMatchMedia(768);
    render(<DeleteDialog {...baseProps} />);
    expect(
      document.querySelector('[data-slot="sheet-content"]'),
      "뷰포트 768px 에서 Dialog 가 떴다 — 훅 경계가 767 로 되돌아갔다. " +
        "셸은 768 에서 이미 모바일(--sidebar-w:0 · drawer)이라 1픽셀이 어긋난다.",
    ).not.toBeNull();
    expect(document.querySelector('[data-slot="dialog-content"]')).toBeNull();
  });

  it("경계 바로 밖 769px 은 데스크탑이다", () => {
    installMatchMedia(769);
    render(<DeleteDialog {...baseProps} />);
    expect(document.querySelector('[data-slot="dialog-content"]')).not.toBeNull();
    expect(document.querySelector('[data-slot="sheet-content"]')).toBeNull();
  });

  it("훅에 넘어간 media query 문자열이 정확히 `(max-width: 768px)` 다", () => {
    installMatchMedia(1440);
    render(<DeleteDialog {...baseProps} />);
    expect(observedQueries.length).toBeGreaterThan(0);
    expect([...new Set(observedQueries)]).toEqual(["(max-width: 768px)"]);
  });

  it("calls delete mutate when 삭제 button clicked (mobile Sheet)", () => {
    installMatchMedia(375);
    render(<DeleteDialog {...baseProps} />);
    const btn = screen.getByRole("button", { name: /^삭제$/ });
    fireEvent.click(btn);
    expect(deleteMutate).toHaveBeenCalledWith("strat-1");
  });

  it("calls delete mutate when 삭제 button clicked (desktop Dialog)", () => {
    installMatchMedia(1440);
    render(<DeleteDialog {...baseProps} />);
    const btn = screen.getByRole("button", { name: /^삭제$/ });
    fireEvent.click(btn);
    expect(deleteMutate).toHaveBeenCalledWith("strat-1");
  });

  it("mobile Sheet: 취소 button renders before 삭제 (thumb-reach)", () => {
    installMatchMedia(375);
    render(<DeleteDialog {...baseProps} />);
    const footer = document.querySelector('[data-slot="sheet-footer"]');
    expect(footer).not.toBeNull();
    const buttons = Array.from(footer!.querySelectorAll("button"));
    expect(buttons[0]?.textContent).toMatch(/취소/);
    expect(buttons[1]?.textContent).toMatch(/^삭제$/);
  });

  it("cancel button closes sheet via onOpenChange(false)", () => {
    installMatchMedia(375);
    render(<DeleteDialog {...baseProps} />);
    fireEvent.click(screen.getByRole("button", { name: /취소/ }));
    expect(baseProps.onOpenChange).toHaveBeenCalledWith(false);
  });
});
