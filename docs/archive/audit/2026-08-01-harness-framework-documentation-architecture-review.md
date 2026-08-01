# Harness Framework 기반 문서·작업 하네스 구조 검토

> **일자:** 2026-08-01  
> **범위:** `jha0313/harness_framework` 원본과 QuantBridge 현재 문서·루트 파일 구조의 대조. 구현 변경 제안이 아니라, 다음 문서 정리 스프린트의 의사결정 입력이다.  
> **판정:** Harness의 **문서 최소화 원칙과 작업 단위 계약**은 채택 가치가 있다. 반면 자동 실행기·`phases/`·전문서 프롬프트 주입은 QuantBridge에 그대로 가져오지 않는다.

---

## 1. 조사 근거

### 외부 1차 소스 — Harness Framework

- [저장소 트리](https://github.com/jha0313/harness_framework) — main은 `CLAUDE.md`, `docs/` 4개, `.claude/commands/` 2개, `scripts/execute.py`와 그 테스트 1개로 구성된 작은 템플릿 저장소다.
- [문서 4종 트리](https://github.com/jha0313/harness_framework/tree/main/docs) — PRD, Architecture, ADR, UI Guide를 각각 한 파일로 둔다.
- [`/harness` 명세](https://raw.githubusercontent.com/jha0313/harness_framework/main/.claude/commands/harness.md) — step을 작은 범위·자기완결 입력·시그니처 수준 지시·실행 가능한 AC·명시적 금지사항으로 작성하게 한다. `phases/index.json`과 각 phase의 `index.json`에 `pending/completed/error/blocked` 상태와 사유·요약을 기록하도록 정의한다.
- [`/review` 체크리스트](https://raw.githubusercontent.com/jha0313/harness_framework/main/.claude/commands/review.md) — architecture, ADR, test, critical rule, build라는 5개 고정 축으로 결과표를 낸다.
- [실행기 원본](https://raw.githubusercontent.com/jha0313/harness_framework/main/scripts/execute.py) — 완료 step 요약을 다음 step에 누적하고, 최대 3회 재시도하며, status/시간/원시 출력 JSON을 남긴 뒤 코드와 메타데이터를 분리 커밋한다.
- [실행기 테스트](https://raw.githubusercontent.com/jha0313/harness_framework/main/scripts/test_execute.py) 및 [강화 커밋](https://github.com/jha0313/harness_framework/commit/a47cc27e2f242b3f222de2bb33bb1e19f9878f65) — 상태 전이·재시도·컨텍스트 생성·커밋을 단위 테스트로 고정했다.

### 로컬 1차 소스 — QuantBridge

- 문서 지도와 새 세션의 3종 입력은 [`docs/README.md`](../../README.md), [`AGENTS.md`](../../../AGENTS.md), [`CONTEXT.md`](../../../CONTEXT.md), [`docs/status.md`](../../status.md)에 이미 명시돼 있다.
- 기존 작업 문서의 승격/강등/삭제 종결 규칙은 [`docs/guides/sprint-template.md` §9](../../guides/sprint-template.md)에 있다.
- BL 상태의 기계 검증은 [`scripts/bl-audit.sh`](../../../scripts/bl-audit.sh)와 [`scripts/bl-audit-test.sh`](../../../scripts/bl-audit-test.sh)가 담당한다.
- 제품의 현재 비전은 [`docs/reference/project/vision.md`](../../reference/project/vision.md), 초기 PRD의 historical 선언은 [`2026-04-14-original-prd.md`](../product/2026-04-14-original-prd.md) 서두, 디자인 구현 SSOT는 [`DESIGN.md`](../../../DESIGN.md) 서두에 있다.

---

## 2. 확인된 사실

### 2.1 Harness가 실제로 제공하는 것

| 축 | 구현 방식 | 가져갈 원칙 |
| --- | --- | --- |
| 문서 입력 | PRD/Architecture/ADR/UI Guide 4개만 프로젝트 문맥으로 사용 | **읽는 사람이 답할 질문마다 canonical 문서는 하나**여야 한다. |
| 작업 분해 | Step마다 읽을 파일·정확한 작업·AC 명령·금지사항을 독립 기록 | 작업 지시는 대화 기억이 아닌 파일만 읽어도 재개돼야 한다. |
| 진행 상태 | JSON manifest의 제한된 상태와 timestamp·사유·한 줄 summary | 상태는 서술형 회고와 분리하고, 재개 가능한 최소 필드로 표현한다. |
| 검증 | 각 step의 shell AC + review 5축 표 | “완료”에는 실행 가능한 증거가 붙어야 한다. |
| 실패 처리 | 실패 원인을 다음 재시도 prompt에 주입하고 3회 후 error로 고정 | 실패를 조용히 덮지 말고, 원인과 다음 행동을 상태로 남긴다. |

**성숙도 경계.** 이 저장소는 main 기준 6개 커밋의 템플릿이며, 실제 제품을 여러 sprint에 걸쳐 운영한 증거는 제공하지 않는다. 따라서 “4개 문서면 항상 충분하다”는 일반 법칙으로 읽으면 안 된다. QuantBridge처럼 금융 실행·운영·규제 경계가 있는 시스템은 도메인 계약과 runbook을 더 보존해야 한다.

### 2.2 그대로 복제하면 안 되는 부분

| Harness 구현 | QuantBridge와의 충돌/위험 | 결정 |
| --- | --- | --- |
| `execute.py`가 root `docs/*.md` 전체를 매 step prompt에 주입 | QuantBridge는 `status.md` 1,245행 + `backlog.md` 6,463행이다. 매 step에 넣으면 필요한 입력보다 잡음이 훨씬 커진다. | **미채택.** step마다 읽을 파일을 명시적으로 고른다. |
| `claude -p --dangerously-skip-permissions` | QuantBridge의 사용자 승인·Git Safety Protocol을 우회한다. | **미채택.** |
| `--push`가 `git push`를 수행 | “사용자 승인 없는 push 금지” Golden Rule과 직접 충돌한다. | **미채택.** |
| `npm run build && npm test`를 AC 예시/Stop hook으로 고정 | FE·BE·DB·Celery가 분리된 QuantBridge의 실제 gate와 맞지 않는다. | **미채택.** 각 작업이 `gates-and-traps.md`에서 필요한 gate만 선언한다. |
| phase/step JSON을 새 최상위 `phases/`에 생성 | 현재 규칙은 active sprint 진입점을 `docs/status.md` 하나로 고정한다. 두 번째 진입점은 드리프트를 만든다. | **별도 도입하지 않음.** 상태 필드는 현 `status.md`의 다음 sprint 블록에 흡수한다. |

---

## 3. QuantBridge 현재 구조의 병목

### 3.1 물량은 `docs/` 최상위 파일 수보다 ledger와 cold history에 있다

2026-08-01 tracked 파일 기준 `docs/`는 587개(Markdown 381개)다. 분포는 archive 337개, dev-log 113개, reference 100개, decisions 20개, guides 9개, reports 4개, docs 최상위 4개다. 즉 `docs/` 루트는 이미 작지만:

- [`docs/status.md`](../../status.md)는 1,245행이다. 지금 할 일 외의 최근 sprint 서술이 계속 남아 새 세션 입력이 비대해졌다.
- [`docs/backlog.md`](../../backlog.md)는 6,463행이다. 활성·해결·반증·근거가 하나의 ledger에 누적돼 “우선순위 판단”과 “역사 추적”이 섞였다.
- `archive/` 337개와 `dev-log/` 113개는 cold history다. 이것을 기본 탐색 표면으로 노출하면 파일 수가 곧 인지 부하다. 반대로 삭제하면 금융 실행의 판단 근거를 잃는다.

따라서 목표는 **파일을 일괄 삭제하는 것**이 아니라, live 읽기 표면을 3~5개로 제한하고 history를 명시적으로 cold path로 만드는 것이다.

### 3.2 루트에는 실제 중복과 역사 문서가 남아 있다

현재 tracked 루트 파일은 14개다. 구성 파일(`.env.example`, `.gitignore`, `.editorconfig`, `Makefile`, `docker-compose*.yml`, `package.json`, `skills-lock.json`, `.worktreeinclude`, `NOTICE`)은 루트에 두는 것이 자연스럽다. 줄여야 할 후보는 프로젝트 설명 문서다.

| 파일 | 확인된 상태 | 권고 |
| --- | --- | --- |
| `README.md` | 외부/새 개발자 진입점이나, 초반 sprint 표와 오래된 설명이 섞여 있다. | **유지·축소.** 제품 한 줄, 빠른 시작, 최신 docs 지도만 둔다. history는 링크만 둔다. |
| `AGENTS.md` | 새 AI 세션 3종 중 하나이며 Golden Rule·운영 위험을 제공한다. | **유지.** stable orientation만 둔 현재 방향을 지킨다. |
| `CONTEXT.md` | 도메인 용어·관계 SSOT이고 새 AI 세션 3종 중 하나다. | **유지.** 현재 크기(144행)는 합리적이다. |
| `CLAUDE.md` | `AGENTS.md`와 현재 133행이 byte-for-byte 동일하다. | **내용 병합.** `AGENTS.md`를 정본으로 하고, Claude 호환이 필요하면 `CLAUDE.md`는 symlink 또는 “먼저 AGENTS.md를 읽으라”는 짧은 redirect만 유지한다. |
| `DESIGN.md` | 748행이며 구현 코드·프로토타입이 직접 인용한다. | **루트에서 이동.** `docs/reference/design-system.md`로 옮기되, 코드/문서 링크를 같은 변경에서 일괄 갱신한다. 내용 축약은 별도 결정이다. |
| `QUANTBRIDGE_PRD.md` | 1,724행이며 서두가 스스로 historical snapshot이라고 선언한다. 현재 비전은 `reference/project/vision.md`가 맡고 있다. | **루트에서 퇴역.** `docs/archive/product/2026-04-14-original-prd.md`로 보존하고, `requirements-overview.md` 등에서 이 파일을 현재 detailed SSOT로 가리키는 링크를 현행 정본으로 교체한다. 새 PRD를 다시 쓰는 일은 필요하지 않다. |

이후 루트의 사람이 읽는 프로젝트 문서는 `README.md`, `AGENTS.md`, `CONTEXT.md`와 호환 redirect `CLAUDE.md`뿐이다. 나머지는 실행/배포 구성 파일이다.

---

## 4. 권고 구조 — “작은 live surface, 보존된 evidence”

```text
root/
├── README.md                 # 사람용 시작점·docs 지도 (짧게)
├── AGENTS.md                 # AI/개발 가드레일·3종 입력 규칙 (정본)
├── CONTEXT.md                # 도메인 용어·관계 SSOT
├── CLAUDE.md                 # 선택: AGENTS.md 호환 redirect/symlink
├── Makefile · compose · env example · package metadata … # 실행 구성
└── docs/
    ├── README.md             # 질문 → 정본 문서 지도
    ├── status.md             # 지금의 단 하나의 sprint/작업 계약
    ├── roadmap.md            # 다음 후보와 trigger만
    ├── backlog.md            # 열린 BL의 짧은 ledger, 현 bl-audit 입력
    ├── reference/            # 계속 참인 계약: domain/architecture/operation/product/design/api
    ├── decisions/            # 주소 가능한 ADR, 삭제 대신 Superseded
    ├── dev-log/              # append-only 결정·결과의 history
    └── archive/              # 완료 sprint와 상세 evidence의 cold storage
```

### 4.1 `status.md`에 Harness의 “작업 계약”만 이식

새 최상위 `phases/`나 자동 실행기는 만들지 않는다. `status.md`의 **다음 sprint 블록**을 아래 고정 필드로 제한하면, 기존 단일 진입점과 Harness의 장점을 함께 얻는다.

| 필드 | 의도 | 확인 방법 |
| --- | --- | --- |
| 목표/비목표 | 한 sprint가 해결할 것과 피할 것 | 사람이 1분 안에 scope를 재진술할 수 있는가 |
| 먼저 읽을 파일 | 최소 입력 set | 목록 밖의 문서를 일괄 주입하지 않았는가 |
| 작업 단위 | 1개 단위 = 1개 변경 경계 | 각 단위가 독립적으로 완료/보류될 수 있는가 |
| AC 명령 | 실제 실행할 gate | 명령 exit code와 산출물을 남겼는가 |
| 판정/중단 조건 | PASS, fail, 표본 부족, 사용자 결정 필요 | 0/불충분 표본을 성공으로 쓰지 않았는가 |
| evidence 링크 | dev-log 또는 archive의 결과 | 완료 뒤 `status.md`에 서술을 누적하지 않고 링크로 넘겼는가 |

**권장 예산:** active `status.md`는 다음 sprint 블록 + 직전 결과 링크만 남겨 약 160행 이내로 관리한다. 완료된 narrative·측정 표는 dev-log 또는 sprint archive로 이동한다. 이 예산은 기술적 한계가 아니라, 3종 입력을 실제로 읽을 수 있게 하는 운영 가드다.

### 4.2 `backlog.md`는 “현재 queue”, history는 “증거”로 분리

`scripts/bl-audit.sh`가 이미 `backlog.md`의 `**상태:**`와 `roadmap.md` 체크박스를 검증하므로, BL SSOT 자체를 JSON으로 갈아엎을 이유가 없다. 대신 다음의 내용 수명을 분리한다.

| 남길 위치 | 남기는 내용 | 제거/이동 기준 |
| --- | --- | --- |
| `backlog.md` | 열린 BL의 ID, 상태, 한 줄 영향, trigger, 검증 링크 | 해결/보류가 확정되면 상세 서술을 더 쌓지 않는다. |
| `roadmap.md` | 사용자 가치 순서와 고수준 trigger | BL 원장의 근거표를 복제하지 않는다. |
| `dev-log/` | sprint가 무엇을 왜 결정했고 무엇을 측정했는지 | append-only history다. |
| `archive/sprints/<theme>/` | 재현에 필요한 상세 표·스크립트 출력·중간 설계 | sprint 종료 §9에서 승격/강등/삭제를 선택한다. |

이렇게 하면 BL은 “체크 가능한 열린 문제 목록”으로 다시 읽히고, 상세 반증은 사라지지 않는다. 첫 정리 대상은 이미 Resolved/Deferred인 장문 BL 본문이며, 한 번에 per-BL 파일 수백 개를 만들지 말고 sprint/반기 단위 archive 파일로 묶는다.

### 4.3 `reference/`는 파일 합치기보다 독자 경계를 선명하게 한다

ADR 20개와 API/ERD/상태머신 같은 계약 문서를 하나로 합치는 것은 검색성과 링크 안정성을 해친다. 대신 1차 정리 후 점진적으로 다음 질문별 입구를 두는 것이 맞다.

- `reference/domain/` — domain overview, entities, ERD, state machines, Pine/trading 계약
- `reference/architecture/` — system architecture, data flow, trust layer, conformance
- `reference/operations/` — local setup, gates, env, worktree, CI/CD, runbook/observability
- `reference/product/` — vision, positioning, beta path, 경쟁/phase 자료
- `reference/design/` — 디자인 시스템과 prototype 캐논
- `reference/api/` — endpoints와 요청 계약

이는 **2단계 path 이동**이다. 먼저 active surface와 ledger를 줄인 뒤, 링크/테스트 참조를 자동 검증하며 이동한다. 파일 개수 자체보다 “이 문서를 언제 읽는가”가 분명해지는 효과가 크다.

---

## 5. 안전한 이행 순서와 완료 판정

### 1단계 — 정보 구조를 고정 (문서-only)

1. `README.md`와 `docs/README.md`를 현재 정본 링크만 남기는 지도 역할로 축소한다.
2. `AGENTS.md` 하나를 instruction 정본으로 확정하고 `CLAUDE.md` 중복을 redirect/symlink로 바꾼다.
3. legacy `QUANTBRIDGE_PRD.md`와 design 문서의 **이동 계획 및 모든 참조 목록**을 확정한다. 이 단계에서는 경로 이동을 하지 않는다.

**완료:** 새 세션의 입력은 여전히 `CONTEXT.md + AGENTS.md + docs/status.md` 3개뿐이고, 사람이 `docs/README.md`에서 현재 정본을 찾을 수 있다.

### 2단계 — 루트와 live ledger를 줄임 (작은 원자 변경)

1. `DESIGN.md`를 `reference/design/`으로, legacy PRD를 `archive/product/`으로 옮기고 모든 링크를 같은 PR에서 갱신한다.
2. `status.md`의 완료 narrative를 dev-log/archive로 이관해 live block만 남긴다.
3. backlog의 완료 항목 상세 근거를 sprint/반기 archive로 이관하되 ID·상태·결과 링크는 감사 규칙이 요구하는 위치에 남긴다.

**완료:** 루트의 사람용 정본은 3개(+호환 redirect), `status.md`는 예산 이내, `bl-audit`의 상태 대조는 이전과 동등하게 통과한다.

### 3단계 — 재증식 방지

1. `status.md` template에 작업 계약 6필드를 고정한다.
2. `scripts/bl-audit.sh`의 현 검증을 유지하고, 별도 `docs-audit`가 정말 반복 실패를 보인 뒤에만 추가한다. 첫 규칙은 “새 도구를 만들기 전 기존 `bl-audit`와 sprint §9을 통과시키기”다.
3. 두 sprint 동안 신규 문서가 어느 질문/수명에 속했는지 기록하고, 그 뒤에만 `reference/` path 재편을 시행한다.

**완료:** 스프린트 종료 시 active 문서가 늘지 않고, 새 파일마다 owner·독자·수명이 명확하며, 완료 근거가 실행 명령 또는 링크로 추적된다.

### 이행 중 필수 검증

```bash
scripts/bl-audit.sh
scripts/bl-audit-test.sh
git diff --check
rg -n 'QUANTBRIDGE_PRD\.md|DESIGN\.md|CLAUDE\.md' .
```

경로 이동 PR에는 해당 코드/문서 참조를 모두 갱신했음을 확인하고, 변경한 영역에 해당하는 `docs/reference/gates-and-traps.md`의 gate만 추가 실행한다. Celery/라이브 실행 검증을 문서 구조 변경에 끼워 넣지 않는다.

---

## 6. 최종 제안

1. **Harness를 실행기로 도입하지 말고, 문서 계약으로 도입한다.** QuantBridge에는 이미 더 엄격한 단일 진입점·BL 감사·sprint 종결 규칙이 있다.
2. **루트에서는 legacy PRD와 디자인 시스템만 이동한다.** `AGENTS.md`와 `CONTEXT.md`는 단순화 대상이 아니라 안전한 재개를 위한 최소 입력이다. `CLAUDE.md`는 중복 내용만 제거한다.
3. **문서 수 감축의 첫 KPI는 파일 삭제 수가 아니라 live surface다.** 다음 sprint에 읽어야 할 파일은 3개, 현재 작업 상태는 약 160행, 열린 BL은 짧은 ledger로 제한한다.
4. **과거 증거는 보존하되 기본 경로에서 내린다.** archive/dev-log/ADR을 무리하게 합치거나 삭제하지 않는다.
5. **새 JSON manifest·새 executor·새 최상위 디렉터리는 만들지 않는다.** 기존 `status.md`와 `bl-audit`를 강화하는 것이 가장 작은 변화다.

---

## 변경 이력

- **2026-08-01** — Harness Framework의 README-less template 구조, `/harness`·`/review` 명세, 실행기·테스트·커밋 이력과 QuantBridge의 root/docs inventory를 대조해 작성. 코드 변경 없음.
