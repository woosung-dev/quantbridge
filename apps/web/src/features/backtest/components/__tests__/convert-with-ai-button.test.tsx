import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  convertIndicator: vi.fn(),
  getToken: vi.fn(),
}));

vi.mock("../../api", () => ({
  convertIndicator: mocks.convertIndicator,
}));

vi.mock("@/hooks/use-auth-ctx", () => ({
  useAuthCtx: () => ({ getToken: mocks.getToken }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { ConvertWithAIButton } from "../ConvertWithAIButton";

const CONVERTED_RESULT = {
  converted_code: 'strategy("Converted")',
  input_tokens: 0,
  output_tokens: 0,
  warnings: ["AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)"],
  sliced_from: 3,
  sliced_to: 2,
  token_reduction_pct: 33.3,
};

describe("ConvertWithAIButton", () => {
  beforeEach(() => {
    mocks.convertIndicator.mockReset();
    mocks.getToken.mockReset();
    mocks.getToken.mockResolvedValue("test-token");
  });

  it("클릭하면 sliced 모드로 변환하고 성공 결과를 부모에 전달한다", async () => {
    const onConverted = vi.fn();
    mocks.convertIndicator.mockResolvedValueOnce(CONVERTED_RESULT);

    render(
      <ConvertWithAIButton indicatorCode={'indicator("Example")'} onConverted={onConverted} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "AI로 변환하기" }));

    await waitFor(() => {
      expect(mocks.convertIndicator).toHaveBeenCalledWith(
        {
          code: 'indicator("Example")',
          strategy_name: "Converted Strategy",
          mode: "sliced",
        },
        "test-token",
      );
      expect(onConverted).toHaveBeenCalledWith(CONVERTED_RESULT);
    });
  });
});
