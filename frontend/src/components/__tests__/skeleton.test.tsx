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
});
