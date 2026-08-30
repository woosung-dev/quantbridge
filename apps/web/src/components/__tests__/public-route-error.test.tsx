import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PublicRouteError } from "../public-route-error";

describe("PublicRouteError", () => {
  it("고정 문구와 재시도만 렌더한다", () => {
    const reset = vi.fn();
    render(
      <PublicRouteError
        heading="열지 못했습니다"
        body="잠시 후 다시 시도해 주세요."
        reset={reset}
      />,
    );

    expect(screen.getByRole("heading", { name: "열지 못했습니다" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
