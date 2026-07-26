# docs-restructure 컨텍스트 노트

> 작업 중 내린 결정과 그 근거. 다음 세션이 재도출하지 않도록 계속 덧붙인다.

---

## 1. 왜 이 작업을 하는가 — 측정된 사실

90개 고스타 레포를 실측했다(후보 642 → 적중 362 → 심층 90). 원본 보고서는 `~/Downloads/조사/` 5종.

| 항목 | 우리 | 표본 90개 | 판정 |
|---|---|---|---|
| `docs/` 최상위 디렉토리 | **34** | 중앙값 1 · p90 13 · 최대 30 | **100 백분위 — 표본 전체보다 많다** |
| `AGENTS.md` 크기 | 7,737B / 141줄 | 중앙값 6,816B · 권고 200줄 | **정상 (55 백분위)** |
| 루트 `CLAUDE.md` | 없음 | 67% 보유 | 결손 |
| 커밋된 `.claude/` 자산 | `settings.json` 1개 | 실사용 63% · `!` 예외 1위는 `skills/`(14건) | 공유 경계 오설정 |

**결론 — 진입 문서는 건강하다. 이탈은 `docs/` 한 곳이고, 원인은 분류 실패가 아니라 "완결된 것을 내리는 규칙이 없음" 이다.**

## 2. ★스코프 축소 결정 — `dev-log/` 와 `reports/` 는 건드리지 않는다

초안은 `dev-log/` 를 archive 로 내리고 `reports/` 도 정리할 계획이었다. **실측이 이를 반박했다.**

- `.husky/pre-commit:4~6` 이 `docs/dev-log/*.md` 커밋을 감지해 `INDEX.md` 갱신을 요구한다.
- `.claude/settings.json:83` 훅도 같은 경로를 본다.
- `backend/src/core/config.py:147` — `dogfood_report_output_dir` 기본값이 **`docs/reports/dogfood`**. 런타임 출력 경로다.
- `.gitignore:88~90` 이 `docs/reports/*.html` 을 무시하되 `auto-dogfood/` 만 예외로 둔다.

그리고 성격상으로도 둘은 "완결 기록" 이 아니다. `dev-log/` 는 **append-only 활성 로그**이고 `reports/` 는 **생성물 출력 디렉토리**다. archive(= 기존 항목 수정 금지)에 넣으면 의미가 어긋난다.

→ **최상위 목표를 7개에서 9개로 조정한다.** (실제 착지는 활성 스프린트 1개 포함 10개) 위험 대비 이득이 나쁜 2개를 뺀 것이지 물러선 게 아니다.

## 3. ★`prototypes/` 는 archive 가 아니라 `reference/` 다

초안에서 `docs/prototypes/`(49파일)를 완결 산출물로 보고 archive 후보에 넣었다. **틀렸다.**

- `frontend/src/__tests__/design-canon-kit-port.test.ts:21` 이 `docs/reference/prototypes/shotgun-2026-07/_kit.html` 을 **실제로 로드한다**.
- `design-canon-tokens.test.ts:21` 도 `variant-c.html` 을 로드한다.

즉 프로토타입은 **FE 디자인 캐논의 살아있는 정본**이다. 테스트가 매번 대조하는 대상을 "읽기 전용 보관소" 에 넣을 수 없다. → `reference/prototypes/` 로 승격한다.

**교훈** — 아카이브 후보를 파일 개수와 최종 수정일로만 고르면 안 된다. **누가 그 파일을 읽는지**(사람이냐 테스트냐)를 먼저 봐야 한다.

## 4. `docs/superpowers/` — archive 로 내린다 (gitignore 는 보류)

조사에서 **17개 레포가 `.superpowers/` 또는 `docs/superpowers/` 를 `.gitignore`** 한다(스킬 저자 `obra/superpowers` 본인 포함). `ant-design` 은 `.claude/*` 에 `!.claude/skills/` 를 뚫은 바로 다음 줄에서 `docs/superpowers/` 를 버린다.

우리 `.gitignore:15~21` 도 이미 `.gstack/*` 에 같은 판단을 적용 중이라 **정책 불일치**가 있다.

그럼에도 **이번엔 archive 이관까지만 한다.** 사용자가 과거에 "docs/superpowers/ = writing-plans 전용" 으로 의도해 분리한 기록이 있고, `git rm` 은 되돌리기 비용이 크다. **archive 는 되돌릴 수 있고 gitignore 는 언제든 위에 얹을 수 있다.** 순서를 뒤집을 이유가 없다.

## 5. 코드 참조 갱신 범위 — 문서 이동이 코드 변경을 부른다

`00_`~`07_` → `reference/` 이동은 순수 문서 작업이 아니다. 실측된 참조는 이렇다.

| 유형 | 건수 | 위치 |
|---|---|---|
| **에러 메시지 문자열** | 7 | `backtest/{exceptions,service}.py` · `optimizer/engine/{bayesian,genetic,grid_search}.py` · `stress_test/engine/{cost_assumption_sensitivity,param_stability,walk_forward}.py` |
| **테스트 단언** | 2 | `backend/tests/backtest/test_exception_handler.py:42,70` |
| 도크스트링 | 3 | `trading/providers.py:701` · `test_trust_layer_parity.py` · `baseline_metrics.schema.json` |
| **테스트 파일 로드 상수** | 2 | FE canon 테스트 2종 |

전부 문자열 상수라 기계적이지만, **테스트 단언 2건은 실패로 드러나므로 반드시 전량 테스트를 돌려야 한다**(CLAUDE.md §8).

## 6. 새 구조의 정의 — 각 디렉토리가 답하는 질문

| 위치 | 답하는 질문 | 갱신 규칙 |
|---|---|---|
| `status.md` | 지금 뭘 하고 있나 | 스프린트마다 교체 |
| `roadmap.md` | 다음에 뭘 하나 | 매 세션 확인 |
| `backlog.md` | 미해결 부채가 뭔가 | 발견 시 추가 |
| `reference/` | 이 시스템은 어떻게 생겼나 | 코드와 어긋나면 **코드가 맞다** |
| `decisions/` | 왜 그렇게 정했나 | 폐기는 삭제가 아니라 `Superseded` |
| `dev-log/` | 언제 무슨 일이 있었나 | append-only |
| `reports/` | (런타임 생성물) | 코드가 씀 |
| `archive/` | 끝난 것 | 기존 항목 수정 금지 · 새 완결분 추가는 허용 |

## 7. 증식 차단 규칙이 이 작업의 절반이다

재편만 하고 규칙을 안 만들면 스프린트마다 다시 5개(테마 디렉토리 3 + dev-log 1 + TODO 섹션 1)가 늘어 3주 뒤 원위치한다.

AWS Prescriptive Guidance 의 ADR 운영 원칙(*폐기를 삭제가 아니라 `Superseded` 상태 전이로 다룬다*)을 스프린트 문서에 그대로 적용한다.

```
스프린트 종료 시 docs/<테마>/ 각 파일에 대해 택1
  승격 → docs/reference/   (지금도 유효한 계약·정본)
  강등 → docs/archive/sprints/<테마>/   (완결된 기록)
  삭제
그대로 두는 선택지는 없다.
```

**본 스프린트가 첫 적용 대상이다.** 작업이 끝나면 `docs/docs-restructure/` 자신을 `docs/archive/sprints/` 로 내린다.

## 8. ★S5 축소 — `.claude/skills/` 는 지금 공유할 게 없다

조사에서 `!` 예외 1위가 `skills/`(14건)였고, 초안은 `!.claude/skills/` 를 뚫고
`docs/guides/` 7파일을 스킬로 이관할 계획이었다. **로컬 실물을 열어 보고 철회했다.**

현재 `.claude/skills/` 28개는 전부 **서드파티 설치 패키지**다 — `ask-matt` `code-review`
`diagnosing-bugs` `tdd` `wayfinder` `writing-great-skills` 등. obra/superpowers·mattpocock
계열이며 **우리가 쓴 자산이 하나도 없다.**

여기서 `!.claude/skills/` 를 열면 다음 `git add -A` 가 남의 스킬 28벌을 리포에 벤더링한다.
공유할 게 없는 상태에서 예외를 뚫는 건 이득 0 · 위험만 있는 변경이다.

→ **규칙만 주석으로 남기고 예외는 열지 않는다.** 프로젝트 고유 스킬을 처음 쓰는 시점에
   `!.claude/skills/` 를 추가한다(개인용은 `local-*` 접두사로 구분 — `supabase` 의 `me-*` 방식).

`docs/guides/` 이관도 함께 보류한다. 7파일 중 `bl-audit-checklist.md` 는
`.claude/settings.json:71` 훅이 경로를 직접 참조하고, 나머지는 어느 것을 스킬로 올릴지가
사용자 판단 영역이다. 근거 없이 옮기면 훅이 깨진다.

## 9. 실측 결과 — 게이트

| 게이트 | 결과 |
|---|---|
| FE vitest | **1130 passed** (canon 11건 포함 — 이동한 `reference/prototypes/` 를 실제 로드) |
| BE pytest | **3006 passed · 46 skipped** (3:54) · ruff clean · mypy 205 files clean |
| 깨진 링크 | main 388 → **42** (−89%). 잔여는 선재 결함(gitignore 된 `reports/*.html` 등) |
| `docs/` 최상위 | 34 → **11** (활성 스프린트 `dogfood-restore` 1 포함) |
| FE tsc | clean |

## 10. 이 문서 자신이 규칙의 첫 적용 대상이다

작업이 끝났으므로 `guides/sprint-template.md` §9 를 본 스프린트에 적용한다.

- `checklist.md` · `context-notes.md` → **강등** (`docs/archive/sprints/docs-restructure/`)
  둘 다 완결된 판단 기록이고, 앞으로 다시 읽을 사람은 "왜 이렇게 바꿨나" 를 궁금해하는
  경우뿐이다. `reference/` 에 둘 정본은 아니다.
- 규칙 자체(승격/강등 의무)는 `guides/sprint-template.md` §9 와 `docs/README.md` 에
  **승격**되어 남는다 — 그게 이 스프린트가 만든 유일한 영속 자산이다.
