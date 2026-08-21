# ADR-037: 하네스 제로베이스 — 검사기 층을 전량 걷어내고, 증거로만 다시 쌓는다

> **상태:** 확정 (Accepted — 2026-08-19, 사용자 판정)
> **일자:** 2026-08-19
> **결정자:** woosung (기안: Claude)
> **관련:** [ADR-030](./030-harness-pilot-verdict.md)(러너 파일럿 철거) · [ADR-026](./026-documentation-ssot.md) ·
> [ADR-028](./028-backlog-deferred-verdict.md)(판정어 — 규칙은 유지, 집행기만 철거)
> **대체함:** ADR-026·028 등이 언급하는 감사기 **기계 집행** 문장 전부 (판정어·원장 규칙 자체는 유지)
> **복원 원본:** git 태그 **`harness-v1`** (철거 직전 커밋) — `git show harness-v1:<경로>` / `git checkout harness-v1 -- <경로>`

---

## Context — 왜 걷어내나

`jha0313/finsight`(강사 레포) 하네스 도입 검토가 발단이다. 전면 교체 타당성을 8-에이전트
전수 조사로 쟀다: **우리 하네스 64요소 1,197,552B 중 finsight 등가물로 교체 가능 0.2%,
등가물없음 90.2%** — 「교체」는 성립하지 않는다. 그러나 같은 조사의 반대편(교체 옹호 steelman)이
세운 사실 4개가 이 ADR 의 근거다:

1. **재성장 관성** — [ADR-030] 이 조종 장치 230KB 를 걷어낸 직후 5일 만에 `tools/scripts` 가
   431KB → 737KB (+71%). 부분 감량은 성장 관성을 못 이겼다.
2. **재귀 4단** — 자기시험 `*-test.sh` 14종 = 하네스 줄수의 37%가 하네스를 시험. 활성 LESSON
   28건 중 ~15건이 트레이딩이 아니라 **검증기 자신**에 대한 교훈.
3. **하네스發 사고** — 최근 3주에만 하네스 자신이 낸 문서화 사고 ≥8건(침묵 skip·남의 회차
   파일 초록·감사기 오발·거짓 red·fail-open). 하네스가 막은 사고와 낸 사고가 비등했다.
4. **대리 지표** — 우리 감사기는 텍스트 형태를 재고, 최다 반복 사고 계열(「문서가 코드보다
   앞서 나갔다」)은 어느 감사기도 재지 않는 축이었다.

「하네스가 얇아진다」 렌즈로 층을 갈랐다: 모델이 좋아질수록 값이 주는 **조향층**과, 남는
**검증·권한·지식층**. 이번 철거는 형태-감시 검사기 층 전체를 걷어내고, 남는 층은 finsight 에서
이식한 4종(리뷰 다수결·codex 훅·Eval·커맨드)과 최소 사활 검사 1종으로 다시 세운다.

## Decision

### ① 걷어낸 것 (25파일 + 배선, ~444KB — 전체 원문 = `harness-v1`)

| 축                    | 대상                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------ |
| 게이트 오케스트레이션 | `final-gates.sh` (2단 게이트·유예 원장 `deferred.txt`·스킬 신호·화면 증거 팩 포함 전량)    |
| 원장/문서 감사        | `bl-audit.sh` · `docs-audit.sh` · `bl-trigger-sweep.sh` · `context-budget.sh`              |
| 형태 감사             | `header-audit.sh` · `skip-ratchet.sh` · `signal-check.sh` · `tool-pin-audit.sh`            |
| 자기시험              | `*-test.sh` **14종 전량** (남긴 스크립트의 자기시험 포함 — 검사기 복귀 시 함께 복귀)       |
| 사문                  | `sentinel_bl181_worker_reload.sh` (참조가 Superseded ADR-019 구 경로뿐)                    |
| 배선                  | mise `docs-audit`·`header-audit`·`gate-harnesses` task · pre-commit 의 header-audit 차단 · |

pre-push 의 FE/BE 품질 검사부(ref 가드만 존치) · CI `documentation` 잡 등(ci.yml 은 표준 러너로 재작성) ·
`bl-audit-checklist.md` · settings.json 의 checklist 알림 훅 |

### ② 남긴 것 — 하네스가 아닌 것 3군

1. **운영 런타임**: `soak-*` 6종 · `db-backup.sh` · `disk-guard.sh` — Oracle 서버 systemd 타이머가
   지금 호출 중인 백업·경보·소크 관측이다. 끄는 결정은 별개 사안이다.
2. **CI 테스트 인프라**: pytest·vitest·eslint·tsc·build — 제품 테스트지 메타-하네스가 아니다.
   (nightly 3종 워크플로우는 이번 판정 유보 — 다음 재검토 후보.)
3. **권한 경계 소품**: pre-push **ref 가드**(main 직접 push 영구 금지 = Golden Rule) ·
   `assert-main-checkout.sh`(워크트리→공유 DB 파괴 차단, mise 15개 task 인라인) · settings.json deny.

### ③ 입힌 것 — finsight 이식 4종 + 슬림 복귀 1종

- `/review-code` — 3차원(correctness·security·conventions) 병렬 리뷰 + finding 당 skeptic 3명
  2/3 다수결. 차원 프롬프트는 우리 규칙(Decimal-first·Repository·SecretStr·prefork-safe·H-1~H-3).
  **구 header-audit 은 conventions 차원이 흡수.**
- `.codex/hooks.json` + `tools/scripts/hooks/` — codex 레인 최초의 가드(위험명령 차단 +
  Stop 경량 자가교정: 변경 영역별 ruff/eslint 만, DB·네트워크 의존 0).
- `evals/harness/` — 하네스 자체의 회귀 Eval(review 5 + qa 전제반박 2, 로컬 전용, 키 없으면 exit 2).
  golden set 성장 규칙 = 운영 실패 1건당 케이스 1건.
- `tools/scripts/ledger-vitals.sh` — **재입힘 규칙의 첫 적용례.** 사고 실증 2건([BL-643] 「다음 행동」
  중복 · RESOLVED 13건 역류)이 근거인 3축만: 다음 행동 ≤1 · ⓪ 표 ≥3행 · RESOLVED 역류 0.
  36.7KB+30.8KB 감사기가 아니라 **한 파일 슬림판**으로 돌아왔다 — 복귀는 이렇게 한다.

### ④ ★재입힘 규칙 (이 ADR 의 실질)

> **하네스는 추측으로 자라지 못한다. 「문서화된 사고 1건 = 슬림 복귀 1건」만 허용한다.**
> 복귀는 원판 복원이 아니라 그 사고 하나를 잡는 최소판으로 한다. 원판이 필요하다는 주장에는
> 그 원판이 잡던 사고의 재발 기록을 요구한다. (finsight golden set 성장 규칙과 동형 —
> ADR-030 철거 후 5일 +71% 재성장을 끊는 장치다.)

## Consequences — 눈뜨고 감수하는 리스크

- **무방비가 된 사고 계열**: 스킬 신호 신선도([BL-706] 남의 회차 파일 초록) · 무조건 skip 심기
  (skip-ratchet — 3개월 잠복 실증) · 도구 핀 이탈([BL-785]) · 화면 증거([BL-797], 이틀 전 신설분
  포함). 재발 시 그 사고가 곧 슬림 복귀 티켓이다.
- **원장 정합은 3축 외 수동** — 3면 대조·트리거 스윕·줄 길이 상한은 산문 규칙이 됐다.
  부식이 재발하면(실증상 가능성 높음) ledger-vitals 에 축을 하나씩 더한다.
- **CI 축소** — coverage 래칫·alembic check·e2e·openapi drift 가 CI 에서 빠졌다(로컬 실행은 가능).
  main 브랜치 보호의 required check 이름이 구 잡을 가리키면 사용자가 설정을 갱신해야 한다.
- 구 게이트 절차를 참조하던 문서는 tombstone(`git show harness-v1:<경로>`)으로 갱신했다.
