# ADR-026: 문서 SSOT — 질문 유형별 정본 분할과 로드 계층화

> **상태:** 확정 (Accepted — 2026-08-06, 사용자 판정)
> ★**§2 의 배치 결정만 [ADR-027](./027-nested-agents-md.md) 로 Superseded (2026-08-07)** — 스택 규칙은
> `.claude/rules/` 가 아니라 `backend/AGENTS.md`·`apps/web/AGENTS.md` 에 둔다(codex 가 읽지 못한다는
> 본 ADR 의 `[가정]` 이 그 배치에서 문제 자체로 사라진다). **§1·§3·§4·§5 는 그대로 유효하다.**
> ★**§1 ④ 의 위치(`docs/reference/` 래퍼)는 [ADR-038](038-docs-top-level-by-question.md) 로 Superseded (2026-08-21)** —
> 정본은 `docs/{architecture,domain,api,development,operations,design}/` 최상위로 올라갔고 `decisions/` 는 `adr/` 가
> 됐다. **수명축은 래퍼가 아니라 `docs/README.md` 의 표가 맡는다.** 7축 자체와 §3·§4·§5 는 그대로 유효하다.
> **일자:** 2026-08-06
> **결정자:** woosung (기안: Claude)
> **출처:** 2026-08-06 조사 3건 — Claude Code 로딩 메커니즘(공식 문서 + CHANGELOG) ·
> SSOT 이론(Diátaxis · ETH Zurich "Evaluating AGENTS.md", ICLR 2026) · 우수 OSS 레포 7종 실물
> **관련:** [`AGENTS.md`](../../AGENTS.md) · [`CONTEXT.md`](../../CONTEXT.md) · `.ai/` (본 ADR 이 해체한다) ·
> [`generator-evaluator-pipeline.md`](../development/workflows/generator-evaluator-pipeline.md)
> **선행 실행(추인 대상):** `docs/archive/`(31M)·dev-log 본문(4M) 삭제 · INDEX.md tombstone 색인화 ·
> backlog RESOLVED 94건 + 링크 240개 강등 · 미승격 교훈 2건(LESSON-066/067) 등재

---

## Context — 중복이 드리프트를 낳았다

규칙 한 건이 **평균 4.5곳**에 산다. 사본은 한 곳만 갱신되고 나머지는 조용히 낡는다.

- **실증 ①** — AGENTS.md 의 「`.ai/rules/*.md` 는 자동 로드되지 않는다(2026-08-02 실측)」는 **지금 거짓**이다.
  `.claude/rules/*.md` 자동 로드는 v2.0.64 부터 공식 지원(설치 2.1.223). 실측은 그때 참이었고,
  **사본이 그때에 얼어붙었다.**
- **실증 ②** — `.ai/common/global.md` §1~§6 은 AGENTS.md·docs 와 중복이고, 살아 있는 인용처는
  §7 이 `generator-evaluator-pipeline.md` 에서 참조되는 **한 곳뿐**이다.
  `.ai/` 의 **58%** 는 이 레포에서 한 번도 쓰인 적 없다.
- **`docs/` 의 89.7% 가 「지금 참」이 아니다** — 끝난 것·왜 그랬는지·거짓으로 밝혀진 것이
  「현재 사실」과 같은 층위에 섞여 있다.

뿌리는 파일 개수가 아니라 **한 파일이 서로 다른 종류의 질문에 동시에 답하려 한 것**이다.

---

## Decision

### 1. SSOT 7축 — 질문 유형마다 정본을 하나만 둔다

① **행위**(지금 무엇을 하는가) = 코드·테스트 · ② **용어·관계** = `CONTEXT.md` ·
③ **실행 계약**(뭘 돌려야 통과인가) = 게이트 스크립트 자신(산문은 파생) ·
④ **함정**(비자명·배치 성질) = `docs/reference/` (Diátaxis reference 규율 — 서술만, 지시 금지) ·
⑤ **근거**(왜 이것이고 왜 저것이 아닌가) = `docs/adr/` (한 ADR = 한 결정, Accepted 불변) ·
⑥ **반증**(시험해서 거짓으로 밝혀진 것) = `docs/lessons.md` ·
⑦ **상태** = `status.md`·`roadmap.md`·`backlog.md` (`bl-audit.sh` 기계 검증)
  > ★**2026-08-23 개정** — ⑦축의 실물이 둘 바뀌었다. `roadmap.md` 는 `docs/PRD.md` 로 통합됐고(vision·requirements-overview 와 함께),
  > `bl-audit.sh` 는 [ADR-037] 제로베이스로 **철거**돼 기계 검증은 `tools/scripts/ledger-vitals.sh` 3축뿐이다.
  > 지금 ⑦축 = `status.md`(지금 할 일) · `PRD.md`(제품 범위) · `backlog.md`+`backlog-deferred.md`(열린 결함).
  > **RESOLVED 는 파일이 아니라 삭제**다 — git 이 원문을 갖는다. 축의 *의미*는 그대로다.

★**「코드와 어긋나면 코드가 맞다」에 단서를 단다** — 그 원칙은 **①축에서만** 참이다. ⑤ 근거와
⑥ 반증에 대해 **코드는 증인이 아니다.** 코드는 무엇을 하는지 말할 뿐, 무엇을 버렸는지는 말하지 않는다.

### 2. `.ai/` 를 해체한다

> ★**배치 부분은 [ADR-027](./027-nested-agents-md.md) 로 Superseded (2026-08-07).** 아래 「`.ai/` 를 없앤다」는
> 유효하고, 옮겨 간 자리만 `.claude/rules/` → `backend/AGENTS.md`·`apps/web/AGENTS.md` 로 바뀌었다.

- `.ai/stacks/fastapi/backend.md` → `.claude/rules/backend.md` (실파일, `paths: ["backend/**"]`)
- `apps/web/AGENTS.md` (`paths: ["frontend/**"]`에 있던 FE 규칙을 병합)
- `.ai/common/global.md` §7 → `generator-evaluator-pipeline.md` 병합, §1~§6 은 소멸
- `.ai/project/lessons.md` → `docs/lessons.md` · dead 58%(flutter/integrations/templates) → 삭제

★**`.claude/rules/` 에는 `paths` 가 있는 스택 규칙만 둔다.** `paths` 없는 파일은 매 세션 무조건 로드 =
고정비다. 반증 정본(lessons)은 필요할 때 읽는 것이므로 `docs/` 에 둔다. `CLAUDE.md → @AGENTS.md` 는
정문법이라 유지한다 — AGENTS.md 표준은 Claude Code 가 네이티브로 읽지 않으므로 이 우회가 정답이다.

### 3. 기록 정책 — dev-log 는 이력이 아니라 **입력 버퍼**다

회차당 장문 서사 대신 **구조화된 반증 카드 1~2천자**. 세션 종결 시 `docs/lessons.md` 승격이 **의무**,
승격하면 버퍼를 비운다. `INDEX.md` 에는 한 줄(**300자 상한 유지**)만 남는다.
3층 = INDEX(발견 색인) / lessons.md(지식 정본) / git(원문 검증).

### 4. AGENTS.md 는 오리엔테이션 전용

**명령·컨벤션·비자명 함정 최소분**만. 문체는 ALWAYS / NEVER / PREFER 명령형 불릿, 말미에
「경로 → 용도」 퀵레퍼런스 3~5줄. **도메인 규칙 사본은 제거하고 `.claude/rules/` 포인터로 대체**한다.

### 5. tombstone 의무

문서를 지우면 「**무엇을 + 어디로 + SHA**」 한 줄을 남긴다. git 은 저장·검증 매체이지
**발견 매체가 아니다.**

## 근거 (출처는 헤더)

- **로딩** — `.claude/rules` 자동 로드 v2.0.64+, `paths` glob 이 있으면 해당 파일 Read 시에만 조건부 로드.
- **이론** — 정본 분할 + 로드 계층화 결합 권고. 레포 컨텍스트 파일은 **최소 요구사항만**, 신호 최고치는
  「비자명 패턴」 절.
- **실물** — AGENTS.md 류는 예외 없이 명령·컨벤션 중심(uv 는 25줄), `docs/` 는 제품 문서 전용. 상태
  3종은 OSS 엔 부재(Issues 대체)지만 1인 레포엔 합리적.

## Consequences

**얻는 것** — 갱신 지점이 하나뿐이라 드리프트가 구조적으로 줄고, `paths` 조건부 로드로 세션 고정비가
내려간다. 「이 질문은 어디를 보나」가 결정 가능해진다.

**치르는 것**

- ★**라이브 재현성 손실** — 지운 archive·dev-log 본문은 SHA 로만 닿는다. 과거 소크·발산 회차의 서사
  맥락은 git 을 거쳐야 하고, 실무상 **다시 읽지 않게 된다**. 의도된 거래다.
- **Claude Code 밖의 도구(codex 등)는 `.claude/rules/` 를 못 읽는다.** [가정] 진입점이 AGENTS.md 하나로 좁아진다.
- `paths` 로드는 **그 파일을 Read 할 때** 발동한다 — 파일을 안 열고 설계만 논하는 세션엔 스택 규칙이 없다.
- 이전 중 링크 대량 파손 위험. `scripts/docs-audit.sh` 통과가 완료 조건이다.

## 비고 — 재평가 트리거

⑴ Claude Code 로딩 규약이 또 바뀌면(본 ADR 의 사실 근거는 **버전 종속**이다) · ⑵ `.claude/rules/` 가
5개를 넘거나 `paths` 없는 파일을 넣고 싶어지면 · ⑶ `docs/lessons.md` 가 「검색해야 찾는」 크기가 되면 ·
⑷ 협업자·타 에이전트가 늘어 AGENTS.md 하나로 부족해지면.
