// Monaco wrapper 파일 탭 toolbar 테스트 — 가짜 UI 방지: 프로토타입 screen-08 에 없는
// 죽은 버튼(찾기/전체화면)이 렌더되지 않아야 한다. 파일탭(파일명·버전 라벨)은 유지.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { EditorMonacoWrapper } from "@/features/strategy/components/edit/editor-monaco-wrapper";

// Monaco 에디터는 무겁고 브라우저 API 를 요구하므로 textarea 로 대체.
vi.mock("@/components/monaco/pine-editor", () => ({
  PineEditor: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea data-testid="pine-editor" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

describe("EditorMonacoWrapper — 파일 탭 toolbar (screen-08 이식)", () => {
  afterEach(() => {
    cleanup();
  });

  it("파일탭에 파일명과 버전 라벨을 그린다", () => {
    render(
      <EditorMonacoWrapper
        fileName="ma-cross.pine"
        versionLabel="Pine v5"
        value="//@version=5"
        onChange={() => {}}
      />,
    );
    const filetab = screen.getByTestId("editor-monaco-wrapper-filetab");
    expect(filetab.textContent).toContain("ma-cross.pine");
    expect(filetab.textContent).toContain("Pine v5");
  });

  it("죽은 버튼(찾기/전체화면)을 렌더하지 않는다 — screen-08 에 없는 발명 UI", () => {
    render(<EditorMonacoWrapper value="//@version=5" onChange={() => {}} />);
    expect(screen.queryByRole("button", { name: "찾기 (Cmd+F)" })).toBeNull();
    expect(screen.queryByRole("button", { name: "전체화면" })).toBeNull();
  });
});
