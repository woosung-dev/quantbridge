// [BL-817] 대시보드 동적 라우트가 Next.js 16 params Promise를 해석해 실제 뷰 prop으로 넘기는지 고정한다.
// `notFound()`는 런타임과 같이 예외를 던져 이후 EditorView 렌더를 차단한다.

import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const { notFound, notFoundError } = vi.hoisted(() => {
  const error = new Error("NEXT_NOT_FOUND");

  return {
    notFound: vi.fn(() => {
      throw error;
    }),
    notFoundError: error,
  };
});

vi.mock("next/navigation", () => ({ notFound }));

vi.mock("@/features/backtest/components/backtest-detail-view", () => ({
  BacktestDetailView: vi.fn((props: { id: string }) => (
    <div data-testid="backtest-detail-marker" data-props={JSON.stringify(props)} />
  )),
}));

vi.mock("@/features/optimizer/components/optimizer-run-detail", () => ({
  OptimizerRunDetail: vi.fn((props: { runId: string }) => (
    <div data-testid="optimizer-run-marker" data-props={JSON.stringify(props)} />
  )),
}));

vi.mock("@/features/strategy/components/edit/editor-view", () => ({
  EditorView: vi.fn((props: { id: string }) => (
    <div data-testid="strategy-editor-marker" data-props={JSON.stringify(props)} />
  )),
}));

import BacktestDetailPage, { metadata as backtestMetadata } from "../backtests/[id]/page";
import OptimizerRunPage, { metadata as optimizerMetadata } from "../optimizer/[id]/page";
import StrategyEditPage, { metadata as strategyMetadata } from "../strategies/[id]/edit/page";

import { BacktestDetailView } from "@/features/backtest/components/backtest-detail-view";
import { OptimizerRunDetail } from "@/features/optimizer/components/optimizer-run-detail";
import { EditorView } from "@/features/strategy/components/edit/editor-view";

const LOWERCASE_UUID = "123e4567-e89b-42d3-a456-426614174000";
const UPPERCASE_UUID = LOWERCASE_UUID.toUpperCase();

type RoutePage = (input: { params: Promise<{ id: string }> }) => Promise<ReactNode>;

interface PropsMarker {
  mock: { calls: unknown[][] };
}

interface RouteCase {
  name: string;
  page: RoutePage;
  marker: PropsMarker;
  markerTestId: string;
  propsForId: (id: string) => Record<string, string>;
}

const ROUTE_CASES: readonly RouteCase[] = [
  {
    name: "backtests/[id]",
    page: BacktestDetailPage,
    marker: vi.mocked(BacktestDetailView),
    markerTestId: "backtest-detail-marker",
    propsForId: (id) => ({ id }),
  },
  {
    name: "optimizer/[id]",
    page: OptimizerRunPage,
    marker: vi.mocked(OptimizerRunDetail),
    markerTestId: "optimizer-run-marker",
    propsForId: (id) => ({ runId: id }),
  },
  {
    name: "strategies/[id]/edit",
    page: StrategyEditPage,
    marker: vi.mocked(EditorView),
    markerTestId: "strategy-editor-marker",
    propsForId: (id) => ({ id }),
  },
];

const UNVALIDATED_ROUTE_CASES = ROUTE_CASES.slice(0, 2);

async function renderPage(page: RoutePage, id: string, hasDelayedParams = false): Promise<string> {
  const params = hasDelayedParams
    ? new Promise<{ id: string }>((resolve) => setTimeout(() => resolve({ id }), 0))
    : Promise.resolve({ id });
  const element = await page({ params });

  return renderToStaticMarkup(element);
}

function expectMarkerProps(
  marker: PropsMarker,
  markerTestId: string,
  expectedProps: Record<string, string>,
  html: string,
): void {
  expect(html).toContain(`data-testid="${markerTestId}"`);
  expect(html).toContain("data-props=");
  expect(marker.mock.calls).toHaveLength(1);
  expect(marker.mock.calls[0]?.[0]).toStrictEqual(expectedProps);
}

afterEach(() => vi.clearAllMocks());

describe("[BL-817] 대시보드 동적 라우트 params", () => {
  it.each(ROUTE_CASES)("$name — 해석한 id를 실제 뷰 prop으로 그대로 전달한다", async (route) => {
    const html = await renderPage(route.page, LOWERCASE_UUID);

    // 관측한 전체 prop은 BacktestDetailView={id}, OptimizerRunDetail={runId}, EditorView={id}다.
    expectMarkerProps(route.marker, route.markerTestId, route.propsForId(LOWERCASE_UUID), html);
  });

  it.each(ROUTE_CASES)("$name — 지연된 params Promise도 await한 뒤 렌더한다", async (route) => {
    const html = await renderPage(route.page, LOWERCASE_UUID, true);

    expectMarkerProps(route.marker, route.markerTestId, route.propsForId(LOWERCASE_UUID), html);
  });

  it("strategies/[id]/edit — 소문자 v4 UUID는 EditorView로 전달하고 404를 내지 않는다", async () => {
    const html = await renderPage(StrategyEditPage, LOWERCASE_UUID);

    expect(notFound).not.toHaveBeenCalled();
    expectMarkerProps(vi.mocked(EditorView), "strategy-editor-marker", { id: LOWERCASE_UUID }, html);
  });

  it("strategies/[id]/edit — 대문자 UUID도 EditorView로 전달하고 404를 내지 않는다", async () => {
    const html = await renderPage(StrategyEditPage, UPPERCASE_UUID);

    expect(notFound).not.toHaveBeenCalled();
    expectMarkerProps(vi.mocked(EditorView), "strategy-editor-marker", { id: UPPERCASE_UUID }, html);
  });

  it.each([
    ["빈 문자열", ""],
    ["일반 문자열", "abc"],
    ["하이픈 없는 32자 hex", "123e4567e89b42d3a456426614174000"],
    ["하이픈 위치가 틀린 36자", "123e456-7e89b-42d3-a456-426614174000"],
  ] as const)("strategies/[id]/edit — %s면 notFound에서 중단하고 뷰를 렌더하지 않는다", async (_, id) => {
    await expect(renderPage(StrategyEditPage, id)).rejects.toBe(notFoundError);

    expect(notFound).toHaveBeenCalledOnce();
    expect(vi.mocked(EditorView).mock.calls).toHaveLength(0);
  });

  // 두 라우트의 404는 뷰 또는 BE가 소유한다. 여기서는 현재의 무형식검증 동작만 고정한다.
  it.each(UNVALIDATED_ROUTE_CASES)("$name — 임의 문자열 id를 자체 404 없이 뷰로 전달한다", async (route) => {
    const arbitraryId = "not-a-uuid";
    const html = await renderPage(route.page, arbitraryId);

    expect(notFound).not.toHaveBeenCalled();
    expectMarkerProps(route.marker, route.markerTestId, route.propsForId(arbitraryId), html);
  });

  it("세 라우트의 metadata.title은 비어 있지 않고 서로 다르다", () => {
    const titles = [backtestMetadata.title, optimizerMetadata.title, strategyMetadata.title].map((title) =>
      String(title ?? ""),
    );

    expect(titles.every((title) => title.trim().length > 0)).toBe(true);
    expect(new Set(titles)).toHaveLength(3);
  });

  it("backtests/[id] — URL 인코딩 문자가 든 id도 예외 없이 뷰로 전달한다", async () => {
    const encodedId = "a%2Fb";
    const html = await renderPage(BacktestDetailPage, encodedId);

    expectMarkerProps(vi.mocked(BacktestDetailView), "backtest-detail-marker", { id: encodedId }, html);
  });
});
