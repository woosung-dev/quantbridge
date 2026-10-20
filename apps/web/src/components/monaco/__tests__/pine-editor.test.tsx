import { useEffect, useState } from "react";
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const boundary = vi.hoisted(() => {
  const state = { command: null as (() => void) | null, mounts: 0 };
  return {
    state,
    keys: { KeyMod: { CtrlCmd: 2048 }, KeyCode: { Enter: 3 } },
    editor: {
      addCommand: vi.fn((_keybinding: number, command: () => void) => {
        state.command = command;
      }),
    },
  };
});

interface StubEditorProps {
  onMount: (editor: typeof boundary.editor, monaco: typeof boundary.keys) => void;
  value: string;
}

// 실제 Monaco 처럼 onMount 명령 등록은 editor instance 생성 시 한 번만 실행한다.
vi.mock("next/dynamic", () => ({
  default: () =>
    function StubEditor({ onMount, value }: StubEditorProps) {
      const [mount] = useState(() => onMount);
      useEffect(() => {
        boundary.state.mounts += 1;
        mount(boundary.editor, boundary.keys);
      }, [mount]);
      return <div data-testid="monaco-editor">{value}</div>;
    },
}));
vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "dark" }) }));

import { PineEditor } from "../pine-editor";

beforeEach(() => {
  boundary.state.command = null;
  boundary.state.mounts = 0;
  boundary.editor.addCommand.mockClear();
});
afterEach(cleanup);

function triggerRegisteredCommand() {
  expect(boundary.state.command).not.toBeNull();
  act(() => boundary.state.command?.());
}

describe("PineEditor — 등록된 파싱 키 명령", () => {
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
});
