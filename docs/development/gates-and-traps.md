# 게이트와 함정 — 모든 세션이 여는 문서

> 무엇을 돌려야 "통과" 인지와, 통과한 줄 알았는데 아닌 경우들.
> 2026-07-26 신설. 이 내용은 그전까지 스프린트 문서 7개에 복붙되고 있었고,
> 당시 `reference/` 에 있던 유일한 진술은 **틀려 있었다** ([`traps-gates-measurement.md`](./traps-gates-measurement.md) 의 `pnpm test` 항목).

> ★**[ADR-037](../adr/037-harness-zero-base.md) 제로베이스 (2026-08-19).** 이 문서에서
> `final-gates`·`bl-audit`·`docs-audit`·`bl-trigger-sweep`·`header-audit`·`skip-ratchet`·
> `signal-check`·`context-budget`·`tool-pin-audit`·`gate-harnesses`·`*-test.sh` 를 언급하는 절차는
> **전부 역사 기록이다** — 그 검사기들은 철거됐다(원문 = `git show harness-v1:<경로>`).
> 지금 유효한 것: §1 의 표준 러너(ruff/mypy/pytest/tsc/vitest/lint/build)와 CI 단일 게이트,
> §3 → [`traps-environment-shell.md`](./traps-environment-shell.md) §환경(`.env.local` 소싱·DATABASE_URL 단독 주입 금지 등 — 여전히 전부 참),
> §4 pre-push 는 ref 가드만 남음, 원장 사활 = `tools/scripts/ledger-vitals.sh` 3축.
> 리뷰 = `/review-code` · codex 훅 = `.codex/hooks.json` · 하네스 Eval = `evals/harness/`.
> 재입힘 규칙: 문서화된 사고 1건 = 슬림 복귀 1건 (ADR-037 §④).

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

~~문서 구조·활성 Markdown 링크·폐기 경로는 루트에서 `mise run docs-audit`으로 검사한다.~~
→ **2026-08-19 [ADR-037] 철거** — `docs-audit` 은 없다(원문 = `git show harness-v1:tools/scripts/docs-audit.sh`).

### ~~게이트 3종 신규 · 게이트 2단(`--pre-pr`/`--deferred-only`) · 신호 4종(`.claude/gates/`)~~

→ **2026-08-19 [ADR-037] 철거.** 세 절(150줄)이 기술하던 기계가 전부 사라졌다 —
`tools/scripts/final-gates.sh` · `signal-check.sh` · `skip-ratchet.sh` · `docs-audit.sh` ·
`mise run gate-harnesses`(자기시험 14종) · 증거 마커 디렉터리 `.claude/gates/<run>/`.
**원문 = `git show harness-v1:docs/reference/operations/gates-and-traps.md`** (이 파일 53~202줄).

지금의 판정은 **표준 러너 + CI 단일 게이트** 하나다(위 §1 명령 + `.github/workflows/ci.yml`).
로컬에서 미리 보려면 그 러너를 직접 돌려라 — 유예 원장도, 신호 파일도, 브랜치 전제도 없다.
복귀는 [ADR-037] 재입힘 규칙(문서화된 사고 1건 = 슬림 복귀 1건, 최소판) 경유다.

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

술어·창·리셋 규칙은 [`ADR-024`](../adr/024-soak-stability-gate.md). 계산부는 I/O 없는
순수 함수(`apps/api/scripts/soak_gate_predicate.py`)라 손 계산과 대조할 수 있고, 정의는
`apps/api/tests/scripts/test_soak_gate_predicate.py` 로 동결돼 있다(개수는 세지 마라 — 세어 적으면
낡는다. 이 줄에 「22테스트」라고 박혀 있던 값이 2026-08-08 에 이미 두 배 넘게 틀려 있었다.
★경로도 낡아 있었다 — `tests/tools/scripts/` 는 [ADR-029] 재배치 전 자리다, 2026-08-15 정정).

★**실격의 원인은 게이트가 모른다** — 사람이
[`soak-disqualifications.jsonl`](../operations/soak-disqualifications.jsonl) 에 근거와 함께 등재하고, 게이트는
그것을 **보고 줄 한 줄**로만 낸다(`★실격 귀속(보고 전용 · 판정 불참)`). 판정 C1~C5 는 원장이
있든 없든 같은 값이다 — 계약과 기각된 대안은 [ADR-024 §실격 귀속 원장](../adr/024-soak-stability-gate.md).
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

tools/scripts/soak-restart.sh            # 기본 = dry-run. 재기동 8단계와 실제 값을 출력만 한다
tools/scripts/soak-restart.sh --confirm  # 집행 (⑴ FLAT=YES 아니면 그 자리에서 멈춘다)
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

**재배치·경로 이동 뒤 필수 점검 4줄** — [BL-719] 류 롤아웃 체크리스트에 반드시 넣어라:

```bash
tools/scripts/soak-watch.sh --status          # rc=1 이면 설치본이 낡았다 (ExecStart 실재+일치 판정)
tools/scripts/api-service.sh --status         # 위 표 2행 — ExecStart 의 .venv/bin/uvicorn 경로 대조 ([BL-805])
grep -l quantbridge ~/.config/systemd/user/*  # 유닛 전수 — 각 파일의 절대경로를 눈으로 확인
systemctl --user list-units --all | grep -i quantbridge   # failed 가 없어야 한다
```

★2026-08-18 [BL-805] 전까지 **위 표 2행(`quantbridge-api.service`)에는 점검 수단이 없었다** —
레포에 그 유닛을 만드는 코드가 0건이라 「무엇과 대조할 현재본」 자체가 없었기 때문이다.

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

> **2026-08-21 — 94.6KB 였던 이 절을 주제별 4파일로 나눴다**([ADR-038](../adr/038-docs-top-level-by-question.md) 후속).
> 본문은 전부 옮겼고 여기는 색인만 남는다. 원문 위치 = `git show 9e91809c:docs/development/gates-and-traps.md` L271-1065.
> 새 함정은 **주제가 맞는 파일에** 적는다 — 이 절에 본문을 다시 쌓지 마라.

| 파일                                                         | 다루는 것                                                                                                         | 절                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`traps-environment-shell.md`](./traps-environment-shell.md) | 로컬 환경·셸·캐시·린트가 게이트를 거짓 red/green 으로 만드는 조건                                                 | 환경 · 셸·게이트가 거짓 red 를 내는 경로 (2026-07-28) · 린트가 잡는 문자 · 언어·타입 · 게이트가 **거짓 red** 를 내는 경로 (2026-07-27 live-conditional-hardening) · 캐시·주기 (2026-07-27 live-conditional-hardening)                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| [`traps-ci-e2e.md`](./traps-ci-e2e.md)                       | CI 와 로컬의 차이, 샤딩, e2e 통합·재현, authed 증거, FE 스키마 대조                                               | ★★CI 와 로컬은 같은 명령이어도 **같은 env 가 아니다** (2026-08-01, 실측 5건) · CI pytest 샤딩 (2026-08-06 ci-diet) · e2e spec 을 통합할 때 (2026-08-06 e2e-consolidation) · e2e 가 게이트에서만 red 일 때 — 증거를 남기고 조건을 재현하는 법 ([BL-784], 2026-08-17) · CI 초록은 **authed 통과의 증거가 아니다** ([BL-789], 2026-08-17) · 신규 BE 필드는 FE `.strict()` 스키마와 **항상** 대조해라 (2026-07-30, codex 적대 리뷰 MAJOR)                                                                                                                                                                                                                                                        |
| [`traps-gates-measurement.md`](./traps-gates-measurement.md) | 조용히 통과하는 명령, 측정 도구가 먼저 틀리는 경우, 게이트가 「돌렸다」만 보증하는 경우, 변이·추론·git 으로 셀 때 | 조용히 통과한 것처럼 보이는 것 · 검증이 무언가를 증명하지 못하는 세 가지 방식 (2026-07-28 live-outcome-parity, 한 스프린트에서 3회) · 수정이 새 표면을 만든다 (2026-07-28) · 통계 게이트 (2026-07-28) · 측정 도구가 먼저 틀린다 (2026-07-30 — 한 회차에 **6번**) · 측정 도구가 먼저 틀린다 (2026-07-30 close-mismatch-soak — 또 **2번**) · 게이트가 "돌렸다" 만 보증한다 (2026-07-30) · ★★스위트 결과가 **수집 집합**에 달려 있었다 (2026-08-03 gate-trustworthiness, BL-583) · 죽은 의존성을 걷어낼 때 (2026-08-06 dead-code-sweep) · 측정 도구가 먼저 틀린다 (2026-07-28) · git 으로 세거나 「안전하다」고 말할 때 (2026-08-12 branch-debris) · 변이 검증 (2026-07-27) · 추론 (2026-07-27) |
| [`traps-live-trading.md`](./traps-live-trading.md)           | 라이브 신호 도메인, 거래소 실상, 원장을 읽을 때, 함대·계측, 계기                                                  | 라이브 신호 도메인 · 거래소 실상 (2026-07-28 live-entry-parity, 실거래소 실측) · 원장을 읽을 때 (2026-07-30 close-mismatch-visibility) · 함대·계측 함정 (2026-07-31 reversal-ledger-sync) · 계기(instrument) — 어떤 상품의 가격을 보고 있는가 (2026-07-28)                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## 3.5 컨텍스트 예산 — 세션이 새는 두 채널

> 2026-07-28 승격. 직전 회차가 이 규칙을 **참조는 했으나 이 파일에 없었다** — 핸드오프가 "여기 있다" 고 적었지만 실제로는 없었고, 이번에 실제로 넣는다.

- ★**서브에이전트는 파일이 아니라 상한으로 답한다.** 이 저장소의 읽기 전용 서브에이전트(`Explore`)는 **Write 도구가 없다.** "리포트를 파일에 써라" 는 지시는 실패하고 전문이 반환값으로 돌아온다(단일 최대 소모원). **반환값 줄 수 상한을 명시해라** — "30줄 이내 / 발견마다 3줄 / 코드 덤프 금지" 가 실제로 먹는다.
- ★**Monitor 는 변화 감지가 아니라 위험 신호 + 하트비트다.** 즉시 발화는 **작업을 죽이는 사건만**(세션 비활성화 · kill switch · DNS 실패). 진행 상황은 **10~15분 하트비트 1줄**. 판단 기준 = _"이 발화를 보고 내가 뭘 할 것인가?"_
- worker 로그 전문 금지 — `grep -c` / `sort | uniq -c` 집계만.
- 문서 파일은 `head`/`sed -n` 에 **`cut -c1-200`** 을 붙여라. 이 저장소 dev-log·backlog 는 행 하나가 3,000자다.
- ★**codex 산출물(`*-codex.txt`)은 tool-trace 가 수십만 줄이다.** 최종 답변만 뽑아라 — `awk '/^\[P[123]\]/{f=1} f'` 같은 패턴으로 자른다. 통째로 읽지 마라.

## 4. pre-push 훅

`.husky/pre-push` 는 **ref 가드 하나만** 한다 ([ADR-037] 2026-08-19 — 품질 검사부는 철거,
원문 = `git show harness-v1:.husky/pre-push`). CI 가 품질을 단독 판정한다.

- `main` / `master` push **영구 차단** (bypass 불가)
- `stage/*` `feat/*` `fix/*` `chore/*` `docs/*` `test/*` `refactor/*` `hotfix/*` 만 허용.
  그 외 임의 브랜치는 차단 + bypass 안내 (판정 순수 함수 = `tools/scripts/lib/pre-push-ref-guard.sh`)
- 판정 대상은 현재 브랜치가 아니라 **실제로 미는 ref** 다 ([BL-554]·[BL-555])
- ~~`apps/web/` 변경 시 `pnpm typecheck && pnpm test`~~ ~~`apps/api/` 변경 시 `ruff`·`mypy`~~
  ~~`.env.local` 의 `TEST_` 접두 자동 export~~ → **전부 철거됐다. push 는 품질을 안 본다.**

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
