# 게이트와 함정 — 모든 세션이 여는 문서

> 무엇을 돌려야 "통과" 인지와, 통과한 줄 알았는데 아닌 경우들.
> 2026-07-26 신설. 이 내용은 그전까지 스프린트 문서 7개에 복붙되고 있었고,
> `reference/` 에 있던 유일한 진술은 **틀려 있었다** (아래 `pnpm test` 항목).

---

## 1. 통과 가능한 게이트

```bash
QB=/Users/woosung/project/agy-project/quant-bridge

# 인프라 (격리 포트)
cd $QB && mise run up-isolated && mise run migrate-isolated

# BE — ruff / mypy / pytest
cd $QB/apps/api && uv run ruff check .
cd $QB/apps/api && uv run mypy src/
cd $QB/apps/api && set -a; source .env.local; set +a; uv run pytest -q

# OpenAPI 계약 drift (2026-08-16 배선 — ADR-031)
cd $QB && mise run openapi-check          # 커밋된 contracts/openapi/openapi.json 이 코드와 같은가

# FE — typecheck / vitest / eslint
cd $QB/apps/web && pnpm typecheck
cd $QB/apps/web && pnpm test
cd $QB/apps/web && pnpm lint
cd $QB/apps/web && pnpm build          # apps/web/.env.local 의 BETTER_AUTH_* 필요 (ADR-034)

# 디자인 캐논 런타임 (dev 서버 자동 기동, 인증 불요)
cd $QB/apps/web && pnpm e2e:design-canon

# e2e authed (apps/web/.env.local 에 E2E_AUTH_EMAIL·E2E_AUTH_PASSWORD 필요, 로컬 전용 — CI 에 없다)
cd $QB/apps/web && pnpm e2e:authed
```

`mise run lint` / `mise run typecheck` / `mise run test` 는 위를 FE+BE 로 묶은 것이다. 단 **env 를 source 하지 않으므로** BE pytest 는 셸에 3-env 가 이미 있어야 한다.

문서 구조·활성 Markdown 링크·폐기 경로는 루트에서 `mise run docs-audit`으로 검사한다.

### 게이트 3종 신규 (2026-08-11 ledger-truth)

```bash
cd $QB && bash tools/scripts/skip-ratchet.sh    # 무조건 skip 개수 동결 (baseline 0 · 스코프별 하한 미달 → rc=3)
cd $QB && mise run docs-audit                 # ⓪ 표 정체성 축 포함 (아래)
cd $QB && mise run gate-harnesses             # ★게이트 하네스 14종 전량 (2026-08-17 · tool-pin-audit 추가)
```

- **`skip-ratchet`** — `@pytest.mark.skip` 데코레이터 **와** 모듈 레벨 `pytestmark = pytest.mark.skip(...)`
  을 센다. `skipif` 와 `conftest` 의 프로그램적 마커는 **세지 않는다**. baseline 초과 → rc=1,
  **스코프 경로 부재·스코프별 하한 미달 → rc=3**(빈 입력을 초록으로 통과시키지 않는다).
  ★왜 있나 — 2026-05-14 에 「Sprint 61 follow-up」 사유로 심긴 5건이 **Sprint 61 종료 후 3개월**
  살아남았고 대응 BL 은 0건이었다. pytest 는 skip 을 초록으로 보고하므로 **꺼진 테스트는 통과와
  구분되지 않는다.**
  ★★**2026-08-11 [BL-705] — 하한이 두 스코프 「합계」였다.** `os.walk` 는 없는 디렉터리에서
  조용히 0 을 내므로, 위반이 사는 `apps/api/tests`(505)가 통째로 안 스캔돼도 `apps/api/src`(217)가
  합계 하한 200 을 넘겨 **「위반 0건 ✓ rc=0」** 이었다(`TARGETS` 두 항목 중 하나만 오타 나면
  발화). 하한을 **스코프별**(tests 350 / src 150 = 실측의 70% 선)로 바꾸고 경로 부재를 따로
  판정한다. ★그리고 그 회귀를 잡는 것은 자기검사가 아니라 **`tools/scripts/skip-ratchet-test.sh`**
  (임시 트리 11케이스)다 — 자기검사의 입력은 「한 줄 문자열과 정수」라 **스캔층을 한 줄도
  안 덮는다.** 「하네스는 고아가 된다」는 신설 시 판단이 여기서 반증됐다.
  ★★**자기검사는 정상 상태에서 절대 발화하지 않는다 ⇒ 그것을 통째로 지워도 게이트는 초록**
  이다(실측). 케이스 ⑩⑪ 이 래칫 **사본**에 변이를 심어 「자기검사가 실제로 우는가」를
  behavioral 로 잰다 — 안 그러면 「검사기를 검사하는 검사기」가 다시 무증거가 된다.
  남은 사각 = 함수 몸통 안 `pytest.skip(...)` 인라인 · 기본 ROOT 파생 경로(하네스가 env 로
  트리를 주입하므로 그 갈래는 `final-gates.sh` 의 실물 실행이 덮는다).
- **`docs-audit` ⓪ 표 정체성 축** — 살아 있는 행 == `bl-audit --list ACTIVE ∪ (PARTIAL ∧ 도래)`.
  취소선은 **후보 셀만** 본다(다른 셀의 `~~정정 이력~~` 을 「죽었다」로 읽으면 안 된다).
  양쪽이 비면 **rc=3**. ★~~`(PARTIAL ∧ 도래)` 는 지금 **구조적 공집합**이다 — PARTIAL 24건 중
  `**트리거 판정:**` 줄이 **0건**이다~~ → **2026-08-11 [BL-703] 이 채웠다.** PARTIAL 전건이
  판정줄을 갖고 `docs-audit` 이 그 의무를 강제하므로, 이 축은 이제 **두 항을 다 쓴다**
  (착수 근거였던 「P0 1 + P1 4 가 올라온다」는 실측으로 반증됐다 — 올라온 것은 다른 5건이다).
- **`mise run gate-harnesses`** — 「게이트가 무엇을 재는지 재는」 검사기 **14종**(2026-08-13
  [ADR-030] 이 `fleet-dispatch-test` 를 함대 축과 함께 회수해 9→8, 2026-08-14 `final-gates-test`
  ([BL-721])와 `assert-main-checkout-test`([BL-722])가 8→10, 2026-08-15 `soak-stack-test`
  ([BL-735])가 10→11, 2026-08-16 [ADR-033] 의 `db-backup-test`·`disk-guard-test` 가 11→13,
  2026-08-17 [BL-785] 의 `tool-pin-audit-test` 가 13→14).
  ★★**2026-08-11 실측 — CI 는 종전에 하네스를 하나도 돌지 않았다**(7종 전부 CI 호출 0).
  게이트 본체만 돌면 레포가 이미 깨끗하기 때문에 **판정 로직을 통째로 지워도 초록**이다
  (BL-569 가 `bl-audit` 에서, BL-601 이 구 `fleet-dispatch` 에서 겪은 그 모양). 종전에 그 회귀를
  잡는 유일한 자리가 **회차 끝 로컬 `final-gates.sh` 1회**였다 = 회귀를 **다음 회차 끝까지 못 본다.**
  ⇒ CI `documentation` 잡(경로 필터가 없어 **항상** 돈다)에 배선했다.
  **판별력 실증** — ⓪ 축의 불일치 수집을 죽이면 `mise run docs-audit` 은 **rc=0**(회귀 불가시)인데
  `mise run gate-harnesses` 는 **rc≠0** 으로 잡는다.
  ★**고아 하네스 2종을 같이 붙였다** — `soak-watch-test` · `pre-push-guard-test` 는 레포에
  **존재하고 초록인데 호출자가 0** 이었다. docker·네트워크 의존은 0 이다(`soak-restart-test` 는
  docker 를 언급하지만 로그+`exit 1` 스텁을 PATH 앞단에 깔고 돌려 **17/17 통과 · 스텁 호출 0회**로
  확인했다 — 진짜 docker 를 부르지 않는다).

### 게이트 2단 — `--pre-pr` / `--deferred-only` (2026-08-14)

**왜 나눴나 — 실측이다.** 전량 1회가 **15~20분**인데 그 대부분을 여섯이 먹고, **CI 가 같은 것을
이미 샤딩해서 돈다**(`ci.yml` 의 `backend`·`backend_coverage`·`e2e` 잡). 로컬 전량 실행은 CI 를
직렬로·비샤딩으로 한 번 더 하는 것이었다.

| 게이트                                                        |                                     실측 | CI 가 도나                     |
| ------------------------------------------------------------- | ---------------------------------------: | ------------------------------ |
| BE pytest (4,604건)                                           |                                **379초** | ✅ `backend` 잡이 **샤딩**해서 |
| e2e 3레인                                                     |                               ~**400초** | ✅ `e2e` 잡                    |
| CI fresh DB alembic · 커버리지                                |                                 수십 초~ | ✅                             |
| 나머지 21종 (ruff·mypy·typecheck·lint·감사·하네스 10종·build) | 합계 **1분 안쪽** (최장 = FE build 17초) | 일부만                         |

★★**유예 ≠ 무조건 실행. 영역 판정이 먼저다** (2026-08-14 · [BL-723]). `--deferred-only` 가 도는
것은 「유예분 ∩ **영역이 살아 있는 것**」이다. 종전에는 가장 비싼 셋만 영역 판정 밖에 있어서,
`apps/web`·`apps/api` diff 가 **0줄**인 회차에서 **11분 10초**가 그냥 탔다(BE pytest 357초 ·
e2e authed 268초 · design-canon 42초). 같은 회차에 CI 는 `backend`·`e2e` 잡을 **전부 skip** 했다 —
로컬이 CI 보다 더 돌면서 잴 것은 없었다.

| 게이트                               | 영역 술어               | 왜                                                   |
| ------------------------------------ | ----------------------- | ---------------------------------------------------- |
| BE ruff · mypy · **pytest**          | `has_be`                | `apps/api/**` 가 안 바뀌면 잴 것이 없다              |
| FE typecheck · lint · vitest · build | `has_fe`                | `apps/web/**` 동일                                   |
| `/vercel-react-best-practices`       | `has_fe`                | 신호 게이트도 같은 술어                              |
| e2e chromium · **design-canon**      | `has_fe`                | 랜딩·hermetic `file://` — 서버 무결합                |
| **e2e authed**                       | `has_fe` **∥** `has_be` | 로그인 후 데이터 화면 — **BE 가 죽으면 화면이 빈다** |
| 감사·하네스·CI 재현·신호 3종         | 없음 (항상)             | 레포 전역 규율이라 영역이 없다                       |

★`|| [ -z "$BASE" ]` **fail-safe 는 전부 유지한다** — `merge-base origin/main HEAD` 가 실패하면
영역이 0 으로 보이므로, 그때는 **돈다**. 조용한 skip 이 조용한 초록보다 나쁘다.
★세 e2e 레인 영역이 전부 비면 **정체성 프로브(curl)도 안 돈다** — 잴 것이 없는데 서버를
요구하면 docs 만 고친 회차가 e2e **FAIL** 로 막힌다(종전 동작).

```bash
# ⑴ 중간·PR 직전 — 무거운 9종을 유예한다 (~1분)
tools/scripts/final-gates.sh --run <슬러그> --pre-pr

# ⑵ PR push 후 — CI 가 도는 동안 **나란히** 로컬에서 유예분만
tools/scripts/final-gates.sh --run <슬러그> --deferred-only

# 계획만 보고 싶으면 (아무것도 안 돌린다 — 더러운 트리에서도 된다)
tools/scripts/final-gates.sh --run <슬러그> --pre-pr --dry-run
```

★★**유예는 면제가 아니다.** `--pre-pr` 은 미룬 것을 `.claude/gates/<슬러그>/deferred.txt` 에 적고
종결 문구를 **다르게** 낸다(「pre-PR 통과 — 단 N종을 아직 안 돌렸다. 이것은 종결 판정이 아니다」).
`--deferred-only` 통과가 그 파일을 지운다 ⇒ **원장이 남아 있으면 종결이 아니다.**
같은 「✓ 전건 통과」를 냈으면 「초록인데 안 봤다」가 됐을 것이고, 그게 이 레포가 반복해 덴 병이다.

★**신호 4종도 유예 대상이다** — `--pre-pr` 은 「코드가 성립하나」를 묻는 중간 검사라 아직 스킬을
안 돌렸을 수 있다. 종결 판정(신호가 이 회차 것인가)은 `--deferred-only` 가 진다.

★모드 3종은 **상호 배타**이고 둘을 주면 거부한다. 결과표에 **게이트별 소요(초)**와 실행 합계가
찍히므로, 다음 사람은 인상이 아니라 수치로 무엇을 미룰지 정할 수 있다.
판별력 = `tools/scripts/final-gates-test.sh`(케이스 8 · 변이 3 + 음성 대조 1). ★그 하네스가 **안**
재는 것은 유예 원장의 기록·해제다(실제 통과 실행에서만 일어난다 — 2026-08-14 손으로 1회 확인).

### 신호 4종 (`.claude/gates/<run>/`) — 판정식 · rc 규약 · ★브랜치 전제 ([BL-706]·[BL-714])

`final-gates.sh` 는 스킬 실행의 증거로 파일 4개를 요구한다. 각 파일 **첫 줄은 `commit: <sha>`**
(hex 7~40, `rev-parse` 로 해석)여야 하고, 그 sha 의 **신선도**를 `signal-check.sh` 가 판정한다.

| 파일        | 무엇의 증거                      | 필수 여부                    |
| ----------- | -------------------------------- | ---------------------------- |
| `vercel.ok` | `/vercel-react-best-practices`   | `apps/web/**` diff 있을 때만 |
| `screen.ok` | MCP playwright 또는 `/browse`    | 항상                         |
| `codex.ok`  | `/codex` 적대 리뷰 findings 처분 | 항상                         |
| `g9.ok`     | 계획 vs 실제 구현 최종 점검 표   | 항상                         |

**신선도 판정 — 앵커 A1~A5 를 이 순서로 본다** (`signal-check.sh:60-79`):

| 앵커 | 조건                                       | CODE                | rc  |
| ---- | ------------------------------------------ | ------------------- | --- |
| A1   | `merge-base(origin/main,HEAD)` **== HEAD** | `no-branch-commits` | 1   |
| A2   | `sha == HEAD`                              | `head`              | 0   |
| A3   | `origin/main` 부재                         | `no-origin-main`    | 1   |
| A4   | `sha` 가 HEAD 의 조상이 **아님**           | `not-ancestor`      | 1   |
| A5   | `sha` 가 merge-base 의 조상                | `origin-main`       | 1   |
| —    | 그 외 (브랜치 범위 안)                     | `branch`            | 0   |

**rc 규약** = `0` 신선 / `1` 낡음·부재·형식위반 / `2` 사용법 / **`3` 판정 불가(abort — ★초록을 내지 않는다)**.
호출부 `final-gates.sh:check_signal()` 에서 **rc=3 은 필수 여부와 무관하게 FAIL** 이다(fail-open 금지).

★★**브랜치 전제 — A1 이 A2 **앞**에 있다는 뜻은 이것이다.** 전건 머지돼 `merge-base == HEAD` 가 된
main 에서는 신호 sha 가 HEAD 와 **정확히 같아도** `stale[no-branch-commits]` rc=1 이다. 즉
**「마지막 커밋 뒤에 게이트」는 「그 회차의 PR 브랜치에서, 머지 전에」를 함께 뜻한다.**
2026-08-12 회차가 먼저 머지한 뒤 신호를 취득해 4종을 초록으로 만들 수 없었다 ⇒ [BL-714].

★**이 전제는 이제 문서 규율이 아니라 스크립트가 막는다** — `final-gates.sh` 가 인자 파싱 직후
`merge-base == HEAD` 를 검사해 **게이트 체인 진입 전에 거부**한다([BL-706] 의 `--run eod` 거부와 같은 문형).
`origin/main` 이 없는 저장소에서는 발화하지 않는다. 하네스 케이스 **㉖** 이 양·음성 양쪽을 고정한다.

★**A1 을 우회하는 「범위 탈출구」는 기각됐다**([BL-714] 2026-08-14). A1 의 방어 대상은 정확히 1개
상태이고 그 유일한 증인이 케이스 **⑫** 인데, `--range` 로 merge-base 를 사람이 대체하게 하면 ⑫ 가
green 이 되어 **증인이 사라진다**. 신호 첫 줄에 `range:` 를 적는 안도 기각 — squash 머지라 브랜치
팁이 HEAD 의 조상이 아니어서 제3자·CI 가 그 범위의 실재를 검증할 수 없다.

### 소크 (P0 [BL-003] 의 달력 시간 게이트)

```bash
# 소크를 커밋에 고정해 돌린다 — 그래야 apps/api/src 를 편집해도 워커가 재적재되지 않는다
tools/scripts/soak-stack.sh pin        # .soak/src 를 HEAD 에서 다시 뜬다 (apps/api/src 가 dirty 면 거부)
tools/scripts/soak-stack.sh up         # 3층 compose 로 기동 + celery ready 배너를 기다린다
tools/scripts/soak-stack.sh commit     # ★소크가 도는 커밋 — celery MainProcess 의 /proc 를 통해 읽는다
tools/scripts/soak-stack.sh status     # 고정 여부 · 커밋 · 활성 세션 · main 조상 여부
tools/scripts/soak-stack.sh ps         # ★DB 를 안 건드리는 생존 확인 — exit 0 = 하나라도 running / 1 = 완전 down
                                 #   status 는 psql 을 쏘므로 down 이면 그 자체가 못 돈다 ([BL-656])

# 「1주 안정 운영」을 기계가 판정한다 — PASS / FAIL / UNKNOWN, PASS 만 exit 0
tools/scripts/soak-gate.sh             # 표본을 남기고 판정
tools/scripts/soak-gate.sh --install   # 30분마다 자동 (표본이 없으면 C4 를 판정할 수 없다)
                                 # macOS = launchd / 리눅스 = systemd user timer
                                 # ★리눅스는 lingering 이 필요하다 — 없으면 SSH 끊길 때 timer 도 멈춘다
tools/scripts/soak-gate.sh --status
tools/scripts/soak-gate.sh --prune-archives            # phantom 아카이브 회수 — 기본 dry-run, 옮기고 지우지 않는다
tools/scripts/soak-gate.sh --prune-archives --confirm  #   ★[BL-626] 기준은 개수가 아니라 **포함관계**다
```

★**아카이브 회수에 개수 상한을 쓰지 마라 — 그것은 판정을 깎는다**([BL-626], 2026-08-09 실측).
아카이브는 커버리지 구간(`log_from`~`log_to`)을 들고 있고 C1 은 **커버리지가 덮은 시간만** 센다.
228벌에서 「최근 50개만 남긴다」면 커버리지 시작이 `08-04T15:51` → `08-08T18:21` 로 나흘치가
사라진다. 168h 를 30분 주기로 채우려면 ~336벌이 필요하므로 **안전한 상수 N 은 없다.** 그래서
`--prune-archives` 는 같은 `(log_from, predicate_version, classifier_ok)` 안에서 `log_to` 가 가장
늦은 것만 남긴다(나머지의 상위집합). ★`log_to` 가 ISO 가 아닌 것은 **절대 회수하지 않는다** —
파손본 10벌이 타임스탬프 자리에 문자 `Error` 를 들고 있고, 문자열 정렬로 재면 `'Error'` 가 ISO
보다 커서 **파손본이 대표로 뽑히고 성한 것이 버려진다.**

★★**「지금 `up` 을 눌러도 되나」는 판독이 답한다 — 머릿속으로 풀지 마라** (2026-08-15 [BL-003]).
판독 끝에 `▶ 새 창을 열어도 되나` 블록이 나온다. **`up` 은 진행 중인 귀속 구간을 닫는다** —
자격(연속 24h + 실격 0)을 얻기 **전에** 누르면 그때까지 번 시간이 **창 0회로 소멸**하고,
얻은 **뒤에** 누르면 그 창은 자격 1회로 확정돼 남는다(닫힌 구간도 계속 세어지므로).
그 차이를 매 회차 사람이 손으로 풀고 있었다 — 2026-08-13 창은 **27.4시간**을 돌고도 C1 이
**0/3** 이었다(그 안에서 세션이 죽었다). 네 갈래로만 답한다:

| 출력                | 뜻                                    | 다음 행동                                    |
| ------------------- | ------------------------------------- | -------------------------------------------- |
| `✓ 자격 획득`       | 연속 ≥24h · 실격 0                    | 지금 눌러도 **손실 0**. 누르는 것은 사람이다 |
| `✗ 아직 자격 없음`  | 남은 시간 N · 지금 누르면 소멸할 시간 | **기다린다.** 서버를 건드리지 마라           |
| `✗ 자격 없음(실격)` | 이 창 안에서 죽었다                   | 누르는 것이 곧 「인지했고 새 창을 연다」     |
| `? 판정 불가`       | 열린 귀속 구간이 없다                 | `up` 이 구간을 열기 전에는 시간이 안 쌓인다  |

★**게이트는 절대 스스로 `up` 을 누르지 않는다.** 판독은 판독이고 여는 것은 사람의 명시적
행위로 남긴다 — 그 경계가 무너지면 「인지 없는 재기동」이 실격 시각을 지운다([ADR-024]).

술어·창·리셋 규칙은 [`ADR-024`](../../decisions/024-soak-stability-gate.md). 계산부는 I/O 없는
순수 함수(`apps/api/scripts/soak_gate_predicate.py`)라 손 계산과 대조할 수 있고, 정의는
`apps/api/tests/scripts/test_soak_gate_predicate.py` 로 동결돼 있다(개수는 세지 마라 — 세어 적으면
낡는다. 이 줄에 「22테스트」라고 박혀 있던 값이 2026-08-08 에 이미 두 배 넘게 틀려 있었다.
★경로도 낡아 있었다 — `tests/tools/scripts/` 는 [ADR-029] 재배치 전 자리다, 2026-08-15 정정).

★**실격의 원인은 게이트가 모른다** — 사람이
[`soak-disqualifications.jsonl`](soak-disqualifications.jsonl) 에 근거와 함께 등재하고, 게이트는
그것을 **보고 줄 한 줄**로만 낸다(`★실격 귀속(보고 전용 · 판정 불참)`). 판정 C1~C5 는 원장이
있든 없든 같은 값이다 — 계약과 기각된 대안은 [ADR-024 §실격 귀속 원장](../../decisions/024-soak-stability-gate.md).
MTBF 층화는 `apps/api/scripts/mtbf_stratified.py` 가 그 원장을 읽어 자동으로 만든다.

★**원장은 두 호스트(서버·로컬 맥)의 사건을 함께 담고 판독은 한 호스트만 본다** ([BL-751],
2026-08-15). 그래서 「원장에 있으나 이 판독의 실격 목록에 없는 행」이 상시로 남는다 — 실측 1건은
로컬 맥 세션(`e9c504f1`, 08-14T12:26 사망)이라 서버 DB 에 있을 수 없었다. **낡은 것이 아니라
여기서 볼 수 없는 것**이므로 그 줄을 「원장이 낡았다」로 읽지 마라. 호스트 축을 원장 스키마에
넣는 것이 근본 수리다.

★**고정본 스택이 떠 있으면 `mise run up-isolated` 계열이 거부된다** — 같은 `container_name` 을
덮어써 소크를 끊기 때문이다. 정말 덮어쓰려면 `QB_SOAK_OVERRIDE=1`.

### 소크 무인 감시 + 원터치 재기동

게이트는 판정만 하고 **아무에게도 말하지 않는다**. 2026-08-06 20:31 사망 → 08-07 09:35 수동
재기동까지 **13시간**이 비었고 그 시간은 C1 에 소급되지 않는다. 감시자가 그 지연을 30분으로 줄인다.

```bash
tools/scripts/soak-watch.sh              # 게이트 1회 호출 + 지문 변화 시에만 텔레그램
tools/scripts/soak-watch.sh --dry-run    # 게이트는 부르되 알림은 안 쏘고 판단만 출력
tools/scripts/soak-watch.sh --install    # systemd user timer 30분 (★게이트 타이머는 꺼진다)
tools/scripts/soak-watch.sh --status     # 마지막 지문 · heartbeat · 타이머 상태
tools/scripts/soak-watch-test.sh         # 판단 로직 하네스 (실측 캡처 픽스처, 전건 통과 = exit 0)

tools/scripts/soak-restart.sh            # 기본 = dry-run. 재기동 8단계와 실제 값을 출력만 한다
tools/scripts/soak-restart.sh --confirm  # 집행 (⑴ FLAT=YES 아니면 그 자리에서 멈춘다)
tools/scripts/soak-restart-test.sh       # 갈래·순서 하네스 (final-gates.sh 「소크 재기동 하네스」)
tools/scripts/signal-check-test.sh       # 신호 신선도 하네스 ([BL-706] — 신호 첫 줄 `commit: <sha>` 대조. --mutants 로 변이·음성대조 전량)
#                                        # ★종수를 여기 박지 마라 — 스크립트가 스스로 센다(13→14→15 로 두 번 낡았다)
```

★**재기동은 스택 상태에 따라 두 갈래다 — ⓿ 이 `soak-stack.sh ps` 로 고른다**([BL-656], 2026-08-09).
살아 있으면 종전대로 ⑷ 에서 `down → pin → up`. **완전 down 이면 파라미터 조회보다 먼저**
`pin → up` 을 선행하고 ⑷ 와 증거 덤프를 건너뛴다. 순서가 여기여야 하는 이유는 실측이다 —
스택이 없으면 원장 조회(`_q`)부터 빈 값을 내 `--confirm` 이 「원장에 세션이 하나도 없다」로
exit 2 한다(스택 호출 0건). 그러면 `--strategy-id/--account-id` 를 손으로 줘야 하고, 그것이
이 스크립트가 없애려던 손 절차다. ★down 갈래는 FLAT 확인이 up 뒤로 밀린다 — 종전 손 절차와
같은 순서이므로 새 위험은 아니지만, 원장에 활성 세션이 남아 있으면 up 이 그것을 재개한다.

★**watch 는 게이트 타이머를 대체한다 — 추가가 아니다.** 게이트를 **기본(수집) 모드로 정확히
1회** 부른다. `--no-collect` 로 따로 도는 안은 기각됐다: 새 phantom 아카이브를 안 남겨
**감시자가 게이트와 다른 양을 잰다**(분류기가 깨져도 C5 가 ✓ 로 보이는 fail-open). `--json` 도
기각 — `soak-gate.sh:544-547` 이 `soak-gate-last-result` 를 쓰기 **전에** exit 해서
운영자의 `soak-gate.sh --status` 「최근 판정」이 영구히 낡는다.
★**30분 주기를 바꾸지 마라** — 표본 간격이 곧 C4 판정 대상이다(기본 한계 60분).
★**게이트에는 flock 이 없다**(2026-08-07 실측). 두 타이머를 같이 돌리면 `.soak/gate-samples.jsonl`
경합 + phantom 아카이브 이중 생성이 난다. `--install` 이 게이트 타이머를 끄는 이유다.

★**지문은 `(판정, 실격 건수, 귀속 창 수, C5 플래그 집합)` 4개뿐이다.** C1/C2 는 매 실행 단조
증가하고 어둠 비율은 같은 날 2.9%(09:41) → 70.6%(13:11) 로 요동친다 — 넣으면 30분마다 알림이 온다.

★**크래시는 FAIL 이 아니다.** 판정기가 죽으면 `판정:` 이 **빈 값**인 채 **exit 1** 이 난다 —
진짜 FAIL 과 종료 코드가 같다. 판별자는 **C1 앵커 줄의 유무**뿐이다(2026-08-07 09:10 실측 캡처가
하네스 픽스처로 동결돼 있다).

★**감시자의 종료 코드는 게이트 판정이 아니라 「알림이 나갔나」다.** 게이트가 FAIL 이어도 알림이
나갔으면 0, 텔레그램이 실패하면 1. 그래야 systemd 빨간불이 한 가지 뜻만 갖는다. 반대로 게이트
유닛은 UNKNOWN=2 를 그대로 내보내 **매 실행이 `Failed`** 로 찍혔다(실측 8/8) — 건강 신호로 못 쓴다.

★**설치 후 `soak-gate.sh --status` 의 타이머 줄은 「(등록 안 됨)」이 된다 — 정상이다.** 게이트는
자기 타이머만 보고 watch 타이머를 모른다. **아무것도 안 도는 게 아니다** — 같은 출력의
「최근 판정」과 「표본」이 계속 갱신되는지로 확인해라(watch 가 게이트를 기본 모드로 부르므로
`soak-gate-last-result` 와 표본이 그대로 쌓인다. 2026-08-07 실증: 설치 후 최근 판정 13:46:14 ·
표본 38건). 스케줄 확인은 `soak-watch.sh --status`.

★**`--install` 은 서버 전역 변경이다**(서버는 1대). 워크트리 격리 밖이므로 사용자 승인을 받아라.
서버 실증은 **스크립트만 scp** 한다 — `git pull` 은 체크아웃을 갱신해 게이트 스크립트까지 바꾼다([BL-623]).

#### ★★유닛에 구워진 절대경로 — 재배치가 감시를 죽인다 (2026-08-15 [BL-737]·[BL-744])

**레포에는 systemd 유닛의 원본이 없다.** 유닛은 `--install` 이 그 시점의 `${SCRIPT_DIR}` 를 박아
생성하는 heredoc 이 전부다. 그래서 [ADR-029] 재배치(`scripts/` → `tools/scripts/`)가 파일을 옮기자
서버 유닛은 **없는 경로를 문 채로 남았고**, `soak-watch.service` 는 **41시간 동안 30분마다
`rc=127`** 로 죽으면서 알림을 한 줄도 내지 않았다. 같은 재배치가 **세 곳**을 남겼다:

| 유닛/설정                            | 무엇이 낡았나                                                           | 증상                                                                              |
| ------------------------------------ | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `dev.quantbridge.soak-watch.service` | `ExecStart` = `~/quantbridge/scripts/soak-watch.sh`                     | `rc=127` · 알림 0줄 (41h)                                                         |
| `quantbridge-api.service`            | `WorkingDirectory`·`ExecStart`·`PROMETHEUS_MULTIPROC_DIR` 이 `backend/` | 08-07 프로세스가 **삭제된 cwd** 로 연명 · 죽으면 `rc=203/EXEC` 영구 실패          |
| `soak-stack.sh:SOAK_WATCHED_PATHS`   | 목록에 없는 경로 `scripts`                                              | 감시 축 침묵 (없는 경로의 `git log` 는 **빈 출력**이라 「누락 없음」과 구분 불가) |

**재배치·경로 이동 뒤 필수 점검 3줄** — [BL-719] 류 롤아웃 체크리스트에 반드시 넣어라:

```bash
tools/scripts/soak-watch.sh --status          # rc=1 이면 설치본이 낡았다 (ExecStart 실재+일치 판정)
grep -l quantbridge ~/.config/systemd/user/*  # 유닛 전수 — 각 파일의 절대경로를 눈으로 확인
systemctl --user list-units --all | grep -i quantbridge   # failed 가 없어야 한다
```

★**「타이머가 waiting」은 건강 신호가 아니다.** 41시간 내내 타이머는 정상 waiting 이었다.
★**감시자는 자기 죽음을 알릴 수 없다** — 그래서 `--install` 이 `OnFailure=dev.quantbridge.soak-watch-alarm.service`
를 함께 건다. 그 알람 유닛은 **스크립트 파일에 의존하지 않는다**(인라인 curl · `.env.local` 을
그 자리에서 소싱해 토큰을 유닛에 박지 않는다) — 다음 재배치에 면역이다.

##### ★★systemd 유닛의 함정 3종 (2026-08-15 실측)

**⑴ `${VAR}` 는 `$${VAR}` 로 써야 한다.** systemd 는 `ExecStart` 의 `$VAR`/`${VAR}` 를
**자기 환경으로 먼저 확장**하고, 미정의 변수는 **빈 문자열**로 만든다. `bash -c '…'` 의
작은따옴표도 그것을 막지 못한다 — 인용은 셸의 규칙이지 systemd 의 규칙이 아니다.
실측: 이스케이프를 빠뜨리자 URL 이 `https://api.telegram.org/bot/sendMessage` 가 되어
텔레그램이 **HTTP 404** 를 냈다. systemd 에서 리터럴 `$` 는 `$$` 다.

★**`systemctl show -p ExecStart` 로 반증했다고 믿지 마라** — 그 출력은 systemd 의 **파싱 결과**
(확장 _전_ 문자열)이고, 확장은 실행 시점에 일어난다. 2026-08-15 에 그 출력에 `${TELEGRAM_*}` 가
리터럴로 남아 있는 것을 보고 「확장되지 않는다」고 판정했는데 **틀렸다.** 판정은 **실제 발화**로만
내려라(강제 발화 → HTTP 코드 확인).

**⑵ `curl` 에 `--fail` 이 없으면 유닛 상태가 거짓말을 한다.** `--fail` 없이는 HTTP 404 에도
curl 이 rc=0 이라 `Type=oneshot` 유닛이 `Finished` 로 남는다. 즉 **「알람이 돌았다」와
「알람이 도착했다」가 구분되지 않는다.** `--fail` 을 붙이면 4xx/5xx 가 exit 22 가 되어
유닛이 `failed` 로 남고, **유닛 상태가 도착의 증인**이 된다.
★단 `--show-error` 는 함께 쓰지 마라 — 실패 메시지에 URL(경로에 토큰이 있다)이 실릴 수 있다.

**⑶ 주기는 `OnCalendar` 로 못박는다 — `OnUnitActiveSec` 은 사람이 손으로 돌리면 위상이 밀린다.**
`OnUnitActiveSec=30min` 은 **마지막 활성화 기준**이라, 강제 발화 실증이나 장애 재현으로 유닛을
한 번 돌리면 그 시각부터 30분이 다시 세어진다. 셈: 강제 발화가 마지막 표본 뒤 `d` 분 시점이면
다음 표본까지 **`d+30`분**이고 `d ≤ 29` 이므로 **최악 59분** — C4 한계 60분에 **1분** 남는데,
systemd 기본 `AccuracySec` 이 **1분**이라 그 여유는 사실상 0 이다.
실측(2026-08-15 [BL-737] 회차): AC-2 강제 발화 뒤 표본 간격이 **53분**까지 벌어졌다.
⇒ `OnCalendar=*:00/30` + `AccuracySec=30s`. **실증**: 강제 발화 전후 모두 `NEXT=03:30:00` 으로
불변이었다(종전 설정이면 03:32 로 밀렸을 자리다). `Persistent=true` 는 유지 — 재부팅·정지 구간에서
놓친 발화를 따라잡는다.

#### 소크 DB 스키마 — `soak-stack.sh migrate` (2026-08-15 [BL-743] 신설)

**`pin`·`up`·`down` 중 어느 것도 migration 을 적용하지 않는다.** 소크 compose 6서비스에
**api 롤이 없어서**(`run_alembic_with_lock` 을 부르는 유일한 롤) celery 는 `command:` override 로
entrypoint 의 롤 분기를 통째로 우회한다(`apps/api/docker-entrypoint.sh:117` passthrough).
그래서 서버 DB 는 만들어진 시점에 멈춰 있었고, migration 이 squash base 하나뿐이던 동안은
아무도 몰랐다.

```bash
tools/scripts/soak-stack.sh migrate             # dry-run — 대상 DB · 현재 revision · 적용 대기 목록
tools/scripts/soak-stack.sh migrate --confirm   # 집행 (★사용자 승인이 선행 — status.md ⓵ 비목표)
```

- **`pin` 과 같은 등급의 명시적 배포 행위**다. `up` 에 붙이지 않은 이유 = 창 중 DDL 이
  **암묵적으로** 돌면 「무엇이 언제 스키마를 바꿨나」에 답할 수 없다.
- 집행 뒤 **`docker exec ${DB_CONTAINER} psql` 로 게이트가 보는 그 DB 를 다시 읽어** head 와
  대조한다. `.env.local` 이 다른 DB 를 가리키고 있었다면 upgrade 는 성공하고 여기서 실패한다 —
  조용한 오적용을 막는 유일한 축이다.
- ★`alembic history -r A:B` 는 **A 를 포함**한다(이미 적용된 전이가 목록에 낀다). 초판이 그래서
  「적용 대기 2 항목」을 찍었는데 실제 대기는 1개였다.

## 2. 통과 가능한 게이트가 **아닌** 것

- **`ruff format`** — 이 레포는 포매터를 게이트로 쓰지 않는다.
- **`prettier` / `format:check`** — main 에 선재 red 356 건. 고치라는 신호가 아니다.
- **Pyright / IDE 인라인 진단** — IDE 가 uv 가상환경을 못 잡아 `pandas`·`pydantic`·`celery` 를 "unresolved" 로 표시한다. 권위는 `mypy src/` 다.

## 3. 함정

### 조용히 통과한 것처럼 보이는 것

- **`pnpm test --run` 을 쓰지 마라.** `"test": "vitest run"` 이라 `--run` 이 중복 전달되고 `Unknown option` 으로 죽으면서 **exit code 0** 을 낸다. `pnpm test` 가 정답이다.
  (CI 는 `pnpm test -- --run` 을 쓴다 — `--` 구분자가 있어 동작한다.)
- **`| tail` 로 파이프하지 마라.** 파이프라인 exit code 가 `tail` 것으로 바뀌어 실패가 사라진다.
- **백그라운드 pytest 를 `| tail` 로 감싸면** 끝날 때까지 출력 파일이 비어 있다. 진행 중인지 죽은 건지는 `pgrep -f pytest` 로 본다.
- ★★**소크 병행 e2e 는 라이브 상태와 결합한다** — e2e authed 는 소크가 도는 개발 DB 를 그대로
  검사하므로, 소크 세션이 **포지션을 들고 있으면** `/trading` 에 포지션 표가 추가 렌더되고
  `page.locator("table").first()` 류의 **전역·순서 의존 로케이터가 엉뚱한 표를 집는다**(BL-597,
  2026-08-06 final-gates 1차 red 실측 — 서명은 hydration flake 와 달리 `toContain` 단언 실패였고,
  같은 조건에서 이름 기반 로케이터(`getByRole("table", { name: … })`)는 통과했다).
  표는 **접근성 이름으로** 집어라. 서명이 다른 red 를 기존 flake 로 접지 마라.
- ★★**e2e 가 남의 앱을 검사할 수 있다.** `apps/web/playwright.config.ts` 의 `baseURL` 기본값은 **3000** 인데 격리 스택 FE 는 **3100** 이다. 3000 을 다른 웹앱이 점유하면 캐논이 그 앱을 감사한다. 실측 정체성 프로브:
  ```
  http://localhost:3000  ->  <title>Nexus - AI 챗봇 포털</title>
  http://localhost:3100  ->  <title>QuantBridge</title>
  ```
  `PLAYWRIGHT_BASE_URL=http://localhost:3100` 으로 재실행하면 27/32 가 **32** 가 된다. **실패 5건보다 무서운 건 통과 27건**이다 — 남의 앱 상대 통과라 전부 거짓 그린이었다. **게이트 전에 FE 정체성부터 프로브해라.**

### 환경

- ★★**`pnpm install` 이 `ERR_PNPM_LOCKFILE_BREAKING_CHANGE` 로 죽으면 코드가 아니라 셸이 문제다**
  (2026-08-16 [ADR-036]). 도구 버전 SSOT 가 루트 `mise.toml` 로 옮기면서 `apps/web/package.json` 의
  `packageManager` 를 지웠다 — 그래서 **mise 가 안 걸린 셸**은 corepack 기본값 pnpm **8.15.9** 로
  떨어지고, 그것이 `apps/web/pnpm-lock.yaml`(lockfileVersion **9.0**)을 못 읽는다.
  실측: mise 없이 `pnpm -v` = 8.15.9 → `--frozen-lockfile` **rc=1** / mise shim PATH 에서 9.12.0 → **rc=0**.
  ⇒ 고치는 법은 `brew install mise && mise install` 그리고 `eval "$(mise activate zsh)"` 다.
  ★**`--force` 로 락파일을 다시 쓰지 마라** — CI 의 `frozen-lockfile` 게이트와 정면 충돌한다.
  락파일은 멀쩡하고 틀린 것은 그것을 읽는 pnpm 버전이다.
  ★~~`make` 타깃과 git 훅은 안전하다(`Makefile:15`, `.husky/pre-commit`, `.husky/pre-push`).
  노출되는 것은 **터미널에서 맨손으로 `pnpm`·`uv` 를 칠 때**뿐이다.~~ → **2026-08-17 [BL-785] 이
  절반을 반증했다.** 훅 2종은 그대로 안전하고 `Makefile` 은 [ADR-036] 이 없앴지만, **게이트
  스크립트가 노출돼 있었다** — `final-gates.sh` 가 `uv`·`pnpm`·`node` 를 PATH 로 부르고 있었고,
  그래서 pnpm 8 셸에서는 **lockfile diff 가 0 인 브랜치도 `CI frozen-lockfile` 이 red** 였다.
  증상이 「내 PR 이 lockfile 을 깼다」로 오인된다. ⇒ 로컬 스크립트 5종이 이제
  `tools/scripts/lib/mise-shim-path.sh` 를 소싱해 shim 을 PATH 앞에 세우고,
  `tools/scripts/tool-pin-audit.sh` 가 재유입을 막는다(`final-gates` 의 「도구 핀 감사」).
  ★**서버에서 도는 `soak-*.sh` 6종은 면제다** — 그 환경에 mise 가 있는지 확인된 바 없다.
  ★**워크스페이스가 아니다** — 루트 `package.json` 은 husky 전용이고 `pnpm-workspace.yaml` 이 없다.
  FE 설치는 반드시 `cd apps/web` 에서 한다.
- ★★**BE pytest 는 격리 포트(5433/6380)를 쓴다 — `mise run up` 으로 올린 기본 스택(5432/6379)에서는 안 돈다.**
  `apps/api/.env.local` 의 `DATABASE_URL`·`TEST_DATABASE_URL`·`REDIS_URL` 이 전부 격리 포트를 가리킨다.
  기본 스택에서 돌리면 **`6 failed / 604 errors`** 가 나는데 실패의 정체는 `asyncio/base_events.py` 의
  `OSError`(연결 실패)이고, `test_migrations.py` 가 `sqlalchemy.exc.OperationalError` 로 먼저 눈에 띄어
  **코드 회귀처럼 보인다**(2026-08-08 실측, 13분을 버렸다). ⇒ **게이트가 red 면 코드를 의심하기 전에
  「내가 그 게이트를 올바른 환경에서 돌렸나」를 먼저 물어라.**
  ★워커를 띄우고 싶지 않으면 `DC="docker compose --project-directory . -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.isolated.yml"; $DC up -d db redis`
  로 **두 서비스만** 올려라 (★`--project-directory .` 를 빼면 프로젝트명·볼륨이 `infra/compose` 기준으로
  파생돼 기존 볼륨이 고아가 된다 — ADR-029). 기본/격리는 `container_name` 이 같아 **동시 운영이
  불가능하다** — 갈아탈 때는 먼저 `$DC stop db redis && $DC rm -f db redis` 로 비워라.
- **BE pytest 는 `.env.local` 을 통째로 source 해야 한다.**
  ```bash
  set -a; source .env.local; set +a
  ```
  개별 export 금지. `DATABASE_URL` 만 있으면 `tests/test_migrations.py` 의 `downgrade(base)` 가 **개발 DB 를 향했다** — 실제로 주문 17행과 암호화된 API 키가 전소한 적이 있다.
  ★**2026-08-10 [BL-451] 이후 그 폴백은 사라졌다.** 판정 SSOT 는 `apps/api/tests/_db_guard.py` 이고 루트 `tests/conftest.py::pytest_configure` 가 **세션 최상단**에서 판정한다. `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 있으면 폴백이 아니라 **rc=3 으로 세션이 끝난다**. 그래도 3-env 를 함께 넣어라 — 가드는 「막는다」이지 「돌게 한다」가 아니다.
  ★**종전 문장 「`_assert_disposable_database` 가 막는다」는 절반만 참이었다.** 그 가드는 `tests/test_migrations.py` 파일 안에만 있었고, 같은 판정의 사본이 `tests/real_broker/conftest.py` 에 있었지만 그 파일은 **그 디렉터리를 수집할 때만** 로드됐다. 실측 — `DATABASE_URL`(개발 DB) 하나만 있는 셸에서 `pytest tests/trading/` 이 **rc=0 으로 1088건을 수집**했고, 그 경로의 세션 픽스처는 `SQLModel.metadata.drop_all` 을 돈다.
- **수동 `alembic downgrade` 는 개발 DB 를 향했다.** ★2026-08-10 이후 `apps/api/alembic/env.py` 가 **downgrade 만** 골라 막는다(`upgrade` 는 통과 — 안 그러면 `mise run migrate`·entrypoint·CI 가 함께 죽는다). 정당한 롤백은 `alembic -x allow_destructive=1 downgrade <rev>`.
  ★**이 가드가 못 보는 표면이 하나 있다** — `command.downgrade(cfg, ...)` 처럼 파이썬에서 직접 부르면 `config.cmd_opts` 가 `None` 이라 방향을 알 수 없다. 그 표면은 pytest 쪽 가드가 덮는다.
- ★**파괴적 작업 전에 찍어라 — `mise run db-snapshot`.** `.backups/<db>-<ts>.dump` 로 나온다(gitignore). 복원은 `mise run db-restore FILE=… TO=<대상 DB>` 이고 **`TO` 에 기본값이 없다** — 기본값을 개발 DB 로 두는 편의가 곧 이 항목이 막으려는 사고다. 2026-08-10 실측: 덤프 2.15MB → 임시 DB 복원에서 orders 823 · 암호화 API 키 2/2 가 왕복했다.
- ★★**`alembic check` 는 「migration 으로만 만든 DB」에 대고 재는 것이 정본이다** (2026-08-17 [BL-782]).
  이 레포에는 스키마를 만드는 경로가 둘이다 — `alembic upgrade head` 와 `SQLModel.metadata.create_all`
  (pytest 픽스처). **둘의 결과가 갈릴 수 있고 실제로 갈렸다.** 그래서 「어느 DB 에 대고 재는가」를
  정하지 않으면 같은 명령이 환경마다 다른 답을 낸다 — [BL-770] 이 「`alembic check` rc=0 이 처음」
  이라 닫은 측정이 그 예다. 그것은 **개발 DB** 에 대한 것이었고, 개발 DB 는 `create_all` 이력이
  섞여 있어 `trading.funding_rates.exchange` 가 이미 enum 이었다(2026-08-17 실측: 개발 DB 는
  head `20260816_0001` 인데 그 컬럼이 `exchangename`, migration 계보로만 만들면 `varchar(32)`).
  **판정 기준을 migration-only 로 두는 이유는 하나다 — migration 이 프로덕션 스키마를 만드는
  유일한 경로**이므로, 그 DB 에서의 drift 만이 배포에서 실제로 터진다.
  ⇒ 정본 판정은 게이트의 **`CI fresh DB alembic`** 축이다(throwaway `quantbridge_ci_repro_test` 에
  `alembic upgrade head` → `alembic check`). 손으로 재려면 같은 절차를 밟아라 —
  **개발 DB 나 pytest DB 에 대고 잰 rc 는 이 질문의 답이 아니다.**
  ★파이프를 붙이지 마라. `alembic check` 는 실패 시 **rc=255** 다(1 이 아니다).
  ```bash
  DB=quantbridge_alembic_check_test
  docker exec quantbridge-db psql -U quantbridge -d postgres -qc "DROP DATABASE IF EXISTS $DB;"
  docker exec quantbridge-db psql -U quantbridge -d postgres -qc "CREATE DATABASE $DB;"
  cd apps/api; set -a; . ./.env.local; set +a
  export DATABASE_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/$DB" TIMESCALE_URL="$DATABASE_URL"
  uv run alembic upgrade head > /tmp/up.log 2>&1; echo "upgrade rc=$?"
  uv run alembic check   > /tmp/ck.log 2>&1; echo "check   rc=$?"
  ```
- **`test_migrations.py` 가 `DuplicateColumn` 으로 실패하면 대개 코드 결함이 아니다.** conftest 의 `SQLModel.metadata.create_all` 이 신규 컬럼을 이미 만들어둔 상태에서 `alembic_version` 만 stale 인 경우다. `downgrade base → upgrade head` 로 재구축하면 풀린다.
- compose 는 항상 두 파일을 겹쳐 쓴다. worker 만 재시작할 때는 **`--no-deps`** 를 붙여라.
  ```bash
  docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.isolated.yml ... --no-deps
  ```
- Docker VM 디스크가 차면 Postgres 가 무한 크래시 루프에 빠진다. **`docker builder prune -f` 만 안전**하다 (볼륨·이미지 prune 금지).
- ★**워커는 `apps/api/src` 를 `/app/src` 로 bind-mount + watchfiles 로 문다.** 작업 중인 코드가 실거래 세션에 **즉시** 반영된다. 관측에는 유용하지만(수정 전후를 실데이터로 잡을 수 있다) **변이 스크립트를 돌리기 전에는 워커를 멈춰라** — 문법을 깨는 변이면 평가가 예외로 죽고 세션이 자동 비활성화된다.
  ★★**변이 스크립트만의 문제가 아니다. 평범한 여러-단계 편집도 같은 함정이다.** 호출부를 먼저 넣고 헬퍼를 나중에 정의하는 순간, 그 **사이**에 watchfiles 가 중간 상태를 물어 `NameError` 로 평가가 죽고 세션이 fail-closed 비활성화된다. 2026-07-27 실측 — 활성 라이브 세션이 `live_signal_run_live_crash / NameError: name '_pending_fills_blocked_by_session' is not defined` 로 종료됐다(포지션·미체결은 0이라 피해는 없었다). **라이브 경로 모듈(`event_loop.py` / `strategy_state.py` / `tasks/live_signal.py`)을 편집할 때는 활성 세션이 없는지 먼저 확인하거나 beat 를 멈춰라.** 편집이 원자적일 거라고 가정하지 마라.
- ★**`codex exec -s workspace-write` 의 쓰기 루트 = 호출 시점 cwd.** 다른 디렉터리에서 부르면 대상 밖 파일 패치가 권한 거부되고 **0건 변경**으로 조용히 끝난다. 호출 전에 `pwd` 로 리포 루트를 확인해라. 그리고 `codex exec` 는 10분을 넘길 수 있어 Bash 상한(600000ms)에 걸리는데, **그때도 파일은 이미 쓰여 있을 수 있다** — 죽었다고 재실행하기 전에 `git status` 부터 봐라.
- ★**codex 샌드박스는 격리 Postgres(5433)에 못 붙는다.** 실DB 테스트가 `PermissionError` 로 `errors` 에 잡힌다. **메인 세션이 다시 돌려야 진짜 결과가 나온다**(실측: codex "7 errors" → 메인에서 282 passed). 그리고 **codex 자기보고를 재검증해라** — "gates-and-traps 에 승격했다" 고 보고했지만 파일이 미변경인 사례가 있었다.
- ★★★**`mise run up` / `mise run up-isolated` 는 세션을 만들지 않지만 `is_active` 로 남아 있던 세션을 되살린다.** 그리고 그 부활한 세션은 소크와 **같은 Bybit demo 계정**에 붙는다. 2026-08-07 실측 — 로컬 세션 `fcf1dcbe`(08:52 생성)가 13:52 의 `mise run up` 으로 부활해 16:44 까지 발주했고, 서버 소크 세션 `39484a2c` 를 `position_divergence` 로 죽였다. ★★**그런데 `is_active` 를 끄는 것만으로는 부족하다** — 이미 **체결된 포지션**은 그대로 남는다. 2026-08-08 재부검 실측: 로컬은 `mise run up` **전인** 07:42·07:50·08:10·08:51·09:03 에 이미 체결했고, 로컬 워커가 멈춰 있던 09:23~13:53 구간에도 서버가 09:35·09:36·09:37 에 `category=exchange_only engine_position=0.0 exchange_position=0.029` 를 관측했다 — 그 0.029 는 로컬 `541c6ee1`(09:03:53 buy 0.029)의 포지션이다. **호스트를 세워도 포지션은 계정에 남아 계속 발산을 만든다.** ⇒ **로컬 스택을 켜야 하면 ⑴ 켜기 전에 `live_signal_sessions` 의 `is_active` 를 끄고 ⑵ 거래소가 실제로 flat 인지(`FLAT=YES` **AND** resting 조건부 0) 확인해라.** 판정 도구 = `apps/api/scripts/live_session_admin.py status` 의 `FLAT=` · `RESTING_CONDITIONAL=` · `EXCLUSIVE=` 세 줄. ⇒ 원장만 읽으면 되는 경우엔 스택 전체 대신 `docker compose up -d db` 로 **db 서비스 하나만** 올려라 — 워커가 없으므로 세션 부활도 발주도 구조적으로 불가능하다.
- ★**워커 로그 follow 는 `tools/scripts/soak-logs-follow.sh` 가 정본이다** — `--install` 은 systemd user unit(+`loginctl enable-linger`) / macOS launchd 로 승격하고, `--status` 가 유닛 생존과 로그 나이를 답한다. ★**`nohup` 판(`.soak/logs/follow.sh`)은 ssh 세션·재부팅을 못 넘는다** — 같은 `LOG_FILE` 에 둘이 붙으면 줄이 섞이므로 `--install` 전에 `pgrep -f 'soak/logs/follow.sh'` 로 옛 프로세스를 먼저 죽여라.
- ★**서버 게이트는 언제나 `ssh <서버> 'bash -lc "…"'` 로 불러라.** 비로그인 셸엔 PATH 에 `uv` 가 없어 phantom 분류기가 실패하고 그 구간이 커버리지에서 잘려나간다(2026-08-07 실측 8분 손실).
- ★**서버 `psql` 은 SQL 을 파일로 넣어라** — `scp` → `docker cp` → `psql -f`. 따옴표가 ssh · `bash -lc` · `docker exec` 로 3중 중첩되면 ssh 를 넘어가면서 깨진다(2026-08-08 재현).
- ★**`.metrics` 는 프로세스 역할 + 컨테이너 id 로 파일이 갈린다.** 파일명은 `counter_<role>-<HOSTNAME>-<pid>.db` 이고 `<role>` 은 `worker`/`api`/`beat`/`wsstream`/`optheavy`, `<HOSTNAME>` 은 컨테이너 id 다(`apps/api/src/common/metrics_multiproc.py:105-107` 이 접두사를 만든다). 디렉터리는 마운트라 **죽은 컨테이너의 파일이 그대로 남는다.** ⇒ **전 PID 합산은 「지금 창」의 값이 아니다** — 2026-08-08 실측에서 `engine_only_suppressed` 합산 89 중 **15** 가 이전 컨테이너 것이었다. 창 값을 원하면 현재 컨테이너 id 로 먼저 걸러라.

### 라이브 신호 도메인

- ★**라이브 `live_signal_states.total_realized_pnl` 은 세션 원장이 아니다.** `run_live` 가 **창 안 청산만** 합산해 매 tick 덮어쓰므로 **단조가 아니다**(실측: 3건 `5.16879987` → 2건 `4.07002377`). 세션 손익의 SSOT 는 append-only 인 **`live_signal_events`** 다.
- ★**라이브 OHLCV 프레임은 `RangeIndex` + `timestamp` 컬럼**이다(`_ohlcv_rows_to_dataframe`). 인덱스에 의존하는 엔진 게이트(`sessions_allowed` 계열)는 **예외도 경고도 없이 no-op** 이 된다. 백테스트는 `v2_adapter` 가 422 로 막지만 라이브엔 등가물이 없었다.
- ★**시뮬 PnL 과 거래소 PnL 은 부호까지 다를 수 있다.** 같은 청산이 pine_v2 gross `+1.09877350` vs 거래소 net `-1.09767393` 이었다(수수료 왕복 약 2.057, 손검산 일치, raw HMAC 오라클로 외부 확인). **같은 누적기에 넣지 마라.**
- ★**`leverage` 를 엔진에 넘기면 마진 게이트만 켜지는 게 아니다.** `is_leverage_active` 가 `check_liquidations` 도 함께 켜고, 그건 실제 reduce-only 주문을 내는 **머니-패스 동작**이다. 청산 모델은 isolated 전용이라 cross 계정에는 이르게 발동한다(BL-490).

- ★**조건부(트리거) 주문은 `submitted` 로 몇 시간씩 산다.** `orphan_scanner` 의 30분 stuck 판정과 watchdog 이 그것을 "terminal 증거 미수신" 으로 오판해 **30분마다 CRITICAL 알림이 영구 반복**된다. `list_stuck_submitted` 계열은 `trigger_price IS NULL` 로 면제해야 한다. 면제의 의미는 "미발동을 stuck 으로 보지 않는다" 이지 "추적하지 않는다" 가 아니다.
- ★**`OrderService.execute` 는 같은 `idempotency_key` 를 다시 보면 거래소로 dispatch 하지 않고 캐시 응답을 돌려준다**(`order_service.py:417-419`). 취소 후 같은 의도로 재등재할 때 키가 같으면 **거래소엔 아무것도 안 올라가는데 DB 와 metric 은 "등재됨" 이라고 보고**한다. 라이브 키가 `bar_time` 을 싣는 이유가 이것이다 — 재등재 가능한 키에는 bar 를 넣어라.
- ★**`Order.idempotency_key` 는 `VARCHAR(200)`.** 초과하면 `StringDataRightTruncation` 이 상위 `except` 에 삼켜져 "장전됐다고 믿는데 거래소엔 없는" 상태가 된다. 키에 값을 싣기 전에 길이를 검사해라. 그리고 **`datetime.isoformat()` 은 `:` 를 포함**하므로 `:` 로 split 하는 키 형식에 넣지 마라(epoch 초를 써라).
- ★**`except` 블록도 실패 경로다.** `session.rollback()` 이 ORM 객체를 expire 시킨 뒤 `logger.exception(extra={"id": str(obj.id)})` 를 하면 lazy refresh 가 동기 컨텍스트에서 IO 를 시도해 `MissingGreenlet` 으로 **에러 핸들러 자신이 크래시한다**. 루프 안 예외 처리가 필요하면 ORM 속성을 `try` **밖에서 미리 확보**해라.
- ★**bybit ccxt 는 `precisionMode = TICK_SIZE`** 라 `market["precision"]["amount"]` 는 소수 자릿수가 아니라 **스텝 크기**다(BTCUSDT 0.001). 단 `limits.amount.min` 과 항상 같지는 않다.
- ★**이미 돌파된 트리거는 거래소가 거부한다** — `retCode 110093`. 롱 stop 은 트리거가 > 현재가, 숏 stop 은 < 현재가여야 한다. pine_v2 는 `low <= stop` 을 즉시 체결로 보므로 이 지점에서 시뮬과 거래소가 갈린다.
- ★**codex 프롬프트의 "변경 파일 정확히 N개" 는 신규 작업 파일에만 걸어라.** 그 변경이 깨뜨리는 기존 테스트를 파일 수에 안 넣으면 codex 가 **질문하고 멈춘다**(실측: G7 첫 실행 0건 변경). "부수 정합성 수정은 승인된 것으로 간주" 를 함께 적어라.
- ★**변이가 실제로 의미를 바꾸는지 먼저 확인해라.** `x=None or (...)` 는 Python 에서 `(...)` 라 no-op 이고, 그걸 모르면 "테스트 구멍" 으로 오판한다.

### 거래소 실상 (2026-07-28 live-entry-parity, 실거래소 실측)

- ★★**ccxt 에서 `BTC/USDT` 는 perp 이 아니라 스팟이다.** linear perp 는 `BTC/USDT:USDT` 이고 변환기가 이미 있다(`providers.py` `_to_bybit_linear_symbol`). 실측:
  ```
  ccxt.market("BTC/USDT")      -> type=spot
  ccxt.market("BTC/USDT:USDT") -> type=swap, linear=True
  spot last=63561.2  perp last=63526.7  차이 34.50 USDT (0.0543%)
  ```
  **`fetch_ticker` 를 원문 심볼로 부르면 다른 자산의 가격을 읽는다.** 트리거 판정처럼 bp 단위가 중요한 곳에서는 신호보다 오차가 커진다(실측: 오차 0.054% vs 잡으려던 돌파폭 중앙값 0.025%).
- ★**ccxt ticker 에 `"mark"` 키는 없다.** mark price 는 `ticker["info"]["markPrice"]` 다. `ticker.get("mark")` 는 항상 `None` 이라 `fetch_mark_price` 는 도입 이래 늘 `last` 로 폴백해 왔다.
- ★**돌파 거절코드는 방향별로 다르다** — `110092` = "expect Rising"(**롱** stop), `110093` = "expect Falling"(**숏** stop). 한쪽만 allowlist 에 넣으면 절반을 놓친다.
- ★**`110017` 은 "포지션 0" 이 아니라 "reduce-only 규칙 위반"** 이다(ccxt 에러맵). "포지션 없음" 은 `110034` 다. 우리 원장의 옛 메시지만 보고 매핑하면 **포지션 반전 부작용이 "무해" 로 위장**된다(실측으로 재현됨 — `"reduce-only order has same side with current position"`).
- ★**Bybit demo 는 시장가 주문도 `create_order` 응답에서 `submitted` 로 준다.** 체결 확정은 WS 가 나중에 한다(`websocket/state_handler.py` · `reconciliation.py`). 따라서 "거래소가 수락했다" 를 `filled` 로만 세면 **그 카운터는 영구히 0** 이다.

### 검증이 무언가를 증명하지 못하는 세 가지 방식 (2026-07-28 live-outcome-parity, 한 스프린트에서 3회)

- ★★★**필터는 그 필터가 배제하는 것이 픽스처에 있어야만 증명된다.** 한 스프린트에서 **세 번** 같은 유형으로 탈출했다:
  1. 파생값 직접 단언이 없어 **항등식이 어떤 값이든 통과** (`execution_gap` 이 피연산자에서 파생되므로 자기 자신을 증명한다)
  2. 픽스처에 `entry` 이벤트가 없어 **`action == 'close'` 필터가 no-op**
  3. 픽스처에 미동기 주문이 없어 **`realized_pnl_synced_at IS NOT NULL` 필터가 no-op**
     → 그 필터는 화면이 동어반복이 되는 것을 막는 유일한 방어선이었다.
     **생성자가 쓰는 픽스처는 자연히 happy path 만 담는다. 무언가를 _제외하는_ 규칙은 구조적으로 검증되지 않는다.**
- ★★**항등식은 정합성 검사가 아니다.** `a + (b-a) + (c-b) == c` 는 산술적으로 항상 참이다. 그런 형태를 게이트로 쓰면
  조인이 틀려도 통과한다. 검사는 **"어떤 관측이 그 계산에 들어갔는가"**(coverage)로 해야 한다.
- ★★**커버리지를 하나로 뭉치지 마라.** `matched / (matched + 미매칭)` 은 **분해가 하나도 안 돼도 100%** 가 된다
  (undecomposed 가 matched 의 부분집합이므로). 실측: 매칭 21 · 분해가능 0 → 커버리지 100%. 청산 원장이
  `now - 7일` 부터만 적재되므로 **7일 지난 세션은 전부 그 상태**가 된다. 매칭/분해 두 축으로 쪼개라.
- ★★**"처분했다" 고 문서에 적은 것이 처분되지 않을 수 있다.** 리뷰 지적 D5(네이티브 브래킷 청산 누락)를
  "`actual_only` 가 net 금액도 갖게 한다" 로 처분했다고 적었으나, `actual_only = A \\ M` 이고 `A` 는 확정 **주문**
  집합이라 주문이 없는 청산은 애초에 A 에 없었다. **처분 문장이 아니라 코드로 재확인해라.**

### 수정이 새 표면을 만든다 (2026-07-28)

- ★★★**리뷰 지적을 고친 diff 를 다시 리뷰해라.** live-outcome-parity 에서 G6 P1 수리가 **새 P1 을 세 개** 만들었고
  재리뷰가 두 번째 HOLD 를 냈다. 1차 리뷰가 잡은 것은 1차 수정에서 재발하지 않았다 — **새로 만든 표면에서 났다.**
- ★★★**레포가 이미 배운 버그를 되살리지 마라.** ledger dedup 에 `max(closed_pnl)` 을 썼는데,
  `providers.py` 의 `aggregate_closed_pnl_by_order` docstring 이 **정확히 그 실패 모드**를 이미 적어두고 있었다
  ("마지막 행만 취하면 부분 손익이 영구 고정된다"). 집계 규칙을 새로 쓰기 전에 **같은 데이터에 대한 기존 헬퍼를 먼저 찾아라.**
  ★건수는 맞고 금액만 틀리므로 커버리지 같은 파생은 **정상처럼 보인다.**
- ★★★**동결 스펙을 넓혔으면 그 문서를 갱신해라 — 아니면 삭제할 때 근거가 사라진다.** live-outcome-parity 는
  G1 에서 "변경하려면 사유를 이 문서에 남긴다" 고 스스로 규정해놓고 스코프를 **두 번** 넓히고도(도달 경로 신설 ·
  fail-closed 조건 3->5) 문서를 갱신하지 않은 채 G8 에서 삭제했다. 2축 리뷰가 그 이탈을 전부 잡아냈고,
  "왜 넓혔는가" 를 dev-log 에서 역추적해야 했다.
- ★★★**수용 기준 문서는 자기 집행되지 않는다.** 한 스프린트에서 **두 번** — G1 에 "이렇게 한다" 고 적은 항목이
  구현에 반영되지 않은 채 게이트를 통과했다(브래킷 청산 `actual_only` 편입 · `inferred` 귀속 격리).
  둘 다 **최종 리뷰가 잡았다.** 수용 기준을 쓴 것과 그것이 코드에 있는 것은 다른 사건이다 —
  **G3 코드 대조에서 수용 기준을 한 줄씩 짚어 확인해라.**
- ★★**코드가 스스로 봉인한 값을 우회하지 마라.** `exit_attribution.attribute_exit` 은 주석으로
  "`inferred` 는 검정력이 없다. **리스크 게이트 입력으로 절대 쓰지 않는다**" 를 명시하는데,
  신규 집계가 `attributed_strategy_id` 를 `attribution_confidence` 확인 없이 써서 그 봉인을 뚫었다.
  **`*_confidence` / `*_source` 류 판별자가 있는 컬럼은 값만 읽지 말고 판별자를 함께 읽어라.**
- ★★**"처분했다" 는 문장은 처분의 증거가 아니다.** 리뷰 지적을 처분 표에 "인정 -> 처분" 으로 적었는데
  실제 코드는 그 결함을 그대로 갖고 있던 사례가 났다(`actual_only = A \\ M` 인데 `A` 가 주문 집합이라
  주문 없는 청산은 애초에 A 에 없었다). **처분 문장이 아니라 코드로 재확인해라.**

### 통계 게이트 (2026-07-28)

- ★★**표본 자신에서 유도한 임계는 표본이 작을 때 오히려 열린다.** `required_n = (k x sd / |mean|)^2` 는
  **평균의 정밀도**를 재는데, n 이 작으면 **sd 추정 자체가 신뢰할 수 없다.** 실측: n=3, sd=0.159, mean=-0.921
  → `required_n = 1` → 게이트 통과. 하한을 **데이터가 아니라 추정량의 요구조건**(CLT)에서 가져와라.
- ★**짝지어진 값을 독립 표본으로 다루지 마라.** gross 와 수수료는 같은 주문에서 나온다. 두 평균의 간격을
  독립 표본처럼 재면 틀린다. 올바른 통계량은 **차이 자체**(= net) 한 표본이다.
- ★**분모가 무엇인지 라벨에 적어라.** `cost / round_trip_notional` 에서 분모가 두 leg 합이면 그 값은 **편도**다.
  왕복 가정(0.30%)과 나란히 놓으면 **2배 어긋난 비교**가 된다. 실측에서 화면이 편도 0.06% 를 왕복 0.30% 와 비교했다.
- ★**`Decimal` 기본 컨텍스트는 prec=28 이다.** `Numeric(18,8)` 곱은 최대 36 유효숫자라 조용히 반올림된다.
  금융 파생 모듈은 `localcontext(Context(prec=50))` 로 감싸라. ★그리고 **테스트도 같은 컨텍스트에서 비교**해야 한다 —
  기본 컨텍스트로 항등식을 재계산하면 마지막 자리가 어긋나 거짓 red 가 난다.

### 원장을 읽을 때 (2026-07-30 close-mismatch-visibility)

- ★★★**`orders.filled_at` 은 이름과 달리 terminal_at 이다** — 체결뿐 아니라 **취소·거절 시각도**
  여기 들어간다(`models.py:293-296` 주석이 이미 그렇게 적었다). 그리고 **한 주문의 terminal 과
  다음 주문의 `created_at` 을 섞지 마라.** 실측 사고 — `0.058` 주문이 09:09:46 까지 살아 있다고
  적었는데 그건 **다음 주문의 생성 시각**이었고 실제 terminal 은 09:07:40 이었다(1m49s vs 3분).
- ★★**라이브 진입 key 는 형식이 둘이다.** 조건부 = `live:<sess>:cond:<bar_epoch>:<stop>:<qty>:<trade_id>`,
  시장가 = `live:<sess>:<bar_time ISO>:<seq>:<action>:<trade_id>`. `split_part` 로 한 형식만
  가정해 자르면 **다른 형식이 조용히 오분류**된다(실측: 21행을 `cond` 로 읽었는데
  `LIKE ':cond:%'` 카운트는 0이었다). **분해 결과를 쓰기 전에 원문을 한 번 출력해라.**
  귀속의 권위는 `conditional_entry_planner.parse_live_entry_key` **하나**다.
- ★★★**같은 에러 코드 안의 갈래가 위험도가 다르면 그 코드는 라벨이 될 수 없다.**
  `110017` 이 `same side`(★엔진↔거래소 **반대 방향**) 9건과 `current position is zero`(무해) 30건을
  한 라벨에 담고 있었다. **무해가 3배라 위험이 수적으로 묻혔고** counter 는 계속 "유령 포지션" 만
  가리켰다. 이 저장소가 `110017` 로 이 교훈을 **두 번째** 받은 것이다.
- ★★**`live_signal_events` 는 진입을 세지 않는다.** `entry`/`close` 시장가만 담고
  **조건부 진입은 거치지 않는다**. 그래서 `bool(new_events)` 로 만든 판정
  (`deferred_market_inflight`)은 stop-entry 전략에서 **사실상 「청산 tick 수」** 다.
  ★그 counter 는 `desired` 를 **읽기 전에** 오르므로 **미룰 진입이 0건이어도 발화한다.**
  **분모를 확인하지 않은 비중(예: "합의 75%")은 측정이 아니다.**

### 측정 도구가 먼저 틀린다 (2026-07-30 — 한 회차에 **6번**)

> ★평가자의 계측기가 6번 먼저 틀렸고 **6/6 전부 "코드가 틀렸다" 로 갈 뻔했다.** 유형이 반복된다.

- ★★**출력을 자르면 코드가 틀린 것처럼 보인다.** `final-gates.sh` 의 `skip_gate` 는 라벨(`▶ BE ruff`)을
  먼저 찍고 **다음 줄에** `→ 건너뜀` 을 찍는다. `head -3` 으로 자르면 "돌면 안 되는 게 돌았다" 로 읽힌다.
- ★★**표적 변이 앵커 3대 오류** — ① 앵커 문자열이 **유일하지 않음**(치환이 여러 곳에 먹어 의미가 흐려진다)
  ② **주석**을 앵커로 잡음(코드가 아니라 문서를 바꿨으니 당연히 green) ③ 정의와 사용처를 **함께** 바꾼
  **동치 rename**(이름만 바뀌고 동작은 같다). 셋 다 "탈출" 로 보고될 뻔했다.
  → **변이를 넣기 전에 `text.count(old) == 1` 을 단언하고, 그 앵커가 실제 판정 지점인지 눈으로 확인해라.**
- ★★**두 원장을 비교할 때 시각을 맞춰라.** 원장 `cancelled` 9(10:06)와 counter `replaced` 11(10:20)을
  대조해 "부등식 위반" 을 의심했으나, **같은 시점**에서는 `14 >= 14` 로 정확히 성립했다.
  누적 counter 와 DB 를 비교할 때 **관측 시각이 다르면 그 비교는 무의미하다.**
- ★★**감시 스크립트도 fail-open 이 된다.** soak 감시가 **종료된 세션을 "생존" 으로** 보고했다 —
  `psql` 이 실패하면 빈 문자열이 되어 사망 판정(`= "f"`)에 안 걸리고 하트비트로 넘어갔다.
  **조회 실패를 "이상 없음" 으로 수렴시키지 마라** — 판정 불가는 별도 상태여야 한다.
- ★★★**서로 다른 시점에 도입된 counter 는 절대값 비교가 구조적으로 불가능하다.** 같은 사건을 세는
  두 counter 가 **126 vs 99** 로 어긋났는데, 원인은 로직이 아니라 **출생일**이었다
  (`qb_live_conditional_placed_total` PR #489 / `qb_live_conditional_guard_total` PR #493, **하루 차**).
  **차분에서는 정확히 일치한다.** 절대값을 나란히 놓는 순간 그 표는 거짓말한다.

### ★★CI 와 로컬은 같은 명령이어도 **같은 env 가 아니다** (2026-08-01, 실측 5건)

- ★**추적되지 않는 파일로 링크를 걸면 로컬 게이트는 판별력이 0이다** (2026-08-15 ledger-thaw).
  `docs/reports/*.html` 은 `.gitignore:107` 로 **추적 대상이 아니다**(템플릿·`auto-dogfood/` 만 예외).
  `docs/status.md` 에서 그 파일을 마크다운 링크로 걸었더니 **로컬 `docs-audit` 은 rc=0**(파일이
  거기 있으니까)이고 **CI 의 같은 명령이 red** 였다. 로컬 초록은 「내 작업 트리에 있다」만 말한다.
  ⇒ 추적 안 되는 산출물은 **링크가 아니라 경로**(코드 스팬)로 적어라 — `dev-log/*.md` 를 코드
  스팬으로 적는 관용구와 같은 이유다. **커밋 트리로 재는 방법**: `git archive <브랜치> | tar -x -C <임시>`
  하고 거기서 게이트를 돌린다(로컬 트리의 미추적 파일이 섞이지 않는다).

- ★**`Settings` 의 인프라 기본값은 docker-compose 서비스명이다**(`redis://redis:6379/*`).
  워크플로가 그 필드를 **명시 주입하지 않으면** 러너에서 해석 불가 호스트로 붙는다.
  실측: `REDIS_URL` 만 주입돼 있고 `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`/`REDIS_LOCK_URL`
  이 없어 **backend 5건**이 `Retry limit exceeded ... Celery result store` 로 죽었다.
  **celery 는 `REDIS_URL` 을 읽지 않는다 — 별도 설정이다**(`core/config.py:64-67`).
- ★★**로컬 CI 재현은 이 계열을 구조적으로 못 잡는다** — `.env.local` 이 그 값들을 모두
  `localhost` 로 채운다. "CI 와 같은 스크립트를 돌렸다" 는 **같은 pytest 명령**일 뿐이다.
  ⇒ 감사 테스트 `apps/api/tests/test_ci_workflow_env_parity.py` 가 대신 대조한다(변이로 판별력 증명).
- ★**`env -u` 로 지워도 소용없다** — pydantic-settings 의 `env_file` 이 `.env.local` 에서 다시 채운다.
  CI 를 재현하려면 **지우지 말고 CI 실효값으로 덮어써라**.
- ★**시각 의존 테스트는 스스로 만료된다** — `since=datetime(2026, 7, 25, 1)` 하드코딩 + 7일 롤링 클램프가
  **2026-08-01 00:00 UTC 에 폭발**했다. **실패 값이 실행마다 달라지면 시각 의존을 의심해라.**
  픽스처 시각은 **상대값**(`now - N`)으로 써라.
- ★**CI 가 빨간 것과 CI 가 돌기라도 한 것은 다르다** — main 5회 연속 실패는 테스트가 아니라
  **결제/지출 한도로 잡이 시작조차 안 된 것**이었다(`The job was not started because recent account
payments have failed`). backend 가 `skipped` 면 **게이트는 아무것도 검증하지 않았다.**

### 함대·계측 함정 (2026-07-31 reversal-ledger-sync)

- ★★★**`herdr agent prompt` 는 텍스트를 붙여넣기만 하고 제출하지 않을 수 있다.** 워커 4벌 전부
  `[Pasted text #1 +9 lines]` 상태로 프롬프트에 멈춰 있었는데 **발송 API 는 성공을 반환**했고
  `agent_prompt_stalled` 조차 안 났다. ⇒ **`herdr agent send-keys <name> enter` 를 항상 뒤에 붙이고
  `agent read` 로 눈으로 확인해라.** `working` 으로 바뀌는 것까지 봐야 발송이다.
- ★★★**psql boolean 을 판정에 쓰지 마라.** 감시 스크립트가 `f|*` 패턴으로 세션 사망을 놓쳐
  **3.7시간을 헛돌았다.** ★한동안 여기 「`-At` 가 `false` 로 찍는다」로 적혀 있었지만 **그게
  변수가 아니다** — 2026-08-01 실측: 같은 세션에서 맨 컬럼 `SELECT is_active` 는 **`t/f`**,
  캐스트 `SELECT is_active::text || …` 는 **`true/false`** 를 냈다. **가르는 건 플래그가 아니라
  캐스트다.** ⇒ 표기를 확인하는 게 아니라 **nullable 텍스트 컬럼**(`deactivated_reason` 등)으로
  판정해라. `tools/scripts/soak-observe.sh` 가 그 형태다.
- ★★**`psql -c` 에 세미콜론 여러 개는 암묵적 단일 트랜잭션**이라 뒤 문장의 실패가 앞 UPDATE 를
  통째로 롤백한다(2026-08-01 실측). **`-c` 하나에 문장 하나**로 써라. archive 에만 남아 있던
  것을 2026-08-03 에 승격했다.
- ★★**호스트 `/metrics` 는 워커의 카운터 증가를 곧바로 안 비춘다.** 2026-08-03 실측 — 워커가
  `close_position_flat` 을 올리고 태스크가 성공 반환한 뒤에도 호스트 HTTP 스크레이프는
  **14 를 두 번** 냈고, 같은 시각 컨테이너 안 multiproc 집계는 **15** 였다(잠시 뒤 호스트도 15).
  스크레이프 자체는 0.55초라 렌더 비용이 아니다 — [가정] macOS Docker bind-mount 의 mmap 전파
  지연. ⇒ **이벤트 직후 몇 초 안의 카운터 읽기로 판정하지 마라. 다시 읽어라.**
  일일 관측(하루 1회)에는 영향이 없다.
- ★★**짧은 창으로는 아무것도 판정할 수 없다.** 42분 창에서 **수정 없이도** `same_side` 0 이 나왔다
  (청산 시도 3). 그리고 4창 4.48h 동안 **청산 시도가 0건**이었다 — 이 전략은 전량 조건부 진입만 낸다.
  **판정 지표가 그 창에서 발화 가능한지를 먼저 확인해라.**
- ★★**`docker exec python -c` 는 러닝 워커가 리로드됐다는 증거가 아니다** — 새 프로세스가 마운트된
  소스를 읽을 뿐이다. **로그에서 그 코드가 실제로 실행된 흔적**을 봐라(태스크 received→succeeded).
- ★★**수정이 실주행에서 실행됐는지를 따로 재라.** 이번에 새 write-back 헬퍼가 최종 창에서
  **0회 발화**했다 — 기존 경로가 먼저 잡았다. **지표가 좋아진 것과 내 코드가 돈 것은 다른 사실이다.**
- ★**`python /tmp/x.py` 는 `sys.path[0]` 이 `/tmp` 다** — 컨테이너 안에서 앱 모듈을 쓰려면
  `docker exec -e PYTHONPATH=/app -w /app`.
- ★**`pnpm e2e` 는 자기 dev 서버를 띄우려다 죽는다** — 같은 디렉터리에 `next dev` 가 이미 떠 있으면
  `Another next dev server is already running`. **정체성 프로브 후 `PLAYWRIGHT_BASE_URL=http://localhost:3100`.**
- ★**`herdr pane split --ratio` 는 쪼개지는(기존) pane 이 *남기는* 비율이다**(폭 298 + `--ratio 0.25`
  → 75/223). n 등분은 `1/(남은 열 수)` 로 접는다.
- ★**두 워커가 같은 자리를 고치면 머지 충돌이 「의미 있는 충돌」이 된다** — 이번에 한 워커의
  훅 통합 헬퍼가 다른 워커의 훅을 몰라서, 손으로 접었으면 **codex 가 방금 잡은 결함을 머지에서
  재도입**할 뻔했다. **소유자에게 돌려줘라.**

### 측정 도구가 먼저 틀린다 (2026-07-30 close-mismatch-soak — 또 **2번**)

> ★**0 이든 큰 수든, 숫자를 보면 계측기를 먼저 의심해라.** 이 레포에서 **7번째**다.

- ★★★**JOIN 이 카운트를 조용히 뻥튀긴다.** soak 감시가 `same_side=14` 로 보고했으나 실제는 **1건**이었다.
  `orders JOIN live_signal_sessions ON exchange_account_id` 이 그 계정의 **세션 14개만큼 행을 곱했다**.
  사전등록 판정(V3)을 **오판할 뻔했다**. → **집계 쿼리에 JOIN 을 넣기 전에 `count(*)` 를 JOIN 없이 한 번 재라.**
- ★★**정규화 함수 프로브는 그 함수가 받는 **실제 형태**로 넣어라.** `_normalize_exchange_order_response_reason`
  에 산문(`"bybit 110017 reduce-only ... same side"`)을 넣어 3건 전부 `unparsed` 가 나왔고 "배선이 죽었다" 로
  읽힐 뻔했다. 실제 패턴은 `"retCode"\s*:\s*(\d+)` — **호출부가 넘기는 것은 `str(e)` 의 JSON 본문**이다.
- ★★**`prometheus_client` 는 첫 `.labels()` 증가 전까지 child series 를 만들지 않는다.** 그래서
  "신규 라벨이 `/metrics` 에 **샘플과 함께** 보일 것" 같은 사전등록 문턱은 **발화 전에는 구조적으로 충족 불가**다
  (재기동해도 안 뜬다). → 문턱은 **코드 sentinel(러닝 워커 안에서 import 해 호출)** 과 **사후 발화** 로 갈라 써라.
- ★**before 스냅샷에 그 series 가 없으면 `after - 0` 은 차분이 아니라 절대값이다.** 리포트에 그 사실을 적어라.

### 게이트가 "돌렸다" 만 보증한다 (2026-07-30)

- ★★**`final-gates.sh` 는 exit code 만 기록한다 — 테스트 개수를 찍지 않는다.** 스크립트 자신이 마지막 줄에
  그렇게 경고한다. **baseline 대조는 사람이 따로 해야 한다**(이번에 문서의 `FE 1231` 이 stale 이었고
  main 을 직접 재보니 **1232** 였다). **baseline 은 언제나 대조 대상이다.**
- ~~★★**`pnpm e2e`(chromium 4건)는 게이트 체인 밖이 맞다.** 게이트가 도는 것은
  `chromium-design-canon` · `chromium-authed` 라는 **다른 프로젝트**다. 게이트 로그에 `e2e ... PASS` 가
  보인다고 BL-556 의 수동 1회가 면제되지 않는다.~~
  → ★**2026-08-08 [BL-556] 로 체인 안에 들어왔다.** 라벨 **`e2e chromium`**, 순서는
  `chromium → design-canon → authed`. ★**이것만 영역 판정(`has_fe`)에 걸린다** — 다른 둘은
  무조건 돈다(`authed` 는 backend 변경도 문다). 세 분기(`--skip-e2e` / 프로브 OK / 프로브 실패)
  전부에서 같은 3행이 같은 순서로 나온다. **그리고 4건이 아니라 3건이다** —
  `playwright test --project=chromium --list` = `Total: 3 tests in 1 file`. 「4건」은
  BL-556 본문의 「4 passed」에서 나와 문서 5곳에 복제된 오기였다.
- ★**`pnpm test --run` 은 Unknown option.** 이 레포는 `pnpm test`(= `vitest run`).
- ★**`EXIT=$?` 를 파이프 뒤에 쓰면 마지막 명령(`tail`)의 종료코드를 읽는다.** `bl-audit.sh` 를 exit 0 으로
  오판할 뻔했다. 종료코드가 판정인 스크립트는 **파이프 없이** 돌리고 그 다음 줄에서 `$?` 를 읽어라.
- ★**`bl-audit.sh` 는 이제 `final-gates.sh` 체인 안에 있다**(라벨 `BL 감사`, BL-564). `docs/` 만 읽으므로
  영역 판정과 무관하게 **항상 돈다.** 실패 조건이 넷으로 늘었다 — UNKNOWN / 3면 불일치 / **중복 상태줄** /
  **중복 섹션 헤더**(`### BL-<n>` 두 벌, BL-569 — 파서가 id 로 키를 잡아 뒤 섹션이 앞 섹션 판정을 덮어썼다).
  즉 **BL 을 추가·해결하고 `**상태:**` 줄을 안 달면 게이트가 빨개진다.** 폐기된 옛 판정을 남기고 싶으면
  지우지 말고 `<details>` 로 접어라 — 파서가 ` ``` ` 펜스와 `<details>` 구간을 건너뛴다.
  ★`--list` 는 **판정 불일치로는 exit 0** 이다(목록 출력 전용). 게이트에는 인자 없는 형태만 쓴다.
  ★단 **ABORT(3) 는 `--list` 에서도 난다**([BL-779], 2026-08-16) — 원장 파일이 없거나 비었거나 섹션 0개면
  목록을 낼 근거 자체가 없다. 소비자(`docs-audit`·`bl-trigger-sweep`)는 이 rc 를 읽어 함께 죽는다.
- ★★**원장은 2026-08-16 부터 파일 둘이다** — `docs/backlog.md`(열린 것) + `docs/backlog-resolved.md`
  (RESOLVED 본문, [BL-779]). `bl-audit.sh`·`docs-audit.sh`·`bl-trigger-sweep.sh`·`context-budget.sh`
  넷이 **둘을 한 벌로** 읽는다. 판정 수는 **합계**이고 `bl-audit` 머리줄이 파일별 섹션 수를 함께 찍는다.
  ★**한쪽 파일을 안 읽는 파서는 조용히 초록이다** — 없는 섹션은 불일치를 못 내기 때문이다. 그래서
  ⑴ 원장 한쪽이 비었거나 `### BL-` 섹션이 0개면 rc=1 이 아니라 **rc=3 ABORT** 이고,
  ⑵ `docs-audit` 은 `bl-audit --list` 의 **rc 를 읽어** 정본이 죽으면 함께 ABORT 하며(빈 stdout 을
  공집합으로 읽지 않는다), ⑶ 하네스 `bl-audit-test.sh` ⑫~⑯ · `docs-audit-test.sh` ⒂~⒅ 가 그 축을 잰다.
  ★**옮기는 것이지 복사가 아니다** — 같은 id 를 양쪽에 두면 「중복 섹션 헤더」로 red 다.
- ★**`bl-audit.sh` 의 중복 검사는 원장이 깨끗하면 아무 일도 안 한다** — 즉 그 로직을 지워도 「BL 감사」는
  초록이다. 그래서 `tools/scripts/bl-audit-test.sh`(라벨 `BL 감사 하네스`)가 체인에 함께 있다. 임시 트리
  fixture 로 돌리므로 `docs/` 를 건드리지 않는다. 변이 3종(섹션 헤더 탐지 제거 / dup 키를 BL id 로
  되돌림 / 상태줄 탐지 제거) 전건 red 확인.
- ★**판정어는 2026-08-10 부터 다섯이다** — `ACTIVE / DEFERRED / PARTIAL / RESOLVED / UNKNOWN`
  ([ADR-028](../../decisions/028-backlog-deferred-verdict.md)). `DEFERRED`(상태줄 `⏳ **대기 (트리거
미도래)**`)는 **active 로 세지 않고**, 3면에서는 **ACTIVE 와 같은 「미완」 쪽**이다 — 인덱스 표에
  ✅/🟡 가 있거나 roadmap 이 `[x]` 면 불일치다. 하네스 케이스 ⑥⑦⑧ 이 지킨다.
  ★**어휘는 `**상태:**` 줄 맨 앞에 둬라** — `lead()` 가 첫 `—`/`.`/`:**` 에서 자르므로 뒤로 밀면 UNKNOWN 이다.
  ★**「없어야 할 마커」를 `▶ 블록 머리`로 주면 안 되는 예외가 있다** — `▶ 불일치`·`▶ UNKNOWN` 은
  「없음」일 때도 **항상 찍힌다.** 그 둘은 본문 문장으로 재라(케이스 ⑧ 이 실제로 거짓 통과했다).
- ★**트리거 도래 판정은 `tools/scripts/bl-trigger-sweep.sh`** 다. **`--selftest` 를 전량 스윕보다 먼저 돌려라** —
  양성 2 + 음성 4 를 못 가르면 전량 판정은 값이 0이다. 실제로 초판이 판별력 검사에서 두 번 잡혔다
  (①`지금` 축 누락으로 양성 2건 유실 ②`BL의존` 축이 **절의 접속을 반쪽만 읽어** 5건을 근거 없이 도래로 올림).
- ★**`git merge-tree` 는 커밋을 받는다.** 트리 해시를 넘기면 거짓 충돌처럼 보인다.
  브랜치 2개가 각각 main 에 clean 하고 **변경 파일 집합이 disjoint** 면 순차 머지도 clean 이다.

### ★★스위트 결과가 **수집 집합**에 달려 있었다 (2026-08-03 gate-trustworthiness, BL-583)

> ★★★**「전부 통과」가 증거이려면 그 통과가 수집 집합과 무관해야 한다.** 이 레포는 그렇지 않았다.

- ★★**`-p no:randomly` 는 이 레포에서 no-op 다.** `pytest-randomly` 가 **설치돼 있지 않다**(설치된 플러그인:
  asyncio · celery · cov · json-report · metadata · timeout · docker_tools). 실측으로 그 플래그 유무가 같은
  수치(3848 passed / 46 skipped)를 낸다. 「랜덤 순서라서 red 가 나타났다 사라졌다」는 서술은 **거짓**이었다 —
  실행 순서는 결정론적이고, 바뀌는 것은 **어떤 파일이 함께 수집됐는가**다.
- ★★★**클래스 정의 모듈을 monkeypatch 한 상태에서 소비 모듈이 「처음」 적재되면 그 모듈 전역에 가짜가 영구
  복사된다.** `monkeypatch` teardown 은 **정의 모듈만** 되돌린다. 실측: 오염원 테스트 **4개**가 모듈 3개의
  전역 **8개**를 오염시켰고(`src.tasks.trading` 6 · `orphan_scanner.OrderRepository` ·
  `providers.timescale.CCXTProvider`), 그중 두 경로가 무관한 테스트 **5건**(cancel 2 + orphan_scanner 3)을
  red 로 만들었다. **「소비 모듈이 최상단 import 라 patch 가 안 닿는다」는 이미 적재된 모듈에만 참이다.**
  ★**창이 넓은 실행 형태에서 더 나온다** — 디렉터리 단위 census 가 1건, **파일 단위**가 1건을 더 찾았다.
  「전체 스위트에서 가드 발화 0」은 아무것도 증명하지 않는다(`src.*` 214 모듈 중 수집 시점 미적재 **9개**).
- ★★**그래서 전체 스위트의 green 이 우연일 수 있다.** 위 오염은 알파벳상 앞선 **무관한 파일 6개**가 수집
  시점에 문제 모듈을 미리 적재해 줘서 가려져 있었다(`test_dispatch_snapshot_priority` ·
  `test_provider_dispatch` · `test_exchange_order_response_metric` · `test_beat_schedule` ·
  `test_conditional_entry_janitor` · `integration/test_auto_dogfood`). 6개를 `--ignore` 하면 **3 failed** 다.
  ★**4개만 빼면 여전히 green(3781)** 이다 — ignore 집합을 손으로 고르면 **마스킹된 green** 을 얻는다.
  **AST 모듈수준 폐포로 세라**(선례: `tests/tasks/test_live_signal_import_blast_radius.py`). 그리고 그런 실험은
  「대상 모듈이 수집 시점에 미적재」를 **프로브로 단언한 뒤에만** 결과를 채택해라.
- ★**이제 `tests/conftest.py` 가 상시로 잡는다** — 한 테스트 항목 안에서 **처음** 적재된 `src.*` 모듈 전역에
  테스트 대역(`unittest.mock` 객체 또는 `tests.*` 에서 정의된 lambda·헬퍼)이 남으면 **그 오염원 테스트가
  teardown ERROR** 가 된다. 고치는 법은 하네스가 패치를 걸기 **전에** 그 모듈을 적재하는 것 한 줄이다.
- ★가드가 **못 잡는 5종**: ① 이미 적재된 모듈의 직접 변조 ② 클로저나 객체 내부에 숨은 대역
  ③ `sys.modules` 키의 모듈 객체 교체 ④ 창 안의 `importlib.reload` / `del sys.modules[…]` 후 재import
  ⑤ 비-Mock 대역(`SimpleNamespace()`·`object()` 는 `__module__` 이 없고 `partial` 은 `functools`).
  **「가드 발화 0」을 「전역 오염 없음」으로 인용하지 마라.**

### CI pytest 샤딩 (2026-08-06 ci-diet)

- ★★★**커버리지 잡을 「별도 병렬 잡으로 옮기는」 것은 이득이 0 이다.** 그 잡이 여전히 full suite 를
  돌아 **임계경로**가 된다(1313s). BL-308/309 래칫이 full-suite transitive 커버를 요구하므로 `ci` 가
  그 잡을 기다려야 하고, 23분은 23분으로 남는다. **옮기는 게 아니라 쪼개야 한다** —
  샤드마다 부분 데이터 → `coverage combine`(합집합) → `--fail-under` 1회.
- ★★**`COVERAGE_CORE=sysmon` 은 이 레포에서 못 쓴다.** `coverage/env.py` 의
  `branch_right_left = pep669 and PYVERSION > (3,14,0,a5)` 때문에 **Python 3.12 + `branch = true`** 조합은
  `core.py` 가 sysmon 을 거부하고 ctrace 로 폴백한다. 계측 배율 실측 **1.770배**(무계측 298.97s vs 계측 529.16s).
- ★★★**커버리지 수치는 샤드 누락을 못 본다.** 샤드 a·b 의 데이터 파일은 **내용이 동일**해서
  `coverage combine` 이 `Skipping duplicate data` 를 찍는다 — 즉 **그 아티팩트가 통째로 사라져도 최종
  수치가 안 움직인다.** 그래서 `backend_coverage` 는 조각 **개수**를 `shards.json` 키 개수와 대조한다.
  ★`actions/upload-artifact@v4` 는 **dot 파일을 기본 제외**한다 — `include-hidden-files: true` 가 빠지면
  정확히 그 상황이 된다(`if-no-files-found: error` 와 이중으로 막는다).
- ★★★**`--durations` 순위로 샤드 경계를 정하면 틀린다 — 그 목록은 「누가 먼저 돌았나」의 함수다.**
  코퍼스 스크립트를 **처음** 파싱하는 테스트가 비용을 전부 물고 이후는 거의 공짜다:
  `test_ast_classifier[i3_drfx]` 는 **단독 42.66s** 인데 **전체 스위트 안에서는 4.58s** 다
  (`i1_utbot` 12.06s vs 0.02s). 알파벳상 앞선 `test_alert_hook` 이 값을 치르는 바람에 이 테스트는
  단일 실행 top-10 에 **아예 없었고**, 그 목록으로 잡은 추정이 **2.2배 빗나갔다**(샤드 a 385s→847s).
  ⇒ **쪼개면 그 비용이 샤드마다 중복된다.** CI 3샤드 합 1796s vs 단일 1278s 의 **+519s 전부**가
  이 중복이다. **이 스위트는 샤딩에 저항한다** — 3-way wall 14.8분이 한계고 재분배로 못 내려간다.
  뿌리 = [BL-598].
- ★★**「고정 오버헤드」로 오진하기 쉽다 — 내가 두 번 그랬다.** 처음엔 F≈305s 라고 모델링했는데,
  샤드 b 로그가 반증했다: **70 테스트에 615.42s 인데 top-10 만 596s** 다(오버헤드 ~20s).
  **한 샤드의 로그를 열어 테스트 시간과 총시간을 대조하기 전에는 오버헤드를 주장하지 마라.**
- ★★**샤드 경계를 로컬 durations 로 정하면 틀린다(2).** CI/로컬 비율이 **균일하지 않다** —
  `test_alert_hook[i3_drfx]` 는 2.73배인데 `test_ast_classifier[i3_drfx]` 는 **27.7배**다.
  후자가 이상한 게 아니라 **첫-접촉 비용을 누가 무느냐가 바뀐 것**이다.
- ★**`--durations=0` 은 전수가 아니다** — `--durations-min` 기본 5ms 아래는 안 찍힌다(4199 중 1016건만).
  합계로 검산해라(291.4s / 298.97s).
- ★★**샤드 3벌 합계 > 전체 1벌** — 로컬 688.9s vs 529.2s(**+30%**). 세션 startup·fixture 가 샤드마다
  반복된다. 잡이 병렬이라 벽시계는 줄지만 **러너 분은 늘어난다**.
- ★★★**등가성은 aggregate 로 주장하지 마라.** `TOTAL` 이 같아도 파일별로 다를 수 있다.
  전체 1벌의 데이터를 따로 보관해 두고 `coverage report` 출력을 **diff** 해서 완전 일치를 보여라.
- ★★**`$ARGS` 를 따옴표 없이 펼치는 검증은 반드시 `bash -c` 로 해라.** 이 세션 셸은 **zsh** 이고
  zsh 는 기본적으로 word-splitting 을 **안 한다** — 인자 전체가 한 덩어리로 들어가 `pytest` 가
  `ERROR: file or directory not found: tests/strategy --ignore=…` 로 죽는다. CI 는 bash 라 정상이다.
  **하네스가 거짓 red 를 냈다.** 그래서 `shard_paths.py` 가 공백 경로를 거부해 그 가정을 집행한다.
- ★**소크·다른 pytest 와 동시에 돌리지 마라.** `tests/conftest.py` 세션 픽스처가 `quantbridge_test` 에
  `drop_all`+`create_all` 을 하므로 **진행 중인 다른 실행의 DB 를 도중에 날린다.**

### 죽은 의존성을 걷어낼 때 (2026-08-06 dead-code-sweep)

- ★★★**「시제만 고친다」고 마음먹어도 의미가 바뀐다.** vectorbt 를 지우면서 확장 지표 주석을
  「구 vectorbt 경로에서 추출하던 값」으로 바꿨는데, 그 필드들은 **지금 pine_v2 가 계산해서 채운다**
  (`v2_adapter.py:704-712` 계산 · `:851-856` 반환). `None` 은 죽은 경로라서가 아니라 **필드 신설
  이전 행** 호환용이다. codex 가 잡았다. ⇒ **주석을 고치기 전에 그 문장이 서술하는 값이 지금 어디서
  오는지 코드로 확인해라.** 「vectorbt 를 지운다」는 목적이 「vectorbt 라는 낱말을 지운다」로
  미끄러지는 순간 사실이 바뀐다.
- ★★**틀린 것이 「동작」인지 「귀속」인지 갈라라.** 위 사례에서 `closed only 집계` 는 **여전히 참**
  이었다(`v2_adapter.py:676` 이 `status == "closed"` 로 거르고 `:707` 이 그걸 센다). 틀린 것은
  엔진 이름뿐이었다. 동작 서술까지 같이 지우면 BL-155 의 맥락을 잃는다.
- ★★**의존성 제거의 진짜 위험은 import 가 아니라 버전 재해석이다.** `uv lock` 후 **numpy/pandas/
  scipy/scikit-learn/pynescript 버전이 불변인지** 먼저 확인해라 — 움직이면 pine_v2 수치가 흔들리고
  Trust Layer 골든이 오라클이다. (이번엔 47 패키지가 빠졌는데 그 여섯은 전부 불변이었다.)
- ★**헌법의 「강등」 서술도 측정 대상이다.** ADR-011 이 vectorbt 를 「지표 계산 전용」으로 강등한 뒤
  아무도 다시 안 쟀고, 실제로는 그 시점에 이미 **import 0 건**이었다. 강등은 사실이 아니라 계획이었다.
- ★**문서를 한 곳만 고치면 자기모순이 된다.** CONTEXT.md 에 「드리프트 정정 완료」를 적었으면
  같은 주장을 하는 다른 문서(README · 아키텍처 2종 · entities)도 같이 고쳐라. codex 가 잡았다.
- ★**파일을 옮기면 그 파일 안의 usage 안내도 옮겨라** — 아카이브한 스크립트 3종이 여전히
  `tools/scripts/<name>.py` 를 안내해 즉시 실패했다.
- ★**`docs/archive/` 는 문서 전용이다.** 은퇴한 스크립트는 `apps/api/scripts/archive/` 로.

### e2e spec 을 통합할 때 (2026-08-06 e2e-consolidation)

- ★★★**「A 는 B 에 포함된다」를 assertion 단위로 확인하기 전에 지우지 마라 — 두 번 틀렸다.**
  ⑴ 핸드오프는 `sprint32-dogfood-gate.spec.ts`(306L) 전체가 sprint46 tier 에 「거의 완전 포함」
  이라 했지만, 실제로 겹치는 건 4 테스트 중 **1개**뿐이었다. 나머지 셋은 저장소에서 **유일하게**
  `equity-pane-wrapper` · `drawdown-pane-wrapper` · `axis-label-bar` · 차트 범례 3항목 ·
  MDD `자본 초과` 캡션을 검사하고 있었다.
  ⑵ 그리고 **나도 같은 실수를 한 단계 아래에서 반복했다** — 그 「겹치는 1개」(422)마저 실제로는
  다른 요소를 본다. tier1 은 `backtest-form-unsupported-card`(빌트인 UL), 구 sprint32 는
  `backtest-form-friendly-message`(사람이 읽는 안내)로 **`FormErrorInline` 이 내보내는 별개 두
  testid**다(`form-error-inline.tsx:127` vs `:145`). 그대로 뒀으면 후자를 검사하는 spec 이 0개가 됐다.
  ⇒ **파일 이름·테스트 제목이 아니라 `getByTestId`/`getByRole` 인자를 grep 해서 대조해라.**
- ★★**playwright `testMatch` 열거식은 조용히 샌다.** 새 spec 을 목록에 안 적으면 **발견조차 안 되고**
  playwright 는 초록이다. 이제 `chromium-authed` 는 **잔여 전체**를 가져가고 다른 project 몫만
  `testIgnore` 로 뺀다. `src/__tests__/e2e-project-wiring.test.ts` 가 고아·중복을 둘 다 막는다.
- ★★**정규식에 앵커가 없으면 다른 spec 을 삼킨다.** `/smoke\.spec\.ts$/` 가 **`live-smoke.spec.ts`
  까지** 잡아 전용 project 와 겹쳤고, `pnpm e2e` 가 live-smoke 를 매번 덤으로 돌리고 있었다.
  감사 테스트를 **먼저 써서 red 로 확인**한 뒤 고쳤다(고아 0 · 중복 1 로 정확히 지목).
- ★**config 를 파싱하지 말고 import 해라.** 정규식을 문자열로 다시 쓰면 실제 배선이 아니라 내
  복사본을 검사하게 된다. 감사 통과 후에도 `playwright test --list` 로 **실제 선택 집합**을
  대조해라(1 + 1 + 4 + 14 = 20 전량 일치 확인).
- ★**`--list` 출력은 `[project] › file.spec.ts` 형식이다** — `e2e/` 접두를 기대한 grep 은 빈 결과를
  내고, 그걸 「선택 0건」으로 오독하기 쉽다.
- ★**e2e 를 로컬 검증할 땐 `PLAYWRIGHT_BASE_URL` 을 반드시 고정해라.** 안 주면 `webServer` +
  `reuseExistingServer` 가 :3000 의 **남의 앱**을 그대로 쓴다(이 머신 :3000 = 다른 제품).
  정체성 프로브(`<title>` 에 QuantBridge)를 먼저 통과시켜라.
- ★★**`test.describe.configure({ mode: "serial" })` 은 음성 대조를 지운다.** serial 은 앞 시험이
  깨지면 **뒤를 skip** 한다. 음성 대조를 뒤쪽에 두는 파일에서는 실패하는 순간 「구분이 되는가」라는
  판정 자체가 사라지고, 리포트에는 `1 failed / N did not run` 만 남는다.
  ★**`chromium-authed` 에는 얹을 이유도 없다** — config 가 이미 `fullyParallel: false` 이고
  `pnpm e2e:authed` 가 `--workers=1` 을 준다(이중 보장). 공유 storageState flake 방지 목적이라면
  **이미 달성돼 있다.** 2026-08-10 실측 — 신규 spec 5건 중 3건이 음성 대조라 serial 을 뺐다.

### e2e 가 게이트에서만 red 일 때 — 증거를 남기고 조건을 재현하는 법 ([BL-784], 2026-08-17)

- ★★★**playwright 는 매 실행의 setup 에서 `outputDir` 을 통째로 지운다.** 근거는 관용구가 아니라
  코드다 — `runner/tasks.js` 의 `createRemoveOutputDirsTask` 가 `--project` 필터에 걸린 project 들의
  `outputDir` 을 `removeFolders` 한다. 이 레포의 project 7종은 **전부 기본 `test-results/` 하나를
  공유**하므로 어떤 `--project` 로 돌리든 **직전 회차의 trace·video·screenshot 이 사라진다.**
  ⇒ **「게이트에서 실패했으니 단독으로도 실패하나 확인해 보자」가 그 실패의 증거를 파괴한다.**
  [BL-784] 가 「실패 시점 network trace 가 없다」였던 이유가 이것이고, 설정(`retain-on-failure`)은
  처음부터 정상이었다. 2026-08-17 실측 — 일부러 실패시킨 spec 의 `trace.zip`·`video.webm`·
  `test-failed-1.png` 이 남은 것을 확인한 뒤 `pnpm e2e`(**다른 project**)를 한 번 돌리자
  `test-results/` 에 `.last-run.json` 만 남았다.
- **관측 모드 — `PW_ARTIFACT_RUN=<이름>`** (`apps/web/playwright.config.ts`). 켜면 셋이 바뀐다:
  `outputDir` = `test-results/<이름>/<--project 값>` · `trace: "on"`(실패하지 않아도 남는다) ·
  `test-results/<이름>/<project>/results.json`(테스트별 통과/실패 목록).
  ★**`<--project 값>` 겹이 필수다** — 게이트는 한 번 실행에서 e2e 를 세 번 부르므로 그 겹이 없으면
  마지막 레그가 앞의 둘을 지운다(고치려던 병이 그대로 재현된다).
  ★비용: `trace: "on"` 은 authed 90 테스트 기준 **회차당 약 250MB** 다. 상시로 켜지 마라.
- ★★**「게이트 실행」은 한 모양이 아니다 — 영역 판정이 브랜치마다 다른 집합을 켠다.**
  `e2e authed` 의 술어만 `has_fe ∪ has_be` 이고(`final-gates.sh:378`) `FE vitest`·`FE build`·
  `e2e chromium`·`e2e design-canon` 은 `has_fe` 뿐이다. 그래서 **BE 만 건드린 브랜치에서는
  `e2e authed` 앞에 도는 것이 `BE pytest` 하나뿐**이고, FE 를 건드린 브랜치에서는 `pnpm build` +
  e2e 두 레그가 앞선다. 재현하려면 **어느 모양이었는지부터 확정해라** — [BL-784] 가 관측된
  회차([BL-773])는 `apps/web` diff 가 0 이라 **be-branch 모양**이었다.
- **재현 하네스 = `tools/scripts/e2e-authed-repro.sh <라벨> [반복횟수]`.**
  `QB_REPRO_SHAPE=be-branch`(기본, `BE pytest → e2e:authed`) / `fe-branch`(`build → chromium →
design-canon → authed`). 회차마다 `PW_ARTIFACT_RUN` 을 달리 주므로 **앞 회차 증거가 살아남는다.**
- ★**서버는 짝으로 띄워라** — `mise run be-isolated` **와** `mise run fe-isolated`. FE 만 띄우면
  playwright 가 자기 `webServer` 를 올리는데 그 프로세스는 `BETTER_AUTH_URL` 을 못 받아 로그인이
  403 `INVALID_ORIGIN` 으로 죽는다. 2026-08-17 회차가 이것으로 한 번 오진했다.
  `curl` 은 생존 확인 전용이다 — Origin 헤더가 없어 그 검사를 안 거친다.
- ★★★**그래서 무엇이었나 — `authed` 레그는 BE 의 전역 레이트리밋에 걸린다.**
  `apps/api/src/common/rate_limit.py:122` 가 `default_limits=["100/minute"]` 을 **신원 단위**로 건다.
  authed e2e 는 **한 사용자로 90 테스트**를 연달아 돌고 페이지마다 BE 요청을 4~8건(목록 + 내비
  배지 3종 + strategies) 내므로 60초 창을 넘긴다. 2026-08-17 실측 — 한 밤의 BE 로그에 **429 가
  616건**이었다. 대부분은 테스트가 단언하지 않는 배지 프로브라 조용히 지나가고, **하필 단언
  대상 목록 요청이 걸린 회차만 red** 다. 그래서 「실패 테스트가 실행마다 갈린다」가 나온다.
  ⇒ **원인은 지연이 아니라 거부다.** trace 타임라인에서 그 목록 요청은 **31ms · 5ms 만에 429** 로
  돌아왔고 화면에는 `API 429 /api/v1/backtests` 가 그대로 떠 있었다. 「부하로 렌더가 늦다」는
  가설을 이 증거가 반증한다 — 늦은 것이 아니라 서버가 즉시 거절했다.
  ★★**「단독 실행은 항상 green」도 거짓이다.** 단독도 같은 90 테스트를 같은 신원으로 돌리므로
  429 는 똑같이 난다. 같은 날 **단독 3회 중 1회가 red** 였고(`authed-canon-remaining.spec.ts:108`)
  그 실패 응답도 `x-ratelimit-limit: 100 · remaining: 0` 이었다. 즉 **「게이트에서만」이라는 축이
  틀렸다** — 게이트는 원인이 아니라 그 레그를 돌린 유일한 것이었다. 재현 15회 중 4회 red
  (부하 없음 1/9 · 합성 부하 3/6)이고, 부하는 원인이 아니라 **확률을 올리는 요인**이다.
  ★★★**실패 문구를 믿지 마라.** `:108` 은 429 를 「목록에서 실존 전략 편집 링크를 찾지
  못했습니다 (**데이터 시딩 필요**)」라고 보고한다. [BL-784] 가 세웠다가 반증한 가설
  「BE pytest 가 e2e 시드 데이터를 지운다」의 출처가 바로 이 문구다 — 데이터는 멀쩡했다.

- ★★★**같은 증상에 원인이 둘이다 — 먼저 어느 쪽인지 가려라** ([BL-795], 2026-08-17).
  「authed 스위트가 빨갛다」는 [BL-784] 축(**BE 레이트리밋 429**)과 [BL-795] 축(**Turbopack
  영속 캐시 물림**) 둘 다에서 나온다. 증상만으로는 구분이 안 되고, 원인을 정하기 전에
  처방을 고르면 [BL-784] 가 넉 달을 끈 모양이 그대로 반복된다.

  | 축                      | 어디서 죽나                                                      | BE 로그의 429 | 처방                                                    |
  | ----------------------- | ---------------------------------------------------------------- | ------------- | ------------------------------------------------------- |
  | [BL-784] 레이트리밋     | 개별 spec — 실행마다 **다른** 테스트가 깨진다                    | **있다**      | 신원 단위 한도(위 항목) · `e2e-authed-repro.sh` 로 재현 |
  | [BL-795] Turbopack 캐시 | `setup` 단계 — `global.setup.ts:65` 의 `/sign-in` goto 120s 초과 | **0건**       | dev 서버를 죽이고 `rm -rf apps/web/.next` 후 재기동     |

  ★**구분식 = 「실패가 `setup` 단계에서 나고 BE 로그의 429 가 0건이면 캐시 쪽이다.」**
  `setup` 이 죽으면 뒤 spec 은 전부 `did not run` 이라 **실패 1건 + 미실행 89건**이라는
  독특한 모양이 남는다 — 429 축은 반대로 앞 spec 들이 통과한 뒤 중간에서 갈린다.
  2026-08-17 실측 — `○ Compiling /sign-in/[[...sign-in]] ...` 에서 next-server 가 **CPU 0.0%**
  로 멈췄고 `curl /sign-in` 은 240초를 넘겨도 응답이 없었다. `.next` 를 치우고 재기동하니
  같은 라우트가 **0.79초**에 컴파일됐다.
  ★**크기를 문턱으로 쓰지 마라.** [BL-650] 이 「`.next` 1GB 경고선은 정책이 아니라 관측
  장치이고 근거는 두 점(1.99GB 사망 · 593MB 무해)뿐 — 인용 금지」라고 못박았다. 판정은
  **크기가 아니라 위 표의 두 축**으로 해라.

### CI 초록은 **authed 통과의 증거가 아니다** ([BL-789], 2026-08-17)

- ★★★**authed 계열 e2e 는 GitHub CI 에서 한 번도 돈 적이 없다.** 워크플로가 부르는 playwright
  project 는 `ci.yml:521-523` 의 `chromium` · `chromium-live-smoke` · `chromium-design-canon` 과
  `live-smoke.yml:62` 의 `chromium-live-smoke` 뿐이다. `chromium-authed` 를 부르는 줄은
  `.github/workflows/` 전체에 **없다**(그 이름이 걸리는 두 줄 `ci.yml:468`·`:505` 는 「CI 에는
  없다」고 적은 **주석**이다 — 산문을 배선으로 읽지 마라).
- **규모** — `apps/web/e2e/*.spec.ts` **29개** 중 공개 project 몫이 9개(`smoke` 1 · `live-smoke` 1 ·
  `design-canon-*` 7)이고, `chromium-authed` 의 `testMatch: /\.spec\.ts$/` 가 가져가는 **나머지
  20개가 CI 실행 0회**다. 유일한 실행처는 로컬 `tools/scripts/final-gates.sh` 의 `e2e authed`
  레그(= `pnpm e2e:authed`) 하나뿐이다.
- ⇒ **PR 이 CI 전건 초록이면서 authed 게이트가 red 인 채로 머지될 수 있다.** 반대로 「CI 가
  초록이었다」를 **로컬 authed red 의 음성 대조 근거로 쓰면 그 근거는 무효다** — 그 잡은
  authed 를 애초에 돌리지 않았다. 원장에 그렇게 적힌 항목이 실재한다([BL-668] 의 음성 대조 ②).
- **회귀 방지** — `apps/web/src/__tests__/e2e-project-wiring.test.ts` 의 「CI 실행 표면」 감사가
  `playwright.config.ts` 의 project 이름과 `.github/workflows/*.yml` 을 **양쪽 실파일에서 파싱해**
  대조한다. CI 에서 안 도는 project 는 `LOCAL_ONLY` 상수에 **사유와 함께** 등재해야 하고,
  새 project 를 만들고 워크플로에 안 배선하면 빨개진다. 변이 3/3 red 확인(design-canon 배선
  제거 · `LOCAL_ONLY` 비우기 · project 이름 오타).
- ★**아직 안 닫혔다 — 1단계만 했다.** CI 에 authed 잡을 세우려면 CI 전용 시더 + 로그인 배선이
  필요하고, [ADR-034] 가 CI 인증 secret 을 0개로 만든 결정이라 그 반전은 **사용자 결정**이다.
  그때까지 authed 의 증인은 로컬 게이트 하나뿐이다.

### 신규 BE 필드는 FE `.strict()` 스키마와 **항상** 대조해라 (2026-07-30, codex 적대 리뷰 MAJOR)

> ★★★**읽기 경로가 정상인 것은 쓰기 경로가 정상이라는 증거가 아니다.**

`StrategySettings` 에 필드를 추가하면 BE 가 그것을 **`default=None` 으로 emit** 하고
`strategy/service.py` 의 `update_settings` 가 `settings.model_dump()` 를 **그대로 JSONB 에 저장**한다.
FE `StrategySettingsSchema` 는 `.strict()` 라 모르는 키에서 **파싱이 실패**한다
⇒ **설정을 한 번만 저장해도 그 전략의 FE 파싱이 영구히 깨진다.**

★**GET 응답에는 그 키가 없어서**(BE 가 DB JSONB 를 그대로 돌려준다) **화면을 3개 돌아도 안 잡힌다.**
저장 경로에서만 터진다. 실제로 워커·평가자 둘 다 "동작 영향 없음" 으로 오판했고 codex 가 잡았다.
→ **BE 설정 스키마에 필드를 더하면 같은 PR 에서 `apps/web/src/features/strategy/schemas.ts` 를 고쳐라.**

★**그리고 `nullable` 필드면 FE 폼의 초기값 정규화까지 같은 PR 에서 해라** (2026-08-01, BL-570).
`schemas.ts` 를 맞추는 건 **파싱**을 맞추는 것이고, 깨지는 다음 자리는 **폼 초기값**이다 —
null 저장 → 초기 DOM 값 `""` → `setValueAs` 는 change 에서만 도는데 `z.number()…` 가 `""` 를 거부
→ `handleSubmit` 이 조용히 막고, 그 폼이 `formState.errors` 를 안 그리면 **아무 피드백도 없다.**
★**무편집 저장을 눌러봐야 보인다** — GET 도 「편집 후 저장」도 멀쩡해서 세 회차를 살아남았다.

### 측정 도구가 먼저 틀린다 (2026-07-28)

- ★★**`/metrics` 가 HELP/TYPE 만 보이고 샘플이 없으면 백엔드를 재기동해라.** `PROMETHEUS_MULTIPROC_DIR` 배선 **이전에** 뜬 프로세스는 단일 프로세스 모드라 **자기 값만** 노출한다. 그 상태에서 관측한 worker metric 처럼 보이는 값들이 사실은 API 프로세스 자신의 것일 수 있다.
- ★★**`MmapedDict.read_all_values_from_file` 은 4-튜플을 준다.** `for k, v in ...` 로 풀면 `ValueError` 가 나고, 그걸 `except: pass` 로 삼키면 **"1389개 파일 전부에 metric 0개"** 라는 오답이 나온다. **측정값이 0이면 대상보다 계측기를 먼저 의심해라.**
- ★★**변이가 두 구현이 동치인 지점에 떨어지면 아무것도 증명하지 못한다.** "fail-closed 를 조기 `return` 으로" 변이를 **취소 루프 뒤**에 넣었더니 `to_place=()` 와 의미가 같아 통과했다. 앞으로 옮기니 즉시 잡혔다. **탈출을 보고 "테스트가 약하다" 로 바로 가지 마라 — 변이가 실제로 무엇을 바꿨는지 먼저 봐라.** (같은 회차에서 2번 발생: 다른 하나는 두 가드가 같은 mock 을 써서 서로를 가린 경우였다.)
- ★**변이 대상 테스트 파일을 맞게 골라라.** 리포지토리 SQL 을 겨눈 변이를 서비스 테스트(리포지토리를 mock 함)로 재면 영원히 통과한다.
- ★★★**내용 grep 은 「파일명에만 있는 문자열」을 구조적으로 못 잡는다** (2026-08-02). BL-577 은 `grep -rn "no-raw-enum-labels" .` 로 「그 가드는 이 레포에 존재하지 않는다」고 결론 냈는데, **가드는 `apps/web/src/__tests__/no-raw-enum-labels.test.ts` 로 실재했다** — 그 파일이 자기 이름을 본문에 **0회** 쓰기 때문이다. 그 오진 위에서 backlog 가 「우회 코드를 되돌려라」고 지시했고, **그대로 했으면 CI 가 red** 가 됐다. ⇒ **「없다」를 결론으로 낼 때는 내용 grep 하나로 끝내지 마라 — 파일명(`find` · `ls`)과 실행(그 테스트가 CI 에서 도는가)까지 세 축으로 확인해라.**
- ★★**라벨 있는 counter 는 첫 발화 전까지 series 가 존재하지 않는다** (2026-08-02). 라벨 **없는** counter 는 import 시점에 0 으로 실체화되지만, 라벨 있는 쪽은 `.labels()` 가 불리기 전까지 mmap 에 항목이 없다. 그래서 창 시작 스냅샷에 그 series 가 없고 `CounterBasis.unknown` 으로 **비교가 거부**된다 ⇒ **신설 counter 를 프로덕션에서 증명하려는 바로 그 순간에 계측이 구조적으로 불가능**하다. **미리 실체화해라**(`live_signal._touch_safely` — `record_metric_safely` 로 감싼 **무증분** `.labels()`. `_count_safely` 는 `.inc()` 하므로 초기화에 쓰면 차분이 발화 수보다 커진다).
- ★**소크 종료가 자동 flat 이 아니다** (2026-08-02). 세션 `DELETE` 가 **204** 를 줘도 거래소에 **포지션과 resting 조건부 주문이 남는다.** 실측: DELETE 2건 성공 뒤 포지션 0.03 + resting 1건 잔존. **주문 취소 → 포지션 청산**을 따로 하고 **raw HMAC 으로 재조회**해 `FLAT=YES` 를 확인해라. 착수 시점 flat 확인도 의무다 — 직전 소크의 **고아 포지션**(활성 세션 0인데 포지션 존재)이 남아 있으면 발화 원인이 오염된다.

### 셸·게이트가 거짓 red 를 내는 경로 (2026-07-28)

- ★★**Bash 도구의 cwd 는 호출 간 유지된다.** `cd apps/api && set -a; . ./.env.local; set +a; uv run pytest` 를 **두 번째로** 부르면 `cd apps/api` 가 실패하고 `&&` 때문에 **`set -a` 가 안 돈다.** env 가 export 되지 않아 `localhost:5432` 로 붙고 대량 에러가 난다 — 코드 결함처럼 보이는 거짓 red 다. **절대경로로 `cd` 해라.**
- ★★**부분 선택 실행은 격리가 깨진다.** `pytest tests/tasks/x.py tests/trading/ tests/strategy/` 조합에서 **30건이 실패**했지만 같은 테스트를 단건으로 돌리면 통과하고 **전체 스위트도 통과**한다. 판정 권위는 **전체 스위트**다.
- ★★★**파이프에 넣은 게이트의 종료 코드는 파이프 **끝** 명령의 것이다.** `playwright … | tail -40`
  의 rc 0 은 tail 의 성공이고, 그 뒤에 `2 failed` 가 숨어 있었다(2026-08-10 실측 — 하마터면 baseline
  을 「전건 통과」로 적을 뻔했다). ⇒ **게이트는 파일로 받고(`> /tmp/g.txt; echo $?`) 출력을 읽어라.**
  ★**zsh 에서 `${PIPESTATUS[0]}` 는 빈 문자열이다** — zsh 의 배열은 소문자 `pipestatus` 이고 1-기반이라
  `${pipestatus[1]}` 이 첫 명령이다. bash 관용구를 그대로 쓰면 **아무 값도 안 나오는데 조용하다.**
- ★★**zsh 는 `$VAR` 를 단어분리하지 않는다(`SH_WORD_SPLIT` off) — 변이 판정이 통째로 무효가 된다.**
  `T="a.test.ts b.test.ts"; vitest run $T` 는 **한 인자**로 들어가 vitest 가 아무것도 매치하지 못하고,
  `grep "Tests"` 가 침묵해 **「전부 초록」처럼 보인다**(2026-08-10 실측: 변이 3건의 판정이 공백이었다).
  ⇒ **배열로 써라** — `T=(a.test.ts b.test.ts); vitest run "${T[@]}"`. 위 `$ARGS` 항목과 같은 뿌리이고
  **이번엔 셸이 아니라 판정을 삼켰다.**
- ★**`pnpm test --outputFile=…` 은 pnpm 이 인자를 삼킨다** — 리포터 옵션이 vitest 에 도달하지 않고
  파일이 안 생긴다. `pnpm exec vitest run --outputFile=…` 로 **pnpm 을 우회**해라.
- ★**`rm -rf` 는 권한에서 거부될 수 있다**(2026-08-09·08-10 연속 3회). 대안은 스크래치패드로
  `mv` 해 격리하는 것이고, 결과는 같다. **cwd 착오로 「캐시 없음」이라 오판한 적이 있으니 절대경로로 재라.**
- ★★★**병렬 fan-out 이 0행을 냈고, 그것을 조용하게 만든 것은 내가 붙인 `2>/dev/null` 이었다**
  (2026-08-12 branch-debris, 두 경로로 각각 한 번씩). ⑴ **zsh 의 `export` 는 `-f` 를 옵션으로 받지
  않는다** — bash 관용구 `export -f probe; xargs -I{} bash -c 'probe "$@"' _ {}` 를 쓰면 zsh 가
  **함수 정의를 stdout 으로 출력**하고(실측: `f () {` / `echo hi`) 결과는 **0행**이다.
  ⑵ 고쳐 쓴 `xargs -P 6 -d '\n'` 의 `-d` 는 **GNU 전용**이고 macOS(BSD) xargs 는 무시가 아니라
  **`xargs: invalid option -- d` 로 죽는다**(실측). ★**두 번 다 실제로는 시끄러웠다** — 내가
  `2>/dev/null` 로 stderr 를 버려서 조용해 보였을 뿐이다.
  ⇒ **함수를 export 하지 말고 스크립트 파일로 빼라**, `-d` 대신 `-I{}`(개행 구분) 를 써라,
  **fan-out 의 stderr 를 버리지 마라**(파일로 받아 읽어라), 그리고 **`[ "$(wc -l < out)" -eq "$N" ]`
  가드를 걸어라** — 이번에 0행을 성공으로 읽지 않게 막은 것은 그 가드 하나뿐이었다.
  「전건 조회했다」는 보고가 **아무것도 조회하지 않은 것**일 수 있다.

### git 으로 세거나 「안전하다」고 말할 때 (2026-08-12 branch-debris)

브랜치 291→23·177→51 정리 회차에서 **분모·안전망·API 판별력이 각각 한 번씩 틀렸다.**

- ★★★**`git branch -r --format='%(refname:short)'` 는 `refs/remotes/origin/HEAD` 를 `origin` 으로
  축약한다.** `grep -vx HEAD` 로는 안 걸리고, 그 한 줄이 브랜치 수에 섞여 **291(실제 290)** 이 됐다.
  ⇒ 세는 것은 `git for-each-ref refs/remotes/origin/` 로 **전체 refname** 을 쓰고
  `refs/remotes/origin/HEAD`·`/main` 을 **이름 그대로** 빼라.
- ★★★**`git rev-list --all --remotes=origin` 은 항진명제다.** `--all` 이 **로컬 ref 까지** 포함하므로
  「원격에서 도달 가능한가」를 물으면 로컬 브랜치 팁이 **자기 자신 때문에** 집합에 들어간다 —
  165건 전부 「안전」이라는 답이 나왔다(집합 1,635 → `--all` 제거 후 **1,034**, 601개가 가짜).
  ⇒ `git rev-list --remotes=origin` (`--all` 없이). **그리고 판별력 시험을 먼저 세워라**:
  `git commit-tree` 로 원격에 없는 커밋을 만들어 「밖」으로 판정되는지 본다(음성),
  `origin/main` 팁이 「안」으로 판정되는지 본다(양성).
- ★★**`git rev-list --remotes=origin` 은 「라이브 원격」이 아니라 로컬 `refs/remotes/origin/*` 이다.**
  stale 이면 「원격에 있다」가 거짓이 된다. 지우기 전에 `git ls-remote --heads origin` 과 대조해라 —
  정상이면 차이가 **`origin/HEAD` 한 줄뿐**이다(위 항목과 같은 뿌리).
- ★★★**GitHub 「Restore branch」 버튼이 되살리는 것은 PR 의 `head.sha` 이지 브랜치의 현재 팁이 아니다.**
  PR 이 머지된 뒤 커밋이 더 쌓인 브랜치는 **PR 이 있어도 안전망 밖**이다. 원격 후보 276건 중 **9건**이
  그랬다(이름축으로는 「머지된 PR 보유」였다). ⇒ 안전망은 **이름축(브랜치명 ↔ PR head ref)이 아니라
  해시축(팁 sha ↔ PR head sha)** 으로 판정해라. 이름이 다른데 sha 가 같은 짝도 있다.
- ★★**안전망 확인은 표본이 아니라 전건으로 해라.** 「PR 이 있으면 GitHub 이 sha 를 보관한다」를
  표본 5/5 로 확인하고 넘어갔는데, codex 적대 리뷰가 「5건은 121건을 입증하지 않는다」고 지적했다.
  전건 `gh api repos/:o/:r/commits/<sha>` 조회 → **121/121 OK**. 판별력은 가짜 sha(`000…0`)가
  거부되는지로 확인한다.
- ★★**`GET /repos/:o/:r/commits/{sha}/pulls` 는 이 레포에서 판별력이 0 이다** — 실제 PR 의 head sha 를
  넣었는데 **빈 배열**을 반환했다. 이것을 「PR 없음」의 증거로 쓰면 전건 오판한다. 쓸 수 있는 것은
  `gh api repos/:o/:r/pulls --paginate` 가 주는 **`head.sha` 집합과의 대조**다.
- ★**`git branch -d`(소문자)는 squash 머지 레포에서 거의 전건 거부한다** — 126건 중 **5건**만 통과했다
  (원격 추적이 있는 것). 팁이 main 의 조상이 되는 일이 없기 때문이다(로컬 165건 중 조상 **0건**).
  그래도 `-d` 를 먼저 돌려 **git 의 2차 판정을 기록으로 남기는 것**은 값있다 — 거부 목록이 곧
  「내 안전망 근거로만 지우는 대상」이 된다.
- ★**브랜치 diff 로는 「고유 작업」을 판정할 수 없다.** 표본 8건이 `파일 1,600여 개 · +17만/−31만` 을
  냈는데 그것은 브랜치의 작업이 아니라 **3개월치 시간 차이**였다(브랜치가 그 시점의 레포 전체를 든다).
  판정하려면 `git log main..<브랜치>` 를 **커밋 단위**로 읽어야 한다.
- ★**`comm` 은 바이트 정렬을 가정한다.** 브랜치 이름에 `/`·`+` 가 섞이면 로케일에 따라 `sort` 결과가
  달라져 교집합이 조용히 틀린다. 집합 연산 전에 **`export LC_ALL=C`** 를 걸어라.

### 린트가 잡는 문자

- **RUF003** — 주석 안의 `×`(MULTIPLICATION SIGN) 와 `−`(MINUS SIGN) 가 ruff 를 깬다. ASCII `x` 와 `-` 를 써라. 네 번 재발했다. `tests/` · `tools/scripts/` · `alembic/versions/` 는 면제지만 `src/` 는 아니다.
- **디자인 캐논 em-dash 래칫** — `apps/web/src/__tests__/design-canon-source.test.ts` 가 노출 산문의 `—` 를 **파일별 정확 카운트로 양방향 동결**한다. 늘어도 줄어도 RED 다. `EM_DASH_ALLOWLIST` 를 올리지 말고 **문구에서 빼라**.
  ★ 이 래칫은 **FE 소스만 스캔한다.** 서버가 보내 화면에 렌더되는 문자열은 안 잡히므로 백엔드 문자열은 사람이 지켜야 한다.
  ★★**주석은 안 센다** — `stripComments` 로 지운 뒤 세고 `__tests__` 는 제외한다(2026-08-10 코드 대조).
  종전에 돌던 「FE 주석에 `—` 금지」는 **현행 코드에 거짓**이다. 잡히는 것은 **JSX/문자열 산문**뿐이고,
  양옆이 둘 다 비단어인 고립 `—`(`<td>—</td>` 같은 자리표시자)도 정당하다.
- **`@typescript-eslint/consistent-type-imports`** — 인라인 `import("@playwright/test").Page` 형태의
  타입 주석이 **금지**다. pre-commit 에서만 물리므로 `tsc --noEmit` 초록을 근거로 넘기지 마라.
  상단에서 `import { type Page } from "…"` 로 받아라.
- **`docs-audit` 이 세는 것은 낱말이 아니라 구문 `다음 행동 =` 이다.** 그리고 **인라인 백틱 안은
  건너뛴다**(`docs-audit.sh:317-322`) — 규칙을 설명하는 문장이 규칙 자신을 인용해야 하기 때문이다.
  ⇒ 규칙을 인용할 때는 **문장을 비틀지 말고 백틱으로 감싸라.** 취소선(`~~`) 안도 세지 않는다.
  ★종전 메모의 「인용문도 센다」는 **낡았다**(2026-08-10 코드 대조로 반증).
- **`[BL-NNN]` 바로 뒤에 괄호로 설명을 붙이면 깨진 링크가 된다.** 그 괄호가 링크 타깃으로 읽혀
  `docs-audit` 이 잡는다(실측 4건 RC=1). 설명은 **괄호 밖으로** 빼라 — `[BL-693] 전부 P3`.
  ★**이 항목을 쓰다가 그 게이트에 물렸다** — 위반 예시를 그대로 적었더니 예시가 곧 위반이었다.
  함정을 문서화할 때는 **위반형을 리터럴로 쓰지 말고 서술해라.**

### 언어·타입

- **`bool("false") is True`** — TradingView alert 은 문자열 불리언을 보낸다. 명시 화이트리스트로 방어해라.
- **`getattr(x, "f", False)`** 는 미구현 필드를 정상 False 로 위장한다.

### 게이트가 **거짓 red** 를 내는 경로 (2026-07-27 live-conditional-hardening)

- ★**dev 서버의 Turbopack CSS 캐시는 오래 살아남고, e2e 는 그 stale 자산을 검사한다.** `PLAYWRIGHT_BASE_URL=http://localhost:3100` 은 **실행 중인 dev 서버**를 재사용하므로, 그 서버가 옛 CSS 를 서빙하면 이미 고친 캐논이 다시 red 로 나온다. 거짓 그린만 조심할 게 아니다.
  - **판별법 = 세 층 대조.** ① 소스(`globals.css`) ② 프로덕션 빌드(`.next/static/chunks/*.css`) ③ **dev 서버가 실제로 서빙하는 것**. ③만 다르면 캐시다.
  - 서빙본 확인은 CSSOM 이 아니라 **원문 fetch** 로 해라 — `document.styleSheets` 순회는 inline sheet 를 놓치거나 `cssRules` 접근이 막힐 수 있어 "매치 규칙 0개" 같은 오답을 준다. `fetch(sheet.href).then(r => r.text())` 후 정규식으로 규칙을 찾아라.
  - 실측 — 소스·프로덕션 빌드에는 `.pager-nums{flex-wrap:wrap}` 이 있고 dev 서빙본에는 **없었다**. 프로덕션 빌드를 별도 포트에 띄워 재실행하니 그 캐논이 통과했다.
  - **이 함정의 4차 재발이다.** 앞선 세 번은 "고쳐도 적용이 안 된다" 는 인상으로 나타났다.
  - ★★**5차 재발 (2026-08-11 ledger-truth) — 그리고 「재기동뿐」이 불완전함이 실측으로 드러났다.**
    같은 커밋에서 `e2e design-canon` 이 **PASS → 5 failed** 로 뒤집혔다(코드 변경 0 · frontend diff 0 ·
    `:3100` 은 200). 오래 띄워 둔 dev 서버의 `.next` 가 **1.5GB** 였다.
    **원인을 분리해 쟀다** — 처음엔 재기동과 캐시 제거를 **같이** 해서(42 passed) 무엇이 고쳤는지
    몰랐다. 그래서 스테일 캐시를 되돌리고 **재기동만** 다시 했다:

    | 조건                               | 결과                     |
    | ---------------------------------- | ------------------------ |
    | 오래 띄운 서버 + 스테일 캐시 1.5GB | **5 failed**             |
    | **재기동만** (같은 스테일 캐시)    | **1 failed / 41 passed** |
    | 재기동 + 캐시 제거                 | **42 passed**            |

    ⇒ **재기동이 5건 중 4건을 고치고, 마지막 1건은 캐시 제거가 필요했다.** 남은 1건은
    `design-canon-calibration.spec.ts:121`(라이트 2벌 캘리브레이션)이다. 재기동 후 초록을 보고
    「캐시는 무관」이라 결론내면 다음 사람이 같은 1건에 걸린다.

  - ★★**복구 절차 — 순서가 전부다** (2026-08-17 [BL-795] 로 통합. 종전 「복구 = 재기동뿐,
    지우지 말고 재기동해라」는 **폐기한다** — 그 문장은 2026-07-27 관측 1점에서 나왔고
    위 5차 재발 표가 반증했다. 「지우지 마라」의 진짜 근거는 **살아 있는 서버 밑에서** 지우면
    `routes-manifest.json` ENOENT 로 그 서버가 500 을 낸다는 것이지, 캐시가 무해하다는 것이 아니다):
    1. **재기동만** 먼저 — dev 서버를 죽이고 다시 띄운 뒤 같은 명령을 돌린다. 2026-07-27 에는
       코드 변경 0으로 **64/1 → 65-0** 이 됐고, 2026-08-11 에는 5건 중 4건이 이걸로 풀렸다.
    2. 그래도 남으면 **서버가 죽은 상태에서** 캐시를 치운다 — `rm -rf apps/web/.next`.
       삭제보다 `mv` 로 격리하는 편이 가역적이다. 경로는 **절대경로**로 재라(2026-08-09 에 cwd
       착오로 「캐시 없음」이라는 거짓 판정을 한 이력이 있다 — 실제 372MB 였다).
    3. 치운 뒤 다시 띄운다.

    ★**증상이 「stale 자산」이 아니라 「컴파일이 안 끝난다」로 나타나면 1번을 건너뛰고 2번으로
    가라** — [BL-795] 축이다(`setup` 단계에서 `/sign-in` goto 120초 초과 · next-server CPU 0.0%).
    구분식은 위 §「e2e 가 게이트에서만 red 일 때」의 두 축 표에 있다.
    ★**크기로 판정하지 마라.** `mise run fe` 의 1GB 경고선은 [BL-650] 이 「정책이 아니라 관측
    장치, 근거는 두 점뿐 — 인용 금지」라고 못박은 값이다.

- ★**프로덕션 빌드로 e2e:authed 를 대신 돌리면 다른 것이 깨진다.** 그 suite 는 로컬 dev 전용이다(빌드 타임 env·`e2e/global.setup.ts` 가 발급하는 storageState 전제). 프로덕션 실행은 **"코드가 맞다" 의 증명**으로만 쓰고, 게이트 숫자는 dev 서버를 재기동한 뒤 다시 재라.

### 캐시·주기 (2026-07-27 live-conditional-hardening)

- ★**새 Redis 캐시 키를 만들면 "누가 이 키를 지우는가" 를 같은 PR 에서 답하라.** 계정 스코프 포지션 캐시를 넣으면서 무효화 경로를 안 만들었고, 기존 세션 키 삭제는 **활성 세션 순회**라 활성 0건이면 아무것도 안 지웠다 — 그런데 그 기능이 존재하는 이유가 정확히 "활성 세션 0건" 상태였다. 결과는 청산 직후 15초 동안 **닫은 포지션이 살아 있는 청산 버튼과 함께 다시 렌더**.
  - ★**React Query invalidate 는 서버 캐시를 지우지 않는다.** 쿼리 키를 잘 배치해도 재조회가 서버 TTL 캐시에 적중하면 낡은 값이 그대로 온다. "무효화는 이미 맞다" 를 쓰기 전에 **양쪽 층을 다 확인**하라.
  - ★**dogfood 통과가 커버리지가 아니다.** 이 결함은 dogfood 를 통과했다 — 청산 후 확인까지 30초 넘게 걸려 15초 TTL 창을 못 밟았을 뿐이다.
- ★**"tick 간격" 을 상수의 근거로 삼기 전에 그 tick 이 실제로 언제 도는지 읽어라.** 라이브 평가는 beat 가 60초마다 fire 하지만 `no_new_bar` 조기 return 때문에 reconcile 은 **bar 마다**(1m/5m/15m/1h) 돈다. 60초를 전제로 잡은 3분 게이트는 1h 세션에서 보호값이 0이었다.
- ★**나이로 "사라졌다" 를 판정하지 마라.** 주문의 나이(`submitted_at`)와 부재의 나이는 다른 값이다. 조건부 주문은 정의상 오래 resting 한다. 부재는 **거래소에 직접 물어**(`fetch_order`) terminal 인지 확인하는 것이 유일하게 옳다.

### 변이 검증 (2026-07-27)

- ★**변이 스크립트에 `git checkout <file>` 을 넣지 마라.** 그 파일에 있던 **이번 스프린트 신규 코드까지 함께 사라진다**. 실제로 신규 repository 메서드가 통째로 날아갔고, "복원 확인" 단계에서 테스트가 여전히 red 인 것을 보고서야 알았다. 변이·복원은 **문자열 치환 쌍**으로 하고, 마지막에 **반드시 복원 확인 실행**을 넣어라.
- ★**픽스처 기본값은 게이트가 닫히는 쪽으로 둬라.** 나이 게이트를 넣을 때 `submitted_at` 기본값을 "방금" 으로 뒀다. 늙은 값이 기본이었으면 무관한 테스트들이 조용히 제거 경로를 타고, 변이가 아무것도 뒤집지 못했을 것이다.

### 추론 (2026-07-27)

- ★**"그 코드 경로의 흔적이 원장에 없다" 는 "그 코드가 호출된 적 없다" 가 아니다.** 조건부 UPDATE 가 경합에 **패배**하면 `rowcount=0` 이라 행에 아무것도 쓰지 않는다. 최종 행만 보고 "미주행" 을 결론내면 성공 경로와 시도 횟수를 혼동한 것이다. 호출·패배를 세려면 **전용 metric** 이 필요하다.

### 계기(instrument) — 어떤 상품의 가격을 보고 있는가 (2026-07-28)

- ★★★**"같은 심볼" 이 같은 상품이라는 뜻이 아니다.** `ccxt` 인스턴스의 `defaultType` 이 심볼 해석을 바꾼다. 이 저장소에서 `BTC/USDT` 는 **스팟**, `BTC/USDT:USDT` 가 **무기한선물**이다. `market_data/providers/ccxt.py` 는 `defaultType: "spot"` 이고 `trading/providers.py` 의 `BybitFuturesProvider` 는 `"linear"` 다 — **두 모듈이 같은 문자열을 서로 다른 상품으로 읽는다.**
  - 그래서 라이브 엔진이 **스팟 봉을 재생하면서 perp 에 주문을 냈다**(BL-530). 실측 괴리는 **25~42 USDT (0.04~0.066%)** 로 지속적이고 **한쪽으로 치우친다** — 스팟이 위. 매수 스톱은 시뮬에서만 걸리고 매도 스톱은 거래소에서만 걸리는 **방향성 편향**이 된다.
  - 결정적 증거: 2026-07-28 08:06 UTC 스팟 고가가 **63541.7** 로 시뮬 스톱과 **소수점까지 일치**했는데 같은 분 perp 고가는 **63499.4**. 픽스처로 고정했다(`tests/fixtures/bybit_spot_vs_perp_bars.py`).
  - ★**BL-511 이 같은 결함을 가드 기준가에서 한 번 고쳤는데도 엔진 봉은 그대로였다.** 계기 정렬은 **한 사이트씩** 고쳐지므로, 가격을 읽는 새 코드를 쓸 때마다 _"이건 어느 상품인가"_ 를 되물어라. 실측 대조 1회(`category=spot` vs `category=linear` kline)면 끝난다.
- ★**시뮬 포지션과 거래소 포지션은 자동으로 수렴하지 않는다.** `run_live` 는 OHLCV 재생만 하고 거래소 포지션을 **입력으로 받지 않는다**. 진입이 라이브에서 유실되면 그 유령 포지션은 영원히 남고, 이후 close 는 전부 거절된다(`110017 current position is zero`). 방향까지 어긋나면 `reduce_only=True` 하나가 **반대 방향 포지션 증가**를 막는 유일한 방벽이다.
  - 관측 지점 = `qb_live_position_divergence_total{category}` + `qb_live_signal_divergence_total{stage="position"}`. 진단 SQL 은 [`live-close-diagnostics.md`](live-close-diagnostics.md).

## 3.5 컨텍스트 예산 — 세션이 새는 두 채널

> 2026-07-28 승격. 직전 회차가 이 규칙을 **참조는 했으나 이 파일에 없었다** — 핸드오프가 "여기 있다" 고 적었지만 실제로는 없었고, 이번에 실제로 넣는다.

- ★**서브에이전트는 파일이 아니라 상한으로 답한다.** 이 저장소의 읽기 전용 서브에이전트(`Explore`)는 **Write 도구가 없다.** "리포트를 파일에 써라" 는 지시는 실패하고 전문이 반환값으로 돌아온다(단일 최대 소모원). **반환값 줄 수 상한을 명시해라** — "30줄 이내 / 발견마다 3줄 / 코드 덤프 금지" 가 실제로 먹는다.
- ★**Monitor 는 변화 감지가 아니라 위험 신호 + 하트비트다.** 즉시 발화는 **작업을 죽이는 사건만**(세션 비활성화 · kill switch · DNS 실패). 진행 상황은 **10~15분 하트비트 1줄**. 판단 기준 = _"이 발화를 보고 내가 뭘 할 것인가?"_
- worker 로그 전문 금지 — `grep -c` / `sort | uniq -c` 집계만.
- 문서 파일은 `head`/`sed -n` 에 **`cut -c1-200`** 을 붙여라. 이 저장소 dev-log·backlog 는 행 하나가 3,000자다.
- ★**codex 산출물(`*-codex.txt`)은 tool-trace 가 수십만 줄이다.** 최종 답변만 뽑아라 — `awk '/^\[P[123]\]/{f=1} f'` 같은 패턴으로 자른다. 통째로 읽지 마라.

## 4. pre-push 훅

`.husky/pre-push` 는 main worktree 에서:

- `main` / `master` push **영구 차단** (bypass 불가)
- `feat/*` `fix/*` `chore/*` `docs/*` `test/*` `refactor/*` `hotfix/*` 만 허용. 그 외는 `QB_PRE_PUSH_BYPASS=1` 필요
- `apps/web/` 변경 시 `pnpm typecheck && pnpm test`
- `apps/api/` 변경 시 `uv run ruff check . && uv run mypy src/` (**pytest 는 opt-in** — `QB_RUN_PYTEST=1`)
- `apps/api/.env.local` 에서 **`TEST_` 접두 변수만** 자동 export. `DATABASE_URL` 은 안 들어온다

## 5. 격리 스택

| 항목     | 기본 | 격리 (`mise run up-isolated`) |
| -------- | ---- | ----------------------------- |
| FE       | 3000 | **3100**                      |
| BE       | 8000 | **8100**                      |
| Postgres | 5432 | **5433**                      |
| Redis    | 6379 | **6380**                      |

다른 웹앱과 병렬로 돌릴 때 격리가 디폴트다. 옛 스프린트 문서의 `5436` 표기는 stale — 2026-07-25 포트 정렬 이후 **5433** 이 정답이다.

---

**관리 규약** — 새 스프린트에서 게이트 함정을 발견하면 자기 체크리스트에 적지 말고 **여기에 추가**해라. 그게 이 파일이 존재하는 이유다.
