// EditorMonacoWrapper — file-tab 라벨 / Pine 버전 / toolbar 아이콘 (Sprint 43 W9-fidelity)
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Monaco editor 는 client-only & dynamic import — 테스트 환경에서는 stub.
vi.mock("@/components/monaco/pine-editor", () => ({
  PineEditor: ({ value }: { value: string }) => (
    <div data-testid="pine-editor-stub">{value}</div>
  ),
}));

import { EditorMonacoWrapper } from "../editor-monaco-wrapper";

describe("EditorMonacoWrapper", () => {
  it("기본 fileName/versionLabel 이 렌더되고 PineEditor 자식이 마운트됨", () => {
    render(<EditorMonacoWrapper value="//@version=5" onChange={() => {}} />);

    expect(screen.getByTestId("editor-monaco-wrapper")).toBeInTheDocument();
    expect(screen.getByTestId("editor-monaco-wrapper-filetab")).toHaveTextContent(
      "strategy.pine",
    );
    expect(screen.getByTestId("editor-monaco-wrapper-filetab")).toHaveTextContent(
      "Pine v5",
    );
    expect(screen.getByTestId("pine-editor-stub")).toHaveTextContent(
      "//@version=5",
    );
  });

  it("fileName 커스터마이즈 가능 + toolbar 아이콘 button 2개 (찾기/전체화면)", () => {
    render(
      <EditorMonacoWrapper
        value=""
        onChange={() => {}}
        fileName="ma_crossover.pine"
        versionLabel="Pine v6"
      />,
    );

    expect(screen.getByText("ma_crossover.pine")).toBeInTheDocument();
    expect(screen.getByText("Pine v6")).toBeInTheDocument();
    expect(screen.getByLabelText("찾기 (Cmd+F)")).toBeInTheDocument();
    expect(screen.getByLabelText("전체화면")).toBeInTheDocument();
  });
});
