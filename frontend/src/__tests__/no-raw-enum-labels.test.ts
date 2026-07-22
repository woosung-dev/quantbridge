// C 이식 S4 — 원시 enum 노출 회귀 가드.
//
// 용어 SSOT 이관(labels 모듈 + statusLabelOf)의 회귀를 잡는다. 컴포넌트가
// statusLabelOf / *_LABEL 매핑을 거치지 않고 상태 enum 을 담은 변수(예: {o.state},
// {r.status} — 값은 "queued" / "filled" 같은 원시 문자열)를 JSX 자식으로 그대로
// 인쇄하면 실패시킨다. 이는 no-internal-ids.test.ts 의 재귀 워커 + JSX 문맥 휴리스틱
// 구조를 따른다.
//
// 스코프·필드 이력.
//   S4: 백테스트 `status` + 주문 `state`. /backtests · /orders (_components).
//   S9: /dashboard · /trading (_components) + 두 라우트가 그리는 features 트리.
//   W1(codex#5): optimizer/strategy 용어 SSOT 확장에 맞춰 필드 5종(kind/direction/
//       objective_metric/prior/phase) 추가 + JSX 안 템플릿 리터럴 보간 `${chain.field}`
//       검출 + 스코프에 optimizer/strategy _components 및 features 트리 6종 추가.
//   `side`(주문 방향)와 거래 `direction`(롱/숏)은 삼항(`x === "long" ? …`)으로만 쓰여
//   `{chain}` 단독 패턴에 매치되지 않는다. optimization `direction`(maximize/minimize)만
//   JSX 자식으로 인쇄돼 왔고 그것이 이 가드의 대상이다. Pine 파라미터 식별자·문제 종류
//   discriminator(`p.kind` React key) 같은 비-enum 값은 속성/키 위치라 휴리스틱에서 빠진다.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// 용어 SSOT 로 이관한 상태·enum 계열 필드. 이 필드를 담은 변수는 반드시
// statusLabelOf / *_LABEL 을 거쳐 한국어 라벨로 렌더해야 한다.
const GUARDED_ENUM_FIELDS: readonly string[] = [
  "status",
  "state",
  "kind",
  "direction",
  "objective_metric",
  "prior",
  "phase",
];

// `{ 멤버체인 }` 이 중괄호의 전체 내용인 경우만 잡는다(체인 뒤에 곧바로 `}` 필요).
// 그래서 `{data.status === "x" && ...}` 같은 boolean 식은 매치되지 않고, `?.`(옵셔널
// 체이닝)도 허용한다. 마지막 세그먼트가 가드 필드인지는 아래에서 별도로 판정한다.
const MEMBER_CHAIN_EXPR =
  /\{\s*([A-Za-z_$][\w$]*(?:\s*\??\.\s*[A-Za-z_$][\w$]*)+)\s*\}/g;

// JSX 안 템플릿 리터럴 보간 `${ 멤버체인 }`. 보간 전체가 멤버체인일 때만(예: `${field.kind}`).
// `${LABEL[x.field]}` 처럼 `[` 가 끼면 매치되지 않아, 라벨 매핑 경유는 자동 통과한다.
const TEMPLATE_CHAIN_EXPR =
  /\$\{\s*([A-Za-z_$][\w$]*(?:\s*\??\.\s*[A-Za-z_$][\w$]*)+)\s*\}/g;

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

// JSX 자식 위치의 원시 enum 렌더만 추출한다. 두 형태를 잡는다.
//   ① JSX 식 컨테이너         {chain.field}
//   ② JSX 안 템플릿 리터럴 보간  `${chain.field}`
// 속성(`data-status={b.status}`)·prop(`status={b.status}`)·React key(`key={`${p.kind}`}`)는
// nearest `>`/`<` 휴리스틱으로 걸러낸다.
export function detectRawEnumRenders(rawContent: string): string[] {
  const cleaned = stripComments(rawContent);
  const hits: string[] = [];

  // 화살표 함수 `=>` 의 `>` 는 JSX 태그 닫힘이 아니다. onClick={() => …} 뒤 속성
  // (data-direction={t.direction})을 자식으로 오인하지 않도록 `=>` 의 `>` 는 제외한다.
  const lastRealGt = (s: string): number => {
    for (let i = s.length - 1; i >= 0; i--) {
      if (s[i] === ">" && s[i - 1] !== "=") return i;
    }
    return -1;
  };

  const isJsxChild = (matchStart: number, matchLen: number): boolean => {
    const before = cleaned.slice(Math.max(0, matchStart - 500), matchStart);
    const after = cleaned.slice(
      matchStart + matchLen,
      matchStart + matchLen + 500,
    );
    // JSX text 문맥 = match 앞의 가장 가까운 (화살표 아닌) `>` 가 `<` 보다 뒤 + 뒤에 `<` 존재.
    const gtBeforeIdx = lastRealGt(before);
    const ltBeforeIdx = before.lastIndexOf("<");
    return gtBeforeIdx > ltBeforeIdx && after.indexOf("<") >= 0;
  };

  // ② 템플릿 보간 `${chain.field}` — JSX 자식 문맥일 때만.
  const tpl = new RegExp(TEMPLATE_CHAIN_EXPR.source, TEMPLATE_CHAIN_EXPR.flags);
  let t: RegExpExecArray | null;
  while ((t = tpl.exec(cleaned)) !== null) {
    const chain = t[1];
    if (!chain || !GUARDED_ENUM_FIELDS.includes(lastSegment(chain))) continue;
    if (isJsxChild(t.index, t[0].length)) hits.push(t[0]);
  }

  // ① JSX 식 컨테이너 `{chain.field}`. `${...}` 보간의 내부 `{...}` 는 위에서 처리했으므로 제외.
  const jsx = new RegExp(MEMBER_CHAIN_EXPR.source, MEMBER_CHAIN_EXPR.flags);
  let m: RegExpExecArray | null;
  while ((m = jsx.exec(cleaned)) !== null) {
    const chain = m[1];
    if (!chain || !GUARDED_ENUM_FIELDS.includes(lastSegment(chain))) continue;
    if (m.index > 0 && cleaned[m.index - 1] === "$") continue; // `${...}` 는 템플릿 경로 담당.
    if (isJsxChild(m.index, m[0].length)) hits.push(m[0]);
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
//   W1: optimizer/strategy 라우트 _components + 두 도메인 features 컴포넌트 트리
const NEW_SCOPE_MARKERS: readonly string[] = [
  join("app", "(dashboard)", "optimizer", "_components"),
  join("app", "(dashboard)", "strategies", "_components"),
  join("app", "(dashboard)", "strategies", "new", "_components"),
  join("app", "(dashboard)", "strategies", "[id]", "edit", "_components"),
  join("features", "optimizer", "components"),
  join("features", "strategy", "components"),
];

function getScopedFiles(): string[] {
  const root = resolve(__dirname, "..");
  const dirs = [
    join(root, "app", "(dashboard)", "backtests", "_components"),
    join(root, "app", "(dashboard)", "orders", "_components"),
    join(root, "app", "(dashboard)", "dashboard", "_components"),
    join(root, "app", "(dashboard)", "trading", "_components"),
    join(root, "features", "trading", "components"),
    join(root, "features", "live-sessions", "components"),
    ...NEW_SCOPE_MARKERS.map((m) => join(root, m)),
  ];
  const results: string[] = [];
  for (const d of dirs) walk(d, results);
  return results;
}

describe("S4/S9/W1 — no raw enum rendered in P1 route UI", () => {
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

  // W1 위생 — 신규 6 디렉터리가 실제로 파일을 스캔했는지(0파일 침묵 통과 금지).
  it("W1 확장 스코프 6 디렉터리가 각각 최소 1개 파일을 스캔한다", () => {
    for (const marker of NEW_SCOPE_MARKERS) {
      expect(
        files.some((f) => f.includes(marker)),
        `스코프가 비었다 (0파일): ${marker}`,
      ).toBe(true);
    }
    // 대표 이관 파일 편입 확인.
    expect(files.some((f) => f.endsWith("optimizer-run-list.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("optimizer-run-detail.tsx"))).toBe(true);
    // W3-B: parse-panel.tsx 는 C 이식(screen-08)에서 diagnostics-strip.tsx 로 교체됐다.
    expect(files.some((f) => f.endsWith("diagnostics-strip.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("parse-result-panel.tsx"))).toBe(true);
  });

  // 위생 메타테스트 (falsification) — 검출기가 실제로 동작함을 증명한다.
  it("detector flags a raw {o.state} JSX child", () => {
    expect(detectRawEnumRenders("<td>{o.state}</td>")).toEqual(["{o.state}"]);
    expect(detectRawEnumRenders("<td>{ run?.status }</td>")).toEqual([
      "{ run?.status }",
    ]);
  });

  // W1 신규 필드 — kind/direction/objective_metric/prior/phase 를 JSX 자식으로 인쇄하면 잡는다.
  it("detector flags the W1 enum fields as JSX children", () => {
    expect(detectRawEnumRenders("<td>{data.kind}</td>")).toEqual([
      "{data.kind}",
    ]);
    expect(detectRawEnumRenders("<span>{r.param_space.direction}</span>")).toEqual(
      ["{r.param_space.direction}"],
    );
    expect(
      detectRawEnumRenders("<td>{data.result.objective_metric}</td>"),
    ).toEqual(["{data.result.objective_metric}"]);
    expect(detectRawEnumRenders("<b>{field.prior}</b>")).toEqual([
      "{field.prior}",
    ]);
    expect(detectRawEnumRenders("<td>{it.phase}</td>")).toEqual(["{it.phase}"]);
  });

  // W1 템플릿 보간 — JSX 안 `${chain.field}` 도 잡는다. `[` 매핑 경유는 통과.
  it("detector flags a `${chain.field}` interpolation inside a JSX child template", () => {
    expect(detectRawEnumRenders("<li>{`x ${field.kind} y`}</li>")).toEqual([
      "${field.kind}",
    ]);
    // 라벨 매핑 경유(`[`)는 통과.
    expect(
      detectRawEnumRenders("<li>{`x ${LABEL[field.kind]} y`}</li>"),
    ).toEqual([]);
  });

  it("detector ignores attribute / prop / boolean-expr / key-template usages", () => {
    expect(detectRawEnumRenders(`<tr data-status={b.status}>`)).toEqual([]);
    expect(detectRawEnumRenders(`<Badge status={b.status} />`)).toEqual([]);
    expect(
      detectRawEnumRenders(`<div>{data.status === "running" && <Spinner />}</div>`),
    ).toEqual([]);
    // 비-enum kind 비교식(categorical 값 판별)은 pure-chain 이 아니라 매치 안 됨.
    expect(
      detectRawEnumRenders(`<div>{field.kind === "categorical" && <X />}</div>`),
    ).toEqual([]);
    // React key 안 템플릿 보간(속성 위치)은 JSX 자식이 아니므로 제외.
    expect(detectRawEnumRenders("<li key={`${p.kind}-1`}>x</li>")).toEqual([]);
    // prop 위치 `kind={data.kind}` 도 제외.
    expect(detectRawEnumRenders(`<Oos kind={data.kind} />`)).toEqual([]);
  });

  it("no scoped component renders a raw enum as JSX child or template interpolation", () => {
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
      `원시 enum 이 라벨 모듈을 거치지 않고 렌더됩니다 (statusLabelOf / *_LABEL 사용):\n${violations
        .map((v) => `  ${v.file}: ${v.samples.join(", ")}`)
        .join("\n")}`,
    ).toEqual([]);
  });
});
