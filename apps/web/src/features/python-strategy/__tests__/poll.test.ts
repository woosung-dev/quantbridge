import { describe, expect, it } from "vitest";
import type { Query } from "@tanstack/react-query";
import { pythonRunListPoll, pythonRunPoll } from "../hooks";
import type { PythonRun } from "../schemas";
import { makeRun } from "./fixtures";

function query<T>(data: T | undefined, status = "success") {
  return { state: { data, status } } as unknown as Query<T, Error>;
}
describe("Python 실행 폴링", () => {
  it("완료·실패·취소 및 네트워크 오류에서 상세 폴링을 중단한다", () => {
    for (const status of ["completed", "failed", "cancelled"] as const)
      expect(pythonRunPoll(query(makeRun({ status })))).toBe(false);
    expect(pythonRunPoll(query<PythonRun>(undefined, "error"))).toBe(false);
    expect(pythonRunPoll(query(makeRun()))).toBeGreaterThan(0);
  });
  it("다른 실행에 진행 중 항목이 있는 동안만 이력을 갱신한다", () => {
    expect(
      pythonRunListPoll(
        query({ items: [makeRun({ status: "completed" }), makeRun({ status: "pending" })] }),
      ),
    ).toBeGreaterThan(0);
    expect(pythonRunListPoll(query({ items: [makeRun({ status: "completed" })] }))).toBe(false);
    expect(pythonRunListPoll(query<{ items: PythonRun[] }>(undefined))).toBe(false);
    expect(pythonRunListPoll(query({ items: [makeRun()] }, "error"))).toBe(false);
  });
});
