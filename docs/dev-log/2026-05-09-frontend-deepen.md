# /deepen-modules audit 3/3 — frontend dashboard-shell + cross-page — 2026-05-09

> **Outcome:** Frontend cross-page 컴포넌트 audit 완료. BL-206 1건 신규 등재 (Skeleton + EmptyState 묶음). **§7.5 검증 누적 2/3 → 3/3 정식 승격 완료** + LESSON-063 신규 등재.

## Context

`/deepen-modules` 3번째 invoke = **3/3 검증 완료**. Sprint 46 같은 세션 안 1 스킬 + 3 도메인 audit pilot 종결.

**Frontend audit 의 가치:** Sprint 43-46 prototype-grade 정합 + dashboard-shell 4 컴포넌트 분리 후 cross-page locality 검증. dogfood 직결 영역.

## Phase 1 결과 — Module Inventory & Depth Mapping

**Scope:** `frontend/src/components/**` (~30 파일 / ~2200 LOC, sweet spot 정확 안)

| 모듈                                         | LOC                | 분류                  | 비고                                   |
| -------------------------------------------- | ------------------ | --------------------- | -------------------------------------- |
| **layout/dashboard-shell.tsx** + 3 sub       | 60+79+102+51 = 292 | ✅ **Reference Deep** | Sprint 45 분리, codex G.4 GATE PASS    |
| **ui/dropdown-menu.tsx**                     | 270                | 🟢 Deep               | shadcn 표준                            |
| **ui/select.tsx + select-with-display-name** | 363                | 🟢 Deep               | composite                              |
| **ui/form.tsx**                              | 168                | 🟢 Deep               | RHF wrapper                            |
| **ui/dialog + sheet**                        | 295                | 🟢 Deep               | shadcn 표준                            |
| **charts/trading-chart.tsx**                 | 303                | 🟢 Deep               | lightweight-charts 통합                |
| **providers/query-provider** + app-providers | 68                 | 🟢 Deep               | 깔끔 분리                              |
| **components/skeleton.tsx**                  | small              | 🔴 **Shallow + 우회** | 3 import 만, 5+ inline duplicate       |
| **components/empty-state.tsx**               | small              | 🟡 Mixed              | 2 import + 1 fork (StrategyEmptyState) |
| **components/form-error-inline.tsx**         | small              | 🟡 의심               | 2 import 만                            |
| **components/shortcut-help-dialog.tsx**      | small              | 🟡 의심               | 2 import 만                            |

**Reference Deep ✅** = `dashboard-shell` (Sprint 45 분리 후 codex G.4 GATE PASS), `ui/*` shadcn primitives (보존 권장).

## Phase 2 결과 — Locality & Coupling Analysis

| 패턴                                            | 심각도  | Touch 파일                                                                                                                     | Risk                                                           |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| **A. Skeleton primitive 우회**                  | 🔴 높   | strategies/loading.tsx (5+ 줄) + backtest-detail-view:238 + backtest-list:289 + error-illustration:35 + error-recovery-box:325 | 디자인 system drift. dark mode/theme 변경 시 5+ 파일 동시 수정 |
| **B. EmptyState 로컬 fork**                     | 🟡 중   | components/empty-state + strategies/\_components/strategy-empty-state                                                          | 의도된 도메인 특화? duplicate? 명확화 필요                     |
| **C. dashboard-shell ✅ Reference Deep**        | 🟢 —    | Sprint 45 분리 완료                                                                                                            | 영상 칭찬할 패턴                                               |
| **D. Page-level useEffect 24 file (Zustand 0)** | 🟡 의심 | 24 페이지                                                                                                                      | LESSON-004 후속, 본 scope 외                                   |

**Co-change top:** dashboard-shell.tsx (7회) — Sprint 45 분리 자체. UI atoms 모두 2-3회 안정.

## Phase 3 결정 로그 — Grilling Session

| 후보                                | 별점  | 결정                       | 사유                                     |
| ----------------------------------- | ----- | -------------------------- | ---------------------------------------- |
| **A. Skeleton primitive 우회 통합** | ★★★★☆ | ✅ 승인                    | 명백한 design drift 1줄 = silent         |
| **B. EmptyState 로컬 fork 정합**    | ★★★☆☆ | ✅ 승인                    | duplicate vs 의도 명확화                 |
| **C. A+B 묶음 cleanup**             | ★★★☆☆ | ✅ 승인 (단일 BL-206 으로) | 동일 sprint 안 디자인 system polish 묶음 |

**Sprint 47 권고:** pine_v2 BL-200/201 + trading BL-202~205 + **frontend BL-206** = **7 BL 대형 deepening sprint** 확장.

## Phase 4 등재

### `docs/REFACTORING-BACKLOG.md` 신규 BL 1건 (P2 섹션)

- **BL-206** frontend cross-page primitive cleanup (★★★★☆/★★★☆☆ 묶음, S-M 3-4h)
  - **현 상태:** components/skeleton.tsx 가 있으나 5+ inline duplicate hardcode
  - **목표 인터페이스:**
    ```tsx
    // frontend/src/components/skeleton.tsx
    export function Skeleton({
      variant = "default",
      className,
    }: {
      variant?: "default" | "row" | "chip" | "card" | "kpi";
      className?: string;
    }) {
      const variantCls = {
        default: "h-4 w-full",
        row: "h-12",
        chip: "h-9 w-24",
        card: "h-36 rounded-[var(--radius-lg)]",
        kpi: "h-7 w-32",
      }[variant];
      return (
        <div
          className={cn(
            "animate-pulse rounded bg-[color:var(--bg-alt)]",
            variantCls,
            className,
          )}
        />
      );
    }
    ```
  - **EmptyState fork 정합:**
    ```tsx
    // 옵션 A: prop 확장 후 fork 제거
    <EmptyState
      illustration="strategy" // 신규 prop
      title="No strategies yet"
      cta={{ label: "Create", href: "/strategies/new" }}
    />
    ```
  - **영향 파일:** components/skeleton.tsx 확장 + 5+ 페이지 hardcode 1:1 치환 + components/empty-state.tsx prop 확장 + strategy-empty-state.tsx 제거
  - **Risk:** 🟢 낮 (1:1 치환 + frontend 603 PASS test 안전망)

### LESSON-063 정식 등재 (`.ai/project/lessons.md`)

본 audit 가 **§7.5 의 3/3 검증 완료**를 의미하므로, 영구 LESSON 으로 정식 승격.

```
LESSON-063 (deepen-modules pilot 3-domain, 2026-05-09): AI 가 누적 작성한 코드는
도메인을 가로지르는 3 가지 패턴을 누적시킨다 — (1) **Triple SSOT** (같은 list/enum
이 N 파일에 정의, silent failure source: pine_v2 STDLIB / trading OrderStatus
Literal), (2) **Cross-module dispatcher 분산** (같은 enum 으로 분기하는 if/match
가 N 파일에 흩어짐: pine_v2 Track S/A/M / trading Provider selection), (3)
**Cross-page primitive 우회** (디자인 system primitive 가 있는데도 hardcode
inline duplicate: frontend Skeleton 5+ 위치). 모두 *silent design drift* 또는
*silent failure* 으로 이어짐. 신규 도메인 신설 직후 /deepen-modules 1회 호출이
사전 차단 mechanism. 검증 누적: pine_v2 (1/3) + trading (2/3) + frontend (3/3),
Sprint 46 same-session pilot.
```

## §7.5 정식 승격 (3/3 완료)

`.ai/common/global.md` §7.5 권장 → **권장 유지** (다음 LESSON-063 가 정식 영구 규칙으로 자리잡음). 현 phrasing "권장" 은 그대로 두되, 검증 누적 = **3/3 완료** 로 갱신.

> 의무화 vs 권장 = 사용자 결정. 본 LESSON-063 등재 후 다음 신규 도메인 작성 시 자동 호출 패턴 확립되는지 1-2 sprint 관찰 후 의무 승격 여부 재평가.

## Sprint 47 최종 권고 (7 BL 대형 deepening)

**확장된 Slice 순서:**

1. BL-205 OrderStatus Literal triple (1-2h, XS) — 패턴 가장 작음, hot start
2. BL-204 repository.py 분할 (2-3h, S) — 단순 분할
3. BL-200 STDLIB triple SSOT (4-6h, M) — pine_v2 silent failure 차단
4. **BL-206 frontend cross-page primitive cleanup (3-4h, S-M)** ← 신규
5. BL-203 service.py 분할 (4-5h, S-M) — repository 분할 후 자연스러움
6. BL-202 Provider Registry/Factory (6-9h, M) — mainnet 진입 전 가장 큰 architectural
7. BL-201 Track S/A/M Strategy pattern (9-12h, M-L) — pine_v2 SSOT 핵심

**Total: 29-41h** (4-6 worker 자율 병렬 시 wall-clock 8-13h)

## Verification (스킬 작동 + 3/3 검증)

✅ `/deepen-modules` Skill 도구 invoke 3회 모두 frontmatter 매칭 + Phase 1-4 자동 진행
✅ Iron Law 준수: 1회 = 1 도메인 (pine_v2 / trading / frontend 분리 invoke)
✅ STOP conditions 작동 검증: test coverage <70% 트리거 안 됨 (모두 안전)
✅ Phase 3 사용자 승인 전 코드 수정 X (BL 등재만)
✅ dev-log 3 파일 작성 (pilot + trading + frontend)
✅ BL 7건 신규 등재 (BL-200~206)
✅ LESSON-063 정식 등재

## 다음 audit 권고 (3/3 후 자연 cadence)

- **신규 도메인 신설 직후** (preventive) — §7.5 자동 적용
- **사용자 자각 (이거 또 고친 적 있는데...)** — reactive 호출
- **PR 30+ 누적 후** — quarterly cadence

다음 후보 (필요 시):

- backend Backtest + Optimizer + StressTest (~40 file)
- backend Strategy + Pine SSOT 외부 인터페이스 (~30 file)
- frontend Page-level data fetching pattern (LESSON-004 후속, useEffect 24 file)
- frontend ui/\* shadcn primitive 확장 (보존 위주)
