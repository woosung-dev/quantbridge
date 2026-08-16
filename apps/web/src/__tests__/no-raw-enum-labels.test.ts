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

const UPPERCASE_ENUM_LITERAL = /^[A-Z][A-Z0-9_]{2,}$/;
// 항목마다 enum 이 아닌 도메인 고정 식별자라는 사유를 남긴다.
const NON_ENUM_UPPERCASE_ALLOWLIST: readonly string[] = [
  "USDT", // 거래 쌍의 인용 자산 심볼이다.
  "BTC", // 거래 자산 심볼이다.
  "ETH", // 거래 자산 심볼이다.
  "USD", // 법정화폐 통화 코드다.
  "UTC", // 시간대 약어다.
  "KST", // 시간대 약어다.
  "PNL", // 손익 지표의 관용 약어다.
  "ROI", // 수익률 지표의 관용 약어다.
];
const UPPERCASE_LITERAL_SCOPE: readonly string[] = [
  join("features", "live-sessions"),
];

// BL-572 이전 실제 위반: f631f1c7^:live-session-table.tsx
const BL572_HISTORICAL_SNIPPET =
  '<span className={s.is_active ? "chip accent" : "chip"}>{s.is_active ? "ACTIVE" : "PAUSED"}</span>';

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

// 화살표 함수 `=>` 의 `>` 는 JSX 태그 닫힘이 아니다. onClick={() => …} 뒤 속성
// (data-direction={t.direction})을 자식으로 오인하지 않도록 `=>` 의 `>` 는 제외한다.
function lastRealGt(content: string): number {
  for (let i = content.length - 1; i >= 0; i--) {
    if (content[i] === ">" && content[i - 1] !== "=") return i;
  }
  return -1;
}

// JSX 식 컨테이너 안이면서, 속성이나 prop 안은 아닌지를 두 검출기가 같은 방식으로 판정한다.
function isJsxChild(
  content: string,
  matchStart: number,
  matchLen: number,
): boolean {
  const before = content.slice(Math.max(0, matchStart - 500), matchStart);
  const after = content.slice(matchStart + matchLen, matchStart + matchLen + 500);
  // JSX text 문맥 = match 앞의 가장 가까운 (화살표 아닌) `>` 가 `<` 보다 뒤 + 뒤에 `<` 존재.
  const gtBeforeIdx = lastRealGt(before);
  const ltBeforeIdx = before.lastIndexOf("<");
  return gtBeforeIdx > ltBeforeIdx && after.indexOf("<") >= 0;
}

// JSX 자식 위치의 원시 enum 렌더만 추출한다. 두 형태를 잡는다.
//   ① JSX 식 컨테이너         {chain.field}
//   ② JSX 안 템플릿 리터럴 보간  `${chain.field}`
// 속성(`data-status={b.status}`)·prop(`status={b.status}`)·React key(`key={`${p.kind}`}`)는
// nearest `>`/`<` 휴리스틱으로 걸러낸다.
export function detectRawEnumRenders(rawContent: string): string[] {
  const cleaned = stripComments(rawContent);
  const hits: string[] = [];

  // ② 템플릿 보간 `${chain.field}` — JSX 자식 문맥일 때만.
  const tpl = new RegExp(TEMPLATE_CHAIN_EXPR.source, TEMPLATE_CHAIN_EXPR.flags);
  let t: RegExpExecArray | null;
  while ((t = tpl.exec(cleaned)) !== null) {
    const chain = t[1];
    if (!chain || !GUARDED_ENUM_FIELDS.includes(lastSegment(chain))) continue;
    if (isJsxChild(cleaned, t.index, t[0].length)) hits.push(t[0]);
  }

  // ① JSX 식 컨테이너 `{chain.field}`. `${...}` 보간의 내부 `{...}` 는 위에서 처리했으므로 제외.
  const jsx = new RegExp(MEMBER_CHAIN_EXPR.source, MEMBER_CHAIN_EXPR.flags);
  let m: RegExpExecArray | null;
  while ((m = jsx.exec(cleaned)) !== null) {
    const chain = m[1];
    if (!chain || !GUARDED_ENUM_FIELDS.includes(lastSegment(chain))) continue;
    if (m.index > 0 && cleaned[m.index - 1] === "$") continue; // `${...}` 는 템플릿 경로 담당.
    if (isJsxChild(cleaned, m.index, m[0].length)) hits.push(m[0]);
  }

  return hits;
}

export function detectRawUppercaseEnumLiterals(rawContent: string): string[] {
  const cleaned = stripComments(rawContent);
  const hits: string[] = [];
  const quotedLiteral = /(["'])([A-Z][A-Z0-9_]{2,})\1/g;
  let match: RegExpExecArray | null;

  while ((match = quotedLiteral.exec(cleaned)) !== null) {
    const literal = match[2];
    if (
      !literal ||
      !UPPERCASE_ENUM_LITERAL.test(literal) ||
      NON_ENUM_UPPERCASE_ALLOWLIST.includes(literal) ||
      !isJsxChild(cleaned, match.index, match[0].length)
    ) {
      continue;
    }
    const afterLiteral = cleaned.slice(match.index + match[0].length);
    if (/^\s*\)?\s*\.toUpperCase\s*\(/.test(afterLiteral)) continue;
    hits.push(match[0]);
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
//   S4: /backtests · /orders   S9: /dashboard · /trading   W1: optimizer · strategy
//
// ★★2026-08-16 ADR-035 — 이 목록은 종전에 `app/**/_components/` 를 가리키고 있었다.
//   그 디렉터리들이 `features/*/components/` 로 옮겨졌고, `walk()` 는 `existsSync` 가 false 면
//   **조용히 건너뛴다**(:176). 즉 목록을 안 고쳤으면 스코프가 통째로 비고 **테스트는 초록**이었다.
//   ★그래서 이 파일을 고칠 때는 `apps/web/scripts/canon-scope-census.mjs` 로 스캔 파일 수를
//     이동 전후 비교해라. 줄어들면 배선이 죽은 것이다 (2026-08-16 실측: 112 → 246).
// ★아래 목록에 없는 디렉터리는 감사받지 않는다. feature 를 새로 만들면 여기에 줄을 추가해라.
const SCOPE_MARKERS: readonly string[] = [
  join("features", "backtest", "components"), // 구 app/(dashboard)/backtests/_components
  join("features", "trading", "components"), // 구 .../trading/_components + orders/_components
  join("features", "dashboard", "components"), // 구 .../dashboard/_components
  join("features", "optimizer", "components"), // 구 .../optimizer/_components
  join("features", "strategy", "components"), // 구 .../strategies{,/new,/[id]/edit}/_components
  join("features", "live-sessions", "components"),
];

function getScopedFiles(): string[] {
  const root = resolve(__dirname, "..");
  const dirs = SCOPE_MARKERS.map((m) => join(root, m));
  // ★목록의 디렉터리가 실제로 있어야 한다 — `walk()` 의 침묵 건너뛰기가 스코프를 비우는 것을 막는다.
  const gone = dirs.filter((d) => !existsSync(d));
  if (gone.length > 0) {
    throw new Error(
      `가드 스코프 디렉터리가 사라졌다: ${gone.join(", ")}\n` +
        "옮겼다면 SCOPE_MARKERS 를 함께 고쳐라. 안 고치면 이 테스트는 빈 입력으로 초록이 된다.",
    );
  }
  const results: string[] = [];
  for (const d of dirs) walk(d, results);
  return results;
}

function getUppercaseLiteralScopedFiles(): string[] {
  const root = resolve(__dirname, "..");
  const results: string[] = [];
  for (const marker of UPPERCASE_LITERAL_SCOPE) {
    walk(join(root, marker), results);
  }
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

  // 위생 — 스코프 6 디렉터리가 실제로 파일을 스캔했는지(0파일 침묵 통과 금지).
  it("스코프 6 디렉터리가 각각 최소 1개 파일을 스캔한다", () => {
    for (const marker of SCOPE_MARKERS) {
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

describe("BL-577 — no raw uppercase enum literal in live sessions", () => {
  const files = getUppercaseLiteralScopedFiles();

  it("scope inventory is non-empty and includes live-session-table.tsx", () => {
    expect(files.length).toBeGreaterThan(0);
    expect(files.some((file) => file.endsWith("live-session-table.tsx"))).toBe(true);
  });

  it("detector flags the BL-572 historical literal and direct JSX child", () => {
    expect(
      detectRawUppercaseEnumLiterals(BL572_HISTORICAL_SNIPPET).length,
    ).toBeGreaterThan(0);
    expect(detectRawUppercaseEnumLiterals('<span>{"FILLED"}</span>')).toEqual([
      '"FILLED"',
    ]);
  });

  it("detector ignores non-enum JSX positions and toUpperCase output", () => {
    expect(
      detectRawUppercaseEnumLiterals(
        '<span>{(mode ?? "UNKNOWN").toUpperCase()}</span>',
      ),
    ).toEqual([]);
    expect(detectRawUppercaseEnumLiterals("<th>MDD</th>")).toEqual([]);
    expect(detectRawUppercaseEnumLiterals('<Badge label="ACTIVE" />')).toEqual([]);
    expect(
      detectRawUppercaseEnumLiterals(
        "<td>{LIVE_SESSION_STATUS_LABEL[k].label}</td>",
      ),
    ).toEqual([]);
    expect(
      detectRawUppercaseEnumLiterals('<td>{s.symbol === "BTC/USDT" && <X/>}</td>'),
    ).toEqual([]);
  });

  it("detector ignores every allowed uppercase non-enum literal", () => {
    for (const literal of NON_ENUM_UPPERCASE_ALLOWLIST) {
      expect(detectRawUppercaseEnumLiterals(`<span>{"${literal}"}</span>`)).toEqual([]);
    }
  });

  it("features/live-sessions 에 원시 대문자 enum 리터럴이 없다", () => {
    const violations: { file: string; samples: string[] }[] = [];
    for (const file of files) {
      const hits = detectRawUppercaseEnumLiterals(readFileSync(file, "utf-8"));
      if (hits.length > 0) {
        violations.push({
          file: file.replace(/.*\/quant-bridge\//, ""),
          samples: [...new Set(hits)].slice(0, 3),
        });
      }
    }

    // ★검출기 생존 확인 — 이게 없으면 검출기를 무력화해도 이 테스트가 green 이다.
    //   ★"하나라도 잡히나" 로는 부족하다 (2026-08-02 codex MINOR#4): 검출기를
    //   `ACTIVE`·`FILLED` 만 통과시키도록 좁혀도 그 단언은 통과하고, 현 스코프 위반이
    //   0건이라 스캔도 green 이라 `PAUSED` 류가 조용히 사라진다. 그래서 **서로 다른
    //   리터럴 집합**이 전부 잡히는지를 단언한다.
    expect(detectRawUppercaseEnumLiterals(BL572_HISTORICAL_SNIPPET)).toEqual(
      expect.arrayContaining(['"ACTIVE"', '"PAUSED"']),
    );
    for (const canary of ["PAUSED", "PENDING", "CANCELLED", "REJECTED"]) {
      expect(
        detectRawUppercaseEnumLiterals(`<span>{"${canary}"}</span>`),
      ).toEqual([`"${canary}"`]);
    }
    expect(violations).toEqual([]);
  });
});
