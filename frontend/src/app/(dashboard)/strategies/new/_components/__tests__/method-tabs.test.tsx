// MethodTabs — value 분기 + onChange 호출 검증 (Sprint 42-polish W3)

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { MethodTabs } from "../method-tabs";

describe("MethodTabs", () => {
  afterEach(() => {
    cleanup();
  });

  it("3개 탭 (직접/파일/URL) 모두 렌더한다", () => {
    render(<MethodTabs value="direct" onChange={() => {}} />);

    expect(screen.getByText("Pine Script 직접 입력")).toBeInTheDocument();
    expect(screen.getByText("파일 업로드")).toBeInTheDocument();
    expect(screen.getByText("TV URL 가져오기")).toBeInTheDocument();
  });

  it("value='direct' 에서 direct 탭이 활성 (data-active)", () => {
    render(<MethodTabs value="direct" onChange={() => {}} />);

    const directTab = screen.getByRole("tab", { name: /Pine Script 직접 입력/ });
    expect(directTab).toHaveAttribute("data-active");
  });

  it("disabled 탭은 data-disabled 속성을 가진다", () => {
    const onChange = vi.fn();
    render(<MethodTabs value="direct" onChange={onChange} />);

    const uploadTab = screen.getByRole("tab", { name: /파일 업로드/ });
    const urlTab = screen.getByRole("tab", { name: /TV URL 가져오기/ });
    // base-ui Tabs disabled prop → data-disabled attribute (HTML disabled 미적용)
    expect(uploadTab).toHaveAttribute("data-disabled");
    expect(urlTab).toHaveAttribute("data-disabled");

    // disabled 탭 fireEvent.click — onChange 미호출
    fireEvent.click(uploadTab);
    expect(onChange).not.toHaveBeenCalled();
  });
});
