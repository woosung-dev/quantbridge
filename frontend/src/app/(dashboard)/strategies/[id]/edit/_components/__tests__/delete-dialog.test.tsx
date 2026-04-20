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

function installMatchMedia(mobile: boolean) {
  const listeners = new Set<Listener>();
  const mql = {
    matches: mobile,
    media: "(max-width: 767px)",
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
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => mql),
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

  it("renders bottom Sheet on mobile viewport (<768px)", () => {
    installMatchMedia(true);
    render(<DeleteDialog {...baseProps} />);
    expect(document.querySelector('[data-slot="sheet-content"]')).not.toBeNull();
    expect(document.querySelector('[data-slot="dialog-content"]')).toBeNull();
    // drag handle (시각적 afformance)
    expect(document.querySelector('[data-slot="sheet-handle"]')).not.toBeNull();
  });

  it("renders centered Dialog on desktop viewport (≥768px)", () => {
    installMatchMedia(false);
    render(<DeleteDialog {...baseProps} />);
    expect(document.querySelector('[data-slot="dialog-content"]')).not.toBeNull();
    expect(document.querySelector('[data-slot="sheet-content"]')).toBeNull();
  });

  it("calls delete mutate when 삭제 button clicked (mobile Sheet)", () => {
    installMatchMedia(true);
    render(<DeleteDialog {...baseProps} />);
    const btn = screen.getByRole("button", { name: /^삭제$/ });
    fireEvent.click(btn);
    expect(deleteMutate).toHaveBeenCalledWith("strat-1");
  });

  it("calls delete mutate when 삭제 button clicked (desktop Dialog)", () => {
    installMatchMedia(false);
    render(<DeleteDialog {...baseProps} />);
    const btn = screen.getByRole("button", { name: /^삭제$/ });
    fireEvent.click(btn);
    expect(deleteMutate).toHaveBeenCalledWith("strat-1");
  });

  it("mobile Sheet: 취소 button renders before 삭제 (thumb-reach)", () => {
    installMatchMedia(true);
    render(<DeleteDialog {...baseProps} />);
    const footer = document.querySelector('[data-slot="sheet-footer"]');
    expect(footer).not.toBeNull();
    const buttons = Array.from(footer!.querySelectorAll("button"));
    expect(buttons[0]?.textContent).toMatch(/취소/);
    expect(buttons[1]?.textContent).toMatch(/^삭제$/);
  });

  it("cancel button closes sheet via onOpenChange(false)", () => {
    installMatchMedia(true);
    render(<DeleteDialog {...baseProps} />);
    fireEvent.click(screen.getByRole("button", { name: /취소/ }));
    expect(baseProps.onOpenChange).toHaveBeenCalledWith(false);
  });
});
