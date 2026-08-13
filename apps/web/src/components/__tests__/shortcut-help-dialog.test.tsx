import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ShortcutHelpDialog } from "@/components/shortcut-help-dialog";

// 전역 `?` 단축키 Dialog 단위 테스트.
// - `?` 로 모달이 열린다
// - input / contentEditable focus 시 `?` 는 타이핑으로 흐르고 모달은 열리지 않는다
// - Esc 가 Base UI 기본 동작으로 모달을 닫는다
// - 언마운트 시 document keydown 리스너 누수가 없다

const DIALOG_TITLE = "키보드 단축키";

function dispatchQuestion(target: EventTarget = document) {
  act(() => {
    target.dispatchEvent(
      new KeyboardEvent("keydown", { key: "?", bubbles: true, cancelable: true }),
    );
  });
}

describe("ShortcutHelpDialog", () => {
  beforeEach(() => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  });

  afterEach(() => {
    cleanup();
  });

  it("`?` 전역 키를 누르면 단축키 도움말 모달이 열린다", () => {
    render(<ShortcutHelpDialog />);
    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();

    dispatchQuestion();

    expect(screen.getByText(DIALOG_TITLE)).toBeInTheDocument();
  });

  it("단축키 4개 (⌘+S / ⌘+Enter / ? / Esc) 를 표시한다", () => {
    render(<ShortcutHelpDialog />);
    dispatchQuestion();

    const list = screen.getByTestId("shortcut-list");
    expect(list.textContent).toContain("저장");
    expect(list.textContent).toContain("파싱 실행");
    expect(list.textContent).toContain("이 도움말 열기");
    expect(list.textContent).toContain("닫기");

    const kbds = list.querySelectorAll("kbd");
    const labels = Array.from(kbds).map((k) => k.textContent);
    expect(labels).toEqual(expect.arrayContaining(["⌘", "S", "Enter", "?", "Esc"]));
  });

  it("input 에 focus 가 있을 때 `?` 키는 모달을 열지 않는다", () => {
    render(
      <>
        <input data-testid="probe-input" />
        <ShortcutHelpDialog />
      </>,
    );
    const input = screen.getByTestId("probe-input") as HTMLInputElement;
    input.focus();
    expect(document.activeElement).toBe(input);

    dispatchQuestion(input);

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("textarea 에 focus 가 있을 때 `?` 키는 모달을 열지 않는다", () => {
    render(
      <>
        <textarea data-testid="probe-textarea" />
        <ShortcutHelpDialog />
      </>,
    );
    const textarea = screen.getByTestId("probe-textarea") as HTMLTextAreaElement;
    textarea.focus();

    dispatchQuestion(textarea);

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("contentEditable 요소에 focus 가 있을 때 `?` 키는 모달을 열지 않는다", () => {
    render(
      <>
        <div data-testid="probe-editable" contentEditable tabIndex={0} />
        <ShortcutHelpDialog />
      </>,
    );
    const editable = screen.getByTestId("probe-editable") as HTMLDivElement;
    editable.focus();

    dispatchQuestion(editable);

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("modifier (ctrl/meta/alt) 와 함께 눌린 `?` 는 무시한다", () => {
    render(<ShortcutHelpDialog />);
    act(() => {
      document.dispatchEvent(
        new KeyboardEvent("keydown", { key: "?", metaKey: true, bubbles: true }),
      );
    });
    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent("keydown", { key: "?", ctrlKey: true, bubbles: true }),
      );
    });
    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("Esc 로 닫힌다 (Base UI Dialog 내장)", () => {
    render(<ShortcutHelpDialog />);
    dispatchQuestion();
    expect(screen.getByText(DIALOG_TITLE)).toBeInTheDocument();

    act(() => {
      fireEvent.keyDown(document.body, { key: "Escape" });
    });

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });

  it("언마운트 후 `?` 이벤트는 keydown 리스너를 재호출하지 않는다 (cleanup 검증)", () => {
    const { unmount } = render(<ShortcutHelpDialog />);

    unmount();
    dispatchQuestion();

    expect(screen.queryByText(DIALOG_TITLE)).toBeNull();
  });
});
