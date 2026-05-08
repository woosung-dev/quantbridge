// Sprint 43-W12 — KillSwitchModal 단위 테스트.
// - 1단계: "다음" 버튼 → 2단계 진입
// - 2단계: 정확한 "KILL" 타이핑 전엔 실행 버튼 disabled
// - 2단계: "KILL" 정확 입력 → 실행 버튼 enabled + onConfirm 호출

import { fireEvent, render, screen } from "@testing-library/react";

import { KillSwitchModal } from "@/app/(dashboard)/trading/_components/kill-switch-modal";

describe("KillSwitchModal", () => {
  test("1단계 → 2단계 진입 + KILL 미입력 시 실행 버튼 disabled", async () => {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();

    render(
      <KillSwitchModal
        open={true}
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
        activeSessionsCount={3}
      />,
    );

    const nextBtn = await screen.findByTestId("kill-step1-next");
    fireEvent.click(nextBtn);

    const executeBtn = await screen.findByTestId("kill-confirm-execute");
    expect(executeBtn).toBeDisabled();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  test("2단계: 'KILL' 정확 입력 → 실행 버튼 enabled + onConfirm 호출", async () => {
    const onConfirm = vi.fn();

    render(
      <KillSwitchModal
        open={true}
        onOpenChange={vi.fn()}
        onConfirm={onConfirm}
        activeSessionsCount={1}
      />,
    );

    fireEvent.click(await screen.findByTestId("kill-step1-next"));

    const input = await screen.findByTestId("kill-confirm-input");
    fireEvent.change(input, { target: { value: "KILL" } });

    const executeBtn = await screen.findByTestId("kill-confirm-execute");
    expect(executeBtn).not.toBeDisabled();

    fireEvent.click(executeBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  test("2단계: 'kill' (소문자) → 실행 버튼 disabled", async () => {
    const onConfirm = vi.fn();

    render(
      <KillSwitchModal
        open={true}
        onOpenChange={vi.fn()}
        onConfirm={onConfirm}
        activeSessionsCount={2}
      />,
    );

    fireEvent.click(await screen.findByTestId("kill-step1-next"));
    fireEvent.change(await screen.findByTestId("kill-confirm-input"), {
      target: { value: "kill" },
    });

    const executeBtn = await screen.findByTestId("kill-confirm-execute");
    expect(executeBtn).toBeDisabled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
