// Optimizer 3폼의 zod field 오류 렌더와 제출 차단을 검증한다.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BayesianSearchForm } from "../bayesian-search-form";
import { GeneticSearchForm } from "../genetic-search-form";
import { GridSearchForm } from "../grid-search-form";

const BACKTEST_ID = "3f9c1a52-1111-4222-8333-944455556666";

const gridMutateAsync = vi.fn();
const bayesianMutateAsync = vi.fn();
const geneticMutateAsync = vi.fn();

vi.mock("@/features/optimizer/hooks", () => ({
  useSubmitGridSearch: () => ({ mutateAsync: gridMutateAsync, isPending: false }),
  useSubmitBayesianSearch: () => ({ mutateAsync: bayesianMutateAsync, isPending: false }),
  useSubmitGeneticSearch: () => ({ mutateAsync: geneticMutateAsync, isPending: false }),
}));

const forms = [
  {
    name: "그리드",
    Form: GridSearchForm,
    submitLabel: /그리드 탐색 실행/,
    mutateAsync: gridMutateAsync,
  },
  {
    name: "베이지안",
    Form: BayesianSearchForm,
    submitLabel: /베이지안 탐색 실행/,
    mutateAsync: bayesianMutateAsync,
  },
  {
    name: "유전 알고리즘",
    Form: GeneticSearchForm,
    submitLabel: /유전 알고리즘 탐색 실행/,
    mutateAsync: geneticMutateAsync,
  },
];

beforeEach(() => {
  gridMutateAsync.mockClear();
  bayesianMutateAsync.mockClear();
  geneticMutateAsync.mockClear();
});

describe("OptimizerSearchForm field errors", () => {
  it.each(forms)("$name 폼은 빈 변수 이름 오류를 row에 표시하고 제출을 차단한다", async ({
    Form,
    submitLabel,
    mutateAsync,
  }) => {
    render(<Form backtestId={BACKTEST_ID} />);
    fireEvent.click(screen.getByRole("button", { name: submitLabel }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("변수 이름을 입력하세요."),
    );
    expect(screen.getByPlaceholderText("변수 이름 (예: length)")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it.each(forms)("$name 폼은 최소값이 최대값 이상이면 최대값 오류를 표시하고 제출을 차단한다", async ({
    Form,
    submitLabel,
    mutateAsync,
  }) => {
    render(<Form backtestId={BACKTEST_ID} />);
    fireEvent.change(screen.getByPlaceholderText("변수 이름 (예: length)"), {
      target: { value: "length" },
    });
    fireEvent.change(screen.getByPlaceholderText("최소"), { target: { value: "30" } });
    fireEvent.change(screen.getByPlaceholderText("최대"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: submitLabel }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("최소값은 최대값"),
    );
    expect(screen.getByPlaceholderText("최대")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByPlaceholderText("최대")).toHaveAttribute(
      "aria-describedby",
      "optimizer-param-0-max-error",
    );
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  // 최종 diff 리뷰 P2 — 행 0개면 행별 슬롯이 없어 .min(1) 오류가 사라지는 무피드백 회귀 가드.
  it.each(forms)("$name 폼은 파라미터 행을 전부 삭제하고 제출하면 배열 오류를 표시하고 제출을 차단한다", async ({
    Form,
    submitLabel,
    mutateAsync,
  }) => {
    render(<Form backtestId={BACKTEST_ID} />);
    fireEvent.click(screen.getByRole("button", { name: "파라미터 삭제" }));
    fireEvent.click(screen.getByRole("button", { name: submitLabel }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "파라미터를 하나 이상 추가하세요.",
      ),
    );
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("F6 normal prior 와 로그 스케일 조합은 log_scale 오류를 표시하고 제출을 차단한다", async () => {
    render(<BayesianSearchForm backtestId={BACKTEST_ID} />);
    fireEvent.change(screen.getByPlaceholderText("변수 이름 (예: length)"), {
      target: { value: "length" },
    });
    const normalOption = screen.getByRole("option", {
      name: "정규분포 (중앙 집중)",
    });
    fireEvent.change(normalOption.parentElement!, { target: { value: "normal" } });
    fireEvent.click(screen.getByLabelText("로그 스케일"));
    fireEvent.click(screen.getByRole("button", { name: /베이지안 탐색 실행/ }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "정규분포 prior 는 로그 스케일과 함께 쓸 수 없습니다. 로그 스케일은 로그균등 prior 를 사용하세요.",
      ),
    );
    expect(screen.getByLabelText("로그 스케일")).toHaveAttribute("aria-invalid", "true");
    expect(bayesianMutateAsync).not.toHaveBeenCalled();
  });
});
