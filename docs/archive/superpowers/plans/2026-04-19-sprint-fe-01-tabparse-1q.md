# Sprint FE-01: TabParse 1질문 UX (대화형 파싱 해설 모달)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TabParse 탭의 정적 4-섹션 UX를, 감지 함수 하나씩 자연어로 해설하고 에러/경고에 조치 제안까지 붙인 대화형 shadcn Dialog로 전환. 마지막 1-질문 ("저장/돌아가기")으로 dogfood 마찰을 제거.

**Architecture:** TabParse 탭 컨텐츠는 콤팩트 요약 카드 + "해설 시작" 버튼으로 축소. 모달(`ParseDialog`)이 단계 머신(step machine)으로 에러 → 경고 → 감지 함수 → 최종 confirm 순서로 walk-through. 자연어 해설은 `pine-lexicon.ts` 하드코딩 테이블 (LLM 호출 금지). Dialog 컴포넌트·sonner·React Query는 기존 자산 재사용, BE touch 0.

**Tech Stack:** Next.js App Router, React 19, TypeScript strict, shadcn/ui Dialog (Base UI 기반), lucide-react icons, Tailwind v4, sonner toast, vitest + @testing-library/react.

---

## Context — 왜 필요한가

- **BE 상태 (완료):** Sprint 7b에서 `ParsePreviewResponse.functions_used`까지 확장 완료. 에러(`{code, message, line}`) · 경고(string[]) · 감지 함수(string[]) · status · pine_version 모두 노출 중. Backend 수정 불필요.
- **FE 현 상태 (정적):** `tab-parse.tsx` (215줄) — 4섹션 Card 뷰. 내용 자체는 정확하지만 **"사용자가 읽고 이해했다" 확인 흐름이 없다**. 엔지니어는 OK지만, 처음 보는 사용자 입장에서 `ta.crossover` · `strategy.entry` 같은 식별자가 무엇을 뜻하는지 모른다.
- **dogfood 관점 마찰:** 저장 버튼까지 가는 동안 "이 스크립트를 신뢰해도 되는가"를 확인할 기회가 없다. 이번 세션은 `Trust ≥ Scale > Monetize` 기조에 맞춰 **Trust 레이어 한 겹**을 추가한다.

## Scope Check

이 플랜은 단일 서브시스템(frontend TabParse UX)만 다룸. BE/배포/스키마 변경 없음. 쪼갤 필요 없다.

---

## File Structure

```
frontend/src/features/strategy/
├── pine-lexicon.ts                            [NEW] 하드코딩 해설/조치 테이블 + lookup helper
└── __tests__/
    └── pine-lexicon.test.ts                   [NEW] lexicon lookup 테스트

frontend/src/app/(dashboard)/strategies/[id]/edit/_components/
├── parse-dialog.tsx                           [NEW] 대화형 Dialog 컴포넌트 + 단계 머신
├── parse-dialog-steps.ts                      [NEW] buildParseSteps 순수 함수
├── tab-parse.tsx                              [MODIFY] 요약 카드 + ParseDialog 트리거
└── __tests__/
    ├── parse-dialog-steps.test.ts             [NEW] 단계 머신 단위 테스트
    └── parse-dialog.test.tsx                  [NEW] 렌더/네비게이션 통합 테스트
```

**왜 이렇게 쪼갰는가:**
- `pine-lexicon.ts` — 기능 도메인(Pine 식별자 → 자연어)이라 `features/strategy/`에 귀속. 다른 곳에서도 재사용 가능 (예: backtest 결과 페이지).
- `parse-dialog-steps.ts` — 순수 함수는 컴포넌트에서 분리해 단위 테스트. React 없이 테스트 가능해야 함.
- `parse-dialog.tsx` — React 컴포넌트 + 상태. 단일 책임.
- `tab-parse.tsx` — 수정 최소화. 요약 + 트리거 버튼만 추가.

---

## Natural-Language Lexicon — 설계

**14개 stdlib 함수 + 구조 함수 ~10개 + 구조 객체 = 약 24개 키.** 하드코딩 가능한 규모.

```typescript
// pine-lexicon.ts 구조 예시
export type PineFunctionDescription = {
  summary: string;      // 한 줄 요약 (한국어)
  purpose: string;      // 무엇을 위한 함수인가
  example?: string;     // 전형적 호출
};

// 14 stdlib + 6 strategy.* + 5 input/plot/alert 등 ≈ 25개 엔트리
export const PINE_FUNCTION_LEXICON: Record<string, PineFunctionDescription>;

// 4개 error code + message 패턴 fallback
export const PINE_ERROR_ADVICE: Record<string, { what: string; action: string }>;

// 경고는 현재 1종 (duplicate strategy.exit) — 메시지 패턴 매칭
export function adviseWarning(message: string): { what: string; action: string };

// 알려지지 않은 식별자 fallback
export function describeFunction(name: string): PineFunctionDescription;
```

## Error / Warning Advice — 알려진 카테고리

| code / pattern | What (사용자 관점) | Action |
|---|---|---|
| `function` | 지원하지 않는 함수 호출 | 해당 함수명을 Pine v5 지원 목록으로 교체하거나, 간이 구현으로 대체 |
| `syntax` | 구문 오류 (괄호/연산자) | 해당 라인의 괄호 균형·연산자 위치 확인 |
| `type` | 타입 불일치 (int↔float, series↔simple) | 인자 타입 맞추거나 `float()` 캐스트 추가 |
| `v4_migration` | v4 → v5 네이밍 변경 (예: `rsi` → `ta.rsi`) | `ta.` 또는 `math.` prefix 추가 |
| `PineLexError` | 토크나이저가 문자 시퀀스를 해석 못함 | 해당 라인의 특수 문자/인용부호 점검 |
| `PineParseError` | 파서가 문법 구조를 못 맞춤 | 이전 라인의 `=>` · `:=` 누락 점검 |
| 기타 | 알 수 없는 오류 | 라인 번호 확인 후 수동 점검 |
| `duplicate strategy.exit` (경고 메시지 매칭) | 같은 전략에 exit 콜이 여러 번 | 마지막 호출만 반영됨. stop/limit 재정의 의도였다면 의도 확인 |

---

## Step Machine — 설계

**Step 타입 (discriminated union):**

```typescript
type ParseStep =
  | { kind: "intro"; summary: { errorCount: number; warningCount: number; functionCount: number } }
  | { kind: "error"; index: number; total: number; error: ParseError; advice: ErrorAdvice }
  | { kind: "warning"; index: number; total: number; message: string; advice: WarningAdvice }
  | { kind: "function"; index: number; total: number; name: string; description: PineFunctionDescription }
  | { kind: "final"; summary: ...; canSave: boolean };
```

**순서:** intro → [error…] → [warning…] → [function…] → final.

**canSave 규칙:** `status === "error"` 일 땐 final에서 저장 버튼을 비활성화하고 "에러를 해결하고 다시 시도해주세요" 힌트 노출.

**엣지 케이스:**
- 에러 0 + 경고 0 + 함수 0 → intro → final (2 steps). 깔끔한 exit path.
- 함수 14개 (최대 stdlib full-house) → intro + 14 + final = 16 steps. 허용.
- 함수 30+ (user defined 많을 때) → "총 N개 중 14개만 해설, 나머지는 요약" (cap 14) + "전체 목록 보기" 접기 링크 검토 (design-review에서 확정).

**네비게이션:**
- 다음(Next) · 이전(Prev) · 건너뛰기(스텝 그룹 단위) · 닫기(X).
- 키보드: `→` Next, `←` Prev, `Esc` 닫기 (Dialog 기본).

---

## Task N: [Pine Lexicon 테이블 + lookup 헬퍼]

**Files:**
- Create: `frontend/src/features/strategy/pine-lexicon.ts`
- Test: `frontend/src/features/strategy/__tests__/pine-lexicon.test.ts`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/features/strategy/__tests__/pine-lexicon.test.ts
import { describe, expect, it } from "vitest";
import {
  describeFunction,
  adviseError,
  adviseWarning,
  PINE_FUNCTION_LEXICON,
} from "@/features/strategy/pine-lexicon";

describe("PINE_FUNCTION_LEXICON", () => {
  it("covers 14 stdlib functions", () => {
    const stdlib = [
      "ta.sma", "ta.ema", "ta.rma", "ta.rsi", "ta.atr", "ta.stdev",
      "ta.crossover", "ta.crossunder", "ta.cross",
      "ta.highest", "ta.lowest", "ta.change",
      "nz", "na",
    ];
    for (const name of stdlib) {
      expect(PINE_FUNCTION_LEXICON[name], `missing: ${name}`).toBeDefined();
    }
  });

  it("describes known function with purpose + example", () => {
    const d = describeFunction("ta.rsi");
    expect(d.summary).toMatch(/RSI|상대.*강도/);
    expect(d.purpose.length).toBeGreaterThan(10);
    expect(d.example).toContain("ta.rsi");
  });

  it("returns fallback for unknown function", () => {
    const d = describeFunction("some.unknown.fn");
    expect(d.summary).toContain("some.unknown.fn");
    expect(d.purpose).toBeTruthy();
  });
});

describe("adviseError", () => {
  it("maps known code v4_migration to actionable hint", () => {
    const a = adviseError({ code: "v4_migration", message: "rsi() is v4 syntax", line: 12 });
    expect(a.what).toBeTruthy();
    expect(a.action).toMatch(/ta\.|prefix/i);
  });

  it("falls back for unknown code", () => {
    const a = adviseError({ code: "mystery", message: "???", line: null });
    expect(a.what).toBeTruthy();
    expect(a.action).toBeTruthy();
  });
});

describe("adviseWarning", () => {
  it("detects duplicate strategy.exit pattern", () => {
    const a = adviseWarning("duplicate strategy.exit calls at lines [10, 15]");
    expect(a.what).toMatch(/exit/);
    expect(a.action).toMatch(/마지막/);
  });

  it("generic fallback for unknown warning", () => {
    const a = adviseWarning("some unknown warning");
    expect(a.what).toBeTruthy();
    expect(a.action).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- pine-lexicon`
Expected: FAIL — module not found.

- [ ] **Step 3: Create pine-lexicon.ts with 14 stdlib + 6 strategy.* + 3 input/plot/alert entries**

```typescript
// frontend/src/features/strategy/pine-lexicon.ts
// 하드코딩 Pine 식별자 해설 테이블. LLM 호출 없음, 오프라인 결정적.

import type { ParseError } from "@/features/strategy/schemas";

export type PineFunctionDescription = {
  summary: string;
  purpose: string;
  example?: string;
};

export type ErrorAdvice = { what: string; action: string };
export type WarningAdvice = { what: string; action: string };

export const PINE_FUNCTION_LEXICON: Record<string, PineFunctionDescription> = {
  // 14 stdlib
  "ta.sma": { summary: "단순 이동평균(SMA)", purpose: "최근 N봉 종가의 산술 평균을 추세선으로 사용", example: "ta.sma(close, 20)" },
  "ta.ema": { summary: "지수 이동평균(EMA)", purpose: "최근 가격에 더 큰 가중치를 두는 추세선", example: "ta.ema(close, 12)" },
  "ta.rma": { summary: "Wilder 이동평균(RMA)", purpose: "RSI/ATR 계산에 쓰이는 smoothed 평균", example: "ta.rma(source, 14)" },
  "ta.rsi": { summary: "상대강도지수(RSI)", purpose: "가격 모멘텀을 0-100 범위로 측정해 과매수/과매도 판별", example: "ta.rsi(close, 14)" },
  "ta.atr": { summary: "평균 진폭(ATR)", purpose: "최근 변동성을 측정해 손절 폭·포지션 사이징에 활용", example: "ta.atr(14)" },
  "ta.stdev": { summary: "표준편차", purpose: "가격 분산의 통계적 측정 (볼린저밴드 등에 사용)", example: "ta.stdev(close, 20)" },
  "ta.crossover": { summary: "상향 크로스", purpose: "이전 봉에서 아래, 현재 봉에서 위에 있는 순간을 true로", example: "ta.crossover(fast, slow)" },
  "ta.crossunder": { summary: "하향 크로스", purpose: "이전 봉에서 위, 현재 봉에서 아래에 있는 순간을 true로", example: "ta.crossunder(fast, slow)" },
  "ta.cross": { summary: "양방향 크로스", purpose: "방향 무관 교차 순간 true", example: "ta.cross(a, b)" },
  "ta.highest": { summary: "최근 N봉 최고값", purpose: "롤링 최고가 계산 (돌파 전략에 사용)", example: "ta.highest(high, 20)" },
  "ta.lowest": { summary: "최근 N봉 최저값", purpose: "롤링 최저가 계산", example: "ta.lowest(low, 20)" },
  "ta.change": { summary: "차이값", purpose: "현재값 - N봉 전 값", example: "ta.change(close, 1)" },
  "nz": { summary: "NaN 대체", purpose: "NaN을 0(또는 지정값)으로 변환", example: "nz(value, 0)" },
  "na": { summary: "NaN 체크", purpose: "값이 NaN인지 검사", example: "na(value)" },
  // 6 strategy.*
  "strategy": { summary: "전략 선언", purpose: "스크립트를 전략 모드로 정의하고 기본 옵션 설정", example: 'strategy("name", overlay=true)' },
  "strategy.entry": { summary: "진입 주문", purpose: "롱/숏 포지션 진입을 예약 (조건 충족 시 다음 봉에서 체결)", example: 'strategy.entry("long", strategy.long)' },
  "strategy.exit": { summary: "청산 주문", purpose: "stop/limit/trail 중 하나로 포지션 청산 조건 예약", example: 'strategy.exit("tp", "long", profit=100)' },
  "strategy.close": { summary: "즉시 청산", purpose: "지정된 엔트리 ID를 시장가로 즉시 닫음", example: 'strategy.close("long")' },
  "strategy.long": { summary: "롱 방향 상수", purpose: "strategy.entry의 direction 인자로 사용", example: "strategy.long" },
  "strategy.short": { summary: "숏 방향 상수", purpose: "strategy.entry의 direction 인자로 사용", example: "strategy.short" },
  // 3 UI/alert
  "input": { summary: "사용자 입력", purpose: "차트에서 조정 가능한 파라미터 정의", example: "input(14, 'length')" },
  "plot": { summary: "선 그리기", purpose: "차트에 값을 시각화", example: "plot(ema20, color=color.blue)" },
  "alert": { summary: "알림", purpose: "조건 충족 시 TradingView 알림 발생", example: 'alert("cross", alert.freq_once_per_bar)' },
};

const ERROR_ADVICE_TABLE: Record<string, ErrorAdvice> = {
  function: {
    what: "지원하지 않는 함수가 호출되었습니다.",
    action: "Pine v5 지원 함수 목록으로 교체하거나, 간이 구현으로 대체해보세요.",
  },
  syntax: {
    what: "구문 오류가 발견되었습니다.",
    action: "해당 라인의 괄호 균형과 연산자 위치를 확인하세요.",
  },
  type: {
    what: "타입이 일치하지 않습니다 (예: int ↔ float, series ↔ simple).",
    action: "인자의 타입을 맞추거나 `float()` 같은 명시적 캐스트를 추가하세요.",
  },
  v4_migration: {
    what: "v4 문법을 v5가 지원하지 않습니다.",
    action: "함수 앞에 `ta.` 또는 `math.` prefix를 붙여보세요. (예: `rsi` → `ta.rsi`)",
  },
  PineLexError: {
    what: "토크나이저가 문자 시퀀스를 해석하지 못했습니다.",
    action: "해당 라인의 특수 문자나 인용부호를 확인하세요.",
  },
  PineParseError: {
    what: "파서가 문법 구조를 인식하지 못했습니다.",
    action: "이전 라인의 `=>`, `:=` 같은 키워드 누락 여부를 점검하세요.",
  },
  PineRuntimeError: {
    what: "실행 중 오류가 발생했습니다.",
    action: "변수 정의 순서와 `na` 처리를 확인하세요.",
  },
  PineUnsupportedError: {
    what: "이 버전에서 지원하지 않는 기능입니다.",
    action: "해당 함수/객체를 지원되는 대체 구현으로 교체하세요.",
  },
};

export function describeFunction(name: string): PineFunctionDescription {
  const hit = PINE_FUNCTION_LEXICON[name];
  if (hit) return hit;
  return {
    summary: `${name}`,
    purpose: "해설이 등록되지 않은 식별자입니다. Pine 공식 문서를 확인하세요.",
  };
}

export function adviseError(error: ParseError): ErrorAdvice {
  return (
    ERROR_ADVICE_TABLE[error.code] ?? {
      what: "알 수 없는 오류가 발생했습니다.",
      action: error.line != null
        ? `라인 ${error.line} 주변을 수동으로 점검해주세요.`
        : "에러 메시지 내용을 기반으로 수동 점검이 필요합니다.",
    }
  );
}

export function adviseWarning(message: string): WarningAdvice {
  if (message.includes("duplicate strategy.exit")) {
    return {
      what: "같은 전략에 strategy.exit 콜이 여러 번 선언되어 있습니다.",
      action: "마지막 호출만 반영됩니다. stop/limit을 중첩 설정하려 했다면 하나의 strategy.exit 호출로 합치세요.",
    };
  }
  return {
    what: "주의가 필요한 패턴이 감지되었습니다.",
    action: "메시지 내용을 확인하고 의도된 동작인지 점검하세요.",
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- pine-lexicon`
Expected: PASS — all 7 test cases green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/strategy/pine-lexicon.ts frontend/src/features/strategy/__tests__/pine-lexicon.test.ts
git commit -m "feat(fe-01): add Pine lexicon with 23 function descriptions + error/warning advice"
```

---

## Task N+1: [Step Machine 순수 함수]

**Files:**
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog-steps.ts`
- Test: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/parse-dialog-steps.test.ts`

- [ ] **Step 1: Write the failing tests**

```typescript
// parse-dialog-steps.test.ts
import { describe, expect, it } from "vitest";
import { buildParseSteps } from "../parse-dialog-steps";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const emptyResponse: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 0,
  exit_count: 0,
  functions_used: [],
};

describe("buildParseSteps", () => {
  it("returns intro + final when nothing to show", () => {
    const steps = buildParseSteps(emptyResponse);
    expect(steps).toHaveLength(2);
    expect(steps[0].kind).toBe("intro");
    expect(steps[1].kind).toBe("final");
  });

  it("orders steps error -> warning -> function", () => {
    const steps = buildParseSteps({
      ...emptyResponse,
      status: "error",
      errors: [{ code: "syntax", message: "bad", line: 12 }],
      warnings: ["duplicate strategy.exit calls at lines [5, 9]"],
      functions_used: ["ta.rsi"],
    });
    expect(steps.map((s) => s.kind)).toEqual([
      "intro", "error", "warning", "function", "final",
    ]);
  });

  it("caps function steps at 14 and flags overflow", () => {
    const many = Array.from({ length: 20 }, (_, i) => `fn.${i}`);
    const steps = buildParseSteps({ ...emptyResponse, functions_used: many });
    const functionSteps = steps.filter((s) => s.kind === "function");
    expect(functionSteps).toHaveLength(14);
    const final = steps.at(-1);
    expect(final?.kind).toBe("final");
    if (final?.kind === "final") {
      expect(final.hiddenFunctionCount).toBe(6);
    }
  });

  it("prioritizes known stdlib functions before unknown ones under the cap", () => {
    // 15 unknown + 2 known → cap=14 so user-defined 11개만 + 2 known 들어가야 함
    const unknowns = Array.from({ length: 15 }, (_, i) => `my.fn_${i}`);
    const knowns = ["ta.rsi", "strategy.entry"];
    const steps = buildParseSteps({
      ...emptyResponse,
      functions_used: [...unknowns, ...knowns],
    });
    const functionStepNames = steps
      .filter((s): s is Extract<typeof s, { kind: "function" }> => s.kind === "function")
      .map((s) => s.name);
    expect(functionStepNames.slice(0, 2)).toEqual(["ta.rsi", "strategy.entry"]);
    expect(functionStepNames).toHaveLength(14);
  });

  it("final.canSave is false when status is error", () => {
    const steps = buildParseSteps({ ...emptyResponse, status: "error" });
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.canSave).toBe(false);
  });

  it("final.canSave is true when status is ok", () => {
    const steps = buildParseSteps(emptyResponse);
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.canSave).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- parse-dialog-steps`
Expected: FAIL — module not found.

- [ ] **Step 3: Create parse-dialog-steps.ts**

```typescript
// frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog-steps.ts
import type { ParseError, ParsePreviewResponse } from "@/features/strategy/schemas";
import {
  adviseError,
  adviseWarning,
  describeFunction,
  PINE_FUNCTION_LEXICON,
  type ErrorAdvice,
  type PineFunctionDescription,
  type WarningAdvice,
} from "@/features/strategy/pine-lexicon";

const FUNCTION_CAP = 14;

// stdlib / 구조 함수를 먼저, 알려지지 않은(user-defined) 함수를 뒤로 정렬.
// cap 적용 시 알려진 식별자가 우선 노출된다.
function prioritizeFunctions(fns: readonly string[]): string[] {
  const known: string[] = [];
  const unknown: string[] = [];
  for (const fn of fns) {
    if (fn in PINE_FUNCTION_LEXICON) known.push(fn);
    else unknown.push(fn);
  }
  return [...known, ...unknown];
}

export type StepSummary = {
  errorCount: number;
  warningCount: number;
  functionCount: number;
  pineVersion: "v4" | "v5";
};

export type ParseStep =
  | { kind: "intro"; summary: StepSummary }
  | { kind: "error"; index: number; total: number; error: ParseError; advice: ErrorAdvice }
  | { kind: "warning"; index: number; total: number; message: string; advice: WarningAdvice }
  | { kind: "function"; index: number; total: number; name: string; description: PineFunctionDescription }
  | { kind: "final"; summary: StepSummary; canSave: boolean; hiddenFunctionCount: number };

export function buildParseSteps(result: ParsePreviewResponse): ParseStep[] {
  const summary: StepSummary = {
    errorCount: result.errors.length,
    warningCount: result.warnings.length,
    functionCount: result.functions_used.length,
    pineVersion: result.pine_version,
  };

  const prioritized = prioritizeFunctions(result.functions_used);
  const visibleFunctions = prioritized.slice(0, FUNCTION_CAP);
  const hiddenFunctionCount = Math.max(0, prioritized.length - FUNCTION_CAP);

  const errorSteps: ParseStep[] = result.errors.map((error, i) => ({
    kind: "error",
    index: i,
    total: result.errors.length,
    error,
    advice: adviseError(error),
  }));

  const warningSteps: ParseStep[] = result.warnings.map((message, i) => ({
    kind: "warning",
    index: i,
    total: result.warnings.length,
    message,
    advice: adviseWarning(message),
  }));

  const functionSteps: ParseStep[] = visibleFunctions.map((name, i) => ({
    kind: "function",
    index: i,
    total: visibleFunctions.length,
    name,
    description: describeFunction(name),
  }));

  return [
    { kind: "intro", summary },
    ...errorSteps,
    ...warningSteps,
    ...functionSteps,
    {
      kind: "final",
      summary,
      canSave: result.status === "ok",
      hiddenFunctionCount,
    },
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- parse-dialog-steps`
Expected: PASS — 6 test cases green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog-steps.ts frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/parse-dialog-steps.test.ts
git commit -m "feat(fe-01): add buildParseSteps pure function with 14-function cap"
```

---

## Task N+2: [ParseDialog 컴포넌트 + 네비게이션]

**Files:**
- Create: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog.tsx`
- Test: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/parse-dialog.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// parse-dialog.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ParseDialog } from "../parse-dialog";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const sample: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 1,
  exit_count: 1,
  functions_used: ["ta.rsi", "strategy.entry"],
};

describe("ParseDialog", () => {
  it("renders intro step first when opened", () => {
    render(<ParseDialog open={true} onOpenChange={() => {}} result={sample} onSave={() => {}} />);
    expect(screen.getByText(/파싱 결과를 함께 살펴/)).toBeInTheDocument();
  });

  it("walks to function step on next click with description", () => {
    render(<ParseDialog open={true} onOpenChange={() => {}} result={sample} onSave={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    expect(screen.getByText("ta.rsi")).toBeInTheDocument();
    expect(screen.getByText(/RSI|상대.*강도/)).toBeInTheDocument();
  });

  it("fires onSave on final save button when status ok", () => {
    const onSave = vi.fn();
    const onOpenChange = vi.fn();
    render(<ParseDialog open={true} onOpenChange={onOpenChange} result={sample} onSave={onSave} />);
    // intro -> ta.rsi -> strategy.entry -> final
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    const saveBtn = screen.getByRole("button", { name: /저장/ });
    expect(saveBtn).not.toBeDisabled();
    fireEvent.click(saveBtn);
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("disables save when status is error", () => {
    const errored: ParsePreviewResponse = {
      ...sample, status: "error",
      errors: [{ code: "syntax", message: "bad", line: 3 }],
      functions_used: [],
    };
    render(<ParseDialog open={true} onOpenChange={() => {}} result={errored} onSave={() => {}} />);
    // intro -> error -> final
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    const saveBtn = screen.getByRole("button", { name: /저장/ });
    expect(saveBtn).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- parse-dialog.test`
Expected: FAIL — module not found.

- [ ] **Step 3: Create parse-dialog.tsx**

```typescript
// frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog.tsx
"use client";

import { useMemo, useState } from "react";
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { buildParseSteps, type ParseStep } from "./parse-dialog-steps";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: ParsePreviewResponse;
  onSave: () => void;
};

export function ParseDialog({ open, onOpenChange, result, onSave }: Props) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);

  const step = steps[index] ?? steps[0];
  const isFirst = index === 0;
  const isLast = index === steps.length - 1;

  const handleNext = () => setIndex((i) => Math.min(i + 1, steps.length - 1));
  const handlePrev = () => setIndex((i) => Math.max(i - 1, 0));
  const handleSave = () => {
    onSave();
    onOpenChange(false);
  };
  const handleReturn = () => onOpenChange(false);

  // open prop change 시 index 리셋
  const resetOnOpen = (next: boolean) => {
    if (next) setIndex(0);
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={resetOnOpen}>
      <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{renderTitle(step)}</DialogTitle>
          <DialogDescription>
            {index + 1} / {steps.length} 단계
          </DialogDescription>
        </DialogHeader>
        <div className="py-3" aria-live="polite">
          <StepBody step={step} />
        </div>
        <DialogFooter className="gap-2">
          {isLast ? (
            <>
              <Button variant="ghost" onClick={handleReturn}>
                <ChevronLeftIcon className="mr-1 size-4" />
                코드로 돌아가기
              </Button>
              <Button
                onClick={handleSave}
                disabled={step.kind === "final" ? !step.canSave : false}
              >
                이 전략 저장
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" onClick={handlePrev} disabled={isFirst}>
                <ChevronLeftIcon className="mr-1 size-4" />
                이전
              </Button>
              <Button onClick={handleNext}>
                다음
                <ChevronRightIcon className="ml-1 size-4" />
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function renderTitle(step: ParseStep): string {
  switch (step.kind) {
    case "intro":
      return "파싱 결과를 함께 살펴볼게요";
    case "error":
      return `에러 ${step.index + 1}/${step.total}`;
    case "warning":
      return `경고 ${step.index + 1}/${step.total}`;
    case "function":
      return `감지된 함수 ${step.index + 1}/${step.total}`;
    case "final":
      return step.canSave ? "저장할까요?" : "에러 해결 후 다시 시도";
  }
}

function StepBody({ step }: { step: ParseStep }) {
  switch (step.kind) {
    case "intro": {
      const { errorCount, warningCount, functionCount, pineVersion } = step.summary;
      return (
        <div className="space-y-2 text-sm">
          <p>
            Pine <Badge variant="secondary">{pineVersion}</Badge> 스크립트 파싱 결과:
          </p>
          <ul className="ml-4 list-disc space-y-1">
            <li>에러 {errorCount}건</li>
            <li>경고 {warningCount}건</li>
            <li>감지된 함수 {functionCount}개</li>
          </ul>
          <p className="text-xs text-[color:var(--text-muted)]">
            다음을 눌러 하나씩 확인해보세요.
          </p>
        </div>
      );
    }
    case "error":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs">
            {step.error.line != null && <span className="mr-1">L{step.error.line}:</span>}
            <span className="text-[color:var(--destructive)]">[{step.error.code}]</span>{" "}
            {step.error.message}
          </p>
          <p className="mt-2">
            <span className="font-bold">원인: </span>
            {step.advice.what}
          </p>
          <p>
            <span className="font-bold">조치: </span>
            {step.advice.action}
          </p>
        </div>
      );
    case "warning":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs">{step.message}</p>
          <p>
            <span className="font-bold">원인: </span>
            {step.advice.what}
          </p>
          <p>
            <span className="font-bold">조치: </span>
            {step.advice.action}
          </p>
        </div>
      );
    case "function":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-base">{step.name}</p>
          <p className="font-bold">{step.description.summary}</p>
          <p>{step.description.purpose}</p>
          {step.description.example && (
            <pre className="mt-2 overflow-x-auto rounded bg-[color:var(--bg-alt)] p-2 font-mono text-xs">
              {step.description.example}
            </pre>
          )}
        </div>
      );
    case "final": {
      if (!step.canSave) {
        return (
          <p className="text-sm">
            에러가 {step.summary.errorCount}건 있습니다. 코드로 돌아가 수정한 뒤 다시 시도해주세요.
          </p>
        );
      }
      return (
        <div className="space-y-2 text-sm">
          <p>파싱 결과를 확인하셨습니다. 이 전략을 지금 저장할까요?</p>
          {step.hiddenFunctionCount > 0 && (
            <p className="text-xs text-[color:var(--text-muted)]">
              (총 {step.summary.functionCount}개 중 {step.hiddenFunctionCount}개는 요약에서 생략)
            </p>
          )}
        </div>
      );
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- parse-dialog.test`
Expected: PASS — 4 test cases green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-dialog.tsx frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/parse-dialog.test.tsx
git commit -m "feat(fe-01): add ParseDialog conversational walk-through with step machine"
```

---

## Task N+3: [TabParse 요약 축소 + Dialog 트리거]

**Files:**
- Modify: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx`

- [ ] **Step 1: Update TabParse — 4섹션 요약 + Dialog 런처**

```typescript
// tab-parse.tsx (교체판)
"use client";

// Sprint FE-01: 요약 카드 + ParseDialog 런처로 전환. 상세 워크스루는 모달에서.
// BE 변경 없음. ParsePreviewResponse 그대로 사용.

import { useState } from "react";
import { SparklesIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { usePreviewParse, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";
import { toast } from "sonner";
import { ParseDialog } from "./parse-dialog";

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const preview = usePreviewParse(strategy.pine_source);
  const live = preview.data;
  const [dialogOpen, setDialogOpen] = useState(false);
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("전략을 저장했습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  const meta = PARSE_STATUS_META[live?.status ?? strategy.parse_status];
  const canWalkthrough = Boolean(live);
  const previewError = preview.isError ? (preview.error as Error).message : null;

  const handleSave = () => {
    update.mutate({ pine_source: strategy.pine_source });
  };
  const handleRetry = () => {
    preview.refetch();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Badge variant="outline" data-tone={meta.tone}>
              {meta.label}
            </Badge>
            <Badge variant="secondary">
              Pine {live?.pine_version ?? strategy.pine_version}
            </Badge>
            {preview.isFetching && (
              <span className="text-xs text-[color:var(--text-muted)]">파싱 중...</span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <Summary label="에러" value={live?.errors.length ?? 0} tone="destructive" />
            <Summary label="경고" value={live?.warnings.length ?? 0} tone="warn" />
            <Summary label="감지 함수" value={live?.functions_used.length ?? 0} tone="info" />
          </dl>
          {previewError ? (
            <div className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 text-xs">
              <p className="font-bold text-[color:var(--destructive)]">파싱 요청 실패</p>
              <p className="mt-1 font-mono">{previewError}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRetry}
                className="mt-2"
              >
                다시 시도
              </Button>
            </div>
          ) : (
            <Button
              onClick={() => setDialogOpen(true)}
              disabled={!canWalkthrough}
              className="w-full"
            >
              <SparklesIcon className="mr-1 size-4" />
              {canWalkthrough ? "파싱 결과 해설 시작" : "파싱 준비 중..."}
            </Button>
          )}
          <p className="text-xs text-[color:var(--text-muted)]">
            ※ 자연어 해설로 각 함수·에러·경고를 단계별 확인할 수 있습니다.
          </p>
        </CardContent>
      </Card>
      {live && (
        <ParseDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          result={live}
          onSave={handleSave}
        />
      )}
    </>
  );
}

function Summary({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "destructive" | "warn" | "info";
}) {
  const colorClass =
    tone === "destructive"
      ? "text-[color:var(--destructive)]"
      : tone === "warn"
        ? "text-amber-600"
        : "text-[color:var(--text-primary)]";
  return (
    <div>
      <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
        {label}
      </dt>
      <dd className={`mt-1 font-mono text-lg ${colorClass}`}>{value}</dd>
    </div>
  );
}
```

- [ ] **Step 2: Verify `useUpdateStrategy` hook exists with expected signature**

Run: `grep -n "useUpdateStrategy" frontend/src/features/strategy/hooks.ts`
Expected: `useUpdateStrategy(id: string, opts: MutationCallbacks<StrategyResponse>)` — confirmed during planning. Hook returns React Query `UseMutationResult` with `.mutate(payload)`.

- [ ] **Step 3: Run the vitest suite end-to-end**

Run: `cd frontend && pnpm test`
Expected: existing 9 tests + 17 new = 26 tests pass. If tests that reference old TabParse fail, those tests are snapshot/structure tests — update them or delete obsolete assertions.

- [ ] **Step 4: Run linter & typecheck**

Run: `cd frontend && pnpm lint && pnpm typecheck`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx
git commit -m "feat(fe-01): replace TabParse 4-section view with summary card + ParseDialog launcher"
```

---

## Task N+4: [Dev 서버 스모크 테스트 + design-review]

**Files:** none modified; verification only.

- [ ] **Step 1: Start dev servers**

Run: `pnpm dev` (from repo root, should start FE + BE concurrently per project convention)
Expected: FE at `http://localhost:3000`, BE at `http://localhost:8000`.

- [ ] **Step 2: Manual smoke walkthrough**

Navigate to `/strategies/<any-id>/edit` → click TabParse → observe:
- Summary card shows error/warning/function counts
- Click "파싱 결과 해설 시작" button
- Dialog opens with intro step
- Click "다음" repeatedly — each function step shows name + Korean summary + example
- Reach final step — "이 전략 저장" button; click it to trigger mutation + sonner toast
- Test with a v4 script to trigger v4_migration error — verify advice text renders

- [ ] **Step 3: gstack /design-review pass**

Invoke the gstack `design-review` skill on the running site. Capture screenshots for:
- Summary card (light + dark theme if both exist)
- Dialog intro + function step + error step + final step (canSave true + false)
Fix any 1-point visual issues surfaced.

- [ ] **Step 4: Final commit (if design-review changes)**

```bash
git add frontend/
git commit -m "fix(fe-01): address design-review findings on ParseDialog"
```

---

## Verification — 종합 체크리스트

- [ ] `cd frontend && pnpm test` — 26+ tests green (기존 9 + 신규 17)
- [ ] `cd frontend && pnpm lint` — no new warnings
- [ ] `cd frontend && pnpm typecheck` — no errors
- [ ] `cd backend && pytest` — 778 tests still green (BE touch 0이므로 당연)
- [ ] 수동 스모크: intro → function → final 흐름 완주, "저장" 버튼 정상 동작
- [ ] 에러 있을 때 "저장" 비활성화 확인
- [ ] `design-review` 1-pass 통과

---

## Known Trade-offs / Non-goals

- **LLM 해설은 스코프 밖:** 이번은 하드코딩 테이블만. 다음 스프린트에서 `describeFunction` fallback을 LLM으로 교체할 수 있는 인터페이스로 이미 설계됨 (`describeFunction(name: string): PineFunctionDescription`).
- **User-defined 함수는 "알 수 없음" fallback:** Sprint 8c가 user function 지원을 열어둔 만큼, fallback도 의미 있는 메시지로 나옴. 추후 signature 파싱으로 확장 가능.
- **모바일 반응형:** shadcn Dialog 기본 스타일 활용. 별도 튜닝은 design-review에 맡김.
- **키보드 네비게이션:** `Esc` 닫기는 기본. `←/→`는 이번 범위 밖 (hover ok 사용자 기준 dogfood엔 충분).

---

## 참조

- 메모리: `project_sprint7c_complete` (FE 패턴), `feedback_dogfood_first_indie`
- Sprint 7b plan: `docs/superpowers/plans/2026-04-17-sprint7b-edit-parse-ux.md`
- Sprint 7c plan: `docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md`
- Next Session prompt: `docs/next-session-tabparse-fe-1q-prompt.md`

---

## Design Review 1-Pass Findings (plan-design-review, 2026-04-19)

### Scorecard (초기 → fix 후)

| Dimension | 초기 | After fix | 비고 |
|---|---|---|---|
| Pass 1 — Information Architecture | 7 | 8 | intro count 제시 방식은 dogfood 라운드에서 재평가 |
| Pass 2 — Interaction State | 5 | 8 | preview.isError → retry 버튼 추가, save-in-flight는 TODOS |
| Pass 3 — User Journey | 6 | 7 | skip-to-final 버튼은 TODOS (포스트-dogfood 결정) |
| Pass 4 — AI Slop Risk | 8 | 8 | 플레인, emoji 없음, product-specific 문구 |
| Pass 5 — Design System | - | 8 | `--warning` → `text-amber-600`, `--code-bg` → `--bg-alt` 교체 |
| Pass 6 — Responsive & A11y | 4 | 7 | `w-[calc(100vw-2rem)]` + `aria-live` 추가, 키보드 shortcut은 TODOS |
| Pass 7 — Unresolved Decisions | — | — | 아래 결정 테이블 참조 |

**Overall plan design readiness: 6/10 → 8/10.**

### Fixed (인라인 반영 완료)

1. **모바일 Dialog 너비**: `w-[calc(100vw-2rem)] sm:max-w-lg` — 375px 뷰포트에서도 좌우 여백 1rem 확보.
2. **aria-live region**: StepBody 부모에 `aria-live="polite"` — 스텝 전환 시 스크린 리더 안내.
3. **코드 예시 overflow**: `overflow-x-auto` 추가 — 긴 example이 모바일에서 잘리지 않음.
4. **CSS 토큰 검증**: `--warning` / `--code-bg` 미정의 확인. `text-amber-600` / `--bg-alt`로 교체 (globals.css 기존 토큰만 사용).
5. **preview.isError UX**: TabParse에 네트워크 에러 블록 + "다시 시도" 버튼. 기존엔 "파싱 준비 중..." 무한 대기였음.
6. **stdlib-first cap**: `prioritizeFunctions()` 헬퍼 추가. 14개 cap 적용 시 알려진 stdlib/strategy 함수가 우선. user-defined 많을 때 유용한 해설이 먼저 나옴.
7. **테스트 추가**: prioritize 동작 검증 1건 (총 파싱 단계 스텝 테스트 6건).

### 결정 테이블 (Pass 7)

| Decision | Resolution |
|---|---|
| "저장" 버튼이 실제 mutation trigger? | **Yes** — `useUpdateStrategy(id).mutate({pine_source})` 직접 호출. 사용자 기대치에 정직. |
| 저장 중 Dialog open 유지? | **No, 즉시 close + toast** — 현재 UI는 즉시 닫고 sonner로 성공/실패 알림. 저장은 근접 실패율 낮음. (TODOS에 "실패 시 롤백 UX" 기록) |
| 함수 cap 우선순위 | **Known stdlib first** — `prioritizeFunctions()` 구현 완료. |
| 0-count 빈 상태 (intro → final 2-step) | **유지** — 2 클릭으로 저장 confirm 흐름. 더 짧게 줄이면 실수로 저장 위험. |
| 모바일 < 640px | **해결** — `calc(100vw-2rem)` 너비로 확보. |

### 배부된 TODOS (implementation 시 추가)

1. **Skip-to-final 버튼 (intro)** — repeat 사용자 dogfood 후 필요하면 추가. 1-pass 완성도 평가에 영향 없음.
2. **Save-in-flight 롤백 UX** — 저장 실패 시 Dialog 재열기 + 에러 메시지. sonner 단독은 실패 인지 낮음.
3. **키보드 shortcut (←/→)** — Dialog 내 focus trap 안에서 키 처리. 접근성 enhance.
4. **첫 에러 라인으로 점프** — final step canSave=false일 때 "코드로 돌아가기" 클릭 시 Monaco editor가 해당 line으로 스크롤. Monaco 통합 필요.
5. **User-defined 함수 signature 파싱** — Sprint 8c가 user function을 지원. pine-lexicon이 "알 수 없음" fallback 대신 signature 요약 생성 (다음 스프린트).

### 적용되지 않은 것 (사유)

- **Visual mockup 생성**: Dialog는 content-driven (코드 + 텍스트). Mockup 생성 ROI 낮음. dogfood 직후 `/design-review` 실행으로 라이브 검증.
- **DESIGN.md 생성**: 이 프로젝트는 Sprint 7c에서 shadcn + CSS var 체계 정립. 별도 DESIGN.md 없음. 기존 `globals.css` 토큰을 single source of truth로 유지.

### 다음 단계 권고

- 이 플랜은 `executing-plans`로 실행 가능한 상태. Pass 7의 fixes는 Tasks 안에 반영됨.
- 구현 완료 후 dogfood 스모크 + `/design-review` live pass로 visual QA.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | 제품 방향성 명확, scope 적정 — skip |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | FE UX 중심 + BE 0변경 — skip |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | executing 전 선택 (Sprint 7b/7c 패턴 준수 시 생략 가능) |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR | score 6/10 → 8/10, 5 decisions, 0 unresolved, 5 TODOS 보류 |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | FE only — N/A |

**VERDICT:** DESIGN CLEARED — 플랜은 구현 가능 상태. Eng review는 선택.
