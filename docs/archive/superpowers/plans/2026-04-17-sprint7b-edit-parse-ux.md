# Sprint 7b — Edit 페이지 Pine 이터레이션 UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Edit 페이지의 Pine 이터레이션 루프에서 (a) 코드 탭 진입 시 저장된 코드의 파싱 결과를 즉시 노출, (b) 파싱 결과 탭을 warnings / errors / 감지된 지표·전략 콜 / 메타 4-섹션으로 풍부화하여 ISSUE-003 + ISSUE-004 해소.

**Architecture:** Approach B 하이브리드 — BE는 `ParsePreviewResponse`에 `functions_used: list[str]` 필드 1개만 확장 (Pydantic schema 1필드 + service `_parse` 튜플 1요소). Strategy ORM 모델 / Alembic migration / router 전부 불변. FE는 코드 탭 + 파싱 결과 탭 모두 마운트 시 `useParseStrategy`를 자동 1회 호출하여 실시간 스냅샷을 렌더. persist는 Sprint 7d+로 defer.

**Tech Stack:** FastAPI + Pydantic V2 (BE), Next.js 16 + React Query + Zod v4 + Tailwind v4 + shadcn/ui v4 (FE), pnpm / uv / pytest / vitest / Playwright.

---

## Context

Sprint 7c 직후 실행한 `/qa Quick tier` sweep에서 Edit 페이지 dogfood 루프의 80% 마찰이 확인됨 (`.gstack/qa-reports/qa-report-localhost-2026-04-17.md`).

- **ISSUE-003 (Medium):** 코드 탭 우측 `ParsePreviewPanel`이 Monaco에 이미 코드가 로드되어 있어도 "코드를 입력하면 자동으로 파싱 결과가 표시됩니다"라는 빈 상태 문구만 표시. ⌘+Enter 1회 입력 전까지 사용자는 본인 저장 코드의 현재 파싱 상태를 볼 수 없음.
- **ISSUE-004 (Medium):** 파싱 결과 탭은 "Pine 버전 / 아카이브 상태" 두 줄만 노출. 파서가 이미 산출하는 warnings / errors / functions_used는 UI에서 확인 불가 → 사용자는 curl로 `/strategies/parse` 재호출.

Q-1 verify 결과 `strategy.parse_metadata` JSONB는 DB에 존재하지 않으며, 저장되는 파싱 정보는 `parse_status` + `parse_errors` + `pine_version` 뿐이다. 파서 내부 `ParseOutcome.supported_feature_report["functions_used"]`는 존재하지만 API 응답 DTO `ParsePreviewResponse` 스키마에는 미노출. 따라서 "완전 pure FE"로는 design doc Success Criteria C-2를 충족 불가. Approach B(응답 DTO 1필드 확장)로 진행한다.

본 Sprint는 메이커 본인 dogfood 루프의 quality bar를 올리는 wedge sprint. 외부 공개(Horizon H2) 전 선행 작업.

---

## File Structure

### Backend (변경 범위 최소 — migration/model 불변)

- **Modify** `backend/src/strategy/schemas.py` — `ParsePreviewResponse`에 `functions_used: list[str] = Field(default_factory=list)` 1필드 추가.
- **Modify** `backend/src/strategy/service.py` — `_parse()` 반환 튜플에 `functions_used` 7번째 요소 추가, `parse_preview()` 응답에 매핑. `create()` / `update()` 경로는 튜플 언팩 자리만 정정 (persist는 여전히 안함).
- **Create** `backend/tests/strategy/test_parse_preview_functions_used.py` — parse_preview 응답에 functions_used 포함되는지 & golden 입력에서 `ta.ema`/`strategy` 등 기대 함수가 등장하는지 검증.

### Frontend (3-tab 편집 UI 구조 유지)

- **Modify** `frontend/src/features/strategy/schemas.ts` — `ParsePreviewResponseSchema`에 `functions_used: z.array(z.string()).default([])` 추가.
- **Modify** `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx` — `functions_used` 섹션 추가 (감지 지표 / 전략 콜 구분 렌더) + 빈 상태 copy 수정 ("⌘+Enter로 첫 파싱 실행"). 이 컴포넌트는 TabCode와 /strategies/new 둘 다 재사용하므로 공통 변경.
- **Modify** `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx` — 마운트 시 `parse.mutate(strategy.pine_source)` 자동 1회 호출. pine_source가 비어있을 때만 빈 패널.
- **Modify** `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx` — 전면 재작성. `useParseStrategy` 마운트 트리거 + 4-섹션 (에러 → 경고 → 감지 → 메타) 구조로 풍부화. 저장 시점 `strategy.parse_errors`도 함께 표시 (실시간 결과와 구분 가능한 라벨).
- **Create** `frontend/src/features/strategy/__tests__/parse-preview-schema.test.ts` — Zod `ParsePreviewResponseSchema` round-trip + `functions_used` 기본값 검증.

### Docs

- **Modify** `docs/TODO.md` — /qa Quick tier findings 섹션에 ISSUE-003/004 ✅ 체크. Next 7b/7c 표시 업데이트.

---

## Regression Guard (공통)

모든 task 완료 후 최종 T7에서 회귀 가드를 돈다. 개별 task는 각 step 내부에서 아래 부분집합만 요구.

- **BE:** `cd backend && pytest -v` (424+ tests green), `ruff check .`, `mypy src/`
- **FE:** `cd frontend && pnpm tsc --noEmit`, `pnpm lint`, `pnpm test`
- **Smoke:** docker compose up → `/strategies`에서 기존 MA Crossover 전략 선택 → 코드 탭/파싱 결과 탭에서 functions_used/warnings/errors 렌더 확인 → 신규 전략 wizard → 바로 `/edit` 진입하여 parse_metadata 없는 케이스 확인.

---

## Task 1: BE — ParsePreviewResponse에 `functions_used` 필드 추가 (TDD)

**Files:**
- Modify: `backend/src/strategy/schemas.py:40-46`
- Modify: `backend/src/strategy/service.py:43-97, 112-121`
- Test: `backend/tests/strategy/test_parse_preview_functions_used.py` (create)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/strategy/test_parse_preview_functions_used.py
"""ParsePreviewResponse.functions_used 필드 회귀 테스트.

Sprint 7b (ISSUE-004): UI 파싱 결과 탭에서 '감지된 지표/전략 콜' 섹션
렌더링을 위해 응답 DTO에 functions_used 노출.
"""
from __future__ import annotations

import pytest

from src.strategy.repository import StrategyRepository
from src.strategy.service import StrategyService


EMA_CROSS_V5 = """//@version=5
strategy("EMA Cross", overlay=true)
fast = ta.ema(close, 9)
slow = ta.ema(close, 21)
longCond = ta.crossover(fast, slow)
exitCond = ta.crossunder(fast, slow)
if longCond
    strategy.entry("long", strategy.long)
if exitCond
    strategy.close("long")
"""


@pytest.mark.asyncio
async def test_parse_preview_returns_functions_used(db_session):
    service = StrategyService(StrategyRepository(db_session))
    result = await service.parse_preview(EMA_CROSS_V5)

    assert result.status == "ok"
    assert "ta.ema" in result.functions_used
    assert "ta.crossover" in result.functions_used
    assert "strategy.entry" in result.functions_used
    # 결정적 정렬 보장 (supported_feature_report는 sorted(used))
    assert result.functions_used == sorted(result.functions_used)


@pytest.mark.asyncio
async def test_parse_preview_functions_used_empty_on_error(db_session):
    service = StrategyService(StrategyRepository(db_session))
    result = await service.parse_preview("!!! invalid pine !!!")

    assert result.status == "error"
    # parser가 tokenize 단계에서 실패하면 report 빈 상태로 반환
    assert result.functions_used == []
```

- [ ] **Step 2: Run test → verify FAIL**

Run: `cd backend && pytest tests/strategy/test_parse_preview_functions_used.py -v`
Expected: FAIL with `AttributeError: 'ParsePreviewResponse' object has no attribute 'functions_used'` (또는 Pydantic validation error).

- [ ] **Step 3: Extend Pydantic schema**

Modify `backend/src/strategy/schemas.py:40-46`:

```python
class ParsePreviewResponse(BaseModel):
    status: ParseStatus
    pine_version: PineVersion
    warnings: list[str] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)
    entry_count: int = 0
    exit_count: int = 0
    # Sprint 7b ISSUE-004: UI 파싱 결과 탭에서 감지된 지표/전략 콜 섹션
    # 렌더링을 위해 노출. Parser supported_feature_report["functions_used"] 반영.
    functions_used: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Extend service `_parse()` & `parse_preview()`**

Modify `backend/src/strategy/service.py:43-97` (`_parse` 반환 튜플 + 추출 로직) and `:112-121` (parse_preview 매핑). Show full replacement:

```python
def _parse(
    source: str,
) -> tuple[
    ParseStatus,
    PineVersion,
    list[str],
    list[ParseError],
    int,
    int,
    list[str],
]:
    """parse_and_run → (status, version, warnings, errors, entry_count, exit_count, functions_used).

    functions_used: supported_feature_report["functions_used"] 반영 (빈 dict fallback).
    """
    try:
        outcome = parse_and_run(source, _empty_ohlcv())
    except Exception as exc:
        return (
            ParseStatus.error,
            PineVersion.v5,
            [],
            [ParseError(code=type(exc).__name__, message=str(exc))],
            0,
            0,
            [],
        )

    warnings: list[str] = list(outcome.warnings)
    if outcome.signals is not None:
        warnings.extend(outcome.signals.warnings)

    errors: list[ParseError] = []
    if outcome.error is not None:
        e = outcome.error
        errors.append(
            ParseError(
                code=getattr(e, "category", type(e).__name__),
                message=str(e),
                line=getattr(e, "line", None),
            )
        )

    status = (
        ParseStatus(outcome.status)
        if outcome.status in {"ok", "unsupported", "error"}
        else ParseStatus.error
    )
    version = (
        PineVersion(outcome.source_version)
        if outcome.source_version in {"v4", "v5"}
        else PineVersion.v5
    )

    entry_count = int(outcome.signals.entries.sum()) if outcome.signals is not None else 0
    exit_count = int(outcome.signals.exits.sum()) if outcome.signals is not None else 0
    functions_used = list(outcome.supported_feature_report.get("functions_used", []))

    return status, version, warnings, errors, entry_count, exit_count, functions_used
```

Update `parse_preview` (line 112):

```python
    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count, functions_used = _parse(
            pine_source
        )
        return ParsePreviewResponse(
            status=status,
            pine_version=version,
            warnings=warnings,
            errors=errors,
            entry_count=entry_count,
            exit_count=exit_count,
            functions_used=functions_used,
        )
```

Also update call sites in `create()` (line 126) and `update()` (line 202). Tuple unpacking must absorb the new 7th element:

```python
# create() — line 126
        status, version, _warnings, errors, _e, _x, _fu = _parse(data.pine_source)

# update() — line 202
            status, version, _w, errors, _e, _x, _fu = _parse(data.pine_source)
```

Rationale: persist 범위를 넓히지 않는다 (design doc P3 — Strategy 모델 불변). `create`/`update`는 errors만 저장하는 기존 동작 유지.

- [ ] **Step 5: Run test → verify PASS**

Run: `cd backend && pytest tests/strategy/test_parse_preview_functions_used.py -v`
Expected: PASS 2/2.

- [ ] **Step 6: Regression sweep**

Run: `cd backend && pytest tests/strategy/ -v && ruff check src/strategy/ && mypy src/strategy/`
Expected: 기존 strategy 도메인 테스트 전체 green. `_parse` 튜플 arity 변경으로 인한 실패 0건.

- [ ] **Step 7: Commit**

```bash
git add backend/src/strategy/schemas.py backend/src/strategy/service.py backend/tests/strategy/test_parse_preview_functions_used.py
git commit -m "feat(strategy): expose functions_used in ParsePreviewResponse — Sprint 7b BE wedge"
```

---

## Task 2: FE — Zod `ParsePreviewResponseSchema` 확장 (TDD)

**Files:**
- Modify: `frontend/src/features/strategy/schemas.ts:19-27`
- Test: `frontend/src/features/strategy/__tests__/parse-preview-schema.test.ts` (create)

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/features/strategy/__tests__/parse-preview-schema.test.ts
// Sprint 7b: ParsePreviewResponse.functions_used Zod round-trip 검증.

import { describe, expect, it } from "vitest";

import { ParsePreviewResponseSchema } from "../schemas";

describe("ParsePreviewResponseSchema", () => {
  it("parses functions_used from BE response", () => {
    const raw = {
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 3,
      exit_count: 2,
      functions_used: ["strategy.entry", "ta.crossover", "ta.ema"],
    };
    const parsed = ParsePreviewResponseSchema.parse(raw);
    expect(parsed.functions_used).toEqual([
      "strategy.entry",
      "ta.crossover",
      "ta.ema",
    ]);
  });

  it("defaults functions_used to empty array when omitted", () => {
    const raw = {
      status: "error",
      pine_version: "v5",
      errors: [{ code: "LexError", message: "boom", line: null }],
    };
    const parsed = ParsePreviewResponseSchema.parse(raw);
    expect(parsed.functions_used).toEqual([]);
    expect(parsed.warnings).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test → verify FAIL**

Run: `cd frontend && pnpm test -- parse-preview-schema`
Expected: FAIL with "Cannot find property 'functions_used'" or type error.

- [ ] **Step 3: Extend Zod schema**

Modify `frontend/src/features/strategy/schemas.ts:19-27`:

```typescript
export const ParsePreviewResponseSchema = z.object({
  status: ParseStatusSchema,
  pine_version: PineVersionSchema,
  warnings: z.array(z.string()).default([]),
  errors: z.array(ParseErrorSchema).default([]),
  entry_count: z.number().int().default(0),
  exit_count: z.number().int().default(0),
  // Sprint 7b ISSUE-004: BE ParseOutcome.supported_feature_report["functions_used"] 반영.
  functions_used: z.array(z.string()).default([]),
});
export type ParsePreviewResponse = z.infer<typeof ParsePreviewResponseSchema>;
```

- [ ] **Step 4: Run test → verify PASS**

Run: `cd frontend && pnpm test -- parse-preview-schema`
Expected: PASS 2/2.

- [ ] **Step 5: Type check**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: zero errors. `functions_used` 타입이 `ParsePreviewPanel` 사용처에서 자동 노출.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/strategy/schemas.ts frontend/src/features/strategy/__tests__/parse-preview-schema.test.ts
git commit -m "feat(strategy/fe): extend ParsePreviewResponseSchema with functions_used — Sprint 7b"
```

---

## Task 3: FE — `ParsePreviewPanel`에 functions_used 섹션 추가 + 빈 상태 copy 수정

**Files:**
- Modify: `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx` (전체 교체)

> 이 컴포넌트는 `/strategies/new` step-code 와 Edit 코드 탭(`tab-code.tsx`)에서 모두 재사용된다. functions_used 섹션 + 빈 상태 copy 업그레이드가 양쪽에 동시 적용됨.

- [ ] **Step 1: 섹션 구조 업데이트**

Modify `frontend/src/app/(dashboard)/strategies/new/_components/parse-preview-panel.tsx`. 기존 구조 위에 `functions_used` 섹션을 "경고" 다음 위치에 삽입하고, 빈 상태 copy를 "⌘+Enter로 첫 파싱을 실행하세요" 로 교체.

섹션 분류 규칙:
- `ta.*` → "감지된 지표" 서브섹션
- `strategy.*` → "전략 콜" 서브섹션
- 그 외(`input.*`, `plot`, etc.) → "기타 함수" 서브섹션 (접어두기, 5개까지만 노출)

Full replacement:

```tsx
"use client";

// Sprint 7c T4 + Sprint 7b ISSUE-003/004: 실시간 파싱 결과 패널.
// - Sprint 7c: aria-live + status badges + entry/exit + warnings/errors
// - Sprint 7b: functions_used 섹션 (감지 지표 / 전략 콜 / 기타) + 빈 상태 copy 수정

import { CheckIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

function groupFunctions(fns: readonly string[]): {
  indicators: string[];
  strategies: string[];
  others: string[];
} {
  const indicators: string[] = [];
  const strategies: string[] = [];
  const others: string[] = [];
  for (const fn of fns) {
    if (fn.startsWith("ta.")) indicators.push(fn);
    else if (fn.startsWith("strategy.") || fn === "strategy") strategies.push(fn);
    else others.push(fn);
  }
  return { indicators, strategies, others };
}

export function ParsePreviewPanel({
  result,
  loading,
}: {
  result: ParsePreviewResponse | null;
  loading: boolean;
}) {
  return (
    <aside
      aria-live="polite"
      aria-label="실시간 파싱 결과"
      className="rounded-[var(--radius-md)] border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] p-5"
    >
      <header className="mb-3 flex items-center gap-2">
        <span
          aria-hidden
          className={
            "block size-2 rounded-full " +
            (loading ? "animate-pulse bg-[color:var(--primary)]" : "bg-[color:var(--success)]")
          }
        />
        <h3 className="font-display text-sm font-bold text-[color:var(--primary)]">
          {loading ? "파싱 중..." : "실시간 파싱 결과"}
        </h3>
      </header>

      {!result && !loading && (
        <p className="text-xs text-[color:var(--text-secondary)]">
          ⌘+Enter로 첫 파싱을 실행하세요.
        </p>
      )}

      {result && <ResultBody result={result} />}
    </aside>
  );
}

function ResultBody({ result }: { result: ParsePreviewResponse }) {
  const { indicators, strategies, others } = groupFunctions(result.functions_used);
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="outline" data-tone={PARSE_STATUS_META[result.status].tone}>
          {PARSE_STATUS_META[result.status].label}
        </Badge>
        <Badge variant="secondary">Pine {result.pine_version}</Badge>
      </div>

      {result.status === "ok" && (
        <div className="mb-3 flex items-center gap-2">
          <span
            className="inline-grid size-5 place-items-center rounded-full bg-[color:var(--success)] text-white motion-safe:animate-[scale-in_200ms_ease-out]"
            aria-hidden
          >
            <CheckIcon className="size-3" strokeWidth={3} />
          </span>
          <span className="text-xs text-[color:var(--success)]">
            변환 완료. 바로 저장할 수 있어요.
          </span>
        </div>
      )}

      <dl className="grid grid-cols-2 gap-y-2 text-xs">
        <dt className="text-[color:var(--text-secondary)]">진입 신호</dt>
        <dd className="text-right font-mono font-semibold">{result.entry_count}</dd>
        <dt className="text-[color:var(--text-secondary)]">청산 신호</dt>
        <dd className="text-right font-mono font-semibold">{result.exit_count}</dd>
      </dl>

      {result.status === "unsupported" && (
        <p className="mt-3 text-xs text-[color:var(--text-secondary)]">
          <strong>저장은 가능합니다.</strong> 백테스트 실행 시 해당 함수는 제외되거나 에러를 반환합니다.
        </p>
      )}

      {result.warnings.length > 0 && (
        <section className="mt-3">
          <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
            경고 ({result.warnings.length})
          </h4>
          <ul className="mt-1 space-y-1 text-xs text-[color:var(--text-secondary)]">
            {result.warnings.slice(0, 5).map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </section>
      )}

      {result.errors.length > 0 && (
        <section className="mt-3">
          <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--destructive)]">
            에러 ({result.errors.length})
          </h4>
          <ul className="mt-1 space-y-1 text-xs text-[color:var(--destructive)]">
            {result.errors.slice(0, 5).map((e, i) => (
              <li key={i}>
                {e.line !== null && <span className="font-mono">L{e.line}: </span>}
                {e.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(indicators.length > 0 || strategies.length > 0 || others.length > 0) && (
        <section className="mt-3">
          <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
            감지된 함수 ({result.functions_used.length})
          </h4>
          {indicators.length > 0 && (
            <FunctionSubsection label="지표" items={indicators} />
          )}
          {strategies.length > 0 && (
            <FunctionSubsection label="전략 콜" items={strategies} />
          )}
          {others.length > 0 && (
            <FunctionSubsection label="기타" items={others.slice(0, 5)} />
          )}
        </section>
      )}
    </>
  );
}

function FunctionSubsection({ label, items }: { label: string; items: readonly string[] }) {
  return (
    <div className="mt-2">
      <p className="text-[0.65rem] text-[color:var(--text-muted)]">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {items.map((fn) => (
          <Badge key={fn} variant="outline" className="font-mono text-[0.65rem]">
            {fn}
          </Badge>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type check & lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint src/app/\(dashboard\)/strategies/new/_components/parse-preview-panel.tsx`
Expected: 0 errors, 0 warnings.

- [ ] **Step 3: Visual smoke — `/strategies/new` step-code**

Run dev server (`pnpm dev`), navigate to `/strategies/new`, paste MA Crossover Pine v5 source, press ⌘+Enter. Verify:
- 경고 섹션 아래에 **"감지된 함수 (N)"** 섹션이 새로 나타남.
- 지표 / 전략 콜 / 기타 서브섹션이 함수 이름 badge로 표시.
- 에러 케이스에서 functions_used가 빈 배열이면 섹션 자체 숨김.
- 빈 상태 copy가 "⌘+Enter로 첫 파싱을 실행하세요" 로 변경됨.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/strategies/new/_components/parse-preview-panel.tsx
git commit -m "feat(strategy/fe): show functions_used sections in ParsePreviewPanel — Sprint 7b ISSUE-004"
```

---

## Task 4: FE — TabCode 마운트 시 자동 파싱 (ISSUE-003)

**Files:**
- Modify: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx`

- [ ] **Step 1: 마운트 자동 파싱 트리거 주입**

Modify `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-code.tsx`. 기존 코드를 보존하되 `useEffect` 1개를 추가하여 `strategy.pine_source`가 비어있지 않으면 마운트 시 `parse.mutate()`를 1회 호출. 반복 호출 방지를 위해 `mutate()` 호출 여부를 id별로 ref tracking.

Full replacement:

```tsx
"use client";

// Sprint 7c T5 + Sprint 7b ISSUE-003: 코드 탭 — Monaco Pine 에디터 + 실시간 파싱 + 저장.
// 마운트 시 저장된 pine_source 자동 파싱으로 빈 상태 오표시 제거.

import { useEffect, useRef, useState } from "react";
import { SaveIcon } from "lucide-react";
import { toast } from "sonner";

import { PineEditor } from "@/components/monaco/pine-editor";
import { Button } from "@/components/ui/button";
import { useParseStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";

import { ParsePreviewPanel } from "../../../new/_components/parse-preview-panel";

export function TabCode({ strategy }: { strategy: StrategyResponse }) {
  const [source, setSource] = useState(strategy.pine_source);
  const dirty = source !== strategy.pine_source;
  const parse = useParseStrategy();
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  // 마운트 자동 파싱 — strategy.id 기준 1회만 실행.
  // 다른 전략으로 전환되면 ref 리셋되어 재파싱.
  const mountedForId = useRef<string | null>(null);
  useEffect(() => {
    if (mountedForId.current === strategy.id) return;
    mountedForId.current = strategy.id;
    if (strategy.pine_source.trim().length > 0) {
      parse.mutate(strategy.pine_source);
    }
    // mutate는 안정 참조 — deps에서 제외 (react-query 표준 패턴).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy.id, strategy.pine_source]);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs text-[color:var(--text-muted)]">
            ⌘+S 저장 · ⌘+Enter 파싱 미리보기
          </p>
          <Button
            onClick={() => update.mutate({ pine_source: source })}
            disabled={!dirty || update.isPending}
          >
            <SaveIcon className="size-4" />
            {update.isPending ? "저장 중..." : "저장"}
          </Button>
        </div>
        <PineEditor
          value={source}
          onChange={setSource}
          onTriggerParse={() => source.trim() && parse.mutate(source)}
          height={520}
        />
      </div>
      <ParsePreviewPanel result={parse.data ?? null} loading={parse.isPending} />
    </div>
  );
}
```

주의:
- `parse.mutate()`를 ref 가드 없이 useEffect에 넣으면 React 18 StrictMode double-invoke로 2회 호출됨. `mountedForId` ref로 id별 1회만 보장.
- `strategy.pine_source`가 빈 문자열(trim 결과 0)인 경우 자동 파싱 스킵 → 빈 패널에 "⌘+Enter로 첫 파싱을 실행하세요" CTA 노출 (Task 3 copy와 정합).

- [ ] **Step 2: Type check & lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint src/app/\(dashboard\)/strategies/\[id\]/edit/_components/tab-code.tsx`

- [ ] **Step 3: Visual smoke — Edit 코드 탭**

Run dev server, open existing MA Crossover strategy → `/strategies/[id]/edit?tab=code`. Verify:
- 페이지 렌더 직후 "파싱 중..." indicator 잠깐 노출 → 파싱 결과 즉시 표시.
- ⌘+Enter 필요 없음.
- "감지된 함수" 섹션에 `ta.ema`/`strategy.entry` 등 badge 노출.

신규 전략 (빈 pine_source)의 경우 빈 패널 + "⌘+Enter로 첫 파싱을 실행하세요" CTA (Task 3과 정합).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/strategies/\[id\]/edit/_components/tab-code.tsx
git commit -m "fix(strategy/fe): auto-parse on TabCode mount — Sprint 7b ISSUE-003"
```

---

## Task 5: FE — TabParse 풍부화 (ISSUE-004, 4-섹션 구조)

**Files:**
- Modify: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx` (전면 교체)

- [ ] **Step 1: 전면 재작성**

Modify `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-parse.tsx`. 마운트 시 `useParseStrategy` mutation을 1회 실행. 섹션 순서: (1) 에러 → (2) 경고 → (3) 감지 지표/전략 콜 → (4) 메타. 저장 시점 `strategy.parse_errors`도 "저장 시점" 라벨과 함께 같은 에러 섹션에 노출.

Full replacement:

```tsx
"use client";

// Sprint 7c T5 + Sprint 7b ISSUE-004: 파싱 결과 탭.
// 섹션 순서: (1) 에러 → (2) 경고 → (3) 감지 지표/전략 콜 → (4) 메타.
// 실시간 스냅샷은 useParseStrategy 마운트 호출. 저장 스냅샷은 strategy.parse_errors.

import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useParseStrategy } from "@/features/strategy/hooks";
import type { ParseError, StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

function groupFunctions(fns: readonly string[]): {
  indicators: string[];
  strategies: string[];
  others: string[];
} {
  const indicators: string[] = [];
  const strategies: string[] = [];
  const others: string[] = [];
  for (const fn of fns) {
    if (fn.startsWith("ta.")) indicators.push(fn);
    else if (fn.startsWith("strategy.") || fn === "strategy") strategies.push(fn);
    else others.push(fn);
  }
  return { indicators, strategies, others };
}

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const parse = useParseStrategy();
  const mountedForId = useRef<string | null>(null);

  useEffect(() => {
    if (mountedForId.current === strategy.id) return;
    mountedForId.current = strategy.id;
    if (strategy.pine_source.trim().length > 0) {
      parse.mutate(strategy.pine_source);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy.id, strategy.pine_source]);

  const live = parse.data;
  const meta = PARSE_STATUS_META[live?.status ?? strategy.parse_status];
  const liveErrors = live?.errors ?? [];
  const snapshotErrors = strategy.parse_errors ?? [];

  const warnings = live?.warnings ?? [];
  const functions = live?.functions_used ?? [];
  const { indicators, strategies, others } = groupFunctions(functions);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Badge variant="outline" data-tone={meta.tone}>
            {meta.label}
          </Badge>
          <Badge variant="secondary">
            Pine {live?.pine_version ?? strategy.pine_version}
          </Badge>
          {parse.isPending && (
            <span className="text-xs text-[color:var(--text-muted)]">파싱 중...</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* (1) 에러 섹션 */}
        {(liveErrors.length > 0 || snapshotErrors.length > 0) && (
          <section>
            <h3 className="text-sm font-bold text-[color:var(--destructive)]">
              에러
            </h3>
            {liveErrors.length > 0 && (
              <ErrorList
                label="현재 코드"
                errors={liveErrors.map((e) => ({
                  code: e.code,
                  message: e.message,
                  line: e.line,
                }))}
              />
            )}
            {snapshotErrors.length > 0 && (
              <ErrorList
                label="저장 시점"
                errors={snapshotErrors.map((e) => ({
                  code: String((e as { code?: unknown }).code ?? ""),
                  message: String((e as { message?: unknown }).message ?? JSON.stringify(e)),
                  line:
                    typeof (e as { line?: unknown }).line === "number"
                      ? ((e as { line: number }).line)
                      : null,
                }))}
              />
            )}
          </section>
        )}

        {/* (2) 경고 섹션 */}
        {warnings.length > 0 && (
          <section>
            <h3 className="text-sm font-bold text-[color:var(--text-secondary)]">
              경고 ({warnings.length})
            </h3>
            <ul className="mt-2 space-y-1 text-xs text-[color:var(--text-secondary)]">
              {warnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          </section>
        )}

        {/* (3) 감지 지표 / 전략 콜 섹션 */}
        {functions.length > 0 && (
          <section>
            <h3 className="text-sm font-bold">감지된 함수 ({functions.length})</h3>
            <div className="mt-2 space-y-2">
              {indicators.length > 0 && (
                <DetectedGroup label="지표" items={indicators} />
              )}
              {strategies.length > 0 && (
                <DetectedGroup label="전략 콜" items={strategies} />
              )}
              {others.length > 0 && <DetectedGroup label="기타" items={others} />}
            </div>
          </section>
        )}

        {/* Progress/Loading 상태 안내 */}
        {parse.isPending && !live && (
          <p className="text-xs text-[color:var(--text-muted)]">
            저장된 코드를 파싱 중입니다...
          </p>
        )}

        {/* (4) 메타 */}
        <section>
          <dl className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
            <div>
              <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                버전
              </dt>
              <dd className="mt-1 font-mono">
                Pine {live?.pine_version ?? strategy.pine_version}
              </dd>
            </div>
            <div>
              <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                아카이브 상태
              </dt>
              <dd className="mt-1">{strategy.is_archived ? "보관됨" : "활성"}</dd>
            </div>
            {live && (
              <>
                <div>
                  <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                    진입 신호
                  </dt>
                  <dd className="mt-1 font-mono">{live.entry_count}</dd>
                </div>
                <div>
                  <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                    청산 신호
                  </dt>
                  <dd className="mt-1 font-mono">{live.exit_count}</dd>
                </div>
              </>
            )}
          </dl>
        </section>

        <p className="text-xs text-[color:var(--text-muted)]">
          ※ '현재 코드' 섹션은 마운트 시 자동 파싱 결과. '저장 시점'은 최근 저장에서 DB에 기록된 스냅샷입니다.
        </p>
      </CardContent>
    </Card>
  );
}

function ErrorList({
  label,
  errors,
}: {
  label: string;
  errors: readonly ParseError[];
}) {
  return (
    <div className="mt-2">
      <p className="text-[0.65rem] text-[color:var(--text-muted)]">{label}</p>
      <ul className="mt-1 space-y-1 text-xs">
        {errors.map((e, i) => (
          <li
            key={i}
            className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 font-mono"
          >
            {e.line !== null && <span className="mr-1">L{e.line}:</span>}
            <span className="mr-2 text-[color:var(--destructive)]">[{e.code}]</span>
            {e.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DetectedGroup({
  label,
  items,
}: {
  label: string;
  items: readonly string[];
}) {
  return (
    <div>
      <p className="text-[0.65rem] text-[color:var(--text-muted)]">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {items.map((fn) => (
          <Badge key={fn} variant="outline" className="font-mono text-[0.65rem]">
            {fn}
          </Badge>
        ))}
      </div>
    </div>
  );
}
```

Verifications baked into implementation:
- `strategy.parse_errors`는 `Array<Record<string, unknown>>` 타입이라 좁히기 필요 — `e as { code?: unknown }` 가드로 처리.
- `ParseError` 타입을 schemas.ts에서 re-use (`import type { ParseError }`).
- 빈 전략 (pine_source 비어 있음)의 경우 live는 undefined, snapshot errors 없음 → 메타 섹션만 노출, 섹션 1~3은 자동 숨김.

- [ ] **Step 2: Type check & lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint src/app/\(dashboard\)/strategies/\[id\]/edit/_components/tab-parse.tsx`

- [ ] **Step 3: Visual smoke — Edit 파싱 결과 탭**

Dev server → 기존 MA Crossover strategy → `/strategies/[id]/edit?tab=parse`. Verify:
- 섹션 순서: 에러 → 경고 → 감지된 함수 → 메타.
- 에러 없는 OK 전략은 "경고 → 감지 → 메타" 3섹션만 노출.
- 감지된 함수 섹션에 `ta.ema` / `strategy.entry` 등 기대 목록.
- 메타 섹션에 버전, 아카이브, 진입/청산 수.
- 저장된 parse_errors가 있으면 "저장 시점" 라벨로 별도 표시 (현재 코드와 구분).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/strategies/\[id\]/edit/_components/tab-parse.tsx
git commit -m "feat(strategy/fe): enrich TabParse with 4-section layout — Sprint 7b ISSUE-004"
```

---

## Task 6: 회귀 테스트 & 크로스 브라우저 smoke

**Files:** 없음 (verification only)

- [ ] **Step 1: BE 전체 회귀**

Run:
```bash
cd backend && pytest -v && ruff check . && mypy src/
```
Expected: 524+ 기존 tests + 2 신규 (Task 1) 전부 green. `_parse` 튜플 arity 변경으로 인한 collection error 0건.

- [ ] **Step 2: FE 전체 회귀**

Run:
```bash
cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test
```
Expected: zero TS errors, zero lint errors, 기존 vitest 전부 pass + 2 신규 (Task 2).

- [ ] **Step 3: 로컬 smoke 시나리오 2종**

Dev server: `docker compose up -d && cd frontend && pnpm dev` + `cd backend && uvicorn src.main:app --reload`.

**Case A — 기존 저장 전략 (MA Crossover 시드):**
1. `/strategies` → MA Crossover 선택 → `/strategies/[id]/edit`.
2. 코드 탭 진입 즉시 우측 패널에 파싱 결과 (OK 배지 + functions_used badges) 자동 노출. ⌘+Enter 입력 없음.
3. 파싱 결과 탭 클릭 → 감지된 함수 + 메타 2섹션 (에러/경고 없음). 저장 시점 에러 없음 확인.

**Case B — 신규 전략 wizard 직후:**
1. `/strategies/new` → Step 1 (메타) → Step 2 (method) → Step 3 (code)에서 비어있는 에디터 유지 → 저장.
2. `/strategies/[id]/edit?tab=code` 진입 → pine_source 빈 문자열이므로 마운트 자동 파싱 skip → 우측 패널에 "⌘+Enter로 첫 파싱을 실행하세요" CTA.
3. 파싱 결과 탭 클릭 → 섹션 1~3 전부 숨김, 메타만 표시.
4. 코드 탭으로 돌아가 Pine 코드 입력 → ⌘+Enter → 실시간 파싱 동작 확인.

**Case C — unsupported 함수 포함 전략:**
1. 임시로 `ta.macd(close, 12, 26, 9)` 같은 미지원 함수 포함한 전략 생성 → 저장.
2. Edit 파싱 결과 탭에 "미지원" 배지 + 에러 섹션 (L? [function] function not supported: ta.macd).
3. 감지된 함수 섹션에 `ta.ema` 등 지원 함수만 일부 노출 (parser가 validate_functions 단계에서 throw하면 functions_used는 빈 배열일 수 있음 — 이 경우 섹션 자동 숨김, 정상).

- [ ] **Step 4: 반응형 smoke (≥1024px 깨지지 않음 검증)**

브라우저 dev tools로 1024 / 1280 / 1440 폭에서 Edit 페이지 3탭 전부 확인. 그리드 붕괴 없음. 모바일(375px)은 본 sprint scope 밖이나 `grid-cols-1 md:grid-cols-2` 패턴 유지로 가로 스크롤 없음.

- [ ] **Step 5: 회귀 없음 확인 — `/qa` Quick tier 로컬 재측정 (선택)**

필요 시 `.gstack/qa-reports/` 에 2026-04-17b 리포트 생성. ISSUE-003/004가 FIXED 상태로 기록되는지 확인. (이번 task에서는 선택적 — 시간 타이트 시 skip하고 수동 smoke로 대체.)

- [ ] **Step 6: 회귀 test commit (모든 task가 green 이면 생략 가능)**

회귀 가드에서 발견된 버그를 수정했다면 해당 fix를 commit. 모두 green이면 no-op.

---

## Task 7: Docs 동기화

**Files:**
- Modify: `docs/TODO.md`

- [ ] **Step 1: /qa findings 섹션 업데이트**

`docs/TODO.md`의 `/qa Quick tier findings (2026-04-17 ...)` 섹션에 다음 표기 추가:

```markdown
- ISSUE-003 Edit 코드 탭 우측 패널 misleading empty state — ✅ FIXED (Sprint 7b, TabCode 마운트 자동 파싱)
- ISSUE-004 파싱 결과 탭 정보량 부족 — ✅ FIXED (Sprint 7b, 4-섹션 구조 + BE ParsePreviewResponse.functions_used 노출)
```

- [ ] **Step 2: Sprint 7b 완료 기록**

`docs/TODO.md` Sprint 7 섹션에 Sprint 7b 완료 항목 추가:

```markdown
### Sprint 7b Edit UX 풍부화 ✅ 완료 (YYYY-MM-DD, PR #N)
- T1: BE ParsePreviewResponse.functions_used 노출 (schema 1필드, migration 없음)
- T2-T3: FE Zod schema + ParsePreviewPanel 감지 함수 섹션 + 빈 상태 copy 수정
- T4: TabCode 마운트 자동 파싱 (ISSUE-003)
- T5: TabParse 4-섹션 구조 (에러 → 경고 → 감지 → 메타) (ISSUE-004)
- 회귀: BE 526+ / FE tsc·lint·vitest 전부 green
```

- [ ] **Step 3: `## 현재 컨텍스트` 마지막 Sprint 기록 갱신 (CLAUDE.md)**

`.claude/CLAUDE.md`의 `### 현재 작업` 목록 끝에 Sprint 7b 추가:

```markdown
- Sprint 7b Edit UX 풍부화 ✅ 완료 (YYYY-MM-DD, PR #N) — TabCode 마운트 자동 파싱 + TabParse 4-섹션 + BE functions_used 노출 (pure FE+schema 확장)
- **다음:** Sprint 8a (OKX 멀티 거래소 + Trading Sessions) → Sprint 8b (Binance mainnet 실거래 + Kill Switch capital_base 동적 바인딩)
```

- [ ] **Step 4: Commit**

```bash
git add docs/TODO.md .claude/CLAUDE.md
git commit -m "docs(sprint7b): mark ISSUE-003/004 fixed + sprint completion log"
```

---

## Task 8: PR 준비 (사용자 승인 필요)

- [ ] **Step 1: 브랜치 상태 확인**

```bash
git status
git log --oneline origin/main..HEAD
```
Expected: 7개 commit (T1~T7 + 가능한 fix commit들) 모두 local.

- [ ] **Step 2: 사용자에게 push 승인 요청**

CLAUDE.md Git Safety Protocol에 따라 **"Sprint 7b 구현 완료, PR을 위해 feat/sprint7b-edit-parse-ux 브랜치로 push할까요?"** 질문하고 승인 대기.

- [ ] **Step 3: 승인 후 push & PR**

```bash
git checkout -b feat/sprint7b-edit-parse-ux   # 또는 이미 브랜치면 skip
git push -u origin feat/sprint7b-edit-parse-ux
```

Then:
```bash
gh pr create --title "feat: Sprint 7b — Edit page Pine iteration UX (ISSUE-003 + ISSUE-004)" --body "$(cat <<'EOF'
## Summary
- ISSUE-003: TabCode mounts now auto-parse `strategy.pine_source`, removing the misleading empty-state placeholder.
- ISSUE-004: TabParse rewritten with 4-section layout (errors → warnings → detected functions → meta). Errors show both live snapshot and DB-saved snapshot with distinct labels.
- BE: `ParsePreviewResponse` gains `functions_used: list[str]` (Pydantic + Zod schema field only; no Alembic migration, no Strategy model change).

## Test plan
- [ ] `cd backend && pytest -v` 전체 green
- [ ] `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test` 전체 green
- [ ] Case A: 기존 MA Crossover 전략 열기 — 코드 탭 즉시 파싱 + 파싱 결과 탭 functions_used 렌더
- [ ] Case B: 신규 빈 전략 — "⌘+Enter로 첫 파싱" CTA
- [ ] Case C: Unsupported 함수 — 에러 섹션 + 미지원 배지
- [ ] 1024/1280/1440 폭 반응형 미붕괴

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Open Questions (Deferred)

- **Q-3 (해소됨):** 신규 전략(빈 pine_source) 우측 패널 copy는 "⌘+Enter로 첫 파싱을 실행하세요" (Task 3에 적용).
- **미결정:** 저장 시점 parse_metadata persist는 Sprint 7d+ 로 defer. Approach B의 delta(Strategy 모델에 JSONB parse_metadata 추가 + Alembic migration)는 별도 spec으로 분리.
- **미결정:** live debounce reparsing (Approach B 오리지널의 일부)도 Sprint 7d+ 로 defer. 이번 wedge에서는 ⌘+Enter 명시적 재파싱 + 마운트 자동 1회로 충분.

---

## Rollback Plan

본 Sprint는 Strategy DB schema 불변 + router 불변이므로 rollback은 코드 revert 1회로 완결.

```bash
git revert <T1_SHA>..<T7_SHA>
cd backend && pytest
cd frontend && pnpm tsc --noEmit && pnpm test
```

이전 동작(빈 상태 문구 + 메타 2줄)이 즉시 복귀한다. `functions_used` 필드가 이미 wire 위에 있어도 FE가 파싱하지 않으면 무해하므로 부분 rollback도 안전.

---

## Success Criteria Check (design doc)

- **C-1 (코드 탭 즉시 파싱 결과 노출):** ✅ Task 4 — 마운트 시 자동 `parse.mutate()` → 첫 paint에 "파싱 중..." → 결과 렌더.
- **C-2 (파싱 결과 탭 warnings/errors/detected/unsupported 노출):** ✅ Task 5 + T1 (BE functions_used).
- **C-3 (tsc/lint/test green):** ✅ Task 6 Step 1~2.
- **C-4 (기존/신규 전략 2-case 회귀):** ✅ Task 6 Step 3 Case A + B + C.
- **C-5 (Before ⌘+Enter 1회 → After 0):** ✅ Task 4 마운트 자동 파싱.
