// C 이식 S4 — 원시 enum 노출 회귀 가드.
//
// 용어 SSOT 이관(labels 모듈 + statusLabelOf)의 회귀를 잡는다. 컴포넌트가
// statusLabelOf / *_LABEL 매핑을 거치지 않고 상태 enum 을 담은 변수(예: {o.state},
// {r.status} — 값은 "queued" / "filled" 같은 원시 문자열)를 JSX 자식으로 그대로
// 인쇄하면 실패시킨다. 이는 no-internal-ids.test.ts 의 재귀 워커 + JSX 문맥 휴리스틱
// 구조를 따른다.
//
// 스코프 판정. S4 가 이관한 필드는 백테스트 `status` 와 주문 `state` 두 가지다.
// S9 에서 스코프를 /dashboard · /trading 라우트가 렌더하는 컴포넌트 트리까지 넓힌다
// (dashboard/·trading/ _components + 두 라우트가 실제로 그리는 features/trading·
// features/live-sessions 컴포넌트). `side` / `direction`(거래 방향)은 자유문자열이라
// GUARDED_ENUM_FIELDS 밖이므로 여전히 잡지 않는다 — status/state enum 만 대상이다.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// S4 가 용어 SSOT 로 이관한 상태 계열 enum 필드. 이 필드를 담은 변수는
// 반드시 statusLabelOf / *_LABEL 을 거쳐 한국어 라벨로 렌더해야 한다.
const GUARDED_ENUM_FIELDS: readonly string[] = ["status", "state"];

// `{ 멤버체인 }` 이 중괄호의 전체 내용인 경우만 잡는다(체인 뒤에 곧바로 `}` 필요).
// 그래서 `{data.status === "x" && ...}` 같은 boolean 식은 매치되지 않고, `?.`(옵셔널
// 체이닝)도 허용한다. 마지막 세그먼트가 가드 필드인지는 아래에서 별도로 판정한다.
const MEMBER_CHAIN_EXPR =
  /\{\s*([A-Za-z_$][\w$]*(?:\s*\??\.\s*[A-Za-z_$][\w$]*)+)\s*\}/g;

function lastSegment(chain: string): string {
  return (
    chain
      .replace(/\?\./g, ".")
      .split(".")
      .map((s) => s.trim())
      .filter(Boolean)
      .pop() ?? ""
  );
}

// comment(// · /* */ · JSX {/* */} · JSDoc `* line`) 제거 — JSX text/식만 검사.
function stripComments(content: string): string {
  let cleaned = content.replace(/\{?\/\*[\s\S]*?\*\/\}?/g, "");
  cleaned = cleaned
    .split("\n")
    .map((line) => {
      const trimmed = line.trimStart();
      if (trimmed.startsWith("*")) return "";
      const idx = line.indexOf("//");
      if (idx < 0) return line;
      const before = line.slice(0, idx);
      const quoteCount = (before.match(/["'`]/g) || []).length;
      if (quoteCount % 2 === 1) return line;
      return before;
    })
    .join("\n");
  return cleaned;
}

// JSX 자식 위치의 원시 enum 렌더만 추출한다. 속성(`data-status={b.status}`)이나
// prop(`status={b.status}`)은 nearest `>`/`<` 휴리스틱으로 걸러낸다.
export function detectRawEnumRenders(rawContent: string): string[] {
  const cleaned = stripComments(rawContent);
  const hits: string[] = [];
  const re = new RegExp(MEMBER_CHAIN_EXPR.source, MEMBER_CHAIN_EXPR.flags);
  let m: RegExpExecArray | null;
  while ((m = re.exec(cleaned)) !== null) {
    const matched = m[0];
    const chain = m[1];
    if (!chain || !GUARDED_ENUM_FIELDS.includes(lastSegment(chain))) continue;
    const matchStart = m.index;
    const before = cleaned.slice(Math.max(0, matchStart - 500), matchStart);
    const after = cleaned.slice(
      matchStart + matched.length,
      matchStart + matched.length + 500,
    );
    // JSX text 문맥 = match 앞의 가장 가까운 `>` 가 `<` 보다 뒤 + 뒤에 `<` 존재.
    const gtBeforeIdx = before.lastIndexOf(">");
    const ltBeforeIdx = before.lastIndexOf("<");
    const isJsxChild = gtBeforeIdx > ltBeforeIdx && after.indexOf("<") >= 0;
    if (isJsxChild) hits.push(matched);
  }
  return hits;
}

function walk(dir: string, results: string[] = []): string[] {
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    if (entry === "__tests__" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      walk(full, results);
    } else if (
      stat.isFile() &&
      full.endsWith(".tsx") &&
      !full.endsWith(".test.tsx") &&
      !full.endsWith(".spec.tsx")
    ) {
      results.push(full);
    }
  }
  return results;
}

// 가드 스코프 = P1 라우트가 렌더하는 컴포넌트 트리.
//   S4: /backtests · /orders (_components)
//   S9: /dashboard · /trading (_components) + 두 라우트가 그리는 features 컴포넌트 트리
//       (features/trading = OrdersPanel 등, features/live-sessions = LiveSession* 등).
function getScopedFiles(): string[] {
  const root = resolve(__dirname, "..");
  const dirs = [
    join(root, "app", "(dashboard)", "backtests", "_components"),
    join(root, "app", "(dashboard)", "orders", "_components"),
    join(root, "app", "(dashboard)", "dashboard", "_components"),
    join(root, "app", "(dashboard)", "trading", "_components"),
    join(root, "features", "trading", "components"),
    join(root, "features", "live-sessions", "components"),
  ];
  const results: string[] = [];
  for (const d of dirs) walk(d, results);
  return results;
}

describe("S4/S9 — no raw status/state enum rendered in P1 route UI", () => {
  const files = getScopedFiles();

  it("scope inventory is non-empty and includes the migrated files", () => {
    expect(files.length).toBeGreaterThan(0);
    // S4 스코프 (backtests · orders)
    expect(files.some((f) => f.endsWith("status-badge.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("backtest-list.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("orders-blotter.tsx"))).toBe(true);
    // S9 확장 스코프 (dashboard · trading · features 트리)
    expect(files.some((f) => f.endsWith("dashboard-cockpit.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("trading-cockpit.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("orders-panel.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("live-session-detail.tsx"))).toBe(true);
  });

  // 위생 메타테스트 (falsification) — 검출기가 실제로 동작함을 증명한다.
  it("detector flags a raw {o.state} JSX child", () => {
    expect(detectRawEnumRenders("<td>{o.state}</td>")).toEqual(["{o.state}"]);
    expect(detectRawEnumRenders("<td>{ run?.status }</td>")).toEqual([
      "{ run?.status }",
    ]);
  });

  it("detector ignores attribute / prop / boolean-expr usages", () => {
    expect(detectRawEnumRenders(`<tr data-status={b.status}>`)).toEqual([]);
    expect(detectRawEnumRenders(`<Badge status={b.status} />`)).toEqual([]);
    expect(
      detectRawEnumRenders(`<div>{data.status === "running" && <Spinner />}</div>`),
    ).toEqual([]);
  });

  it("no scoped component renders a raw status/state enum as JSX child", () => {
    const violations: { file: string; samples: string[] }[] = [];
    for (const file of files) {
      const raw = readFileSync(file, "utf-8");
      const hits = detectRawEnumRenders(raw);
      if (hits.length > 0) {
        violations.push({
          file: file.replace(/.*\/quant-bridge\//, ""),
          samples: [...new Set(hits)].slice(0, 3),
        });
      }
    }
    expect(
      violations,
      `원시 status/state enum 이 라벨 모듈을 거치지 않고 렌더됩니다 (statusLabelOf / *_LABEL 사용):\n${violations
        .map((v) => `  ${v.file}: ${v.samples.join(", ")}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});
