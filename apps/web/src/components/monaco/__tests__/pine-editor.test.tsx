// PineEditor ⌘+Enter 회귀 — `addCommand` 는 마운트 때 한 번만 등록되므로, 마운트 뒤에 부모가
// 넘긴 새 `onTriggerParse`(최신 소스를 잡은 클로저)를 불러야 한다.

import { act, cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const registered: { command: (() => void) | null } = { command: null };

// next/dynamic 을 동기 렌더로 바꾸고, Monaco 자리에는 onMount 를 한 번만 부르는 가짜를 둔다.
vi.mock("next/dynamic", async () => {
  const React = await import("react");
  return {
    default: () =>
      function FakeMonaco(props: { onMount?: (editor: unknown, monaco: unknown) => void }) {
        const { onMount } = props;
        React.useEffect(() => {
          const editor = {
            addCommand: (_key: number, cb: () => void) => {
              registered.command = cb;
            },
          };
          const monaco = { KeyMod: { CtrlCmd: 2048 }, KeyCode: { Enter: 3 } };
          onMount?.(editor, monaco);
          // 실제 Monaco 처럼 마운트 1회만 — deps 를 비워 재등록하지 않는다.
        }, []);
        return null;
      },
  };
});

vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "dark" }) }));
vi.mock("@/lib/fonts", () => ({ ibmPlexMono: { style: { fontFamily: "mono" } } }));
vi.mock("@/components/monaco/pine-language", () => ({ registerPineLanguage: vi.fn() }));

import { PineEditor } from "@/components/monaco/pine-editor";

describe("PineEditor ⌘+Enter", () => {
  afterEach(() => {
    cleanup();
    registered.command = null;
  });

  it("마운트 뒤에 바뀐 onTriggerParse 를 부른다", () => {
    const first = vi.fn();
    const latest = vi.fn();
    const { rerender } = render(<PineEditor value="" onChange={() => {}} onTriggerParse={first} />);
    rerender(<PineEditor value="//@version=5" onChange={() => {}} onTriggerParse={latest} />);

    act(() => {
      registered.command?.();
    });

    expect(latest).toHaveBeenCalledTimes(1);
    expect(first).not.toHaveBeenCalled();
  });
});
