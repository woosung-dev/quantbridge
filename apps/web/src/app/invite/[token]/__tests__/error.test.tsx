import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import InviteError from "../error";

describe("InviteError", () => {
  it("원본 Error 없이 고정 공개 오류 화면을 렌더한다", () => {
    render(<InviteError reset={vi.fn()} />);

    expect(screen.getByTestId("public-route-error")).toHaveTextContent(
      "잠시 후 다시 시도해 주세요.",
    );
    expect(screen.getByTestId("public-route-error")).not.toHaveTextContent("digest");
  });
});
