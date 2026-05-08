// MethodTabs — value 분기 + onChange 호출 검증 (Sprint 42-polish W3-fidelity)
// fidelity 1차 = shadcn `<Tabs>` `line` variant 의 width/underline mismatch 해결 위해
// raw <button role="tab"> + aria-selected/aria-disabled 로 교체. 테스트도 ARIA 기반으로 정렬.

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

  it("value='direct' 에서 direct 탭이 활성 (aria-selected=true)", () => {
    render(<MethodTabs value="direct" onChange={() => {}} />);

    const directTab = screen.getByRole("tab", { name: /Pine Script 직접 입력/ });
    expect(directTab).toHaveAttribute("aria-selected", "true");
  });

  it("disabled 탭은 aria-disabled + native disabled, click 무반응", () => {
    const onChange = vi.fn();
    render(<MethodTabs value="direct" onChange={onChange} />);

    const uploadTab = screen.getByRole("tab", { name: /파일 업로드/ });
    const urlTab = screen.getByRole("tab", { name: /TV URL 가져오기/ });
    expect(uploadTab).toHaveAttribute("aria-disabled", "true");
    expect(urlTab).toHaveAttribute("aria-disabled", "true");
    expect(uploadTab).toBeDisabled();
    expect(urlTab).toBeDisabled();

    // disabled 탭 fireEvent.click — onChange 미호출
    fireEvent.click(uploadTab);
    expect(onChange).not.toHaveBeenCalled();
  });
});
