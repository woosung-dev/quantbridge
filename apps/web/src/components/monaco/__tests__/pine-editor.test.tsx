import { createRef, useEffect, useState } from "react";
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const boundary = vi.hoisted(() => {
  const state = {
    command: null as (() => void) | null,
    mounts: 0,
    changeRegistrations: 0,
    change: null as ((value: string | undefined) => void) | null,
    hasModel: true,
    lineCount: 12,
  };
  const model = { getLineCount: vi.fn(() => state.lineCount) };
  return {
    state,
    keys: {
      KeyMod: { CtrlCmd: 2048 },
      KeyCode: { Enter: 3 },
      Selection: class Selection {
        constructor(
          readonly selectionStartLineNumber: number,
          readonly selectionStartColumn: number,
          readonly positionLineNumber: number,
          readonly positionColumn: number,
        ) {}
      },
    },
    editor: {
      addCommand: vi.fn((_keybinding: number, command: () => void) => {
        state.command = command;
      }),
      getModel: vi.fn(() => (state.hasModel ? model : null)),
      revealLineInCenter: vi.fn(),
      setSelection: vi.fn(),
      focus: vi.fn(),
      updateOptions: vi.fn(),
    },
  };
});

interface StubEditorProps {
  onMount: (editor: typeof boundary.editor, monaco: typeof boundary.keys) => void;
  value: string;
  options: unknown;
  onChange: (value: string | undefined) => void;
}

// 실제 Monaco 처럼 onMount 명령 등록은 editor instance 생성 시 한 번만 실행한다.
vi.mock("next/dynamic", () => ({
  default: () =>
    function StubEditor({ onMount, value, options, onChange }: StubEditorProps) {
      const [mount] = useState(() => onMount);
      useEffect(() => {
        boundary.state.mounts += 1;
        mount(boundary.editor, boundary.keys);
      }, [mount]);
      useEffect(() => {
        boundary.editor.updateOptions(options);
      }, [options]);
      // 실제 @monaco-editor/react도 onChange 참조가 바뀌면 모델 listener를 교체한다.
      useEffect(() => {
        boundary.state.changeRegistrations += 1;
        boundary.state.change = onChange;
        return () => {
          boundary.state.change = null;
        };
      }, [onChange]);
      return <div data-testid="monaco-editor">{value}</div>;
    },
}));
vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "dark" }) }));

import { PineEditor, type PineEditorHandle } from "../pine-editor";

beforeEach(() => {
  boundary.state.command = null;
  boundary.state.mounts = 0;
  boundary.state.changeRegistrations = 0;
  boundary.state.change = null;
  boundary.state.hasModel = true;
  boundary.state.lineCount = 12;
  boundary.editor.addCommand.mockClear();
  boundary.editor.getModel.mockClear();
  boundary.editor.revealLineInCenter.mockClear();
  boundary.editor.setSelection.mockClear();
  boundary.editor.focus.mockClear();
  boundary.editor.updateOptions.mockClear();
});
afterEach(cleanup);

function triggerRegisteredCommand() {
  expect(boundary.state.command).not.toBeNull();
  act(() => boundary.state.command?.());
}

describe("PineEditor — 등록된 파싱 키 명령", () => {
  it("타이핑과 부모 callback 변경 후에도 같은 listener가 최신 callback을 부른다", () => {
    const first = vi.fn();
    const latest = vi.fn();
    const { rerender } = render(<PineEditor value="A" onChange={first} />);
    act(() => boundary.state.change?.("AB"));
    expect(first).toHaveBeenCalledWith("AB");

    rerender(<PineEditor value="AB" onChange={first} />);
    rerender(<PineEditor value="AB" onChange={latest} />);
    act(() => boundary.state.change?.(undefined));

    expect(latest).toHaveBeenCalledWith("");
    expect(first).toHaveBeenCalledOnce();
    expect(boundary.state.changeRegistrations).toBe(1);
    expect(boundary.state.mounts).toBe(1);
  });

  it("타이핑은 옵션을 다시 적용하지 않고 readOnly 변경은 즉시 반영한다", () => {
    const onChange = vi.fn();
    const { rerender } = render(<PineEditor value="A" onChange={onChange} />);
    rerender(<PineEditor value="AB" onChange={onChange} />);
    rerender(<PineEditor value="ABC" onChange={onChange} />);
    expect(boundary.editor.updateOptions).toHaveBeenCalledTimes(1);

    rerender(<PineEditor value="ABC" onChange={onChange} readOnly />);
    expect(boundary.editor.updateOptions).toHaveBeenCalledTimes(2);
    expect(boundary.editor.updateOptions).toHaveBeenLastCalledWith(
      expect.objectContaining({ readOnly: true }),
    );
  });

  it("마운트 뒤에 바뀐 onTriggerParse 를 부른다", () => {
    const first = vi.fn();
    const latest = vi.fn();
    const { rerender } = render(<PineEditor value="" onChange={vi.fn()} onTriggerParse={first} />);
    rerender(<PineEditor value="//@version=5" onChange={vi.fn()} onTriggerParse={latest} />);

    triggerRegisteredCommand();

    expect(latest).toHaveBeenCalledTimes(1);
    expect(first).not.toHaveBeenCalled();
  });

  it("부모가 callback 을 바꿔도 같은 editor 명령이 최신 원문을 사용한다", () => {
    const onChange = vi.fn();
    const parse = vi.fn();
    const { rerender } = render(
      <PineEditor value="A" onChange={onChange} onTriggerParse={() => parse("A")} />,
    );
    triggerRegisteredCommand();
    expect(parse).toHaveBeenLastCalledWith("A");

    rerender(<PineEditor value="B" onChange={onChange} onTriggerParse={() => parse("B")} />);
    triggerRegisteredCommand();
    expect(parse).toHaveBeenLastCalledWith("B");
    expect(parse).toHaveBeenCalledTimes(2);
    // 최신 callback 을 받기 위해 무거운 editor 나 명령을 재생성하지 않는다.
    expect(boundary.state.mounts).toBe(1);
    expect(boundary.editor.addCommand).toHaveBeenCalledTimes(1);
  });

  it("마운트 뒤 callback 을 추가하면 기존 명령으로 실행할 수 있다", () => {
    const onChange = vi.fn();
    const parse = vi.fn();
    const { rerender } = render(<PineEditor value="A" onChange={onChange} />);
    rerender(<PineEditor value="A" onChange={onChange} onTriggerParse={parse} />);
    triggerRegisteredCommand();
    expect(parse).toHaveBeenCalledTimes(1);
  });

  it("callback 을 제거한 뒤에는 이전 callback 을 실행하지 않는다", () => {
    const onChange = vi.fn();
    const parse = vi.fn();
    const { rerender } = render(
      <PineEditor value="A" onChange={onChange} onTriggerParse={parse} />,
    );
    rerender(<PineEditor value="A" onChange={onChange} />);
    triggerRegisteredCommand();
    expect(parse).not.toHaveBeenCalled();
  });

  it("서버 행으로 이동해 선택하고 focus하며 EOF 초과 행은 마지막 행으로 제한한다", () => {
    const ref = createRef<PineEditorHandle>();
    render(<PineEditor ref={ref} value="A" onChange={vi.fn()} />);

    expect(ref.current?.revealLine1(99)).toBe(true);
    expect(boundary.editor.revealLineInCenter).toHaveBeenCalledWith(12);
    expect(boundary.editor.setSelection).toHaveBeenCalledWith(
      expect.objectContaining({
        selectionStartLineNumber: 12,
        selectionStartColumn: 1,
        positionLineNumber: 12,
        positionColumn: 1,
      }),
    );
    expect(boundary.editor.focus).toHaveBeenCalledOnce();

    // 같은 행을 다시 눌러도 다시 reveal/focus 한다.
    expect(ref.current?.revealLine1(12)).toBe(true);
    expect(boundary.editor.revealLineInCenter).toHaveBeenCalledTimes(2);
    expect(boundary.editor.focus).toHaveBeenCalledTimes(2);
  });

  it("안전한 양의 정수가 아니거나 모델이 없으면 이동하지 않는다", () => {
    const ref = createRef<PineEditorHandle>();
    render(<PineEditor ref={ref} value="A" onChange={vi.fn()} />);

    for (const line of [0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
      expect(ref.current?.revealLine1(line)).toBe(false);
    }
    boundary.state.hasModel = false;
    expect(ref.current?.revealLine1(1)).toBe(false);
    expect(boundary.editor.revealLineInCenter).not.toHaveBeenCalled();
    expect(boundary.editor.setSelection).not.toHaveBeenCalled();
    expect(boundary.editor.focus).not.toHaveBeenCalled();
  });
});
