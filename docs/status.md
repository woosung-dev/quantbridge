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
> 가입에 초대 토큰이 없고 서버의 승인·발송 env 가 둘 다 미설정이다.
> ~~[BL-070] 의 Access 축은 [BL-776] 뒤로 간다.~~ → **2026-08-30 [BL-776] 종결** — 2026-08-19 결정
> 「개방 유지 + 카피 수정」이 초대 게이트를 짓지 않기로 했으므로 Access 축이 기다릴 선행이 없다.
> **막는 것은 결정 ⑵ 하나**다(Beta 를 열지 않는다).

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

~~**다음 행동 = n9 2 lane 병렬 주행**~~ → **2026-08-24 완주** — 8 step 전부 `completed`(blocked·error 0건), PR #806·#807 → `stage/n9-close`. **RESOLVED 4건**([BL-547]·[BL-671]·[BL-383]·[BL-811]) + **PARTIAL 전진 2건**([BL-520]·[BL-453]) ⇒ 열린 결함 **16 → 12**.
★**「6건 종결」 예측이 2건 과했다** — 착수 전엔 [BL-520]·[BL-453] 도 닫힌다고 봤지만 둘 다 실측이 범위를 넓혔다: [BL-520] 은 `src` 전량으로 재니 `live_signal.py` 밖에 **22건이 더** 있었고, [BL-453] 사용 축은 **타입 정보 없이는 못 닫는다**.
★★**lane 이 세운 가드가 기존 가드 2개를 깼다** — ⑴ n7 의 `test_metric_guard_census.py` 가 미보호 census 를 **정확히 36항목/합 79** 로 동결하는데 **동등 비교**라 감소도 red 다(재측정 32/63, 신규 0) · ⑵ `test_metrics_multiproc.py` 가 `"<gauge>.set("` **문자열**을 찾는데 `record_metric_safely(g.set, value)` 는 괄호가 없어 목록이 빈다. **저작 실수** — 이미 metric census 가드가 있는데 찾지 않고 두 번째를 만들게 했다. 지금 레포에 metric 가드가 둘이다.
★변이 자기점검 4/4 기대 일치(음성 대조 1건 포함). ★`phases/index.json` 충돌은 **n7·n8·n9 3회차 연속** 같은 자리에서 났다.

~~**다음 행동 = 러너 `phases/index.json` 동시 갱신 수리**~~ → **2026-08-24 수리 완료**([BL-820]). **소유자를 하나로 되돌리는 것이 답이었다** — 그 파일이 담는 것은 오케스트레이션 상태지 lane 의 산출이 아니다. `_in_linked_worktree()` 로 연결 워크트리를 판별해 lane 러너가 공유 파일을 **쓰지도 커밋하지도 않게** 했고(순차 모드는 종전대로 — 거기엔 경합이 없다), `--status` 는 대신 **워크트리의 lane 파일을 읽는다**(종전에는 메인 파일만 읽어 주행 내내 `pending` 만 찍었다). ★**같이 고친 둘째 결함** — `_wait_ci_and_merge` 가 `mergeable` 을 **요청해 놓고 안 읽어** 충돌 PR 에서 45분을 태운 뒤 「CI 대기 시간 초과」로 적었다. 이제 즉시 충돌이라 보고하고 나간다. 검증: 신규 `tests/harness/test_execute_shared_index.py` 8건 · **변이 3/3 red** · 기존 하네스 41건 무회귀.
★동승 2건 처리 — ⑴ **metric 가드 2벌 중 n9 것을 삭제**했다. 변이(try 본문에 raw metric 심기)를 **둘 다 잡았고**, n7 census 는 「감싸이지 않은 것 전부」를 세므로 try 밖까지 덮어 **엄격히 포섭**한다. ⑵ **항진명제 2개 제거**(BE `actual >= frozenset()` · FE 빈 allowlist 필터). ★**「3개」라고 적었던 것은 과했다** — env 의 `_env_example_keys() >= _ALLOWLIST_NON_SETTINGS` 는 allowlist 가 11개라 실제로 잰다.

~~**다음 행동 = `apps/web/AGENTS.md` 373줄(7,195 tok)을 200줄 아래로**~~ → **2026-08-24 완료**(PR #811 머지 `63f8320f`) — 아래.
~~★그 뒤 CONTROL 단독 잔여 = `apps/web/AGENTS.md` 373→200줄~~ → **2026-08-24 완료 — 373→199줄**(21,587→17,348B · −19.6%, PR #811). 같은 날 러너 수리([BL-820])와 항진명제 제거도 닫혀 **CONTROL 단독 잔여 = 0**.
★**이 회차의 산출은 줄 수가 아니라 반증 9건이다** — 자동 로드 층이 lane 에게 거짓을 가르치고 있었다.
⑴ **`ActionResult<T>` 는 레포에 존재한 적이 없다**(`features/*/api.ts` 함수 55개 중 **0건** · 문서의 타입 블록은 zod4 에서 컴파일도 안 된다). ⑵ **배포는 Vercel 이 아니다**(`vercel.json`·`.vercel`·CI `vercel` **0건** — 실제는 오라클 A1 + Cloudflare Tunnel + `output: "standalone"`). ⑶ **`min-width` 0건이 거짓**(`globals.css:4017` — 그것을 만든 것이 **그 절 자신의 `max-[N]:` 경계 처방**이다. `DESIGN.md` 2곳도 같은 거짓을 복사 중이었다). ⑷ **`[@media(...)]:` Tailwind 변형 · `account-button.tsx` 선례가 둘 다 실재하지 않았다** — 그 파일 주석은 오히려 **반대**를 경고한다(codex P2 실사고 재현 절차를 문서가 지시하고 있었다). ⑸ **bare `"zod"` = v3 라는 §8 의 근거가 거짓**(zod@4 에서 `require('zod').z === require('zod/v4').z` → **true**). ⑹ **`biome.jsonc` 가 `components/ui` 수정을 막는다는 방향이 반대**(Biome **자신이** 고치는 것을 막을 뿐 · 부작용으로 그 디렉터리는 lint 게이트 **밖**). ⑺ **「1회성 토큰 reconciliation」이 거짓**(`button.tsx` 설치 후 4회 더 — 제약은 횟수가 아니라 **범위**다). ⑻ **`if(isLoading)/if(error)` 금지가 실태와 정반대**(조기 반환 15건 · `<Suspense>` 1곳). ⑼ **`e2e/design-canon-responsive.spec.ts` 는 CI 에서 안 돈다**(문서는 「집행」이라 적었다).
★★**「lint 가 막아 준다」류 문장은 이번엔 5건 전부 참이었다** — 2026-08-22 사고 **직후에 다시 쓰인 문장들**이라 그렇다. 대신 **그 사고를 안 지난 축**(§8 zod · §9 shadcn · §11 `any`)이 거짓이었다. ⇒ **정정은 정정된 축만 살린다 — 옆 축은 같이 안 낫는다.**
★**숨은 취약점 1건** — `useHookAtTopLevel` 은 `biome.jsonc` 에 **이름이 없고** `domains.react: "recommended"`(`:54`) 한 줄로만 켜진다. 그 줄을 지우면 조용히 함께 죽는다(문서가 그 의존을 안 적고 있었다).
★**`live-smoke.yml` 은 이름이 약속하는 것을 안 잰다** — hooks 판별식 **0줄**(경로 glob), 재는 것은 공개 5라우트의 `console.error` 개수, authed 훅 **0회**, required check **아님**, base `feat/**` 이면 트리거조차 안 걸린다.
★**내 정정도 한 번 살이 쪘다** — 초판이 340줄이었다. 원인은 「종전 문장은 X 였고 거짓이었다」를 파일 안에 쓴 것 — **정정의 서사는 커밋 메시지가 갖고 파일은 참인 문장만 갖는다**([ADR-026]). 이 규칙을 적용해 340→199.

~~**다음 행동 = ⓪ 표에서 다음 항목을 고른다**~~ → **2026-08-24 n10 저작으로 확정.**

~~**다음 행동 = n10 2 lane 병렬 주행**~~ → **2026-08-25 완주** — 13 step 전부 `completed`(blocked·error 0건), PR #813·#814 → `stage/n10`.
★**산출 실측** — 미보호 metric census **63 → 30**(동결 키 32→17) · `record_metric_safely` 의 첫 인자에서 `.labels()` 가 **가드 밖**이던 **14건 → 0**(정답 형태 = `_count_safely` 또는 `lambda` 지연 평가) · metric 삭제 **0건**(제거·추가 1:1 대조) · `xfail` 신설 **0건**. 좌표 축 = `globals.css` 줄 번호 인용 **0건**(앵커 전환이고 삭제가 아니다 — `DESIGN.md` 순증 **+5줄**) · 철거된 FE 규칙 문서 경로 **3종** 참조 **0건**(경로명은 `d1c8fd67` 커밋이 갖는다 — 여기 적으면 감사기 자신이 잡는다) · 신설 `tools/scripts/doc-coord-audit.py`(`--check`·`--dead-paths`·`--selftest`).
★**CONTROL 대조 — 두 lane 다 실체가 있었다.** 감사기 판별력은 selftest 를 믿지 않고 **실파일에 위반을 심어** 쟀다(`DESIGN.md` 좌표 1건 · `ui-store.ts` 죽은 경로 1건 → 둘 다 rc=1, 복구). 새로 심은 좌표의 참·거짓도 대조했다 — `apps/web/AGENTS.md` §3·§9 는 실재하고 인용된 규칙 문장도 그 안에 있으며, `auth-server.ts` 주석이 「3곳 → **4곳**」으로 고친 호출부 수는 실측과 일치한다(비-테스트 4곳).
★★**러너 부모 프로세스가 주행 39분 시점에 환경에 의해 kill 됐다.** lane B 는 이미 머지된 뒤였고 lane A 는 step 8/9 에서 멈췄다. **step 마다 커밋하는 설계 덕에 손실 0** — 워크트리에서 같은 러너를 재기동하니 step 8 만 이어 돌았다. ⇒ **러너를 대화 세션의 백그라운드 태스크로 띄우지 마라. 별도 세션 그룹으로 분리해라**(`start_new_session=True` · `nohup`). 이 실패 모드는 `/harness` 문서가 이미 적어 두었고 **내가 안 따랐다.**
★**[BL-650] 소멸성 표본 재채취** — `du -sm apps/web/.next` = **1,711MB** 로 3번째 측정점과 **같다**(이 회차는 메인에서 FE 빌드를 안 돌렸다). 측정점은 여전히 셋이다.
★**2026-08-25 n11 preflight 재채취도 1,711MB** — 그리고 이번엔 **같은 값인 이유를 직접 쟀다**: `stat` 상 `apps/web/.next` mtime 이 **2026-08-22 01:30** 으로 n10·n11 사이에 메인이 FE 를 한 번도 빌드하지 않았다. **「4번째 측정점」은 생기지 않았다 — 같은 표본을 세 번 잰 것이고 측정점은 셋 그대로다.** ⇒ 이 항목을 닫으려면 재채취가 아니라 **메인에서 FE 빌드를 돌린 뒤** 채취해야 한다.

~~**다음 행동 = 남은 census 30건이 「결과 보고 `try` 본문」 안인지 실측**~~ → **2026-08-25 `n11-census-scope` lane 재료로 확정**(step0·step2). 아래 원문은 그 lane 의 근거로 보존한다.
**남은 census 30건이 「결과 보고 `try` 본문」 안인지 실측** — 이 측정 하나가 [BL-520] 을 가른다(범위 밖이면 RESOLVED · 안이면 n11 lane 재료). `apps/api/tests/common/test_metric_guard_census.py` 의 `_result_reporting_try_count` 스캐너를 `_FROZEN_CENSUS` 30건에 교차해라.
★**왜 지금 재야 하나** — 현재 「해로운 자리 0건」 단언은 **손으로 고른 후보 4쌍**만 본다(`_HARMFUL_MUTATION_CANDIDATES`). 30건 전체를 덮지 않으므로 **BL-520 의 종결 여부는 지금 미측정**이다.

~~**다음 행동 = n11 3 lane 병렬 주행**~~ → **2026-08-25 2/3 완주** — `n11-census-scope`(4 step) · `n11-strenum-mypy`(3 step) 이 PR #819·#818 로 `stage/n11` 에 머지됐고, `n11-guard-truth` 는 step0 에서 `blocked`.
★**러너 분리는 성공했다** — macOS 에 `setsid` 가 없어 `nohup setsid` 는 죽는다. `subprocess.Popen(start_new_session=True)` 로 띄워 PPID=1 · 자기 PGID · 세션 리더(`Ss`)를 `ps` 로 확인했다. n10 의 39분 kill 은 재발하지 않았다.
★★**`blocked` 가 진짜 결함이었고, 그 결함이 그 lane 의 주제 자체였다** — `doc-coord-audit.py --dead-paths` 가 레포에서 **rc=1** 이고 원인은 `docs/status.md:368` 의 「철거된 FE 규칙 문서 경로(3종) 참조 **0건**」이라는 n10 산출 요약 문장 **자신이 그 3건**이었다는 것. 감사기(`c3cac3f4`)와 그 줄(`d1c8fd67`)이 **같은 PR #815 로 main 에 들어왔으므로 감사기는 태어난 순간부터 red 였고 아무도 돌리지 않았다.** 「감사기가 있다 ≠ 감사가 돈다」를 lane 이 착수 5분 만에 자기 자신으로 실증했다. ⇒ CONTROL 이 그 줄에서 경로명을 뺐다(감사기는 **안 건드렸다** — red 는 고칠 신호이지 약화할 신호가 아니다). 경로명 원문은 `d1c8fd67` 이 갖는다.
★**내 저작 결함 1건** — step0 은 테스트 1의 `--check` 에는 「현재 실측 rc=0」을 적었는데 테스트 2의 `--dead-paths` 는 **재지 않고 rc=0 을 전제**했다. 재료 실사에서 한 축을 빠뜨리면 그 전제가 곧 AC 가 되어 lane 을 세운다([BL-814] 와 같은 가족).

~~**다음 행동 = `n11-guard-truth` lane 재주행**~~ → **2026-08-25 완주** — 3 step 전부 `completed`, PR #821 → `stage/n11`. **n11 은 10 step 전건 완주**(PR #818·#819·#821), 통합 PR **#820**.
★**CONTROL 대조 — lane 주장을 코드로 다시 쟀다.** 동결 census **30건 = in-scope 0 · out-of-scope 30**(결과 보고 try 실측 **137건**). 판별력은 selftest 를 믿지 않고 **실파일 변이 2벌**로 쟀다: ⑴ census 밖 새 metric 을 shape-A try 에 심으면 **개수 축만** red(범위 축은 침묵 — `_census_scope_counts()` 가 `_FROZEN_CENSUS` 키만 분류한다) · ⑵ **census 안 metric**(`qb_order_rejected_total`)을 shape-A try 에 심으면 **범위 축 2건 + 개수 축 1건 = 3건 red**. 둘 다 sha256 대조로 원복했다. ⇒ **범위 분류기는 살아 있다.**
★**[BL-520] RESOLVED — 본문 삭제**(원문 = `git show 69c7cc96:docs/backlog.md`). 원장이 못박아 둔 닫는 조건(「30건을 그 스캐너에 교차하는 실측 1건」)이 충족됐고 결과가 **범위 밖**이라 사전 합의대로 종결이다.
★**단, 「커버리지 4쌍 → 30건」이라고 적으면 거짓이 된다** — `_harmful_scan_candidates()` 는 **여전히 4쌍**이다(in-scope ∪ 4쌍 = ∅ ∪ 4쌍). 바뀐 것은 **집합이 아니라 유도 규칙**(손으로 고른 목록 → 기계 유도)이고, `test_harmful_scan_covers_every_in_scope_census_entry` 는 in-scope 가 0인 지금 **항진명제**다. 판별력을 지탱하는 것은 그 옆의 `_lower_bound_is_still_covered`(4쌍)와 「결과 보고 try ≥100」 대조다.
★★**원장 구조 결함 1건 — `ledger-vitals` ② 가 이제 거짓말을 요구한다.** [BL-520] 을 지우면 ⓪ 표가 2행이 되는데 ② 는 **≥3행**을 강제한다. 그런데 backlog 실측은 **DEFERRED 10 · PARTIAL 1**([BL-641], 「닫을 수 있는 일이 아니라 소크 창마다 반복하는 측정」으로 재분류됨) 뿐이라 **표 정의(`ACTIVE ∪ (PARTIAL ∧ 도래)`)를 만족하는 세 번째 후보가 실제로 없다.** 이번엔 기존 `AP` 행 관행(도래 아님을 표기하고 싣는다)을 따라 [BL-650] 을 A행에 올렸지만, **이것은 규칙이 사실을 이긴 자리다** — ② 의 상한 근거를 사용자가 다시 정해야 한다. → ★**2026-08-25 사용자 결정 — ② 하한 ≥3→≥1.** 표의 불변량을 「고를 수 있다」에서 「진입점이 실재한다」로 좁혔다(집행 = `ledger-vitals.sh` · ADR-037 개정 주석).

~~**다음 행동 = 통합 PR #820 판단**~~ → **2026-08-25 머지**(`00410a22`). 회차 정의 철거 = #822(`608af7b6`) — `phases/` 는 `index.json`(`[]`) + `README.md` 만 남았다. 4번째 측정점 채취 = #823.

★★**[BL-650] 4번째 측정점을 채취했고, 그 과정에서 내 처방이 반증됐다.** 메인에서 `pnpm build` 를 돌린 뒤 재니 `du -sm apps/web/.next` = **1,715MB**(빌드 전 1,711MB, **+4MB**). 「메인 FE 빌드 직후에 채취해야 측정점이 는다」고 적었는데 **빌드는 이 숫자를 거의 안 움직인다.**
★**구성을 갈라 보니 이유가 나온다** — `.next/dev` = **1,618MB**(그중 `dev/cache` **1,462MB**)이고 **프로덕션 빌드 산출 전체는 85.7MB** 다. 즉 이 표본의 **94.4% 가 dev 서버 turbopack 캐시**이고, 그것은 `mise run fe` 가 돌 때만 자란다. ⇒ **재야 할 축은 `.next` 총량이 아니라 `.next/dev/cache` 이고, 자라게 하는 것은 빌드가 아니라 dev 서버 가동 시간이다.**
★**선행 측정점 재해석** — 「1.99GB 사망 · 593MB 무해」도 같은 `du -sm .next` 라 **둘 다 dev 캐시가 지배한 값**이다. 축은 처음부터 일관됐고, 틀린 것은 **그것을 늘리는 방법에 대한 내 처방**뿐이다. `mise run fe` 의 1GB 경고선이 `.next` 총량을 재는 것도 결과적으로 옳은 축을 재고 있었다.

★★**2026-08-25 [BL-650] 종결 — 사용자 결정 「기동 시 자동 소각」.** `mise run fe` 가 `.next/dev/cache` ≥ 1GB(`FE_CACHE_BURN_MB`)면 dev 시작 전에 `rm -rf apps/web/.next` 한다(3000 청취 중이면 소각 생략 — 가동 중 캐시 삭제 금지). 임계 1GB 는 문턱 실측치가 아니라 **사망점 1.99GB 의 절반에서 끊는 보수값**이다. ★업스트림 재확인(Next 16.2 docs) — 디스크 캐시 상한·GC 옵션은 **없다**(손잡이는 `turbopackFileSystemCacheForDev` on/off · `turbopackMemoryEviction` 뿐, panic 시 자동 무효화만 존재) ⇒ 수리 방향 중 ①′(임계 소각)만 실행 가능했다. 원장 원문 = git(이 커밋 직전 `docs/backlog.md`).

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — 표 3행 중 A행([BL-650])은 「도래 아님」 표기이고, 진짜 후보는 B([BL-453])·AP([BL-774]) 둘이다. ★함께 정할 것 = `ledger-vitals` ② 의 **≥3행** 근거(위에 적은 대로 세 번째 후보가 실재하지 않는다).~~ → **2026-08-25 둘 다 사용자 결정으로 종결**([BL-650] 자동 소각 · ② ≥1).

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — 후보는 B([BL-453] 재기술 필요)·AP([BL-774] 사람 동반 필요) 둘이다.~~ → **2026-08-25 qa-sweep(2026-08-25) 이 등재한 P2 5건이 먼저 큐에 들어왔고 전부 종결됐다** — [BL-821]·[BL-825] = PR #826, [BL-823]·[BL-824] = PR #827(잔여 축은 [BL-826] DEFERRED), [BL-822] = 아래.

★**[BL-822] 종결** — 응답이 「거래 수」(미청산 포함)와 **`completed_trades`**(승률 분모)를 각각의 이름으로 싣고, 목록·상세·온보딩·share·거래 목록 탭이 같은 정의를 인쇄한다. 근거·실측·반증은 PR #828 과 커밋 메시지가 갖는다.

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — 후보는 B([BL-453] 재기술 필요)·AP([BL-774] 사람 동반 필요) 둘이다. qa-sweep P2 큐는 비었다.~~ → **2026-08-25 `n12-execution-speed` 회차가 먼저 큐에 들어와 완주했다** — 아래.

★★**2026-08-25 n12-execution-speed 완주** — 4 step 전부 `completed`(blocked·error 0건), PR #829. **관측 전용 회차로 `src/` 는 0줄 고쳤다** — 무엇이 느린지 모르는 상태에서 손대면 프로파일이 이미 바뀐 코드를 재게 된다. ★산출 3벌 = `execution_speed_baseline.json`(7 corpus 의 `bar/s`·`ratio_to_fastest`, `REGEN_EXECUTION_SPEED=1` 일 때만 덮어씀) · `execution_stage_breakdown.json` · `execution_hotspots.json`. 가드는 **절대 시간을 단언하지 않는다**(머신이 바뀌면 통째로 움직여 간헐 red → 다음 사람이 가드를 끈다) — 대상은 같은 실행 안의 **corpus 상대비**뿐이고, 3배 저하 주입에 발화하는 것을 CONTROL 이 재확인했다.

★**반증 ⑴ — PRD §5 「단일 심볼 1Y/1H 백테스트 < 10초」는 세 겹으로 성립하지 않았다.** 근거 없음(출처 = 초기 설정 커밋 `89ff1d4e`, 유도 과정 부재) · 잴 수단 없음(프로즌 코퍼스는 6M/1H **4,368 bar**, 1Y 데이터가 레포에 없다) · 정의 불성립(같은 제품의 처리량이 corpus 간 **13.31배** — 277.18~3,689.36 bar/s). 취소선 + 실측 범위·측정 경로·`[가정]` 1Y 선형 환산으로 재기술했다([LESSON-129]). ★**새 목표선(임계)은 사용자 결정으로 남아 있다** — 이 회차가 한 것은 「현재 값은 이것이고 이렇게 재면 된다」까지다.

★**반증 ⑵ — 회차 설계가 세운 병목 가설 2건이 둘 다 틀렸다.** `run_backtest_v2`(21.75초) − `parse_and_run_v2` 단독(5.11초) = 16.6초의 정체를 ⑴ strict sizing ⑵ 후처리 중 하나로 봤는데, 실측은 **파싱**이었다 — `s3_rsid` 21.752초 = parse **16.432초(75.5%)** + execute 5.185초 + 후처리 **0.132초**.

★★★**그 16초는 「느린 코드」가 아니라 「첫 파스」다**(CONTROL 추가 실측). 같은 프로세스에서 같은 소스를 다시 파싱하면 `s3_rsid` **16.15초 → 0.39초(41배)**, `s5_ema_trend` 0.43 → 0.01초. **ANTLR DFA 를 처음 세우는 비용이고 프로세스 안에서 1회만 낸다**(`adaptivePredict` 호출 s3 14,688 vs s5 2,044 = 7.19배 · parser 누적 41.54배). ⇒ **콜드 워커의 첫 백테스트만 이 값을 문다.** 이 사실이 없었다면 다음 회차는 bar 루프를 최적화하러 갔을 것이다.

~~**다음 행동 = 파스 콜드 비용 수리 회차를 설계한다** — 방향 후보 둘이고 어느 쪽인지는 아직 안 정했다: ⑴ 기동 시 DFA 워밍 · ⑵ 문법 모호성 축소. 착수 전 재야 할 것 = 프로세스 수명 동안 몇 번 무는가 · 미지 스크립트가 워밍된 DFA 를 재사용하는가.~~ → **2026-08-25 둘 다 실측됐고 그 결과 후보 ⑴⑵ 가 **둘 다 주력에서 내려갔다**.**

★★★**반증 ⑴ — 「ANTLR DFA 는 프로세스 안에서 1회만 낸다」가 거짓이다.** DFA 상태·간선은 **지연 생성**이라 새 문법 표면마다 다시 문다. 격리 실측(corpus 당 새 프로세스 · median-of-3 · 스프레드 **1.013~1.065×**): 새 프로세스에서 X 를 파싱한 뒤 미지의 Y 를 파싱하면 Y 는 자기 콜드 대비 **24.7~70.2% 만** 줄고 **자기 웜값의 33~254배**로 남는다. corpus **8벌 전량**(비용 33.8~66.3초)을 워밍해도 홀드아웃 `s3_rsid` 3.045s(자기 웜 0.252s 의 **11.4배**) · `i3_drfx` 34.672s(자기 웜 3.665s 의 **9.2배**). ⇒ 후보 ⑴ 은 「콜드 창을 없앤다」가 아니라 **「33.8~73.7% 줄인다」**이고, 그 대가로 워밍 비용이 **child 기동 지연**으로 옮겨간다(concurrency=2 라 둘이 동시에 워밍하면 그 창 동안 기본 큐가 멈춘다). ★구조적 상한의 이유 = full-context(LL) 재시도 경로는 **DFA 에 전혀 기록되지 않는다**(`antlr4/atn/ParserATNSimulator.py:418` → `:441-445`, `execATNWithFullContext` 본문 `:558-659` 에 `addDFAEdge` **0건**) — 원리상 캐시 가능하지도 않다([BL-829]).

★★★**반증 ⑵ — 후보 ⑵ 의 유일한 근거 「7.19배」가 무너졌다.** `adaptivePredict` s3 14,688 / s5 2,044 = 7.19배를 **모호성 특이성**의 증거로 썼는데, 두 파일의 줄 수가 208 / 27 = **7.70배**다. 7.19배는 「s3 가 모호하다」가 아니라 **「s3 가 크다」**다. 게다가 `.g4` 는 레포에 없고(`apps/api/.venv/.../antlr4/resource/`) 포크 + ANTLR 재생성 + LGPL 판단이 붙는다 ⇒ **lane 불가.**

★★★**원장에 없던 세 번째 축이 실측에서 나왔고 그것이 이 회차의 주력이다 — 백테스트 1회가 같은 소스를 4번 파싱한다.** 4회 전부 **동일 sha1** 확인(`s3_rsid` = `162ad75b…`, 6555B). 좌표 = `ast_classifier.py:119`(`compat.py:82`) · `ast_extractor.py:382`(`compat.py:85`→`sizing.py:60`→`:13`) · `ast_extractor.py:382`(`compat.py:104`) · `event_loop.py:125`(`compat.py:106`→`track_runner.py:94`). Track A 는 `virtual_strategy.py:194`→`alert_hook.py:388` 로 갈려 **5회**. ★**조건부가 아니라 무조건**이다(`v2_adapter.py:93` 이 `initial_capital` 을 항상 채우고 `types.py:28` 기본값이 `Decimal("10000")` 이라 `sizing.py:57-58` early-return 을 안 탄다). ★★**값이 큰 곳은 백테스트 1건이 아니라 옵티마이저다** — `grid_search.py:241`·`genetic.py:509`·`bayesian.py:391` 이 **동일 `pine_source`** 로 셀마다 `run_backtest` 를 반복하고, genetic 상한이 `population_size ≤ 200`(`schemas.py:165`) × `n_generations ≤ 100` ⇒ 한 번의 최적화가 같은 소스를 **최대 20,200 × 4 = 80,800번** 파싱한다. 프로세스 수명 캐시는 그것을 **1회**로 만든다.

★**함정 — `parse_to_ast` 에만 캐시를 걸면 제거되는 중복이 0건이다.** 4파스 중 그 함수를 지나는 것은 **1회**(`event_loop.py:125`)뿐이고 콜드 11.23초를 무는 첫 파스는 `ast_classifier.py:119` 의 **직접 `pyne_ast.parse`** 다. `parser_adapter.py:1` 의 「이 파일만 `import pynescript` 허용」은 **이미 8개 파일에서 깨져 있고** 같은 디렉터리 `README.md:12` 는 「둘」이라 적어 문서끼리도 어긋난다.

★★**기존 가드 하나가 판별력 0 이다.** `test_execution_speed.py:178` 의 양성 대조는 baseline `ratio_to_fastest` 를 10배로 조작하는데, `_assert_relative_ratio_regression` 이 `:149` 의 **내부 정합 검사**에서 먼저 터지고 두 메시지가 같은 문자열(`ratio_to_fastest`)을 담아 `match=` 가 갈라내지 못한다 ⇒ **`:154` 의 2.0배 회귀 임계는 한 번도 실행된 적이 없다.** n13 step0 이 수리한다.

★**AC 축은 시간이 아니라 호출 횟수다**(quant-bridge-07 세션 실측 채택) — 다른 프로세스 2회에서 `adaptivePredict` 3672 · `closure` 4621 · `execATN` 5455 가 **완전 일치**했다. 같은 파스의 초는 8.97~16.15로 흔들린다. ★그 세션이 낸 「워밍 효과 21%」는 **본인이 적은 소음 폭(±40%)이 주장 효과보다 커서** 기각했고(다른 프로세스·다른 시점 비교), 격리 재측정이 **25.3~70.3%(쌍마다 다름)** 로 대체했다.

★**사용자 결정 2건(2026-08-25)** — ⑴ 회차 범위 = **A+F 2 lane**(중복 파스 제거 · API 루프 블로킹). ⑵ `worker_max_tasks_per_child` 250→1000 완화는 **이번엔 손대지 않는다**(판정 수단이 소크뿐이라 AC 를 못 세운다 — [BL-828]). 기각·유예된 축은 [BL-828]·[BL-829]·[BL-830]·[BL-831] 로 등재했다.

~~**다음 행동 = n13 2 lane 병렬 주행**~~ → **2026-08-25 완주** — 6 step 전부 `completed`(blocked·error 0건), PR #832·#833 → `stage/n13`, 통합 PR **#834**.

★★**산출 — 백테스트 1회의 파스가 4→1(Track A 5→1)이 됐고 그것이 결정적으로 단언된다.** `parse_to_ast` 에 `lru_cache(maxsize=8)` + `ast_classifier.py`·`ast_extractor.py`·`alert_hook.py` 의 직접 `pyne_ast.parse` 3곳을 어댑터 경유로. 신설 `test_parse_call_census.py` 6건 = 계수 단언 2(Track S/A · sha1 동일성 포함) + **양성 3**(직접 호출 N회 계수 · 소스 변경 시 캐시 미스 · 예외는 캐시되지 않음) + **음성 1**. ★값이 큰 곳은 백테스트 1건이 아니라 **옵티마이저**다 — genetic 상한 `200 × 101` 셀이 동일 소스를 셀마다 파싱하던 것이 프로세스당 1회가 된다.
★**API 파스가 이벤트 루프를 막던 것도 닫혔다** — `service.py` 의 세 `async def`(`:201`·`:231`·`:375`)가 동기 `_parse` 를 직접 부르고 uvicorn 워커가 1개라 콜드 파스(최대 52초) 동안 `/healthz` 까지 멈췄다. 신설 `test_parse_event_loop_blocking.py` 는 **경과 초가 아니라 하트비트 틱 수**로 판정한다.
★**기존 가드의 판별력 0 을 고쳤다** — `test_execution_speed.py` 의 양성 대조가 `:149` 내부 정합 검사에서 먼저 터지고 두 메시지가 같은 문자열을 담아 `match=` 가 못 갈랐다. 기존 것은 정직한 이름·`match=` 로 정정하고, **2.0배 임계를 실제로 통과하는 새 대조**를 더했다(`bars_per_second` 와 `ratio_to_fastest` 의 정합을 유지한 채 한 corpus 만 임계 밖으로).

★★**lane AC 초록이 광역 green 이 아님을 #833 이 또 실증했다**(n8 에 이어 두 번째). lane 4 step 전부 통과 후 광역 CI 가 `test_live_signal_import_blast_radius.py::test_pine_v2_import_surface_does_not_grow` 로 red — `ast_classifier` 를 어댑터 경유로 바꾸자 `parser_adapter` 가 `live_signal` 의 top-level 폐포에 들어왔다. **가드가 요구한 대로 근거를 적어 동결 집합을 갱신**했다(잎 모듈·`src` import 0건 · 본문이 데코레이터+1줄 · `pynescript` 는 이미 허용된 `ast_extractor` 가 같이 끌어옴). CONTROL 이 수리 후 **로컬 전량 5427 passed / 0 failed** 로 재확인.

★**주의 — 픽스처의 초 값으로 절감량을 주장하지 마라.** 재생성된 `execution_stage_breakdown.json` 은 s3_rsid `execute` 5.185→2.787초(총 21.75→14.60)를 보이지만 **1회 측정**이고, 웜 중복 3회의 실측 합은 0.830초다. 차이는 측정 소음이다([BL-830]). 이 회차의 방어 가능한 주장은 **결정적 계수 4→1** 뿐이다.

★**회고 = 반증 카드 2장으로 정본 층에 올렸다** — [LESSON-130](「ANTLR DFA 는 프로세스당 1회」가 거짓이고 그 한 문장이 방향 둘을 잘못 세웠다) · [LESSON-131](동료 세션의 실측이 자기 문장으로 반증됐다 — 소음 폭이 주장 효과보다 컸다).

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — … ★[BL-829] 는 **콜드 파스 자체를 줄이는 유일한 축**이므로, 콜드가 여전히 문제로 관측되면 그것이 최우선이다.~~ → **2026-08-26 [BL-829] 를 고른 뒤 preflight 가 그 항목 자체를 반증해 기각했다.**

★★★**반증 — 「콜드 파스의 지배 성분 = full-context(LL) 재시도」가 거짓이다.** [BL-829] 의 증상 절은 코드 읽기(`ParserATNSimulator.py:418`→`:441-445`, `execATNWithFullContext` 본문에 `addDFAEdge` 0건)까지는 맞았지만 **귀속이 틀렸다** — 그 경로가 실제로 거의 안 돈다. 계측: `execATNWithFullContext` 가 `s5_ema_trend` **0회** · `s3_rsid` **29회**(`adaptivePredict` 3,672 중) · `i3_drfx` **204회**(27,652 중 **0.7%**). SLL 2단계로 **전부 0 으로 만들어도** `i3_drfx` 49.91→48.06초 = **3.7%**, `s3_rsid` 는 10.79→10.84초로 **차이 없음**이다(AST digest 3벌 전부 동일 — 정확성은 성립했고 **이득이 없었다**). 진짜 지배 성분 = `s3_rsid` cProfile 의 `ParserATNSimulator.closure_` cumtime **35.77/36.96초(96.8%)** + `PredictionContext.merge` 15.6초, 6,555B 소스에 함수 호출 **1억 6,963만회**. ⇒ **파서 층 축(SLL·워밍·문법 모호성)은 전부 이 성분을 못 건드린다.** [BL-829] 본문 삭제 + 기각 tombstone = `docs/backlog-deferred.md` 헤더.

★★**대체 축이 같은 preflight 에서 나왔고 실측으로 성립한다 — [BL-832] 프로세스 밖 AST 캐시.** pynescript AST 는 그대로 pickle 왕복이 되고 **digest 가 보존된다**: `s5_ema_trend` 2.69초→**0.0002초**(4.9KB) · `s3_rsid` 11.47초→**0.0006초**(34.3KB) · `i3_drfx` 53.38초→**0.0048초**(283.2KB). n13 이 「프로세스당 1회」로 만든 것을 **「소스당 영구 1회」**로 만든다. 꽂을 자리는 n13 이 이미 하나로 모은 `parser_adapter.py` 다.

★**preflight 가 lane 을 한 줄도 안 쓰고 방향을 바꿨다** — `AGENTS.md` §4 「kickoff 첫 step = baseline 재측정」의 N번째 실증이고, [LESSON-130](「한 문장이 방향 둘을 잘못 세웠다」)과 **같은 형태의 재발**이다. 카드 = [LESSON-132].

~~**다음 행동 = [BL-832] 의 저장소·신뢰 경계를 정한다**~~ → **2026-08-26 결정 + 구현 + 종결.**

★**저장소 = 로컬 디스크**(Redis 기각). 근거: Redis 는 이 레포에서 **Celery broker + 락**으로만 쓰고 있어 pickle payload 를 얹는 순간 역직렬화 신뢰 경계가 새로 생긴다. 반면 이득의 본체인 워커 재활용 (`worker_max_tasks_per_child`)로 생기는 콜드는 **같은 컨테이너 안**에서 나므로 디스크만으로 그 축이 통째로 잡힌다. Redis 는 디스크로 이득이 부족한 것이 관측되면 그때 올린다.

★**산출** — `parser_adapter.py` 에 L2 디스크 캐시(L1 `lru_cache` 유지). 키 = `sha256(스키마 버전 ∥ pynescript 버전 ∥ 소스)`. **판정은 초가 아니라 계수·digest 동일성**이다 — 신설 `test_parse_ast_disk_cache.py` 10건(핵심 = **새 프로세스에서 `pyne_ast.parse` 를 던지게 해 두고도 AST 가 나오는가** + 그 **양성 대조**로 캐시가 비면 반드시 죽는 것). **변이 5/5 red · 전부 국소 red**(L2 읽기 제거 · 버전 키 제거 · 예외 캐시 · 소각 제거 · 손상 폴백 제거).

★★**광역이 또 잡았다(세 번째)** — lane 급 스위트 16건이 초록인 뒤 BE 전량에서 `test_execution_hotspots.py::test_execution_hotspot_json_source_coordinates_are_real` red. n12 픽스처가 `parse_to_ast` 를 **16행**으로 기록했는데 재작성이 그 함수를 밀었다 — **phantom 좌표 가드가 제 일을 한 것**이고 코드 결함이 아니다. `REGEN_EXECUTION_HOTSPOTS=1` 로 재생성(`parse_to_ast:114`). 최종 **로컬 전량 5,440 passed / 0 failed**.

★**내가 만든 실제 결함 1건을 광역이 먼저 잡았다** — 캐시가 기본 켜진 채로 테스트가 돌자 `apps/api/.ast-cache` 가 **테스트 프로세스 사이에서 살아남아** n13 계수 테스트 3건이 `assert 0 == 1` 로 red 였다. 「어제 무엇을 돌렸는지」에 의존하는 계수는 테스트가 아니다 ⇒ `tests/conftest.py` autouse 로 **기본 비활성**, 캐시 자신의 스위트만 tmp_path 로 켠다.

★★**같은 세션에서 CI 경로 스코프도 넣었다(사용자 요청) — PR #836.** `changes` 잡이 PR diff 를 분류해 `backend`·`frontend` 의 `if:` 를 만든다. [ADR-037] 이 **의도적으로 철거한 축의 재입힘**이라 실측을 먼저 냈다 — 최근 머지 PR 30건 중 **문서만 9건(30%)** · BE만 11 · FE만 3 · 둘다/공유 7 ⇒ BE ~13분 · FE ~4분 기준 **30 PR 당 약 236분**이 검증 대상 없는 잡에 들어가고 있었다. 구 구조의 사고(「필터가 좁아 워크플로만 고친 PR 에서 감사가 skip 되고 초록」)를 막은 것 셋 = ⑴ **`on.paths` 미사용**(required check 영구 대기 방지 — 잡은 항상 생성되고 `if:` 로 skip) ⑵ `.github/**`·`tools/**` 는 **양쪽 실행**(테스트에 단언) ⑶ **fail-safe 3중**(diff 실패 · 빈 입력 · **미분류 경로 1건**). 변이 4/4 국소 red. 실 CI 자기 검증 완료.

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — 표는 4행이고 살아 있는 후보는 **D([BL-827] `openapi-check` CI 편입 · ⑴ 은 한 줄)** · **B([BL-453] 재기술 필요)** · **AP([BL-774] 사람 동반 필요)** 셋이다(C행 [BL-832] 는 이 회차가 종결). ★[BL-827] ⑴ 은 **다른 회차에 동승 가능한 크기**라 단독 회차로 열 필요가 없다.~~
→ **2026-08-27 사용자가 ⓪ 표 밖에서 새 축을 열었다 — 「전략 브리핑」.** ⓪ 표의 세 후보(D·B·AP)는 그대로 살아 있고 이 회차 뒤에 다시 고른다.

~~**다음 행동 = Stage 1 — `ParsePreviewResponse` 에 `declaration`/`inputs` 를 노출한다**~~
→ **2026-08-27 Stage 1·2 완주**(PR #839 · CI 4잡 전부 pass). 아래가 그 실측 산출이다.

~~**다음 행동 = Stage 3 — Pine AST → Python 읽기 전용 렌더러**~~
→ **2026-08-27 완주.** 아래가 실측 산출이다.

~~**다음 행동 = Stage 4 — LLM 해설 층**~~ → **2026-08-27 완주.**

~~**다음 행동 = Stage 5 — 자연어 → 전략 생성 + 드리프트 탐지기**~~ → **2026-08-27 완주.**
[ADR-040]·[ADR-041]·[ADR-042] 축 **Stage 0~5 전부 종결** (PR #839).

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다**~~ → **2026-08-28 LLM provider 선택 구조가 먼저 큐에 들어왔다**(PR #839 머지 후 후속).

> ★★**LLM 성공 경로를 처음으로 실증했다.** PR #839 은 provider SDK 를 전부 mock 해 테스트했고
> 실제 왕복은 **한 번도 없었다**. 이번에 실키로 재니 **로컬 anthropic 401 · gemini 400 · openai 200**,
> **서버는 셋 다 비어 있었다.** ⇒ 「anthropic 우선 + gemini fallback」이라는 코드·문서의 전제가
> 환경과 안 맞았다. 순서를 **설정(`LLM_PROVIDER_ORDER`)으로** 빼고 openai 를 넣었다.
> 실측: 해설 **3.4초**(근거 줄 정확) · 생성 **15.7초**(실행 가능·미지원 0).
>
> ★**복제가 사라졌다** — fallback 이 `narrative/service.py` 와 `generate_service.py` 양쪽에 있었다.
> 두 파일 **439 → 291줄**(-148), 신규 `providers.py` 216줄. 4번째 provider 는 한 곳만 고치면 된다.
>
> ★★★**테스트 초록이 「스위트가 느려서」 유지되고 있었다.** 리팩터로 느린 HTTP 테스트 5건이
> 순수 단위 17건으로 바뀌자 **9건이 즉시 red**. 원인은 `POST /strategies` 의 `30/minute` 이고
> 카운터는 **Redis DB 3 에 60초 창**으로 남는다. **대조 실험이 갈랐다** — 변경 전 트리 1,279 전건
> 통과 / 변경 후 9 red. 코드 결함이 아니라 **테스트가 rate limit 에 의존**하고 있었고, 실행 속도·
> 직전 실행 잔여 카운터·개발 중 브라우저 요청 중 무엇이 바뀌어도 터질 상태였다.
> 해법은 레포에 이미 있었다(`tests/waitlist/conftest.py` 의 limiter reset) — `tests/strategy` 에만
> 없었다. 전역 비활성화는 안 한다: waitlist 가 429 를 **실제로 검증**한다.

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다**~~ → **2026-08-28 서버 배포를 먼저 했다.**
`9e71aa96`(2026-08-16) → `5f16952b`, **405 커밋**. DDL 2건 적용(`20260817_0001 → 20260817_0002`) ·
소크 재고정 + 창 재개(06:30:21Z) · FE 이미지 `5f16952b` 교체. 검증: `/health` 200 `env=production` ·
신규 엔드포인트 3종 401(라우팅됨) · celery 3노드 `pong` · 누락 커밋 0 · 컨테이너 안 신규 UI 마커 실재.
★**런북이 두 곳에서 틀렸고 배포가 그것을 물었다**(같은 PR 에서 수정) — ⑴ `down` 이 `quantbridge-db` 를
**제거**하므로 문서의 `down → migrate --confirm` 은 **실행 불가능**했다(`docker exec` 대상이 없다).
⑵ `uv sync` 단계가 **없었다** — 소크는 `apps/api/src` 만 remount 하는데 `openai>=1.60` 이 새로 붙었고
`src.main` 이 그 체인을 물어, 그 단계 없이 재시작하면 **API 가 import 부터 죽는다**(워커 18 task 는 0건 무관).
★**LLM 키도 같은 날 넣었다** — 서버 `.env.local` 에 키 3종이 **한 줄도 없었다**(전부 INSERT).
옮기기 전에 세 provider 에 직접 물어 유효성을 쟀다. **최종 상태(2026-08-29) = `openai,gemini`** ·
`GEMINI_MODEL=gemini-3.5-flash-lite` · **anthropic 은 제외**(사용자 결정 — 키 제거 + 기본 순서에서 삭제).
★`available_providers` 는 **키 존재만** 보고 유효성은 안 본다 ⇒ **무효 키를 순서에 남기지 마라**
(매 호출이 그것을 시도하고 실패한 뒤에야 다음으로 넘어간다).
서버 실왕복 검증: openai · gemini **각각 개별 강제**로 스키마 준수 JSON 반환.

★★**그 검증이 결함을 하나 잡았다**(PR #843) — 기본값 **`gemini-2.0-flash` 가 폐기돼 404** 였고,
convert 작성 시점부터의 기본값이라 **Gemini fallback 은 아무에게도 동작한 적이 없다.**
★키 검사로는 못 잡는다(키는 유효 · 순서대로 한 번 부르면 openai 가 응답해 멀쩡해 보인다) —
**provider 를 개별로 강제해야** 보였다. ⇒ `GET /api/v1/llm/models` 신설: provider 에게 목록을 물어
설정값이 **살아 있는 목록에 있는지**(`configured_listed`) 대조한다. ★**3값이다** — 목록을 못 읽었으면
`False` 가 아니라 `None`. 「못 봤다」를 「없다」로 접으면 죽은 목록 API 가 멀쩡한 설정을 오경보한다.

★**2차 배포 (2026-08-29)** — `5f16952b` → `732ab067`(3커밋 · 마이그레이션 0 · 신규 의존성 0 · 신규 env 0).
**API+FE 를 먼저 올리고 소크는 안 끊었다** — 그때 소크 창이 **23.7h/24h** 였고 미배포 커밋이 워커
import 체인 밖(narrative/catalog)이라 창을 태울 이유가 없었다. **19분 뒤 자격 획득**
(`✓ 24.0182h ≥ 24h · 실격 0 · 손실 0 · 누적 3회` · 게이트 **exit 0 = PASS**)한 뒤
`down → pin → up` 으로 소크를 따라잡혔다 — 창 시작 `2026-08-29T06:33:45Z` · **누락 커밋 0** ·
celery 3노드 `pong` · 라이브 세션 1 유지.
★**기다린 값이 이것이다** — 그대로 눌렀으면 23.7h 가 창 0회로 소멸했다.
검증: `/api/v1/llm/models` 인증 없이 401 · 인증 후 200(openai 61/132 · gemini 39/53 둘 다 `✓목록에 있음`) ·
FE 이미지 `732ab067` · 컨테이너 안 `model-picker` 마커 실재(양성/음성 대조 동반).

~~**다음 행동 = 개발 항목을 ⓪ 표에서 고른다** — 배포·LLM 축이 끝났으므로 표의 **다섯 후보**로 돌아간다:
**E([BL-833] Optimizer 드롭다운 — 추천, 데이터가 이미 있다)** · **D([BL-827] `openapi-check` CI 편입 · ⑴ 은 한 줄)** ·
**F([BL-834] convert 를 provider 층 안으로)** · **B([BL-453] 재기술 필요)** · **AP([BL-774] 사람 동반 필요)**.~~
→ **2026-08-30 사용자가 골랐다 — D·F⑵⑶·E 3 lane 밤샘.** 저작·주행은 아래 ⓾ 가 갖는다.
★**브리핑 축의 잔여 2건은 2026-08-28 원장에 등재했다** — **[BL-833]**(Optimizer `var_name` 자유 타이핑 ·
brief 가 이제 데이터를 갖는다) · **[BL-834]**(`convert` 가 스키마 강제·provider 선택 밖 + `sliced` 도달 불가).
둘 다 ACTIVE·도래라 ⓪ 표 후보가 **3 → 5** 가 됐다.

---

## ⓾ 2026-08-30 밤샘 3 lane — **저작부터 한다. 이 절 하나로 컨텍스트 0 에서 복원된다**

> ★**이 절은 「다음 세션이 빈 컨텍스트로 시작한다」를 전제로 쓰였다.** 여기 적힌 좌표는 전부
> 2026-08-29~30 에 **코드로 대조**했다. 그래도 하네스 §1 대로 **설계 step 에서 다시 확인해라** —
> 이 레포는 「적혀 있다 ≠ 그렇게 동작한다」를 8건 겪었다.

~~**다음 행동 = 아래 3 lane 을 저작하고 주행한다**~~ → ★**2026-08-30 저작 완료**(PR #847 · `a449845c`) —
`phases/` 에 `ci-gates`·`convert-reach`·`optimizer-inputs` 3 lane 이 서 있고 `index.json` 은 전건 `pending` 이다.

**다음 행동 = 그 3 lane 을 주행한다 — `main` 에서 그대로 친다:**

```
/harness parallel 3
```

★★**BL 번호를 붙이지 마라 — 붙이면 이미 저작된 lane 을 버리고 새로 설계한다.**
하네스 인자 규칙: `phases/` 디렉터리명 = 실행 / **그 밖의 값(티켓 ID 포함) = 새 회차 설계** /
**생략 = `pending` 전량**(`.claude/commands/harness.md` §호출 표).
지금 pending 이 정확히 그 3 lane 이므로 **생략이 맞다.**
~~★**재료(BL 번호)를 반드시 함께 줘라.** … `phases/index.json` 이 `[]` 라 러너가 되묻고 멈춘다~~
→ **그 전제는 저작으로 소멸했다**(`index.json` 이 더는 `[]` 가 아니다).
★**브랜치를 미리 파지 마라** — 전제 검사가 「메인이 `main` · 워킹트리 clean」을 요구하고,
**stage 브랜치·워크트리 3벌은 러너가 직접 만든다**(손으로 파던 옛 절차는 2026-08-22 폐기).
★lane 이름은 아래 표의 `ci-gates` · `convert-reach` · `optimizer-inputs` 다 — **한 lane 만 돌릴 때만** 이름을 준다.
★`phases/n12-execution-speed/` 는 **`runs/` 만 남은 gitignore 잔재**다(step 파일도 `index.json` 도 없다).
회차가 아니니 무시하거나 지워라 — `phases/index.json` 이 그것을 등재하지 않아 러너는 애초에 안 본다.

### 착수 시점 baseline (2026-08-30 실측 — 재지 말고 이걸 써라. 단 하루 넘으면 다시 재라)

| 게이트                    | 값                                             |
| ------------------------- | ---------------------------------------------- |
| BE `pytest` 전량          | **5,568 passed · 32 skipped · 3 xfailed · rc=0** (7분 26초) |
| FE `biome check .`        | **clean** (676 파일)                            |
| FE `tsc --noEmit`         | **clean**                                       |
| BE `mypy src`             | ★**에러 3건** (`strict = True` 는 이미 켜져 있다) |
| `mise run openapi-check`  | ★**red — drift 845줄 / 엔드포인트 4종 누락**     |

★**착수 전 red 가 공짜로 확보돼 있다** — lane 1 의 AC 둘(`mypy`·`openapi-check`)이 **지금 실패**한다.
그 측정 없이 난 초록은 아무것도 증명하지 않는다는 규칙을 이번엔 미리 만족했다.
★xfail 3건은 phantom 이 아니다: 둘은 `--help` 의 `sed` 범위 결함, 하나는 [BL-791]「fail 정책 결정 전」이다.

### lane 구성 — 파일 겹침 0 (하네스 §5 묶음 기준 1)

| lane                  | 재료                                                        | 파일 축                                                                                                                                                                                    | AC (rc=0 만 통과)                                                                            |
| --------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| **1 `ci-gates`**      | [BL-827] 전량 + mypy CI 편입 + PoC 삭제                     | `contracts/**` · `.github/workflows/ci.yml` · `mise.toml` · `mypy.ini` · `strategy/pine_v2/py_renderer.py` · `strategy/narrative/service.py` · `strategy/service.py` · `tools/scripts/openapi-poc-filter.py`(삭제) · `apps/web/src/lib/api-contract-poc/**`(삭제) · `apps/web/orval.poc.config.ts`(삭제) · `apps/api/tests/scripts/test_openapi_poc_filter.py`(삭제) · `docs/api/endpoints.md` | `export_openapi.py --check` rc=0 · `uv run mypy src` rc=0 · `grep -c openapi ci.yml` ≥1 · `grep -c mypy ci.yml` ≥1 |
| **2 `convert-reach`** | [BL-834] ⑵⑶ — `sliced`(LLM **0회**) 경로 도달 + 정상 진입점 | `apps/web/src/features/backtest/components/ConvertWithAIButton.tsx` · `apps/web/src/components/form-error-inline.tsx`                                                                        | `pnpm test -- --run` (해당 스펙) · 변이: `mode` 를 `"full"` 로 되돌리면 **red**                |
| **3 `optimizer-inputs`** | [BL-833] — `var_name` 자유입력 → select                  | `apps/web/src/features/optimizer/**`                                                                                                                                                        | `pnpm test -- --run` (해당 스펙) · 변이: select 를 자유입력으로 되돌리면 **red**               |

★**lane 1 이 mypy 를 삼킨 이유** — mypy CI 편입과 `openapi-check` CI 편입이 **둘 다 `ci.yml` 을 만진다**.
따로 두면 하네스 §5 묶음 기준 1(파일 겹침 0)을 위반해 머지 충돌이 난다. **묶는 것이 답이다.**
★lane 2·3 은 둘 다 FE 지만 `features/backtest/` 와 `features/optimizer/` 로 **디렉터리 축이 갈린다** —
2026-08-22 에 「규칙 축으로 자르면 26건 겹친다」를 실증했다. 디렉터리 축이 옳다.

### 확정된 결정 3건 — **다시 묻지 마라. step 에 그대로 실어라**

1. **PoC 생성물 = 삭제.** 참조 0건이고 [ADR-031] 은 전면 전환을 정한 적이 없다. 재생성하면 다음 회차에 또 굳는다.
   ⇒ 파급 **7좌표**는 [BL-827] 본문이 전수로 갖는다. `mise run openapi-check` 는 **2단 → 1단**이 된다.
   ★`zod-v4-coexist.test.ts` 도 함께 지운다 — **PoC 전용**이라 생성 스키마가 없으면 잴 대상이 없다(확인함).
2. **mypy = 차단 게이트**(`continue-on-error` 아님). 에러 3건뿐이고 `strict` 는 이미 켜져 있다.
   ★단 살아 있는 `type: ignore` 가 **490건**이고 `warn_unused_ignores = True` 다 — **lane 이 먼저 재라.**
3. **[BL-833] 데이터 경로 = `GET /strategies/{id}` → `POST /strategies/parse`.** 근거·기각한 대안 2종은 [BL-833] 본문.

### 착수 전 실측 2건 — **이미 쟀다. 다시 재느라 밤을 쓰지 마라**

- ★★**lane 1 의 `.env.local` 함정은 없다.** `mise run openapi-check` 는 `.env.local` 을 통째로 소싱하는데
  **CI 엔 그 파일이 없다** ⇒ 「CI 한 줄」이 거짓일 위험이 있었다. CI backend 잡이 **이미 갖고 있는 env 8종만으로**
  `uv run python scripts/export_openapi.py --check` 를 돌려 **rc=1**(= drift 검출, 설정 크래시 아님)을 확인했다.
  `TRADING_ENCRYPTION_KEYS` 가 그 잡에 이미 있다. **전제 성립 — 정말로 한 줄이다.**
- ★★**[BL-833] 의 「콜드 파스 53.38초」 경고는 낡았다.** L2 디스크 캐시
  (**`bdc13117`** · PR #837 · 2026-08-26 · `apps/api/src/strategy/pine_v2/parser_adapter.py`) 이후
  콜드는 **소스당 1회**이고 재방문 4.8ms 다. **비용을 이유로 설계를 비틀지 마라.**
  ★그 BL 섹션(BL-832)도 **RESOLVED 라 삭제됐다** — 좌표는 이 커밋이다.

### 하네스 함정 — 이 레포가 이미 밟은 것만

- ★**`--stage` 는 `stage/` 접두여야 한다.** `ci.yml` 의 `pull_request.branches` 가 `[main, "stage/**"]` 라
  `feat/**` 를 base 로 하면 **CI 가 아예 안 돈다**(`no checks reported` 는 초록이 아니다).
- ★**`phases/index.json` 에 3 lane 을 사전 등록해 머지한 뒤 시작해라.** 다만 그것이 막는 것은 *배열 추가* 충돌뿐이다 —
  lane 별 `status` 인접 줄 충돌은 **`c1b32d61`(PR #810, 「stop lanes from committing the shared phases/index.json」)**
  의 `_in_linked_worktree()` 가 담당한다. ★그 BL 섹션(BL-820)은 **RESOLVED 라 삭제됐다**([AGENTS.md] §6) — 좌표는 이 커밋이다.
- ★**lane AC 초록 ≠ 광역 green.** n8 #802 가 실증했다. 최종 검출자는 광역 CI 다(설계대로).
- ★**판정 명령에 파이프를 붙이지 마라** — `pytest … | tail` 은 tail 의 rc 를 읽는다(10회 이상 재발).

### 이 회차가 손대지 않는 것 (2026-08-30 확정)

[BL-774](외부 TradingView 실측 — **사람 동반**) · [BL-828](소크 창 실측 선행) · [BL-826](DDL + 519행 backfill) ·
[BL-765](`live_signal.py` 4,606줄 분할 — 무인 리팩터 위험) · [BL-834] ⑴(BE convert → provider 층 · **다음 회차 1순위**).

> ★★**Stage 5 의 핵심은 기능이 아니라 「막을 수 없는 것을 어떻게 다루나」다.**
> 사용자 결정으로 LLM 이 Pine 과 Python 을 **둘 다** 내므로 둘이 어긋날 수 있고 **막을 수단이 없다**.
> 설계는 제거 대신 **가시화**한다 — 통과한 Pine 을 [ADR-042] 렌더러로 Python 화해 대조하고,
> 어긋나면 렌더링본을 정본으로 제시한다. ★**화면 문구가 「다릅니다」가 아니라 「다를 수 있습니다」**인
> 이유가 이것이다: 탐지기는 식별자 집합 비교라 「의미가 같은데 표현이 다름」과 「표현이 같은데 의미가
> 다름」을 완전히 못 가른다. **탐지기의 한계를 화면이 말한다.**
>
> ★★★**또 한 번 내 테스트가 아무것도 안 재고 있었다(이 축에서 두 번째).**
> 「렌더러의 한국어 주석이 드리프트로 잡히면 안 된다」를 쟀는데 **한국어는 애초에 식별자 정규식
> (`[A-Za-z_]…`)에 안 걸린다** — 주석 제거를 죽이는 변이에 15/15 초록이었다. 주석 제거가 실제로
> 지키는 것은 **ASCII 단어**다: 헤더 해설의 `Pine`·`Python`·`pine_v2` 와 **`[원문 보존]` 주석 안의
> 원본 Pine 식별자**. 교체 후 변이 2/2 red. ⇒ **「무엇을 지키는가」를 실측하지 않고 테스트를 쓰면
> 이름만 맞는 항진명제가 된다.**
>
> ★**탐지기는 착수 전에 쟀다** — 항등 검사(렌더링본 vs 자기 자신) corpus 5건 **전건 드리프트 0**,
> 양성 대조(다른 전략) 검출. 이 둘 없이 붙였으면 **항상 「다르다」를 내는 탐지기**를 배포했을 수 있다.
>
> ★**생성은 저장하지 않는다** — 산출물만 돌려주고 사용자가 「이 Pine 코드 쓰기」를 눌러야 편집기에
> 들어간다(`convert` 선례). 검토 없이 저장되는 경로를 만들지 않는 것이 드리프트를 **못 막는** 설계의
> 최소 안전장치다. 판정(`is_runnable`)은 LLM 이 아니라 `analyze_coverage` 가 낸다.

> ★**Stage 4 가 세운 것은 프롬프트가 아니라 계약 셋이다.**
> ⑴ **스키마 강제** — Anthropic tool use(`tool_choice` 고정) + Gemini `response_schema`.
> `convert/service.py` 는 이 인자가 **0건**이라 문자열을 손으로 파싱하고 Gemini 의 ``` 펜스를 벗긴다.
> 프롬프트로 형식을 부탁하면 모델이 안 지킬 수 있지만 스키마는 SDK 가 지킨다. 배선이 빠지면
> 조용히 전자로 후퇴하므로 **인자가 실려 나가는지를 테스트가 직접 잰다**(변이 red 확인).
> ⑵ **근거 검증을 서버가 한다** — 실재하지 않는 줄을 가리키는 항목을 버린다. ★**자르지 않는다**:
> 999번 줄을 5번으로 고쳐 주면 거짓이 참이 된다. 클라이언트에 맡기지 않는 이유는 규칙이 두 곳에
> 살면 언젠가 한쪽만 고쳐지기 때문이다.
> ⑶ **도구 응답이 없으면 실패다** — 빈 해설을 성공으로 내면 화면이 침묵으로 거짓말한다.
>
> ★**[ADR-020] §3 F 와의 경계를 화면이 집행한다** — 배경·라벨을 갈라(`.narrative` 점선 테두리)
> 「AI 해설 · 판정이 아닙니다」를 **본문 위에** 붙이고, 결정론 층 **아래**에 배치한다(순서가 곧 권한).
> 열기 전에는 `enabled: false` 라 **서버를 안 부른다**(LLM 왕복은 느리고 돈이 든다 — 양성 대조 동봉).

> ★★**Stage 3 에서 한 줄이 결과를 갈랐다.** pynescript 는 문 레벨 `if`/`for`/`switch` 도 **`Expr` 로 감싼다**
> (Pine 에서 그것들이 식으로도 쓰이기 때문). 그대로 `expr()` 로 보내면 블록이 통째로 「원문 보존」 폴백에
> 떨어져 **전략의 진입 조건이 주석이 된다.** 감싼 것을 벗기자 corpus 원문 보존이 **48 → 7**,
> 함수 본문 마지막 처리까지 고치고 **7 → 1** 이 됐다(9건 중 8건 완전 렌더).
>
> ★★★**내 테스트 하나가 판별력 0이었고 변이가 그것을 잡았다.** 「못 옮긴 노드를 조용히 빼지 않는다」를
> `array.*` 로 쟀는데 `array.new_float()` 는 평범한 `Call` 이라 **보존 경로를 아예 안 지났다** —
> 보존을 죽이는 변이를 심었는데 14/14 초록이었다. 실제로 그 경로를 지나는 것은
> `for..in` · `import` · `type` 셋이고, 교체 후 **변이 3/3 red · 음성 대조 1건 초록**.
> ⇒ **「보존한다」를 쟀다고 믿었는데 아무것도 안 재고 있었다.** 이 레포의 N번째 같은 패턴이다.
>
> ★**`mode` 가 문자열이 아니라 노드였다** — `Assign.mode` 는 `Var()`/`VarIp()`/`None` 이다.
> 문자열로 비교하면 조용히 항상 거짓이라 **`var` 표시가 통째로 사라진다**(봉을 넘어 유지되는
> 변수인지 아닌지는 전략 독해의 핵심이다).
>
> ★**exec 금지를 재는 게이트가 이 레포에 0건이었다** — [ADR-003] 결정 1(신뢰도 10/10)이 문서에만
> 있었다. `test_py_renderer_not_executed.py` 가 두 층으로 집행한다: `src/` 전역 AST 로 `exec`/`eval`/
> `compile`/`__import__` **이름 호출** 부재 + 렌더러 소비자에 실행/`subprocess` 배선 부재.
> ★첫 판은 **부분 문자열로 재다가 `re.compile(` 을 오검**했다 — 같은 파일의 AST 판정기로 바꿨고
> 음성 대조(`pool.eval` 속성 호출은 안 센다)를 붙였다.

> ★★★**Stage 1 의 최대 산출은 코드가 아니라 계획 3건의 반증이다.**
>
> ⑴ ~~`param_count` 를 AST 로 교체(이중 구현 제거)~~ → **거짓 전제였다.** 두 수는 다른 것을 센다 —
> 정규식은 `input(` **호출 지점**, AST 는 **override 가능한 선언**(엔진이 대입문 좌변 이름으로만 값을
> 갈아끼운다: `interpreter.py` `_assignment_target_stack`). 갈리는 것은 **4형태**이고 전부 AST 가 적게 센다:
> 대입 없는 `plot(w=input.int(2))` · 중첩 · 사용자함수 본문 · 튜플 좌변.
> ★**결정타는 비용** — 콜드 `extract_content` 가 corpus 9건에 **72.0초**(정규식 5.658ms · **12,727배**)이고
> `param_count` 는 목록 페이지의 **전 전략**에 대해 돈다. ⇒ **목록은 정규식, 표·드롭다운은 AST.**
> ★★**corpus 9/9 일치는 증거가 아니었다** — 그 4형태가 corpus 에 없을 뿐이다.
> `test_param_count_vs_ast_inputs.py` 가 **그 초록에 판별력이 없다는 사실 자체**를 고정한다.
>
> ⑵ ~~Optimizer `var_name` 드롭다운을 Stage 1 에 동승~~ → **Stage 2 뒤로 미뤘다.** 지금 붙이면
> 옵티마이저 화면에 콜드 파스(`i3_drfx` 53.38초)를 얹는다. brief 엔드포인트가 그 데이터의 공급처다.
> **여전히 열려 있다** — `features/optimizer/form-schemas.ts:44` 는 아직 자유 타이핑이다.
>
> ⑶ ~~`signals` 를 `SignalExtractor` 로 채운다~~ → **가장 흔한 형태에서 항상 빈 배열이다.**
> 그 추출기는 `when=` · `plotshape` · `alertcondition` · `label.new(v ? ..)` **네 형태만** 본다
> (`_find_signal_vars_ast`). 즉 **indicator 계열에서만** 값이 나오고 Track S 의 `if cond` 형태는 0건이다.
> 감추지 않고 **계약으로 고정**했다 — 빈 배열 단언 + **Track A 양성 대조**(그 대조가 없으면 추출기가
> 통째로 죽어도 초록이다) + 화면은 비면 **절 자체를 안 그린다**(「신호 없음」은 거짓이다).
>
> ★**설계 1건도 바꿨다** — 계획은 `strategy/brief/` 서브도메인이었으나 brief 는 DB 에서 `pine_source` 를
> 읽어야 해서 `convert/`(무DB)와 동형이 아니다. 기존 `StrategyService`(repo 보유 + 소유권 검사)에 얹어
> **새 DI 배선도 `apps/api/AGENTS.md` §3 예외 표 행도 만들지 않았다.**
>
> ★**곁다리로 잡은 것 2건** — ⑴ FE Zod 가 `dogfood_only_warning` 을 **조용히 버리고 있었다**(BE 는 보내고
> 있었고 Trust Layer 위반 경고다). 계약 테스트가 잡았다. ⑵ 위저드 패널의 「서버 응답에 파라미터 필드가
> 없어」 문장이 내 변경으로 **거짓이 되어** 실개수로 교체했다.
>
> ★**베이스라인 1건 재생성** — `StrategyCall.line` 추가가 `ast_content_report.json` 을 바꿨다.
> 맹목 재생성 대신 **`line` 키를 벗기면 옛 것과 완전히 같은지** 대조하고 나서 썼다(드리프트 0 · 바뀐 것은
> strategy_calls 를 가진 3건뿐 · indicator 3건은 0개라 무변경).

> ★**2026-08-27 착수 — 전략 브리핑 축([ADR-040]·[ADR-041]·[ADR-042]).** 사용자 질문 3건(「Python 도 쓰고 싶다」·
> 「LLM 이 전략을 구현해줬으면」·「백테스트 전에 어떤 전략인지 보는 화면」)이 **하나의 화면으로 수렴**했다.
> **Stage 0(ADR 3건 + PRD §4 개정 + CONTEXT 용어 3종)은 이 커밋이 끝냈다.** 남은 것 = Stage 1~5.
>
> ★**조사에서 나온 것 — 재료의 90% 가 이미 코드에 있었고 노출만 안 돼 있었다.**
> `ast_extractor.extract_content()` 가 선언·**파라미터 전량**·var·주문호출을 `to_dict()` 까지 뽑는데
> `ParsePreviewResponse` 가 안 실어서, ⑴ `diagnostics-strip.tsx:169` 「파라미터」 탭이 *「스키마에 파라미터
> 필드가 0건이라 표를 렌더하지 않는다」* 주석과 함께 **라벨만 붙은 채 비어 있고** ⑵ Optimizer 폼은 사용자가
> Pine 변수명을 **손으로 타이핑**한다(`features/optimizer/form-schemas.ts:44`) ⑶ `param_count` 가 AST 가 아니라
> **정규식**이다(`strategy/service.py:48`). **Stage 1 하나가 셋을 동시에 닫는다.**
>
> ★★**「LLM 이 Python 으로 구현」은 기각했고 그 근거가 이 레포에 있었다** — `ADR-011:275-289` 실측:
> DrFX 변환에서 Opus/Sonnet/GPT-5/Gemini 가 **각각 다른 구조적 버그**(SL 기준점·부동소수점 `==`·look-ahead),
> GPT-5·Gemini 는 진입 로직 자체가 실패해 **0 trades**. 기록 문구 = 「**수렴도 0**」.
> 대신 [ADR-004](./adr/004-pine-parser-approach-selection.md) 가 **2026-04-15 에 이미 적어 두고 4개월간
> 구현되지 않은 대안**을 발효했다 — 「AST → Python **읽기 전용 렌더러**」. 보여줄 Python 은 실행할 코드가 아니다.
>
> ★★★**Python 실행기를 안 만드는 근거는 문서가 아니라 실측이다.** 선행 조건 10건이 전부 미충족 —
> API 가 컨테이너가 아니라 **호스트 uvicorn** · DB 접속이 **Postgres 슈퍼유저**(`COPY FROM PROGRAM` 이 컨테이너
> 격리를 무효화) · 워커 4대 env 에 **Fernet 마스터 키** · **개방 가입**(`requireEmailVerification: false`,
> Cloudflare Access 는 **FE 도메인에만**) · `backtest.run` 에 시간 상한 **없음** · CPU·메모리 알림 **0개** ·
> compose 전 파일에 `cpus`/`pids_limit`/`cap_drop` **0건** · 2 OCPU 를 타 프로젝트와 공유하며 소크 창이 도는 중.
> ⇒ **「실사용자 0명」은 「공격자 0명」이 아니다.** 목록 전문 = [ADR-042] §실측.
>
> ★**사용자 결정으로 남은 위험 1건(기록)** — LLM 이 Pine 과 Python 을 **둘 다** 낸다(정본은 Pine).
> 두 산출물이 어긋나는 것을 **막을 수단이 없고** 그것이 위 `ADR-011:275` 가 실측한 실패 모드다.
> 이 설계는 제거 대신 **가시화**한다(통과한 Pine 을 렌더러로 Python 화해 대조 → diff 표시).
> 되돌릴 자리와 비용은 [ADR-041] §트레이드오프에 적어 뒀다.

★★**2026-08-25 외부 관례 대조(n12 가 안 한 것을 사후 보강).** n12 의 `bar/s` 는 레포 사정에서 나온 단위였고 **업계 대조 없이 골랐다.** 대조 결과 **단위 선택 자체는 관례와 일치한다** — QuantConnect LEAN 은 **DPS(data points per second)** 를 「**각 벤치마크 알고리즘별로**」 재고(우리가 corpus 별로 나눠 잰 것과 같은 형태), backtrader 벤치마크는 **candles/second**(지표·브로커 포함 12,473 c/s)로 공표한다. vectorbt 만 처리량이 아니라 「N개 백테스트를 T초에」로 낸다. ★**그러나 방법론 결함 3건이 드러났다.** ⑴ **median-of-3 를 안 했다** — 공개 벤치마크 관례는 **동일 머신 3회의 중앙값**이고, `s1_pbr` 이 3.88초↔9.98초(2.6배)로 흔들린 것이 정확히 그 이유다(가드 임계 2.0배가 이 소음을 흡수하는 것이지 코드 회귀만 보는 게 아니다). ⑵ **TradingView 기준을 안 봤다** — 이 제품은 TV Pine 을 가져오는 제품인데 **TV 는 처리량을 안 쓴다**: 스크립트 실행 **20초(basic)/40초**, bar 당 루프 **500ms**, plan 별 bar 수 상한 5,000~40,000. `s3_rsid` 의 첫 파스 16초는 그 상한권 안에 있는 값이므로, **제품 기준으로는 「TV 가 통과시키는 스크립트가 우리 엔진에서 통과하는가」가 처리량보다 맞는 축일 수 있다.** ⑶ **`bar/s` 의 분모가 오염됐다** — 위 PRD 항목에 적었다(파스는 bar 수 무관 고정비 ⇒ 데이터가 길수록 수치가 저절로 좋아지고 1Y 선형 환산은 60% 과대). 출처 = TradingView Pine 문서 「Limitations」 · QuantConnect 「Engine Performance」 · backtrader 성능 벤치마크 · BacktestScore 2026 벤치마크 방법론.

★**재료 선별에서 나온 것 — 「하네스 가능」이 「트리거 도래」보다 훨씬 좁다.** 열린 12건 중 lane 이 된 것은 **1건**([BL-520])뿐이고, 나머지 lane 은 이번 세션이 표면화한 부채로 채웠다. 기각 사유: [BL-434] 최종 증명이 실주문(외부 네트워크) + 근거 `BL-437` 절이 **docs 에 부재**(죽은 앵커) · [BL-371] 하네스는 가능하나 **아무 원장도 안 닫는다**(투기적 커버리지) · [BL-641] 판정식 테스트가 이미 72건으로 포화 · [BL-453] 아래 ⓪ 표 B행 참조 · 나머지는 사용자 결정·외부 접근.
★★**[BL-520] 착수 전 실측이 n9 선례의 결함을 찾았다** — `record_metric_safely(X.labels(..).inc)` 는 **인자 선평가**라 `.labels()` 가 가드 **밖**에서 돈다(`_count_safely` docstring 이 이미 경고한 것). 실측 **14건 · 전부 `live_signal.py`**. census 는 인자 서브트리를 guarded 로 세어 **거짓 초록**을 낸다 ⇒ lane step0 이 이 축의 검사기를 먼저 세운다. **그 축 없이 스윕했으면 lane 이 초록을 내면서 결함을 복제했다.**
★★**내 탐지기가 위양성 2건을 냈다** — `record_metric_safely(lambda: ...)` 는 지연 평가라 정상인데 `ast.unparse` 로 본문을 읽어 위반으로 셌다. **음성 대조(lambda 4건)를 넣고서야 갈렸다** — step0 의 필수 단언에 그것을 박아 뒀다.
★**census 실패 메시지가 틀린 복구 지시를 한다** — 「이 항목을 0 으로 낮춰라」인데 `Counter() == {'k':0}` 은 False 다. 무인 codex 가 따르면 재시도 한도를 태운다 ⇒ step0 의 첫 작업이다.
★**n8 재료는 후보 6건 중 3건이 코드 대조에서 무너진 뒤 남은 것이다** — ⑴ 금액 경로 `float()` 는 결함이 아니다(`LedgerSeedLeg.qty: float` 등 **pine_v2 엔진 계약으로의 변환**이고 엔진은 설계상 float 기반이다: `strategy_state.py` `: float` 74개) · ⑵ dashboard `error.tsx` 8곳 누락은 결함이 아니다(**`app/(dashboard)/error.tsx` 가 라우트 그룹 전체를 덮고** 「다시 시도」까지 갖췄다) · ⑶ [BL-489] 는 **트리거 미도래**(원장이 든 2-pass 처방 자체가 반증돼 착수하면 반증된 처방을 구현한다). **세 건 다 「문서·개수」를 읽고 「의미」를 안 읽어 생긴 것이다 — 같은 패턴의 N번째다.**
~~남은 세션 비용 축을 마저 깎는다 — `apps/web/AGENTS.md` 373줄(7,195 tok)을 200줄 아래로~~ → **2026-08-24 — 이 항목은 lane 이 될 수 없다.** 그 파일은 **모든 lane 프롬프트에 전문 주입되는 가드레일**이라
주행 중에 바뀌면 lane 마다 다른 규칙을 본다. **CONTROL 이 하네스 주행 전/후에 단독으로** 처리한다. → **2026-08-24 주행 종료로 조건 충족 — 위의 살아 있는 `다음 행동` 으로 승격.**
~~`apps/api/AGENTS.md` 508줄 → 275줄, 목표 <200줄은 아직 75줄 미달~~ → **2026-08-25 n11 preflight 로
275→200줄**(18,878→14,124B). 절 번호 1~10 은 그대로 두고(외부 참조 `docs/lessons.md`·`backlog-deferred.md`),
깎은 것은 ⑴ §1 스택 표 12행 — 10행이 루트 `AGENTS.md` §2 와 **중복**이라 BE 고유 3줄만 남겼다 ·
⑵ JWT 검증 코드 블록(실물 `src/realtime/auth.py` 포인터로) · ⑶ §7 alembic 셸 블록 → 규칙 목록 ·
⑷ 절 구분선 `---` 9개. **가드레일 4축 중 BE 판이 이로써 목표선 아래다**(FE 는 2026-08-24 199줄).
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
> 어느 게이트도 그것을 안 잡는다(`ledger-vitals` 는 **행 수 ≥1** 만 본다). ★대조는 원장으로 하고
> **양쪽이 비면 ABORT** — 빈 입력이 「일치」로 새는 것이 그 회차가 두 번 밟은 함정이다.
>
> **강등 tombstone (2026-08-23 · 700줄 상한).** 서문 25줄 → 이 8줄. 원문 = `git show dfbdfad3:docs/status.md`.

| #      | 후보 (= ACTIVE ∪ (PARTIAL ∧ 도래))                                                                                                                                                                                                                                                                                                                                                                                                                                   | P   | 추천                                                                                                              | 난이도 | 소요            | `apps/api/src` | 왜 지금 (= 트리거 도래 근거)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ----------------------------------------------------------------------------------------------------------------- | ------ | --------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **C**  | ~~[BL-832] 콜드 파스가 **프로세스 경계마다** 다시 든다 — AST 를 프로세스 밖으로 캐시 ~~ | P1  | ★★★ | 중 | M | **건드림** | **2026-08-26 종결** — 로컬 디스크 L2 캐시 구현·변이 5/5·전량 5,440 green. 아래 ⓻ 참조. ~~옛 근거: [BL-829] preflight 가 이 항목을 낳았다. 그 항목의 전제(「지배 성분 = full-context 재시도」)가 실측으로 깨졌고(SLL 로 204→0 을 만들어도 **3.7%**), 진짜 지배 성분은 `closure_` **96.8%** 였다. 콜드 비용을 줄이는 **유일하게 실측된 축**이 이것이다 — pickle 왕복 digest 보존 확인, `i3_drfx` **53.38초 → 0.0048초**. ★첫 step 은 구현이 아니라 **저장소·pickle 신뢰 경계 결정** |
| **D**  | [BL-827] `openapi-check` 가 CI 밖이라 계약 drift 를 2주간 아무도 안 봤다 — ★**2026-08-30 재측정: 「2주」가 아니라 「축 하나 통째」** | P3 → ★**실질 P1** | ★★★ | 하 | S | 0줄 | ★**2026-08-26 표 누락 수리** — `ACTIVE` · 「트리거 도래」인데 이 표에 행이 없었다(2026-08-25 등재 이후). 표 서문이 경고한 바로 그 drift 다. 실측 재확인 = `grep -c openapi .github/workflows/ci.yml` **0**. ⑴ 은 CI 한 줄이라 **다른 회차에 동승 가능**하고, ~~⑵ PoC 생성물 수명은 [ADR-031] 결론 확인이 선행~~ → **2026-08-30 사용자 결정 = 삭제**(참조 0건 · 파급 7좌표는 [BL-827] 본문). ★★★**2026-08-30 재측정 — drift 가 845줄이고 빠진 것은 스키마가 아니라 엔드포인트 4종 전량**(`/llm/models`·`/strategies/generate`·`/{id}/brief`·`/{id}/brief/narrative`) = [ADR-040]·[ADR-041]·[ADR-042]+PR #843 축이 통째로 계약 밖이다. ★**「CI 한 줄」의 `.env.local` 위험도 실측으로 소거**했다 — CI backend 잡의 기존 env 8종만으로 `export_openapi.py --check` 가 rc=1(정상 판정)을 낸다. ⇒ **⓾ lane 1 로 확정** |
| **E**  | [BL-833] Optimizer 폼이 Pine 변수명을 **손으로 타이핑**하게 한다                                                                                                                                                                                                                                                                                                                                                                        | P3  | ★★                                                                                                                | 하     | S               | 0줄            | ★**데이터가 이미 있다** — [ADR-040] Stage 1 이 `ParsePreviewResponse.inputs`(이름·타입·기본값)를 열었고 brief 도 같은 목록을 준다. 남은 것은 `form-schemas.ts:44` 의 자유 입력을 select 로 바꾸는 것뿐. ~~★**비용 함정** — 브리핑을 그냥 부르면 옵티마이저 화면에 **콜드 파스 53.38초**(`i3_drfx` 실측)가 붙는다. warm 경로나 목록 API 에 얹어라.~~ → ★★**2026-08-30 — 그 함정은 L2 디스크 캐시(`bdc13117` · PR #837 · BL-832 는 RESOLVED 라 섹션 삭제)가 이미 없앴다.** 53.38초는 캐시 이전 수치고 지금 콜드는 **소스당 1회**(재방문 4.8ms)다. ★★**진짜 제약은 따로였다 — `inputs` 를 주는 GET 이 없다**(`ParsePreviewResponse` 와 `/{id}/brief` 뿐 · `StrategyResponse` 엔 없음, 필드 전수 확인). ⇒ **확정 경로 = `GET /strategies/{id}` 로 `pine_source` → `POST /strategies/parse`.** BE 0줄·계약 변경 0이라 lane 1 과 안 겹친다. ★스윕 불가(`input_type ∉ {int,float}`)는 **숨기지 말고 비활성+사유**로. ⇒ **⓾ lane 3 으로 확정** |
| **F**  | [BL-834] `convert` 만 스키마 강제·provider 선택 **밖**에 남았다 + `sliced` 도달 불가                                                                                                                                                                                                                                                                                                                                                     | P3  | ★                                                                                                                 | 중     | M               | **건드림**     | PR #840 이 `narrative/providers.py`(세 provider 스키마 강제 + `LLM_PROVIDER_ORDER`)를 세웠는데 `convert/service.py` 는 `tools=`/`response_schema=` **0건**으로 혼자 남아 문자열 수동 파싱 + anthropic→gemini 하드코딩이다. ★같이 묶인 둘 — `mode="sliced"`(토큰 **77~97% 절감**)가 BE 완비인데 FE `"full"` 하드코딩으로 **도달 불가**, 그 버튼의 유일한 호출처가 **422 에러 카드**라 정상 흐름 진입점 0개. ★~~**셋을 따로 고치면 세 번 연다**~~ → **2026-08-30 갈랐다** — ⑵⑶(FE)는 **⓾ lane 2**, ⑴(BE)은 다음 회차. 근거: 파일 축이 FE/BE 로 완전히 갈리고 ⑴ 은 JSON 스키마 계약 결정이 선행이다. ★★★**⑵ 의 값이 원장보다 세다 — `sliced` 는 토큰 절감이 아니라 LLM 을 아예 안 부르는 경로다**(`convert/service.py:52-68` — `is_runnable` 이면 `input_tokens=0, output_tokens=0` 으로 즉시 반환). FE 가 `"full"` 을 박아 둔 한 **그 경로는 한 번도 돈 적이 없다**. ★★**⑴ 은 2026-08-29 anthropic 키 제거로 증상이 발현했다** — convert 는 anthropic→gemini 하드코딩이라 지금 **gemini 단독**인데 응답 경고문에 **`(fallback)`** 을 붙여 사용자에게 거짓을 말하고, `openai` 는 도달 불가다 |

> ★**강등** — 2026-08-24 n9 로 **O([BL-641]) · J([BL-547]) · BO([BL-811])** 3행이 내려갔다: [BL-547]·[BL-811] 은 **종결**(본문 삭제 — 원문은 `git show 1a1169a5:docs/backlog.md`), [BL-641] 은 **재분류** — Trigger 가 「소크 재기동 회차마다 재측정」이라 일회성 종결점이 없고 입력이 살아 있는 소크 창이다. 소크 회차에 **동승**시켜라. 2026-08-16 에 5행([BL-026]·[BL-726]·[BL-729]·[BL-730]·[BL-731], 원문 `git show b5e24fbf:docs/status.md`), 2026-08-17 야간에 4행([BL-725]·[BL-732]·[BL-735]·[BL-737], 원문 `git show 0875789c:docs/status.md`)을 지워 700줄 상한 안에서 신규 행 자리를 만들었다. 지운 것은 전부 **이미 취소선이던 사문**이다.
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
