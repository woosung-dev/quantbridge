// Skeleton + 변형 (Table / Form) 단위 테스트.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { Skeleton, TableSkeleton, FormSkeleton } from "@/components/skeleton";

describe("Skeleton", () => {
  afterEach(() => {
    cleanup();
  });

  it("기본 Skeleton 은 animate-pulse + rounded 클래스를 가진다", () => {
    render(<Skeleton className="h-4 w-32" />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("animate-pulse");
    expect(el.className).toContain("rounded-md");
    expect(el.className).toContain("bg-muted");
  });

  it("TableSkeleton 은 rows × columns 만큼 row cell 을 그린다", () => {
    render(<TableSkeleton rows={3} columns={4} />);
    const rowCells = screen.getAllByTestId("table-skeleton-row-cell");
    expect(rowCells).toHaveLength(3 * 4);
    const headerCells = screen.getAllByTestId("table-skeleton-header-cell");
    expect(headerCells).toHaveLength(4);
  });

  it("FormSkeleton 은 fields 갯수만큼 필드 placeholder 를 그린다", () => {
    render(<FormSkeleton fields={3} />);
    const fields = screen.getAllByTestId("form-skeleton-field");
    expect(fields).toHaveLength(3);
  });

  // Sprint 47 BL-206: variant API 동작 검증.
  it.each([
    ["text", "h-4"],
    ["card", "h-36"],
    ["list-row", "h-12"],
    ["chart", "h-64"],
    ["table-cell", "h-6"],
  ] as const)(
    "variant=%s 는 %s 클래스를 적용한다",
    (variant, expectedClass) => {
      render(<Skeleton variant={variant} />);
      const el = screen.getByTestId("skeleton");
      expect(el.className).toContain(expectedClass);
      expect(el.dataset.variant).toBe(variant);
    },
  );

  it("variant 와 className 가 충돌하면 className 이 우선한다 (twMerge)", () => {
    render(<Skeleton variant="text" className="h-20" />);
    const el = screen.getByTestId("skeleton");
    // twMerge 결과: h-4 → h-20 으로 override.
    expect(el.className).toContain("h-20");
    expect(el.className).not.toContain("h-4");
  });
});
