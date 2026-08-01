# Harness Framework 명령 워크플로우 검토 — QuantBridge 채택 판단

> **조사일:** 2026-08-01  
> **대상:** [`jha0313/harness_framework`](https://github.com/jha0313/harness_framework/tree/da676bc689f10f6db38ff194cf25e983f59ac231) 의 고정 커밋 `da676bc`  
> **판정:** 하네스의 *작업 명세 작성 원칙*은 가져오되, `phases/` 상태 원장·자동 실행기·자동 커밋/푸시는 QuantBridge에 도입하지 않는다.

## 결론

질문한 `docs/status.md`는 하네스의 `phases/{task}/index.json`과 **“지금 이어서 할 일을 잃지 않는 실행 상태”라는 목적에서만 유사**하다. 그러나 정본의 범위가 다르다.

| 구분 | Harness | QuantBridge | 판단 |
| --- | --- | --- | --- |
| 상태 단위 | task와 그 하위 step의 `pending/completed/error/blocked` | 다음 스프린트의 테마·BL·근거·첫 행동·차단 결정 | `status.md`를 유지 |
| 진입점 | 실행기가 phase 인덱스와 step 파일을 순차 소비 | 새 세션은 `CONTEXT.md` + `AGENTS.md` + `status.md` 3종만 읽음 | `status.md`를 phase index로 대체하지 않음 |
| 미해결 업무 원장 | phase index의 step 상태 | `backlog.md`의 BL 섹션 상태, `roadmap.md`와 3면 대조 | 별도 `phases/index.json` 추가 금지 |
| 완료 기록 | step `summary`와 timestamp | dev-log·reference/archive 승격, status/roadmap/backlog 원자 갱신 | 기존 G8 유지 |

Harness 명령은 `phases/index.json`과 task별 `index.json`을 생성하고 상태·timestamp를 기록하라고 한다([`harness.md` L33–84](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L33-L84)). 반면 QuantBridge는 `status.md`의 최상단 「다음 스프린트」를 유일한 진입점으로 명시한다([`AGENTS.md` L3–6](../../../AGENTS.md#L3-L6), [`status.md` L10–17](../../status.md#L10-L17)). 둘을 함께 원장으로 쓰면 동일한 “현재 작업”이 두 곳에서 갈라진다.

## 원문이 실제로 하는 일

`/harness`는 단순한 계획 템플릿이 아니라 다음 자동화 묶음이다.

1. 문서를 읽고(필요하면 병렬 Explore), 사용자와 미결정을 논의한 뒤 step 초안을 승인받는다([`harness.md` L7–31](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L7-L31)).
2. step은 작은 범위·독립 실행성·사전 읽을 파일·인터페이스 수준 지시·실행 가능한 AC·구체적 금지를 요구한다([`harness.md` L19–27](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L19-L27)).
3. `execute.py`는 `feat-<phase>` 브랜치를 checkout/create하고([`execute.py` L113–134](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L113-L134)), 루트 `CLAUDE.md`와 **모든** `docs/*.md`를 프롬프트에 넣는다([L177–186](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L177-L186)).
4. Claude를 `--dangerously-skip-permissions`로 최대 30분 호출하고([L229–255](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L229-L255)), step 상태가 완료가 아니면 최대 3회 자동 재시도한다([L293–360](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L293-L360)).
5. 매 step에서 `git add -A` 뒤 코드/메타데이터를 나누어 자동 커밋하고([L136–157](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L136-L157)), `--push`이면 완료 뒤 branch push까지 한다([L381–400](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L381-L400)).

따라서 “step 계획을 만들어 준다”만 따로 평가하면 안 된다. 상태 원장, 프롬프트 주입, 권한, 재시도, Git 변경까지 결합된 실행기다.

## 그대로 채택할 부분

| 부분 | 근거 | QuantBridge 적용 위치 |
| --- | --- | --- |
| 구현 전 미결정 사항을 사용자와 논의 | Harness의 B 단계([L11–13](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L11-L13)) | `status.md`의 blocking 결정 후보를 먼저 묻는다. 특히 라이브 매매 시맨틱은 사람 결정을 대체하지 않는다. |
| 작은 범위와 구체적인 금지 | 한 step은 한 레이어/모듈, “X 하지 마라. 이유 Y”([L21–27](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L21-L27)) | G1 task spec의 “스펙 밖 리팩토링 금지”를 더 구체적인 파일/이유 수준으로 쓴다. 이미 G2 요구와 정합한다([`generator-evaluator-pipeline.md` L73–82](../../guides/generator-evaluator-pipeline.md#L73-L82)). |
| 실행 가능한 AC | 추상 문구 대신 명령을 적는다([L25](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L25)) | G1의 test·화면·외부 오라클·표적 변이를 **정확한 명령과 기대 결과**로 쓴다. 이 레포는 이미 G1에서 이를 요구한다([L54–61](../../guides/generator-evaluator-pipeline.md#L54-L61)). |
| 이전 산출물/읽을 파일을 명시 | 독립 세션이 맥락을 복구하도록 파일 경로를 준다([L22–24](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L22-L24), [L91–99](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L91-L99)) | task spec에는 **필요한** ADR·코드·BL·gate 문서 경로만 적는다. 새 세션 기본 진입점 3종은 그대로 둔다. |

## 수정해서 채택할 부분

| Harness 요소 | 수정안 | 이유와 안전장치 |
| --- | --- | --- |
| step의 독립 실행성 | 활성 스프린트의 임시 task spec에만 적용하고, 종료 시 G8에 따라 dev-log/reference/archive로 흡수한다. | Harness처럼 영구 `phases/<task>/stepN.md`를 만들면 `status.md`와 두 번째 실행 경로가 된다. QuantBridge는 작업 문서를 흡수 대조 뒤 삭제하도록 한다([`generator-evaluator-pipeline.md` L134–142](../../guides/generator-evaluator-pipeline.md#L134-L142)). |
| `blocked`와 사유 기록 | 사용자의 결정을 기다리는 경우 `status.md`의 blocking 결정 후보와 해당 BL에 사유·재개 조건을 적는다. | 별도 JSON 상태가 아니라 기존 status/backlog 책임에 넣어 SSOT를 보존한다. Harness의 blocked 개념 자체는 유용하지만, BL은 `ACTIVE/PARTIAL/RESOLVED/UNKNOWN`의 별도 계약을 가진다. |
| 완료 summary/timestamp | 짧은 결과는 dev-log에, 현재성은 `status.md`에, BL 상태는 `backlog.md`에 원자 갱신한다. | `scripts/bl-audit.sh`는 backlog 섹션의 선언 상태를 SSOT로 읽고 roadmap·인덱스 표까지 검사한다([`scripts/bl-audit.sh` L2–19](../../../scripts/bl-audit.sh#L2-L19), [L213–257](../../../scripts/bl-audit.sh#L213-L257)). Harness index를 새 진실원으로 추가할 수 없다. |
| Explore 병렬화 | 읽기 전용 탐색에는 사용 가능하되, 쓰기·pytest·e2e·Celery 검증은 QuantBridge의 워크트리/슬롯 제약을 따른다. | 하네스는 병렬 Explore만 말한다([`harness.md` L7–10](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/commands/harness.md#L7-L10)). 이 레포는 공유 테스트 DB·라이브 worker 때문에 임의 병렬 실행이 안전하지 않다([`generator-evaluator-pipeline.md` L84–95](../../guides/generator-evaluator-pipeline.md#L84-L95)). |

## 도입하지 않을 부분

| 항목 | 구체적 충돌/위험 |
| --- | --- |
| `phases/`의 top-level/task index | status/roadmap/backlog와 작업 상태가 중복된다. 특히 Harness 4상태는 QuantBridge BL의 `PARTIAL`·`UNKNOWN`과 3면 정합 검사를 표현하지 못한다. |
| 모든 `docs/*.md`와 누적 summary의 프롬프트 주입 | 현재 문서는 “3종만 먼저 읽고 나머지는 필요할 때”라는 의도적 경계를 둔다([`AGENTS.md` L3–6](../../../AGENTS.md#L3-L6), [`docs/README.md` L10–21](../../README.md#L10-L21)). 전체 주입은 오래된 archive를 현재 명령처럼 만들고, 긴 status 서사까지 증폭시켜 오독 가능성을 높인다. |
| 범용 `npm run lint && npm run build && npm run test` Stop hook | Harness hook은 단일 npm 프로젝트를 가정한다([`.claude/settings.json` L2–22](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/settings.json#L2-L22)). QuantBridge 게이트는 backend `uv`·frontend `pnpm`·e2e로 나뉘며 BE pytest는 `.env.local` 전체 source가 필수다([`gates-and-traps.md` L9–35](../../reference/gates-and-traps.md#L9-L35)). 일반 hook은 누락 검증 또는 위험한 DB 연결을 낳는다. |
| “AC 통과 = step 완료”인 생성자 자기 판정과 자동 3회 재시도 | QuantBridge G1은 평가자가 AC/변이를 구현 전에 동결하고, G3이 외부 오라클·표적 변이로 판정한다([`generator-evaluator-pipeline.md` L54–69](../../guides/generator-evaluator-pipeline.md#L54-L69), [L84–95](../../guides/generator-evaluator-pipeline.md#L84-L95)). 생성자가 3회 재시도하면 diff가 누적된 채 평가 경계가 흐려지고, `blocked`여야 할 설계 결정을 코드 변경으로 우회할 수 있다. |
| 실행기의 `--dangerously-skip-permissions` | 권한 확인을 건너뛴다([`execute.py` L237–241](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L237-L241)). QuantBridge는 금융/실거래소 코드이며 사용자의 Git·배포 승인을 요구한다([`AGENTS.md` L14–18, L36–42](../../../AGENTS.md#L14-L18)). |
| 자동 branch/커밋/push | 실행기는 `git add -A`로 임시·사용자 변경까지 stage할 수 있고([`execute.py` L136–157](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L136-L157)), `--push` 시 실제 push한다([L394–400](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/scripts/execute.py#L394-L400)). 하네스 hook은 `git push --force`만 차단하고 일반 push는 차단하지 않는다([`.claude/settings.json` L14–22](https://github.com/jha0313/harness_framework/blob/da676bc689f10f6db38ff194cf25e983f59ac231/.claude/settings.json#L14-L22)). 이는 “커밋·푸시·배포는 단계별 사용자 승인” 규칙과 정면 충돌한다. |

## 권고하는 최소 통합안

새 스크립트나 `phases/` 디렉토리를 만들지 않는다. 다음 스프린트부터 G1 task spec을 작성할 때만 Harness의 좋은 템플릿을 아래 다섯 항목으로 흡수한다.

1. 한 BL 또는 검증 가능한 한 slice만 다룬다.
2. 먼저 읽을 파일과 기존 코드 경로를 명시한다.
3. 구현 제약을 “하지 말 것 + 이유”로 쓴다.
4. AC에 **이 레포의 정확한** 표적 명령·외부 오라클·표적 변이·음성 대조를 쓴다.
5. 차단된 설계 결정은 자동 재시도하지 않고 사용자에게 올린 뒤 `status.md`와 BL에 재개 조건을 기록한다.

이렇게 하면 하네스의 장점(작은 자기완결 작업, 재현 가능한 수용 기준, 명시적 block)을 얻으면서도 QuantBridge의 단일 진입점, BL SSOT, 독립 평가, 금융 코드의 Git 안전 경계를 보존한다.

