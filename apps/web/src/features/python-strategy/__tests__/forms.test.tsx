import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrategyForm } from "../components/strategy-form";
import { BacktestForm } from "../components/backtest-form";
import { RunResult } from "../components/run-result";
import { ApiError } from "@/lib/api-client";
import { makeRun, STRATEGY } from "./fixtures";

vi.mock("../components/python-editor", () => ({
  PythonEditor: ({ value, onChange }: { value: string; onChange: (source: string) => void }) => (
    <textarea
      aria-label="Python 전략 코드"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  ),
}));

afterEach(cleanup);
describe("Python 실험실 폼과 실행 상태", () => {
  it("잘못된 파라미터는 저장하지 않고 해당 입력 오류를 알린다", async () => {
    const onSave = vi.fn();
    render(
      <StrategyForm strategy={null} isSaving={false} error={null} onSave={onSave}>
        {() => null}
      </StrategyForm>,
    );
    fireEvent.change(screen.getByLabelText("파라미터 JSON"), { target: { value: "[]" } });
    fireEvent.click(screen.getByRole("button", { name: "첫 버전 저장" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("객체 형태의 JSON");
    expect(onSave).not.toHaveBeenCalled();
  });
  it("수정 여부를 실행 폼에 전달하고 저장된 버전을 보여준다", () => {
    render(
      <StrategyForm strategy={STRATEGY} isSaving={false} error={null} onSave={vi.fn()}>
        {(isDirty) => <p>{isDirty ? "저장 필요" : "실행 가능"}</p>}
      </StrategyForm>,
    );
    expect(screen.getByText("실행 가능")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("전략 이름"), { target: { value: "새 이름" } });
    expect(screen.getByText("저장 필요")).toBeInTheDocument();
    expect(screen.getByText(`버전 ${STRATEGY.version_id.slice(0, 8)}`)).toBeInTheDocument();
  });
  it("뒤바뀐 기간은 실행하지 않고 오류를 표시한다", async () => {
    const onRun = vi.fn();
    render(
      <BacktestForm canRun disabledReason={null} isStarting={false} error={null} onRun={onRun} />,
    );
    fireEvent.change(screen.getByLabelText("시작일 (UTC)"), { target: { value: "2026-06-01" } });
    fireEvent.change(screen.getByLabelText("종료일 (UTC, 미포함)"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "저장한 버전으로 백테스트" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("종료일은 시작일 이후");
    expect(onRun).not.toHaveBeenCalled();
  });
  it("실행 불가 사유를 표시하고 시작 버튼을 차단한다", () => {
    render(
      <BacktestForm
        canRun={false}
        disabledReason="격리 실행 환경이 준비되지 않았습니다."
        isStarting={false}
        error={null}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("격리 실행 환경");
    expect(screen.getByRole("button", { name: "저장한 버전으로 백테스트" })).toBeDisabled();
  });
  it("서버가 반환한 실패 이유를 실행 폼에 표시한다", () => {
    const error = new ApiError(422, "data_coverage", "API 422", {
      detail: { code: "data_coverage", detail: "요청 기간의 시세가 부족합니다" },
    });
    render(
      <BacktestForm
        canRun
        disabledReason={null}
        isStarting={false}
        error={error}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("요청 기간의 시세가 부족합니다");
  });
  it("정상 실행 조건을 전달한다", async () => {
    const onRun = vi.fn();
    render(
      <BacktestForm canRun disabledReason={null} isStarting={false} error={null} onRun={onRun} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "저장한 버전으로 백테스트" }));
    await waitFor(() => expect(onRun).toHaveBeenCalledTimes(1));
    expect(onRun.mock.calls[0]?.[0]).toMatchObject({
      symbol: "BTC/USDT",
      timeframe: "4h",
      initial_capital: "10000",
    });
  });
  it("버전 충돌은 저장된 전략을 다시 선택하도록 안내한다", () => {
    render(
      <BacktestForm
        canRun
        disabledReason={null}
        isStarting={false}
        error={new ApiError(409, "python_strategy_version_conflict", "API 409")}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("저장된 전략을 다시 선택한 뒤 실행하세요");
  });
  it("진행 중 실행만 취소할 수 있고 취소 실패를 표시한다", () => {
    const onCancel = vi.fn();
    const view = render(
      <RunResult
        run={makeRun()}
        isCancelling={false}
        cancelError="취소 요청 실패"
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "실행 취소" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent("취소 요청 실패");
    view.rerender(
      <RunResult
        run={makeRun({ status: "cancelled" })}
        isCancelling={false}
        cancelError={null}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("취소됨");
    expect(screen.queryByRole("button", { name: "실행 취소" })).not.toBeInTheDocument();
  });
  it("단일 실행의 수익을 후보 검증 통과로 표시하지 않는다", () => {
    render(
      <RunResult
        run={makeRun({
          status: "completed",
          result: {
            metrics: {
              total_return: "0.2",
              max_drawdown: "0.1",
              profit_factor: "1.5",
              num_trades: 40,
              sharpe_ratio: null,
              total_fees: "30",
              total_slippage: "10",
            },
            equity_curve: [],
            trades: [],
            provenance: { source_hash: STRATEGY.source_hash },
          },
        })}
        isCancelling={false}
        cancelError={null}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("20.00%")).toBeInTheDocument();
    expect(screen.getByText("단일 백테스트 · 후보 검증 미완료.")).toBeInTheDocument();
    expect(screen.queryByText("검증 통과")).not.toBeInTheDocument();
    expect(screen.getByText("발생한 거래가 없습니다.")).toBeInTheDocument();
  });
});
