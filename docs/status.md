# QuantBridge — Status

> 이전 회차 배너·「참고」 후보 목록·⛔종료 블록·완료 이력은 2026-08-06 문서 대개편에서 삭제했다.
> 원문 = `git show 94da86b1:docs/status.md` (회고 요약은 `docs/dev-log/INDEX.md`, 원문은 git history).
>
> **2026-08-10 docs-context-diet — 끝난 회차 회고 6블록(48,452자)을 `dev-log/` 로 강등했다.**
> 원문 = `git show 762e1297:docs/status.md`. 간 곳 = `dev-log/2026-08-{08-soak-death-and-restart,
09-fe-perf-quartet,09-bl003-mainnet-runbook,09-status-triage-mass,10-review-and-merge,
10-close-ownership-axis}.md`. **삭제가 아니라 이동이다** — 색인은 `dev-log/INDEX.md`.
> ★**이 파일은 `docs-audit.sh` 의 `file_line_caps` 가 지킨다.** 넘치면 크기를 늘리지 말고
> **끝난 회차를 강등해라** — 넘쳤다는 것은 승격이 밀렸다는 신호다(ADR-026 §3).
>
> ★**2026-08-13 docs-diet — 이 파일이 걸던 dev-log 링크 13개가 코드 스팬이 됐다.** `dev-log/` 본문
> **25건은 전부 git 으로 내려갔다**(`docs/dev-log/INDEX.md` 헤더 참조). 아래 본문에 `dev-log/*.md` 가
> 코드 스팬으로 보이면 그건 **살아 있는 경로가 아니라 git 좌표**다 — 열려면
> `git show 8abd0d67:docs/dev-log/<파일명>`. 온라인 요약은 `dev-log/INDEX.md` 의 해당 줄이 전부다.

## 다음 스프린트 — **⓪ 표에서 고른다** (아래 ⓻ 의 `다음 행동 =` 이 유일한 진입점)

> ★**이것이 다음 세션의 유일한 진입점이다.** 별도 킥오프 파일을 만들지 않는다([ADR-026] · §G8).
> ★★~~`docs-audit.sh` 가 이 블록을 검사한다([BL-643])~~ → **2026-08-19 [ADR-037]**
> `tools/scripts/ledger-vitals.sh`(pre-commit 배선)가 검사한다 — ⓪ 표 행 **≥3** ·
> 살아 있는 **`다음 행동 =`** ≤1(파일 전체). 낡은 지시는 `~~옛 문장~~ → **날짜 + 새 사실**` 로 바꿔라.
>
> ★★★**착수 전 첫 명령 둘** — ⑴ `tools/scripts/soak-gate.sh`(서버, `bash -lc` 필수)
> ⑵ FE 를 건드릴 회차라면 **`rm -rf apps/web/.next`**. ⑵ 는 농담이 아니다: 2026-08-08 에
> Turbopack 영속 캐시가 1.99GB 까지 자라 `next dev` 가 **요청 0건에서 417% CPU** 를 태우고
> 머신을 두 번 죽였다. 게다가 낡은 CSS 를 **서버 재기동을 넘어** 계속 줘서 음성 대조를
> 거짓 통과시켰다([BL-650]).

### ⓵ 목표 · 왜 지금 · 비목표

~~**원장이 6곳에서 거짓을 말하고 있었고 … ⓪ 표에 게이트를 박아 루프를 끊는다.**~~
→ **2026-08-14 까지 그 루프는 닫혔다.** 08-11 ledger-truth · 08-12 surface-demo-pack·branch-debris ·
08-13 monorepo-realign([ADR-029])·contract-poc([ADR-031]) · 08-14 gate-surface-close. 전문 = git
(`dev-log/INDEX.md` 가 발견 색인). ★08-10~08-12 의 반증 4건은 **[LESSON-101]→§8.6 승격**과
**[LESSON-105]·[LESSON-106]** 으로 정본 층에 올라갔다 — 이 자리는 더 이상 그 서사를 지고 있지 않다.

**다음 회차의 목표는 ⓪ 에서 고른다** — ~~손으로 후보를 얹지 마라(`docs-audit` 의 ⓪ 표 정체성 축이 집행한다). 살아 있는 행은 `bash tools/scripts/bl-audit.sh --list ACTIVE` ∪ (`PARTIAL` ∧ 도래)다.~~
→ **2026-08-19 [ADR-037]** 두 검사기는 철거됐다(원문 = `git show harness-v1:<경로>`) — ⓪ 표는
세션이 `docs/backlog.md` 의 상태줄(`**상태:**`)을 직접 읽어 갱신한다(행 수 ≥3 은
`tools/scripts/ledger-vitals.sh` ② 축이 지킨다).

**비목표(불변)** — 거래소 쓰기([BL-669]) · `exchange_accounts` 행 삭제([BL-477]·[BL-529]·[BL-592]) ·
**서버 소크 DB 에 alembic 적용**. 셋 다 사용자 결정 대기다.

> ★★**2026-08-15 사용자 결정 — alembic 축의 문구가 확정됐다.**
> **「migration 파일 생성 · 로컬/CI 적용 = 허용 / 서버 소크 DB 에 DDL 적용 = 매번 명시 승인」.**
> 근거: 실제 위험은 파일을 만드는 것이 아니라 **소크 창 중에 DDL 이 도는 것**이고, 전면 금지는
> `apps/api/AGENTS.md` §7(models.py 를 바꾸면 migration 생성 **의무**)과 정면충돌한다.
> ⇒ 비목표 항목의 이름을 「alembic 마이그레이션」에서 **「서버 소크 DB 에 alembic 적용」**으로
> 좁혔다. 집행 도구 = `soak-stack.sh migrate`(기본 dry-run · `--confirm` 이 집행 — [BL-743]).
> ~~⑵ alembic 마이그레이션 — 승인을 받지 않았다 … 「금지」인지 「승인 후 허용」인지가 지금 모호하다~~
> → **2026-08-15 해소.** 그때 만든 `20260815_0001` 은 승인을 받아 서버에 적용했고 격차는 0 이다.
> ⑴ **거래소 쓰기** 는 그대로 — 고아 포지션 청산은 **사용자 승인을 받고** 했다([BL-024] 전례).
> ⇒ 「승인 후 허용」으로 읽는 것이 실태에 맞다.

### ⓶ 먼저 읽을 파일

- ★**환경 짝 먼저** — `mise run fe-isolated`(`:3100`) 는 **BE `:8100`** 을 부른다. `mise run be` 는 `:8000`
  이므로 **짝을 맞춰 `mise run be-isolated` 를 띄워라.** 이 한 줄을 몰라 2026-08-12 회차가 authed 12건을
  「미시딩」으로 두 번 오진했다([BL-707]). `mise run fe` 는 `:3000` 이고 게이트가 보는 포트가 아니다.
- **정렬·파생 필드의 정본 2곳** — `apps/api/src/backtest/repository.py`(`sharpe_sort_criteria` =
  등급 4단 + 정규화 · **베끼지 말고 재사용해라**) · `apps/api/src/strategy/repository.py`
  (`list_by_owner` = `DISTINCT ON` LEFT JOIN 후 정렬 → 페이지네이션)
- **E2E base URL 은 1벌이다** — `apps/web/e2e/_base-url.ts`. `?? "http://localhost:3000"` 을
  **다시 만들지 마라**(사본 5벌이 CI 를 190ms 만에 죽였다)
- ~~**판정 스크립트 2벌** — `tools/scripts/bl-audit.sh --list <판정어>` 가 정본이고 `tools/scripts/bl-trigger-sweep.sh` 가 `ACTIVE ∪ PARTIAL` 을 훑는다. **파서를 3벌로 만들지 마라**~~
  → **2026-08-19 [ADR-037]** 두 스크립트는 철거됐다(원문 = `git show harness-v1:tools/scripts/`).
  판정어 5종 규칙은 산문으로 유지한다 — 판정은 섹션의 상태줄 `**상태:**` 를 직접 읽는다.
- ★**[BL-003] 을 이어받는다면 첫 파일은 하나다** —
  [`bybit-mainnet-runbook.md`](./operations/bybit-mainnet-runbook.md).
  **§0(착수 전 재측정)을 먼저 돌려라** — 이 문서의 실측에는 유효기한이 있다.
- ★**원장은 파일 둘이고 축은 판정어다**: `backlog.md`(ACTIVE ∪ PARTIAL + 인덱스 표 전량) ·
  `backlog-deferred.md`(DEFERRED). ★**RESOLVED 는 파일이 아니라 삭제다**(2026-08-23 · `AGENTS.md` §6) —
  닫힌 BL 본문의 좌표는 [`docs/README.md`](./README.md) 가 갖는다.
    ~~★**어느 파일에 있는지는 앵커가 아니라 `bash tools/scripts/bl-audit.sh --list <판정어>` 의 4번째 칸이 답한다**~~
    → **2026-08-19 [ADR-037]** bl-audit 철거 — 어느 파일인지는 판정어가 정한다(위 3분할 규칙 ·
    확인은 `grep -l '^### BL-NNN' docs/backlog*.md`)
    — 표 행의 `#bl-NNN` 은 접두사가 없어 다른 파일을 못 가리킨다([BL-801]). 통째로 읽지 마라.
- [`gates-and-traps.md`](./development/gates-and-traps.md) — 게이트 전문
- [`generator-evaluator-pipeline.md`](./development/workflows/generator-evaluator-pipeline.md)
  **§2**(적용/비적용 — 단건·문서 전용에 파이프라인은 과하다) · **§G8**(종결 절차)

### ⓷ 작업 단위 — 각 단위는 독립적으로 완료·보류할 수 있다

★**2026-08-14 gate-surface-close 로 교체됨.** 앞 회차(surface-demo-pack 5단위)는 전건 종결·보류 확정 —
전문 = `dev-log/2026-08-12-surface-demo-pack.md`(git).

| #   | 단위                              | 담당              | 목표 조건                                                                | 상태     |
| --- | --------------------------------- | ----------------- | ------------------------------------------------------------------------ | -------- |
| 1   | [BL-716] 반증 카드 승격 (P1 인계) | CONTROL           | 후보 3종 실제 반복 횟수 재계수 · 3회 초과분만 승격 · ID/경로 선행 수리   | **완료** |
| 2   | [BL-707] authed e2e 도달성 단언   | codex w1 (슬롯 2) | 기존 `subresourceFail` 단언화 · `net::err_` allowlist 제거 · setup abort | **완료** |
| 3   | [BL-714] 마감 게이트 브랜치 전제  | codex w2 (슬롯 3) | 입구 거부 · 하네스 ㉖ · ★**케이스 ⑫ 와 변이 M1 불변**                    | **완료** |
| 4   | [BL-715] 브랜치 잔재 62건 판정    | Agent 배치        | 원격 23건 전수 sha 판정 + 로컬 축 소멸 확인                              | **완료** |

★**넷 다 착수 전제가 반증됐고 그것이 이 회차의 최대 산출이다** — 원장이 적어 둔 처방을 그대로
이행한 단위는 **하나도 없다**. BL-707 은 기전이 성립하지 않았고(`playwright.config.ts` 에 dotenv 가
없어 프로브가 볼 주소가 그때 살아 있던 `:8000` 이다), BL-714 의 `--range` 는 압수 A1 의 **유일한
증인**(케이스 ⑫ · 변이 M1)을 죽이며, BL-716 의 「22장을 카드로」는 `lessons.md:12` 자기 규약
(「같은 패턴이면 새 항목 말고 누적 증가」)과 충돌하고, BL-715 는 **로컬 축이 이미 소멸**해 있었다.

★**범위 밖 금지와 그 이유** — 워커는 `docs/**` 를 만지지 않는다(`backlog.md` 단일 파일 9천 줄 충돌) ·
celery 경유 검증을 하지 않는다(worker 컨테이너가 **메인의 `apps/api/src`** 를 mount 하므로 내 코드가
아니라 메인 코드가 돈다 — **침묵 실패**) · `mise run up/down/migrate/seed` 를 하지 않는다(앱 DB 1벌 공유).

★**herdr 는 이 회차에서 쓰지 않았다** — 서버가 protocol 19>17 로 막혀 있고 `herdr server stop` 은
**pane 프로세스를 죽인다**(= 오케스트레이터 세션 자신). 워커는 `codex exec -s workspace-write -C <워크트리>`
2벌로 돌렸다. ★**`worktree-bootstrap.sh` 는 워크트리를 만들지 않는다** — 기존 워크트리를 부트스트랩할
뿐이라 메인에서 그냥 돌리면 **메인 체크아웃을 그 슬롯으로 표시**한다. `git worktree add` 가 선행이다.

### ⓸ AC 명령 · 함정

```bash
# ① 세션 첫 명령 — 순서 고정. ★bash -lc 필수(비로그인 셸엔 uv PATH 가 없다)
launchctl unload ~/Library/LaunchAgents/dev.quantbridge.soak-gate.plist  # 게이트에 flock 이 없다
ssh truewords-oracle 'bash -lc "cd ~/quantbridge && tools/scripts/soak-gate.sh"'
#   ★`/metrics` 는 **1회만** 읽는다 — 두 번 읽으면 근거들이 서로 다른 시점을 가리킨다.
#     서버 `apps/api/.metrics` 직독([BL-620]). 방법은 `soak-gate.sh:517-527` 과 같은 것을 쓴다

# ② 항목별 표적 명령
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest -q       # ★.env.local **통째** 소싱
cd apps/api && … uv run pytest --run-mutations tests/strategy/pine_v2/test_trust_layer_parity.py
cd apps/web && pnpm vitest run --coverage                            # 단위 3 — ★문턱 금지
# ~~bash tools/scripts/bl-audit.sh; bash tools/scripts/docs-audit.sh — 둘 다 rc 0~~ → 2026-08-19 [ADR-037] 철거
mise run ledger-vitals                                               # 원장 사활 3축 · rc=0 (pre-commit 배선)

# ③ smoke 도구 — dry-run 은 네트워크 호출 0건이다. 마음 놓고 돌려라
tools/scripts/bybit-smoke.sh --env-file <시크릿파일> --mode demo
#   ★--confirm 은 거래소에 실제로 나간다. **사용자 승인 뒤에만.**

# ④ 하루 끝 — 마지막 커밋 뒤, 클린 트리. 그 뒤로 문서를 더 쓰지 마라
# ~~final-gates.sh --pre-pr → PR push → --deferred-only … deferred.txt 유예 원장 · 신호 4종(.ok)~~
#   → 2026-08-19 [ADR-037] 철거. green = CI 단일 게이트(backend + frontend 2잡)다. PR push 후:
gh pr checks --watch                                       # 2잡 다 초록이어야 종결
```

~~★★**「마지막 커밋 뒤」는 「이 회차의 PR 브랜치에서, 머지 전에」를 함께 뜻한다** ([BL-714]) — `signal-check.sh` 앵커 A1/A2 · `final-gates.sh` 의 입구 거부 · 「신호 4종」 절~~
→ **2026-08-19 [ADR-037] 철거.** 그 문단이 기술하던 것(`signal-check.sh` · 앵커 A1~A5 · 신호 `.ok` 파일 ·
`final-gates.sh` 입구 거부)이 전부 사라졌고, 가리키던 `gates-and-traps.md` 「신호 4종」 절도 같은 날 걷어냈다.
**지금 종결 판정은 `gh pr checks --watch` 하나다.** 원문 = `git show harness-v1:tools/scripts/signal-check.sh`.

**변이와 기대 결과** — 「끝났다」는 양성 + 음성 + 변이 셋을 다 통과해야 한다.
★2026-08-11 회차의 변이 표(4행)는 그 회차와 함께 끝났다 → `git show 79cea10d:docs/status.md`.
2026-08-12 회차의 변이 4종·음성 대조·예측 미스 1건은
`dev-log/2026-08-12-surface-demo-pack.md` 에 있다.

★**`exit 1` 이라 쓰지 마라 — `종료 코드 != 0` 이다.** make 가 2로 감싼다.
★**변이를 심었으면 「그 변이가 도달했는지」를 따로 확인해라** — 도달 못 한 변이의 red 0 은 무증거다.
복원은 **스냅샷 되쓰기 + sha256**(`git checkout` 금지).

★**[BL-003] 을 이어받을 때 반드시 알 것** — 전부 2026-08-09 에 실측으로 밟았다:

- **runbook §0 을 먼저 돌려라.** 그 문서의 실측에는 유효기한이 있고, 이 레포는 「남이 적어 둔
  실측」이 틀린 것을 반복해 겪었다. 이번에도 [BL-003] **본문 4건이 코드 대조로 반증**됐다.
- **cutover 는 코드 2줄이다** — `registry.py:43-44` · `live_session_service.py:115`.
  base URL 매핑(`_apply_bybit_env`)은 **이미 live 를 지원한다.** provider 를 새로 쓰지 마라.
- **그 2곳을 바꾸면 테스트 2건이 red 가 된다**(`test_live_session_commits.py:270,306` ·
  `test_demo_stability_gate.py:100-108`). **「고쳐야 할 red」이지 회귀가 아니다.**
- **credentials 를 argv 로 넘기지 마라** — `ps` 로 읽힌다. `BYBIT_SMOKE_API_*` env 가 정문이다.
- **`.env.production` 에 인라인 주석 금지** — 401 이 아니라 **500** 이 난다([BL-625]).
- ★**상태줄 어휘는 `bl-audit.sh:75-79` 가 읽는다** — `lead()` 가 `—` 앞까지만 자르므로
  「🟡 **부분 —」 로 쓰면 **UNKNOWN → exit 1\*\* 이다. 「부분 해결」을 앞에 둬라.
- ★**zsh `2>&1 >/dev/null` 로 stderr 만 뽑지 마라** — `MULTIOS` 가 stdout 을 양쪽으로 보낸다(파일로 받아라). ★**`cd` 는 Bash 호출 사이에 유지된다** — 2026-08-12 에 세 번 밟았다. 절대경로를 써라.

### ⓹ 차단 · 사용자 결정

**★2026-08-11 사용자 결정 4건 — 확정됐다. 다시 묻지 마라.**

| 무엇                                | 결정                                         | 근거 (코드/실측)                                                                                                                         |
| ----------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [BL-003] C1 **168h** 문턱           | **교체 — 「누적 24h × N회」** (N=3 `[가정]`) | [BL-641] 산출 P(168h 무실격) = **4.115e-09**. 39세션 24h 도달 0건 ⇒ 종전 문턱은 **P0 이 영구히 안 닫힌다**                               |
| `exchange_accounts` `0277c150` 삭제 | **삭제하지 않는다** — 비활성 + 409 핸들러    | FK `ondelete="RESTRICT"` ×3(`models.py:244,509,785`) + `exchange_exits` **103행** + `router.py:288` 핸들러 부재 ⇒ 지금 DELETE 는 **500** |
| 2번째 Bybit demo 계정               | **발급하지 않는다** ⇒ [BL-024] 재정의        | nightly 6회 중 4회 SKIP, 사유 = **소크와 계정 공유**. 소크는 살아 있다(컨테이너 41h · C2 41.11h 진행)                                    |
| 로컬 launchd soak-gate 타이머       | **정지**(2026-08-11 unload 완료)             | `StartInterval 1800` + `RunAtLoad true` + 게이트에 **flock 없음**. 실측 최근 종료 코드 **2** = 이미 실패 중                              |

- ⇒ **[BL-477]·[BL-529]·[BL-592] 는 「행 삭제로 자연 소멸」이 아니다.** 원장이 「가장 싸다」고
  적은 그 경로는 **DB 가 거부한다.** 진짜 처방은 `router.py:288` 의 **409** 이고 이건 다음 회차다.
- 거래소를 건드리는 모든 것 · DB 행 삭제·수정 · `launchctl` · `alembic downgrade` 는
  **전부 사전 승인**. 자동 재시도하지 않는다.

### ⓻ 다음 세션 — 착수 전 실측 의무

> **강등 tombstone (2026-08-12, 700줄 상한).** 2026-08-10 다섯 회차의 `다음 행동` 이력 29줄을
> 6줄로 압축했다(gate-freshness 가 세운 선례). 닫힌 것 = K([BL-517]) · L([BL-671]+[BL-688]+[BL-470]) ·
> F·J·E 트리아주 · I([BL-698])+[BL-306] · F([BL-307]). 전문 = `dev-log/2026-08-10-*.md` 5벌.
> ★**남기는 둘** ⑴ 백테스트 폼 제출이 **212 커밋 동안** 죽어 있었고(기본값이 `step` 격자를 벗어나
> 브라우저가 submit 을 발화조차 안 했다) 단위 17건은 `fireEvent.submit` 으로 native 검증을 우회해
> 못 잡았다 ⑵ **착수 전제는 거의 매번 반증된다**. 원문 = `git show 79cea10d:docs/status.md`.

> **강등 tombstone (2026-08-13 docs-diet, 700줄 상한).** 2026-08-11 다섯 회차 `다음 행동` **65줄 압축**.
> 닫힌 것 = ledger-truth 1~5 · #593→#594 · [BL-703] · [BL-701] · [BL-672] · [BL-705] · [BL-704] · [BL-559]② 기각.
> 원문 = `git show 8abd0d67:docs/status.md`, 회차별 ★반증은 `dev-log/INDEX.md` 각 줄.
> ★**INDEX 에 없어서 여기 남기는 셋** ⑴ **[BL-559]② 는 「제거」가 아니라 「기각」으로 닫혔다 — 처방이
> 반증된 첫 사례다.** 앞선 넷은 원장의 **전제**가 틀렸는데 이번엔 전제가 맞고 **처방**이 틀렸다
> (「사문이니 제거하라」가 **사문인 이유** — 상위 필터 2겹이 막고 있고 그 분기는 그 필터가 깨지는 날을
> 위한 방어선 — 을 안 봤다). ⇒ **「없다」와 「제거하라」 둘 다 되물어라.** ⑵ **상태줄에 `~~취소선~~`
> 금지** — `bl-audit.sh:171` 이 철회 표기로 보고 상태 근거에서 제외해 UNKNOWN 이 된다(판정줄에는 써도
> 된다). ⑶ **변이 복원에 `git checkout` 금지** — 커밋 안 된 편집을 같이 날린다. 스냅샷 되쓰기 + sha256.

★★★**이 회차가 마감에서 하나 더 밟았다 → [BL-706] 등재(⓪ 표 T).** `final-gates` 의 신호
4종(`screen.ok`·`codex.ok`·`g9.ok`·`vercel.ok`)은 **파일이 비어 있지 않은지만** 본다
(`check_signal()` = `[ -s "$f" ]`). 그런데 아래 ⓸ ④가 **모든 회차에 같은 `--run eod`** 를
시키므로, 문서를 그대로 따르면 앞 회차 신호를 그대로 물려받는다. 이 회차는 codex·화면검증·G9 를
**하지 않았는데 4/4 PASS** 였다. ★**사용자 실수가 아니라 문서가 만드는 구조적 사고다.**

★★★**2026-08-11 12:15Z 게이트 실측이 O([BL-641])의 표를 반증했다 — 그것이 다음 회차의 출발점이다.**
서버를 `19870ae3` 로 `git pull` 한 뒤 새 판정식으로 다시 읽었다(**재-pin 안 했고 창은 이어졌다** —
C2 가 60.94h → 60.97h 로 연속): `24h 창 **1/3회** · 최장 연속 **60.9723h** · 실격 **0** · C5 6/6`.

| 축        | [BL-641] 원장 (2026-08-08) | 2026-08-11 실측                      | 2026-08-12 재측정 (surface-demo-pack)                                               |
| --------- | -------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------- |
| 최장 연속 | **19.42h**                 | **60.97h** (3.1배)                   | **65.50h** (게이트) / 65.28h (원시 수명)                                            |
| 24h 도달  | **전 이력 0건**            | **1건** (지금 창)                    | **1건 / 40세션** — 원장에 박았다                                                    |
| 사망      | 「사망률은 그대로다」      | 마지막 08-07T15:10Z → **3.87일 0건** | 노출 **+86.25h 에 자동 사망 0건**. 단 CI 는 전 쌍 겹쳐 「내려갔다」를 **못 말한다** |

⇒ 그 항목의 상태줄·MTBF 표가 **낡았다** → **2026-08-12 정정 완료**(MTBF 13.39h → **24.17h**,
P(168h) 3.6e-06 → 9.6e-04, self-check 2/2).

★★★**여기 적혀 있던 한 문장이 거짓이었다** — ~~「그 표는 `user_stopped` **7건**을 자동 사망과 함께
세고 있어 P(24h) 추정 자체가 오염돼 있다」~~ → **2026-08-12 코드 대조로 반증.** `user_stopped` 는
`AUTOMATIC_DEATH_REASONS`(8종)에 **없고** `auto_death` 는 그 집합 소속 여부 단독이다. 정본이 코드
옆에 이미 적혀 있었다 — `soak_gate_predicate.py:39` 「`SessionDeactivationReason` 에서
`user_stopped` 를 뺀 것 = **자동 사망**」. 독립 대조로 `soak-gate.sh` 실격 목록의 `auto_death` 도
**8건**이고 `user_stopped` 는 0건이다. ⇒ **오염은 없었다.** 실재한 결함은 다른 것이었다 —
`절단` 열이 `alive + operational_dropped` 만 세서 40행이 `사망 8 + 절단 1` 로 인쇄됐다(같은 회차 수리).

> **강등 tombstone (2026-08-13 bl719-close, 700줄 상한).** O([BL-641]) 재측정 2블록(22줄) + `screen.ok`
> 미취득 8줄 압축. 원문 = `git show c3a39d0d:docs/status.md` · `11d9bdde`. 요지 = `dev-log/INDEX.md`.
> ★고를 때 여전히 유효한 셋 — **O 는 통짜 금지**(닫는 조건 = 사망률이 실제로 내려간다) ·
> **P([BL-438])는 잠복** · **R([BL-639])은 결정 선행**(계정 축 소유권 집합 범위는 사용자 몫).

★**착수 전 표본 1건을 열어라.** 두 회차 연속 상속 사실이 낡았다 — 08-11 은 20개 중 2건, 08-12 는 **6건**. 표를 읽지 말고 도구를 돌려라.

> **강등 tombstone (2026-08-16 deploy-activation · 700줄 상한).** harness A/B 3블록(12줄)과
> docs-diet/monorepo-realign 블록(6줄)을 압축했다. 원문 = `git show 821786ac:docs/status.md`
> (233~251행). 발견 색인 = `dev-log/INDEX.md`. 살아남을 세 줄:
> ⑴ **하네스는 걷어냈다**([ADR-030] 정본 — 조종 장치 230.7KB 회수 / 증거 장치 249.7KB 존치).
> ★근거를 갈아 끼우지 마라 — 「모델이 좋아졌으니까」가 아니라 **「40건에서 캐치 0, 커밋 노이즈 5배」** 다.
> ⑵ **B 회차를 죽인 것은 대조해 둔 위험 6건이 아니라 목록에 없던 7번째**(`TimeoutExpired` 미처리) —
> 남은 트리가 정확히 B 가 막으려던 상태였다(**AC 0건 실행 + `completed` 커밋**).
> ⑶ [ADR-029] 전면 재배치(PR #618·#619·#621·#623) 한 줄 = **「영역 판정이 pipefail+`grep -q`
> SIGPIPE 로 대형 diff 에서 비결정」**(FE 3레인 침묵 skip 실사고) + **치환 사각 4종**.
> ★**잔여 부채 1건(미착수)** — `AGENTS.md` 의 「게이트는 마지막 커밋 뒤에」에 **범위(회차 단위)가
> 없어** 무인 세션이 66분을 태웠다. 재개 조건 = ADR-030 §Consequences.

> **강등 tombstone (2026-08-17 auth-selfhost · 700줄 상한).** 08-13 contract-poc · 08-14
> gate-surface-close · 08-14 real-broker-e2e · 08-14 money-path · 08-15 soak-survival —
> 5블록(21줄)을 이 8줄로 압축했다. 원문 = `git show 9920bf9a:docs/status.md` (245~265행).
> 발견 색인 = `dev-log/INDEX.md`. 살아남을 다섯:
> ⑴ **[BL-717]** 결정적 export `contracts/openapi.json` + **orval(client:'zod') 채택**(hey-api 는 TS7 크래시로 탈락, [ADR-031]).
> ⑵ **「처방은 도래 판정과 함께 낡는다」** + **「스텁 초록 ≠ 정본 초록」**([LESSON-108], #627) · ⑶ **「2층
> 자기정리 하네스는 지어진 뒤 10일간 한 번도 작동한 적이 없었다」**([LESSON-109], #628).
> ⑷ **「소크가 돌리던 전략은 백테스트에서도 지고 있었다」** — 라이브 PF 0.223 / 백테스트 0.607. **판정 = 실자금 불가 · 데모 유지**(사용자 결정) · 헤지 모드 기각([ADR-032]). PR #630·#632·#633.
> ⑸ **「소크를 죽인 것은 우리 자신의 테스트 하네스였다」** — `close_position` 이 소유권을 안 봤다([BL-734]). PR #634·#635.

## ★소크 창 — 항목 선택을 지배하는 제약 (2026-08-16 갱신)

> **강등 tombstone (2026-08-23 beta-unlock · 700줄 상한).** 소크 창 실측치를 이 4줄로 압축했다.
> 원문 = `git show dfbdfad3:docs/status.md`. ★**여기 숫자를 인용하지 마라 — 게이트를 돌려라**(그 블록
> 자신이 그렇게 적고 있었고 실측은 2026-08-17 자였다). 남길 규칙 셋: ⑴ **실격 1건이면 T0 리셋**이고
> `apps/api/src` 수리는 재-pin 을 부른다 ⇒ **소크 코드를 안 건드리는 항목부터 고른다**([BL-547]·[BL-591]).
> ⑵ [BL-641] MTBF 층화는 **pin sha 로 층을 나눠라** — 창마다 다른 코드를 잰다. ⑶ **어둠은 C1/C2 를 한
> 시간도 깎지 않는다**(`ratio` 부등식이 레포에 없다).

~~**다음 행동 = [BL-737] 감시자 부활** / **[BL-641] 어둠 98.2% 처방**~~ → **둘 다 2026-08-15 종결**
(soak-watch-restore · clock-fill-sweep — 요약은 `dev-log/INDEX.md`, 원문은 `git show 539dae23:docs/status.md`).
남겨야 할 한 줄: **어둠은 C1/C2 를 한 시간도 깎지 않는다**(`ratio` 부등식이 레포에 없다). 크레딧의 진짜 축은
`세션 lifetime ∩ 귀속 구간 ∩ [창시작, now] ∩ phantom 커버리지` 이고 귀속 구간을 **여는 것은 `up`** 이다.

> **강등 tombstone (2026-08-16 deploy-activation · 700줄 상한).** ledger-thaw(PR #640) 5줄과
> surface-truth(PR #641) 29줄을 압축했다. 원문 = `git show 821786ac:docs/status.md` (280~318행).
> 발견 색인 = `dev-log/INDEX.md`. 살아남을 넉 줄:
> ⑴ **보안 P1 5건(S1~S5)** — 뿌리는 `APP_ENV` 미설정이고 `_enforce_production_safety` 가 조기
> 반환해 production 게이트 4개가 꺼져 있었다. 코드로 3개를 닫았고(`is_production or not debug`
>
> - `debug` 기본값 True→**False**) 나머지 하나는 [BL-753]. **그 3개는 2026-08-16 에 배포로 발효했다**(아래).
>   ⑵ **원장은 얼어붙지 않았다** — 스윕 사람 판정 축 **미판정 0건**. 판정은 이미 있었고 기계가 안 읽었을 뿐이다.
>   C1 자격 판정기(「지금 `up` 을 눌러도 손실 0인가」)가 그 회차 산출이고 이 회차가 처음 쓴다.
>   ⑶ ★★**변이 13종 중 하나가 진짜 초록** — `and limit is None` 가드에 커버리지 0(기본값이
>   `bar_close` 라 어떤 테스트도 그 분기를 안 지났다) ⇒ **[LESSON-087] 3/3** → `apps/api/AGENTS.md` §10.
>   ⑷ ★**`| tail` 이 pytest 대신 tail 의 rc 를 읽어** 「전부 초록」이라는 거짓 전건을 냈다(`6 failed` 가 찍힌 채 rc=0).

> **강등 tombstone (2026-08-17 auth-selfhost · 700줄 상한).** 08-16 deploy-activation(20줄) +
> 08-17 production-readiness(35줄)를 이 8줄로 압축했다. 원문 = `git show 9920bf9a:docs/status.md`
> (305~358행). 발견 색인 = `dev-log/INDEX.md`. 살아남을 다섯:
> ⑴ ★★**보안 노출은 닫혔다** — `/docs`·`/openapi.json`·`/redoc` 전부 **404**(인터넷 실측).
> 배포 절차 = `git pull` → `migrate`(dry-run) → `migrate --confirm` → **API 유닛 재시작** → read-back.
> 그 재시작 한 단계가 절차에서 통째로 빠져 있어 고쳐 둔 보안이 발효하지 않고 있었다(PR #642).
> ⑵ ★★**`git pull` 은 소크 창을 끊지 않는다**(실증 — 워커가 `./.soak/src` 스냅샷을 mount 한다).
> **창을 끊는 것은 `down`/`up`/`pin` 과 DB 실격뿐**이다. `migrate --confirm` 은 안 끊지만 매번 승인이다.
> ⑶ ★★**[ADR-033] self-host TimescaleDB CE 확정** — 관리형이 막힌 것은 업체 사정이 아니라 **TSL
> 라이선스**다. DB 24MB · hypertable 고유 기능 사용처 **0건** ⇒ 되돌리기가 덤프 한 번. 조건 3종
> (백업 [BL-767] · 디스크 경보 [BL-768] · 전환 트리거 4종)이 2026-08-16 에 **서버에서 발효**했다.
> ⑷ ★★**`bl-audit.sh:174` 함정** — `**상태:**` 줄에 `~~취소선~~` 을 쓰면 그 줄이 통째로 무시되고
> 섹션이 ACTIVE 로 떨어진다. 레포 관용구 `~~옛 문장~~ → 새 사실` 은 **상태줄·트리거줄에서만 예외**다.
> ⑸ ★**[BL-736] 의 디스크 94% 사고는 서버가 아니라 로컬 맥 Docker VM 에서 났다** — 서버는 40%.

→ ★★**2026-08-15 완료. C1 = 1/3회.** 창 2가 `b5e24fbf` pin 위에서 16:35:32Z 부터 돈다(위 §소크 창).

> **강등 tombstone (2026-08-22 밤샘 6차 · 700줄 상한).** 2026-08-16 서버 잔여([BL-767]/[BL-768] 발효)와
> 2026-08-17 Beta 진입 갈림(인증 self-host 전환) 두 블록 **17줄 → 이 3줄**. 원문 = `git show 8d3e0e27:docs/status.md`.
> 정본 = [ADR-033]·[ADR-034] · **남길 사실 둘**: [BL-070] 은 도메인 구매가 아니다(`qb.woosung.dev` 302 실측) ·
> 「gunicorn 보안헤더」는 대상이 없다(레포에 gunicorn 0건 → uvicorn `--no-server-header`, [BL-347]).

> **강등 tombstone (2026-08-17 sprint-parallel-lanes · 700줄 상한).** auth-selfhost 블록 압축. 원문 = `git show 9e71aa96:docs/status.md` · 정본 = [ADR-034](adr/034-auth-self-host-better-auth.md) · [LESSON-114].
> ★**남길 한 줄** — `docs-audit.sh` 는 살아 있는 `다음 행동 =` 을 **≤1 만** 재므로 **0 도 통과시킨다**. 진입점이
> 사라진 상태가 게이트를 초록으로 지나간다. 상한만 있고 하한이 없다([BL-643] 후속 후보).

---

## ★2026-08-16 beta-cutover — Beta 는 사용자 축 하나만 남았다

> **강등 tombstone.** 회차 서술 6줄 → 이 2줄. 원문 = `git show acdc12c5:docs/status.md`(321~327행).
> 살아남는 하나: ★★**사용자 결정 — Cloudflare Access 를 유지한다.** 걷으면 얻는 것이 0 이고 **개방 가입만 열린다** —
> 가입에 초대 토큰이 없고([BL-776]) 서버의 승인·발송 env 가 둘 다 미설정이다. [BL-070] 의 Access 축은 [BL-776] 뒤로 간다.

---

## ★2026-08-23 원장 다이어트 — 항목 368 → 39 · docs 33,422 → 22,946줄

**사용자 결정 3건이 판정 기준이었다.** ⑴ **실자금(mainnet) 안 간다** ⑵ **Beta 외부 공개 당분간 안 연다**
⑶ **멀티 거래소 안 한다 — Bybit 하나.** 이 셋에 걸린 항목 170건을 닫았다.
복원 좌표·상세 표 = `backlog.md` 헤더의 「원장 다이어트 tombstone」(`git show 21e40d5c:`).

| 축 | 이전 | 지금 |
| --- | --- | --- |
| `status.md` | 124,237 B (41.4k tok) | **49,845 B (16.6k tok)** |
| ACTIVE / DEFERRED / RESOLVED | 26 / 183 / 159 | **16 / 23 / 0**(파일 삭제) |
| `docs/` 전체 | 33,422줄 | **22,946줄** |
| BE 세션 착수 비용 | 60,198 tok | **약 37,000 tok** |

★**근거는 실측 + 외부 연구다** — ETH Zurich(2026-02, 실제 Python 태스크 138건)에서 **LLM 이 생성한
컨텍스트 파일은 성공률을 3% 떨어뜨리고 비용을 20% 올렸다**. 「에이전트는 너무 순종적이라 불필요한
지시도 전부 따른다」가 그 논문의 진단이다. ⓪ 표 51행 중 **43행이 이미 끝난 일의 취소선**이었고
그것이 매 세션 22k 토큰으로 청구되고 있었다.

★★**이 회차가 두 번 밟은 함정 — 강등하려던 `##` 절 안에 살아 있는 블록이 중첩돼 있었다.**
`## 변경 이력` 다음 `##` 이 716줄 뒤라 그 사이의 `### BL-` 섹션 **4개**(BL-641·547·619·529)가 함께
지워졌고, `## ...tombstone` 절 안에 **⓪ 표 자체**가 들어 있어 진입점을 통째로 날렸다.
**둘 다 「남은 건수」를 뺄셈으로 보고했다가 실측에서 드러났다.** ⇒ **절 단위 삭제 전에 그 범위
안의 `###` 를 먼저 세라. 그리고 삭제 후 건수는 반드시 다시 grep 해라.**

~~**다음 행동 = n7 4 lane 병렬 주행**~~ → **2026-08-24 완주** — 14 step 전부 `completed`(blocked·error 0건), PR #793~#796 → 통합 #797 머지(`159745b7`). ★러너 반증 2건: **`phases/index.json` 사전 등록은 충돌을 못 막는다**(러너가 lane 별 `status` 를 **인접 줄**에 써 첫 머지 후 나머지 3벌이 DIRTY — 사전 등록이 막는 것은 *배열 추가* 충돌뿐) · **러너가 충돌을 「CI 대기 시간 초과」로 오기록한다**(CONFLICTING 이면 CI 가 아예 안 도는데 빈 `statusCheckRollup` 을 「대기」로 읽는다). ★lane→CONTROL 인계 3건 처리: ⑴ 「관측 metric 은 `record_metric_safely` 로 감싼다」를 `apps/api/AGENTS.md` §4 에 등재(lane 은 가드레일 파일을 못 만진다) · ⑵ 기존 테스트 `test_parse_and_run_v2_raises_becomes_parse_failed` 가 **결함을 계약화**하고 있었다(미지 `RuntimeError` 를 사용자 Pine 문법 실패로 단정) — 이름·단언을 `…becomes_error` 로 정정 · ⑶ 신설 가드 2종의 사각을 기록: FE decision-surface 가드는 **이미지·번역 리소스·런타임 응답 문자열**을 못 잡고, BE metric AST 가드는 **별칭·동적 접근·모듈 alias** 를 못 잡는다.
~~**다음 행동 = `apps/web/AGENTS.md` 373줄을 200줄 아래로**~~ → **2026-08-24 n8 저작이 먼저 큐에 들어갔다.** 그 파일은 lane 프롬프트에 전문 주입되므로 **n8 주행 중에는 못 만진다** — n8 종결 후 CONTROL 단독으로 한다.
~~**다음 행동 = n8 3 lane 병렬 주행**~~ → **2026-08-24 완주** — 14 step 전부 `completed`(blocked·error 0건), PR #800~#802 → 통합 #803 머지(`ca477ede`). ★**바로 위 줄(n7)이 기록한 러너 결함 2건이 고쳐지지 않은 채 n8 에서 그대로 재발했다** — `phases/index.json` 충돌로 3 lane 중 **2벌**이 DIRTY(#801·#802), #802 는 그 때문에 CI 가 아예 안 돌아 러너가 또 「CI 대기 시간 초과」로 오기록. **회차마다 손으로 푸는 값보다 러너 수리가 싸다** — `phases/index.json` 을 lane 별 파일로 쪼개거나 러너가 머지 전 rebase 하게 하는 둘 중 하나. ★**lane AC 초록이 광역 green 이 아님을 #802 가 실증** — lane 이 `_StrategySessionsAdapter.__init__` 에 `user_repo` 를 추가하자 `tests/auth` 의 기존 조립이 `TypeError`, 4줄 인라인 조립이 `_async_dispatch_event` 의 `try` 본문을 동결 천장 **225→228** 로 밀었다. lane AC 는 `tests/trading`·`tests/common` 만 덮어 둘 다 못 봤고 **광역 CI 가 최종 검출자였다**(설계대로). 수리 = `_build_sessions_adapter()` 추출 + 테스트 시그니처 갱신. ★산출: 경계 밖 `select()` census **0건**(AST·`tasks/` 제외, 잔여는 `websocket_task.py` 1건) · `.env.example` 누락 **4건 종결**(`DOGFOOD_REPORT_OUTPUT_DIR`·`OPTIMIZER_STALE_THRESHOLD_SECONDS`·`STRESS_TEST_STALE_THRESHOLD_SECONDS`·`E2E_RATE_LIMIT_EXEMPT_EMAIL`) · FE feature 계약 테스트 커버리지 가드. ★신설 가드 3종의 사각: **동결 집합이 빈 대칭 테스트 3개는 항진명제**(`actual >= frozenset()`)라 판별력 0 이면서 통과 수를 늘린다.

**다음 행동 = `python3 tools/harness/execute.py --parallel 2 --stage stage/n9-close --confirm`** — n9 2 lane 저작 완료(2026-08-24). **원장을 여는 회차가 아니라 닫는 회차다** — [BL-520]·[BL-547](lane 1 `src/tasks/`) · [BL-453]·[BL-671](lane 2 `src/trading/`).
★**착수 전 AC red 5/5 측정 완료** · 기준선 green(`tests/tasks` 764 · `tests/trading` 1174 · `ruff` rc=0).
★**재료 실측에서 원장 좌표가 두 번 틀렸다** — [BL-520] 이 지목한 줄은 이미 감싸져 있었고(`record_metric_safely(\n qb_active_orders.dec\n)` 가 줄바꿈돼 grep 에 안 보였다), 진짜 위반은 AST 로 재야 나오는 **`try`/`except`/`finally` 본문 안 15건**이다. [BL-453] 의 **사용처 가드는 성립하지 않는다** — 필드명 기반 census 12건이 **12건 전부 위양성**(`bt.status` 는 진짜 Enum · `tally.channel` 은 로컬 dataclass)이라 **선언 계약 가드**로 좁혔다.
★**CONTROL 이 lane 밖에서 함께 닫는 것 4건** — [BL-383] RESOLVED 확정(`v2_adapter.py` 는 이미 `status="error"` 를 내고 n7 이 테스트도 정정했다) · [BL-811] 권장안 ⓒ 로 종결(자기 절이 「ⓒ 의 유일했던 단점이 사라졌다 — 현재 기본 권장」이라 적었다) · [BL-641] 재분류(Trigger 가 「소크 재기동 회차마다 재측정」이라 일회성 종결이 아니다) · `PRD` §5 정정(**「vectorbt 직접 실행 대비 99%」는 측정 불가** — vectorbt 는 2026-08-06 에 의존성째 제거됐다).
★그 뒤 CONTROL 단독 잔여 = `apps/web/AGENTS.md` 373→200줄 · 러너 `phases/index.json` 수리 · n8 신설 가드의 항진명제 3개 제거.
★**n8 재료는 후보 6건 중 3건이 코드 대조에서 무너진 뒤 남은 것이다** — ⑴ 금액 경로 `float()` 는 결함이 아니다(`LedgerSeedLeg.qty: float` 등 **pine_v2 엔진 계약으로의 변환**이고 엔진은 설계상 float 기반이다: `strategy_state.py` `: float` 74개) · ⑵ dashboard `error.tsx` 8곳 누락은 결함이 아니다(**`app/(dashboard)/error.tsx` 가 라우트 그룹 전체를 덮고** 「다시 시도」까지 갖췄다) · ⑶ [BL-489] 는 **트리거 미도래**(원장이 든 2-pass 처방 자체가 반증돼 착수하면 반증된 처방을 구현한다). **세 건 다 「문서·개수」를 읽고 「의미」를 안 읽어 생긴 것이다 — 같은 패턴의 N번째다.**
~~남은 세션 비용 축을 마저 깎는다 — `apps/web/AGENTS.md` 373줄(7,195 tok)을 200줄 아래로~~ → **2026-08-24 — 이 항목은 lane 이 될 수 없다.** 그 파일은 **모든 lane 프롬프트에 전문 주입되는 가드레일**이라
주행 중에 바뀌면 lane 마다 다른 규칙을 본다. **CONTROL 이 하네스 주행 전/후에 단독으로** 처리한다. → **2026-08-24 주행 종료로 조건 충족 — 위의 살아 있는 `다음 행동` 으로 승격.**
~~`apps/api/AGENTS.md` 508줄(10,040 tok)~~ → **2026-08-23 이 회차로 275줄**(30,122→18,878B). §9(Celery
prefork-safe) 119줄은 `docs/development/celery-prefork.md` 로 분리하고 포인터만 남겼다. **목표 <200줄은
아직 75줄 미달** — 남은 후보는 §3 트리·§2 규칙 표다. FE 도 같은 방법(긴 절 → `docs/development/` + 포인터)으로 깎는다.
★그 뒤의 개발 항목은 **⓪ 표에서 사용자가 고른다** — 열린 16건은 **ACTIVE 3 · PARTIAL 13** 이고,
11건이 데모 라이브 축이다(나머지 5건 = Pine 관측성·소크 게이트·DX 빌드캐시·TV webhook·로컬 origin).

## ★회차 이력 tombstone — 2026-04~08 (2026-08-23 통합)

> **강등 tombstone.** 종전에 이 자리에 있던 회차 tombstone **8개 · 219줄**을 이 한 절로 합쳤다.
> 그 절들 자신이 이미 「N줄 압축」이라 적혀 있었는데도 111줄·68줄이었다 — 압축본이 다시 자란 것이다.
> **원문 전량 = `git show 21e40d5c:docs/status.md`.**
>
> 합친 절: 2026-08-17 sprint-parallel-lanes tombstone — · 2026-08-17~18 통합 tombstone — night-3lane · g · 2026-08-18 backlog-triage tombstone — 원장 3분할 · 2026-08-18 night4-ci-truth tombstone — CI 거짓 · 2026-08-18 n5-ci-truth-close tombstone — aut · 2026-08-19 통합 tombstone — n6-authed-evidence · 2026-08-19~21 하네스 통합 tombstone — 러너 도입부터 밤샘  · 2026-08-04~15 소크 회차 tombstone — 후보 목록 · 판정 지
>
> ★**회차 기록은 이 파일의 일이 아니다.** 「지금 상태」는 status.md, 「무엇이 있었나」는 git log,
> 「무엇이 반증됐나」는 `docs/lessons.md`, 「왜 그렇게 했나」는 `docs/adr/` 다.
> 회차가 끝나면 **여기에 절을 만들지 마라** — 커밋 메시지와 `lessons.md` 로 보내라.

### ⓪ 다음 후보 — ★**고르는 것은 사용자다**

> **계약** — 살아 있는 행(취소선 없는 행) = `ACTIVE ∪ (PARTIAL ∧ 트리거 도래)`. **행 수를 여기 박지 마라**
> (박아 둔 수가 실제와 어긋난 사고가 2026-08-10 에 있었다) · **손으로 후보를 추가하지 마라** — 원장에서
> 도래 판정을 바꾸면 이 표가 따라온다. ★★**이 표를 그대로 읽으면 안 된다** — 종결·기각된 행이 살아 있는
> 행으로 남아 **닫힌 결함이 최상위 추천으로 보인 사고**가 있었고(2026-08-10 status-table-resync),
> 어느 게이트도 그것을 안 잡는다(`ledger-vitals` 는 **행 수 ≥3** 만 본다). ★대조는 원장으로 하고
> **양쪽이 비면 ABORT** — 빈 입력이 「일치」로 새는 것이 그 회차가 두 번 밟은 함정이다.
>
> **강등 tombstone (2026-08-23 · 700줄 상한).** 서문 25줄 → 이 8줄. 원문 = `git show dfbdfad3:docs/status.md`.

| #      | 후보 (= ACTIVE ∪ (PARTIAL ∧ 도래))                                                                                                                                                                                                                                                                                                                                                                                                                                   | P   | 추천                                                                                                              | 난이도 | 소요            | `apps/api/src` | 왜 지금 (= 트리거 도래 근거)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ----------------------------------------------------------------------------------------------------------------- | ------ | --------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **O**  | [BL-641] soak C1 문턱 해석 — MTBF 재측정 (사망률은 그대로다)                                                                                                                                                                                                                                                                                                                                                                                                         | P1  | ★★★                                                                                                               | 중     | M               | **건드림**     | ★**2026-08-11 도래.** Trigger 앞절 「[BL-003] 재계획 시 즉시」가 발화했다 — 사용자 결정으로 C1 문턱이 **168h → 누적 24h × 3회**로 교체됐다(미반영이 [BL-701]). ★**기계는 미도래를 냈다** — 트리거에 「소크」가 들어 있어 소크 축으로 버킷하고 **절의 접속을 반쪽만** 읽었다                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **J**  | [BL-547] 원장 seed 가 다음 tick 에 조용한 고아가 될 수 있다                                                                                                                                                                                                                                                                                                                                                                                                          | P2  | ★★                                                                                                                | 중     | M               | **건드림**     | ★★★**2026-08-11 `/metrics` 1회 실측으로 「미도래」가 반증돼 ACTIVE 로 올라왔다** — `qb_live_position_divergence_total{category="exchange_only"}` = **3.0**. 트리거가 요구한 「실제로 오르는 것이 관측될 때」가 충족됐고, 본문의 「한 번도 오른 적이 없다」도 함께 무너졌다                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **AP** | [BL-774] TradingView webhook 이 **body 기반 HMAC** 을 요구한다 — 동적 alert 본문에서 성립하는지 **미확인**                                                                                                                                                                                                                                                                                                                                                           | P2  | ★★                                                                                                                | 중     | M               | 0줄            | ★첫 step 은 코드 수리가 아니라 **실측 1건**이다 — 정적 body 면 동작하고 `{{close}}` 류 placeholder 면 매번 401 이다. idempotency key 가 optional query 라 **같은 결정에 묶여 있다**(고정=충돌 / 생략=중복 주문). 자동 생성안은 [BL-773] 에 의존                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **BO** | [BL-811] `--deferred-only` 의 두 레그가 **같은 BE 를 서로 다른 origin 으로** 요구한다 — e2e 는 dev `:3100` · 화면 증거 authed 는 프로덕션 `:3110` 인데 CORS 는 단일 값이다                                                                                                                                                                                                                                                                                           | P3  | ★★                                                                                                                | 하     | S~M             | ✗              | 거짓 초록은 안 난다(전제 프로브가 죽는다). 잃는 것은 **한 번에 끝나는 종결**이고, 「유예 원장이 비어야 종결」 규약과 어긋난다                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

> ★**강등** — 2026-08-16 에 5행([BL-026]·[BL-726]·[BL-729]·[BL-730]·[BL-731], 원문 `git show b5e24fbf:docs/status.md`), 2026-08-17 야간에 4행([BL-725]·[BL-732]·[BL-735]·[BL-737], 원문 `git show 0875789c:docs/status.md`)을 지워 700줄 상한 안에서 신규 행 자리를 만들었다. 지운 것은 전부 **이미 취소선이던 사문**이다.
> ★난이도·소요는 `[가정]`이고 preflight 에서 재측정한다.
> ★**이 표에 없던 것들은 사라진 것이 아니다** — `tools/scripts/bl-audit.sh --list DEFERRED` 151건이
> 트리거 미도래로 대기 중이고, 각 섹션의 `**트리거 판정:**` 줄이 **무엇이 막는지**를 적고 있다.
> ★**종전 표의 F·J·E 는 전부 내려갔다.** F([BL-477]+[BL-529])는 PARTIAL 이라 ACTIVE 가 아니고,
> J 의 안전한 XS 3건([BL-385]·[BL-386]·[BL-534])과 E([BL-654])는 **동승 트리거**다 —
> 「pine_v2 coverage 후속」·「parity 산술을 손댈 때」·「고레버리지 백테스트를 신뢰해야 할 때」.
> 셋 다 단독 착수 시 값이 0이라고 트리거 자신이 적었다.
> ★~~실격 귀속 `undecided` 7건 행 단위 대조~~ → **2026-08-08 완료**(soak-attribution-close).

## 📌 소크 운영 상비 참조 (창이 도는 동안 계속 유효)

> 아래는 특정 회차가 아니라 **소크를 굴릴 때마다 다시 밟는 함정**들이다. 회차별 숫자는
> dev-log 로 갔다 — 여기에 낡은 T0/baseline 을 남겨두면 다음 사람이 죽은 세션을 현행으로 읽는다
> (2026-08-03 실측 사고: 이 절이 이미 죽은 세션의 창 종료 시각을 가리키고 있었다).
> ★**`AGENTS.md` 는 읽지 마라 — 자동 로드된다.** `CONTEXT.md`·`docs/` 정본은 반대다(읽어야 들어온다). (`apps/api/AGENTS.md`·`apps/web/AGENTS.md` 는 ADR-027 부터 그 디렉터리 파일을 열면 자동 로드.)

### ★새 counter 를 읽는 법

★★**2026-08-11 — `/metrics` 는 이제 토큰 없이 401 이다**(fail-closed 전환). 종전에 여기 있던
`curl -s localhost:8100/metrics | grep …` 은 **`-f` 가 없어서 401 본문이 rc=0 으로 파이프에
흘러들고 grep 이 0 매치**를 낸다 ⇒ 읽는 사람은 **「counter 미발화 = 이벤트 없음」으로 오독**한다.
이 레포는 「이벤트 부재는 정지의 증거가 아니다」를 이미 한 번 밟았다. 아래를 써라.

```bash
# ⑴ 권장 — 직독. 인증이 없고 게이트가 쓰는 것과 같은 경로다 ([BL-620])
cd apps/api && PROMETHEUS_MULTIPROC_DIR=.metrics uv run python -c '
import sys
from prometheus_client import CollectorRegistry, generate_latest, multiprocess
r = CollectorRegistry(); multiprocess.MultiProcessCollector(r)
sys.stdout.buffer.write(generate_latest(r))' | grep qb_live_conditional_fill_ownership_total

# ⑵ HTTP 로 봐야 하면 **`-f` 와 토큰을 반드시 함께** — 둘 중 하나만 빠지면 조용히 0 매치다
TOKEN="$(sed -n 's/^PROMETHEUS_BEARER_TOKEN=//p' apps/api/.env.local)"
curl -sf -H "Authorization: Bearer ${TOKEN}" localhost:8100/metrics \
  | grep qb_live_conditional_fill_ownership_total || echo "✗ 취득 실패 — 0 매치와 구별해라"
```

| outcome                      | 뜻                                                                    |
| ---------------------------- | --------------------------------------------------------------------- |
| `agree`                      | 시뮬도 체결했을 자리에서 원장도 체결했다                              |
| `engine_only_suppressed`     | ★**형 A 차단** — 시뮬은 체결했을 텐데 원장에 없다                     |
| `ledger_only_adopted`        | ★**형 B 차단** — 원장은 체결했는데 시뮬은 아직이다                    |
| `ledger_only_orphan`         | 원장 체결의 `trade_id` 에 해당하는 pending 이 엔진에 없다(**무동작**) |
| `ledger_fill_out_of_window`  | 창(300봉) 밖 체결 — 엔진이 표현 못 한다                               |
| `ledger_unreadable_fallback` | 원장을 못 읽어 그 tick 만 현행 시뮬로 되돌렸다                        |
| `other`                      | 알려지지 않은 census 키(cardinality 방어). ★오르면 이름을 찾아라      |

★**`agree` 대비 나머지의 비율이 「백테스트가 현실을 얼마나 잘 예측하나」의 첫 실측치다.**
지금은 아무도 그 값을 모른다 — Trust Layer 는 **우리 자신의 얼린 출력**과 대조할 뿐이고 외부
오라클(P-4)은 [ADR-020] 이 이연했다. 값이 쌓이면 그때 백테스트 체결 모델 보정을 **근거로** 정한다.

### 첫 명령 (순서 있음)

```bash
tools/scripts/soak-gate.sh                 # ★첫 명령. PASS/FAIL/UNKNOWN + 누적 시간
tools/scripts/soak-stack.sh status         # 고정 커밋 · 활성 세션 · main 조상 여부
tools/scripts/soak-stack.sh commit         # 소크가 **실제로 돌리는** 커밋 (프로세스 기준)
docker logs quantbridge-worker 2>&1 | (cd apps/api && uv run python \
  scripts/classify_direction_divergence.py)          # 발산 재판정 (회복식)
```

### ★[ADR-025] 판정 — **Accepted** (2026-08-06)

노출 12.28h 에서 사전등록 4관측량 전건 충족 — ① phantom **0건**(관측 4건 전부 `replay_lag`,
p≈0.020 기각 성립) · ② 자동 사망 **0건** · ③ 조건부 발주 **84건**(≥40) · ④ 카운터 차분
**+223**(형 A +183 · 형 B +6 — 양쪽 수리 갈래 발화). 실측 전문 =
[ADR-025](./adr/025-conditional-fill-ownership.md).

### ★착수 전 반드시 읽을 것 (2026-08-21 정정본)

1. ★★★**데스크 회차가 반증하는 것은 「내가 적은 산문」이고, 소크가 반증하는 것은 「코드가 실제로
   하는 일」이다.** 계측 부채는 오프라인에서 검증 가능하고 소크는 느리고 위험하다 — 그래서
   **이 루프는 자기 지속된다.** 데스크만 돌면 코드는 한 번도 안 재진다.
2. ★★**소크 전후로 거래소를 flat 으로 맞춰라.** 세션 `DELETE` 204 는 **아무것도 flat 하지
   않는다**(0.03 포지션 + 조건부 1건 잔존 전례). T0 직전 `FLAT=YES` 를 확인해라.
3. ★★**호스트 `/metrics` 는 워커 증가를 몇 초 늦게 비춘다** — **이벤트 직후 읽기로 판정하지 마라.**
4. ★**`idle` 은 완료가 아니다** · **`:3000` 은 다른 앱(Kairos)** · API `:8100` · DB `:5433`(격리 스택).
5. ★★**재기동은 손으로 밟지 마라 — `tools/scripts/soak-restart.sh`**(기본 dry-run · `--confirm` 으로
   집행 · `FLAT=YES` 아니면 정지). **감시는 `tools/scripts/soak-watch.sh --install`** 이 맡고
   **게이트 타이머를 대체한다**(게이트에 flock 이 없어 같이 돌리면 표본이 경합한다 — 2026-08-15
   실측 0.7초 간격 중복 2건). ★설치본이 낡았는지는 **`soak-watch.sh --status`** 가 답한다(rc=1 이면
   낡음) — 「타이머가 waiting」은 건강 신호가 아니다. ★**watch 는 단일 장애점**이라
   `OnFailure=…soak-watch-alarm.service` 를 붙였다([BL-737] — 41시간 침묵의 대가).
6. ★**게이트를 파이프에 넣지 마라**(rc 를 삼킨다) · **`cd apps/api && set -a; . ./.env.local` 금지**.
   정본 = [`gates-and-traps.md`](./development/gates-and-traps.md) §함정.
7. ★**표적 변이는 CONTROL 이 직접 집행**(`git checkout` 금지 · **sha256 왕복 복원 대조**).
   치환 문자열이 다른 함수와 겹치는지 **먼저 세라**. ★**TS 대상에 타입 수준 변이는 변이가 아니다**
   (`as undefined` 는 타입 소거 — 2026-08-21 실증).
8. ★**브랜치 접두사는 `stage/` 또는 `feat/`** · **`QB_PRE_PUSH_BYPASS=1` 금지**(Golden Rule 집행기를
   끄는 스위치다) · ★**pre-commit 이 `ruff format`·`prettier --write` 를 돌린다 — 커밋 후 게이트를
   다시 재라.**

> ★**2026-08-21 정정 3건.** 종전 이 목록은 **`Clerk JWT 는 60초`** 와 **`세션 등재는 Clerk 의 `azp`
요구로 헤드리스 불가`** 를 적고 있었다 — **[ADR-034] 로 Clerk 은 2026-08-17 에 제거됐다**(지금은
> self-host Better Auth). 그리고 「현행 소크 눈금」이 마이그레이션 head 를 **`20260801_0001`** 이라
> 적었는데 실제 head 는 **`20260817_0002`** 다. 이 절의 머리말이 「낡은 T0 를 남기지 마라」라고
> 경고한 바로 그 병을 **이 절 자신이 앓고 있었다.**

