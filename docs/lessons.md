# Lessons Learned

> AI가 실수를 교정받을 때마다 이 파일이 업데이트됩니다.
> 반복 패턴(3회)은 스택 규칙(`backend/AGENTS.md`·`frontend/AGENTS.md`) 또는 해당 정본 축(ADR-026 7축)으로 승격, 본 파일에는 1-line reference 만 보존합니다.
> 승격 경로(구 global.md §6): dev-log 반증 카드 → 본 파일 (3회 반복) → 스택 `AGENTS.md` 또는 정본 문서 → 삭제(모델 개선으로 불필요 시).

---

## 작성 규칙

- 새 교훈은 `## LESSON-{NNN} — {제목}` 포맷으로 추가
- 반복 패턴이 동일하면 새 항목 만들지 말고 기존 항목의 **반복 횟수** 증가
- 반복 3 이상이면 승격 대상 (target rule file 명시)
- 승격 완료 시 본문 삭제 + §영구 승격 table 1-line 추가
- 본 파일 한계 **400 lines** — 초과 시 stale 항목 archive 정리 의무

---

## 영구 승격 완료 (rule file로 이전된 항목)

> 본문은 해당 rule file에 있음. 본 파일은 reference table 만 유지.

| ID         | 승격 위치                              | 한 줄 요약                                                                                                                    |
| ---------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| LESSON-004 | `frontend/AGENTS.md` §3 H-1            | `useEffect` dep 에 React Query data / Zustand selector / RHF watch / Zod parse 결과 사용 금지 (CPU 100% loop)                 |
| LESSON-005 | `frontend/AGENTS.md` §3 H-2            | `queryKey` 는 `userId` identity 사용 — Clerk `getToken` 직접 포함 금지                                                        |
| LESSON-006 | `frontend/AGENTS.md` §3 H-3            | React Compiler 호환 — render body 에서 `ref.current = value` 금지, deps-less `useEffect` 로 이동                              |
| LESSON-019 | `backend/AGENTS.md` §3                 | Service mutation 메서드는 `tests/<domain>/test_*_commits.py` 의 AsyncMock spy 회귀 의무 (broken-bug 3 회 재발 차단)           |
| LESSON-020 | `backend/AGENTS.md` §9.2               | Module-level `asyncio.<Semaphore/Lock/Event/Queue>` 추가 시 AST audit + allowlist 의무                                        |
| LESSON-037 | `generator-evaluator-pipeline.md` §8.1 | Sprint kickoff 첫 step = baseline 재측정 preflight 의무 (Type A 의무 / B 권장 / C/D 면제)                                     |
| LESSON-038 | `generator-evaluator-pipeline.md` §8.2 | Docker worker auto-rebuild on PR merge 의무 + sentinel function startup health check                                          |
| LESSON-039 | `generator-evaluator-pipeline.md` §8.3 | Surface Trust 차단 (UI false positive) ≠ 기능 작동 (BE 정확 계산). 두 mechanism 분리 의무                                     |
| LESSON-040 | `generator-evaluator-pipeline.md` §8.4 | codex G.0 직후 + Sprint 진입 전 = rapid prereq verification spike (10-30분) 의무                                              |
| LESSON-063 | `generator-evaluator-pipeline.md` §8.5 | 신규 도메인 / 5+ 파일 모듈 신설 직후 = `/deepen-modules` 1 호출 (Iron Law: 1 모듈만) 권장                                     |
| LESSON-066 | `backend/AGENTS.md` §7                 | alembic enum = 처음부터 uppercase + downgrade enum swap 의무 (SAEnum/StrEnum 정합, 7차 영구 검증 — dev-log 삭제 전 등재 보충) |

---

## Archived (2026H1)

> tombstone: LESSON-001~068 중 46건의 본문을 [lessons-archive-2026H1.md](archive/lessons-archive-2026H1.md) 로 이동 (원문 = 커밋 fc1854d5 의 docs/lessons.md).

| ID         | 한 줄 요약                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| LESSON-001 | 사용자 Pine을 Python으로 동적 실행하면 코드 인젝션이므로 AST 인터프리터와 eval/exec 금지가 필요하다.    |
| LESSON-002 | Celery OOM·crash 뒤 running으로 남는 좀비 task는 실패 훅·정기 정리·수동 취소 3층으로 복구한다.          |
| LESSON-003 | Pine 파싱률 80% 이상 가정을 버리고 검증된 40% 패턴 지원과 투명한 Unsupported 처리를 택한다.             |
| LESSON-007 | worktree의 git top-level은 main이 아닌 worktree 경로이므로 공통 git dir 또는 명시 경로를 쓴다.          |
| LESSON-008 | Signal·IPC 식별자는 prefix를 포함한 full id로 고정하고 Monitor가 실제 signal 파일명을 검증한다.         |
| LESSON-009 | Worker가 worktree 밖 main repo에 파일을 만들지 않도록 생성 경로를 worktree 내부로 제한한다.             |
| LESSON-010 | stage worktree 생성 직후 backend .venv와 root·frontend node_modules 3개 symlink를 연결한다.             |
| LESSON-011 | RedisLock의 빈 async with는 mutex가 아니며 correctness는 PG advisory lock과 UNIQUE로 보장한다.          |
| LESSON-012 | slowapi 0.1.9 조합 오류는 request.state.view_rate_limit 선초기화 middleware로 막는다.                   |
| LESSON-013 | worktree symlink 상대 경로는 링크 위치 기준이므로 3단계 prefix와 ls -L 검증이 필요하다.                 |
| LESSON-014 | rate-limit endpoint의 ConnectionError를 막으려면 conftest에 모든 필수 env 기본값을 넣는다.              |
| LESSON-015 | Redis DB 0~2는 cache·Celery가 쓰므로 분산 락과 rate-limit은 DB 3 이상으로 분리한다.                     |
| LESSON-016 | Next.js 16의 edge middleware 파일명은 middleware.ts가 아니라 proxy.ts이며 실파일을 확인한다.            |
| LESSON-017 | codex Generator-Evaluator 루프는 plan 작성 직후 G0 consult로 critical을 반영한 뒤 시작한다.             |
| LESSON-018 | Heavy G-E 루프는 sprint scope를 실측보다 30~50% 키우므로 tier와 G4 반복 상한을 정한다.                  |
| LESSON-026 | **init**.py re-export와 충돌하는 import a.b.c alias는 sys.modules 우회로 module을 참조한다.             |
| LESSON-027 | \_WORKER_LOOP task의 inner 함수는 pytest-asyncio 호환을 위해 async 함수를 직접 await한다.               |
| LESSON-028 | PostgreSQL JSONB에는 NaN·Infinity를 넣을 수 없으므로 재귀 sanitize로 None 변환을 의무화한다.            |
| LESSON-029 | SQLAlchemy enum 자동 cast와 Alembic String 불일치를 피하려면 모델·migration 모두 String을 명시한다.     |
| LESSON-030 | Bybit v5 leverage·margin mode의 not modified BadRequest는 provider 한정으로 idempotent 처리한다.        |
| LESSON-031 | Bybit Linear 계약 symbol은 UI의 BTC/USDT를 ccxt unified BTC/USDT:USDT로 normalize한다.                  |
| LESSON-032 | base-ui Select.Value의 raw ID 노출은 render prop으로 lookup name을 매핑해 해소한다.                     |
| LESSON-033 | Sprint type A~D를 kickoff에서 분류해 신규 기능·BL·hotfix·docs 작업의 의무 강도를 다르게 둔다.           |
| LESSON-034 | 3개월 이상 경과하고 dogfood 증거가 누적되면 office-hours를 재진행해 ADR addendum으로 보존한다.          |
| LESSON-035 | sprint 종료는 self-assess·신규 BL·기존 P0 감소의 세 dual metric을 모두 만족해야 한다.                   |
| LESSON-036 | Slice cascade는 stage branch를 base로 각 slice와 cleanup PR을 쌓고 사용자가 main에 병합한다.            |
| LESSON-041 | Pine strategy의 default_qty_type·value가 한쪽만 있으면 ambiguous하므로 422로 거절한다.                  |
| LESSON-042 | Live mirror position_size_pct와 manual default_qty를 함께 주면 422로 단일 sizing source를 강제한다.     |
| LESSON-043 | engine이 1x equity basis뿐일 때 live leverage Nx는 422로 막고 manual sizing 경로를 제공한다.            |
| LESSON-044 | 메인 세션은 표준 prefix, worktree worker는 worker-\* prefix를 써 pre-push와 작업 대상을 구분한다.       |
| LESSON-045 | 다른 프로젝트 포트 충돌을 막으려면 isolated mode와 테스트 DB·Redis URL inline override를 사용한다.      |
| LESSON-046 | 통합 dogfood는 G-E가 놓친 회귀를 idle CPU·base delta·navigate 변화 세 신호로 발견한다.                  |
| LESSON-047 | Turbopack root를 잘못 지정하면 watcher storm이 나므로 lockfile 위치·fresh restart·idle CPU를 검증한다.  |
| LESSON-048 | Playwright MCP 인증 cookie dogfood는 2/3 누적이며 자동화가 어려운 검증만 사용자에게 위임한다.           |
| LESSON-049 | codex G.4의 P1/P2는 cmux signal reset과 즉시 fix를 우선하고 영향 없을 때만 defer한다.                   |
| LESSON-050 | 디자인 sprint kickoff에는 prototypes·DESIGN·pen·Figma URL을 모두 grep해 design source를 명시한다.       |
| LESSON-051 | agent worktree를 4개 spawn하기 전 dev server·Docker·install·prune baseline을 정리한다.                  |
| LESSON-052 | Worker prompt 첫 단계에 pwd와 worktree cwd 검증을 넣어 메인 cwd면 즉시 중지시킨다.                      |
| LESSON-053 | N=4 이상에서 agent tool isolation 한계가 드러나므로 독립 terminal·signal 가능한 cmux를 우선한다.        |
| LESSON-054 | 핀테크 다크 테마는 유행보다 mental model 일관성을 우선하고 single-page 다크 회피를 검증한다.            |
| LESSON-055 | Worker prompt에 첫 명령으로 절대 worktree path cd를 사전 명시해 main에서의 작업을 막는다.               |
| LESSON-062 | ADR 결정이 AGENTS.md 표현과 어긋나면 ADR을 SSOT로 삼아 동시에 정합시킨다.                               |
| LESSON-064 | /deepen-modules audit의 silent failure는 3/3 누적이며 직접 read와 전체 dispatch 경로 추적으로 판정한다. |
| LESSON-065 | 2단계 subagent review는 monkeypatch 간접 의존성을 놓칠 수 있어 실제 dependency reach를 확인한다.        |
| LESSON-067 | codex evaluator 분산형은 6/6 검증됐고 비용은 revision 양·트랙 수에 따른 scope 함수로 계획한다.          |
| LESSON-068 | 한국어 docs lint 부재는 §5·§6 위반을 누적시키며 lint·hook·헤더 보강은 1/3 누적이다.                     |

---

## Active Candidates (3 회 검증 미달, 또는 sprint-specific)

### LESSON-069 — 저-카디널리티 라벨이 **위험도가 다른 갈래**를 합치면 큰 갈래가 작은 갈래를 묻는다 (1/3)

- **상황:** 2026-07-30 close-mismatch-visibility. `metrics.py` 가 Bybit `110017` 을 단일
  `reduce_only_violation` 으로 접었다. 실측 39건 = `reduce-only ... same side`(★엔진↔거래소
  **반대 방향**, 머니-패스 위험) **9건** + `current position is zero`(무해) **30건**.
  무해가 3배라 counter 를 보면 "유령 포지션 문제" 로만 보이고 **방향 반전은 보이지 않았다.**
  위험 갈래는 **5개 세션에 걸쳐 반복 발생** 중이었다.
- **원인:** 카디널리티 보호를 위해 retCode 로만 매핑했다. 그런데 `gates-and-traps.md:104` 와
  `live-close-diagnostics.md` §2 가 **이미 "코드로만 묶지 마라, retMsg 까지 갈라라" 고 적어 뒀는데**
  코드가 그 경고를 지키지 않았다. 문서가 경고를 적는 것과 코드가 지키는 것은 다른 사건이다.
- **해결:** 코드 확정 **뒤** 그 안에서만 retMsg 로 갈래를 가른다(코드 판정에는 retMsg 를 쓰지 않는
  BL-512 원 제약은 유효). 잔여 버킷을 남겨 미지 문구가 조용히 사라지지 않게 한다.
- **일반 규칙 후보:** **저-카디널리티 라벨을 만들 때 "이 버킷 안의 두 값이 서로 다른 조치를
  요구하는가" 를 물어라.** 요구한다면 그 코드는 라벨이 될 수 없다. 그리고 **큰 갈래가 작은 갈래를
  묻는 방향**(무해가 다수, 위험이 소수)이면 평균이 안전을 말하게 된다.
- **1차 누적.** 3회 시 영구 규칙 승격 후보 (`generator-evaluator-pipeline.md` §8).

### LESSON-070 — 비중(%)을 인용하기 전에 **분모가 무엇을 세는지** 코드로 확인해라 (1/3)

- **상황:** 같은 회차. 직전 스프린트가 `deferred_market_inflight` 를 "유실 채널 합의 **75%**" 로
  적었고 그 위에 다음 스프린트를 설계했다. 실측 — 그 counter 는 `bool(new_events)` 로 오르는데
  `new_events` 는 `entry`/`close` **시장가 이벤트만** 담고 **조건부 진입은 그 테이블을 거치지 않는다.**
  즉 stop-entry 전략에서 그 값은 **「청산 tick 수」** 이고, 세션 실측에서 events 9건(전량 `close`)과
  counter 9 가 **1:1** 이었다. 게다가 증가 지점이 `desired` 를 **읽기 전**이라 미룰 진입이
  0건이어도 발화한다.
- **해결:** 비중을 쓰기 전에 (a) 분자·분모가 **같은 사건 단위**인가 (b) 그 counter 가 증가하는
  **코드 위치가 무엇을 이미 알고 있는가** 를 확인한다. 후자가 이번의 결정타였다 — 증가가
  판정 대상보다 **앞**에 있으면 그 counter 는 판정에 대해 아무것도 모른다.
- **1차 누적.**

### LESSON-071 — 합계가 닫힌다는 것은 귀속이 옳다는 증거가 아니다 (1/3)

- **상황:** 2026-08-06 backtest-reality-gap. 원장 event 를 라이브 진입에 귀속하는 두 방식
  (시간순 FIFO vs 직결 링크)이 86건 중 59건에서 서로 다른 주문을 골랐는데, **양쪽 모두**
  버킷 합이 dedup Σ(−149.85)와 소수 8자리까지 닫혔다. 닫힘은 「한 번씩 세었다」의 성질이지
  「맞는 곳에 붙였다」의 성질이 아니다. 틀린 귀속 위의 「가격 격차 +19.36」은 옳은 귀속에서
  **부호까지 바뀌었다**(+28.35 — 중간 반사실은 −0.36).
- **해결:** 귀속 있는 집계는 3층으로 검증한다 — ⑴ 합계 닫힘 ⑵ 귀속 근거 분포(linked/inferred)
  ⑶ **행별 독립 판별자**(이번엔 event 의 진입가 ↔ 귀속된 주문의 체결가 대조, 80/81 exact).
  합은 telescoping 이라 계열 전체가 한 칸 밀려도 못 본다 — 행별 대조만이 가른다.
- **1차 누적.**

### LESSON-072 — 사전등록 지표는 등록 전에 「기각 영역이 도달 가능한가」를 그려라 (1/3)

- **상황:** 같은 회차. 사전등록 ③(비용 설명 비율 ≥40%, Σ 후 절대값)이 실데이터에서 **거의
  항진명제**였다 — FAIL 영역이 Σdiv > +253 / < −590 뿐(라이브 총손익의 9배 규모)이고 상한이
  없어 134%·3095% 도 「PASS」로 읽힌다. 부호 상쇄 때문에 같은 총발산에서 밖-abs 정의는
  49%~3095%(63배) 흔들린다(행별-abs 는 2.7배). 판정은 「미판정 + 정의 결함 병기」로 강등했다.
- **해결:** 비율 지표는 ⑴ 분자·분모의 상쇄 구조(Σ 후 abs vs 행별 abs)를 등록 전에 정하고
  ⑵ 상·하한을 구간으로 걸고 ⑶ 등록 직후 적대 검증자에게 **기각되는 관측 공간**을 그리게
  한다 — 기각 영역이 물리적으로 원격이면 그 지표는 적중해도 증거가 못 된다.
- **1차 누적.**

### LESSON-074 — 검사 도구를 **그 트리 밖에서** 겨누면 ignore 규칙이 대상을 통째로 삼킨다 (1/3)

- **상황:** ADR-027 회차에서 prettier 검증을 레포 루트에 서서 워크트리 경로
  (`.claude/worktrees/fix-doc/docs/*.md`)로 돌렸다. prettier 3.x 의 기본
  `ignorePath` 는 `[".gitignore", ".prettierignore"]` 이고 `.gitignore` 에 `.claude/*` 가 있어
  **0개 파일이 검사됐다.** 그런데 출력은 `All matched files use Prettier code style!` —
  ★**존재하지 않는 파일을 줘도 같은 문장이 나온다.** 그 근거로 「prettier clean」을 3회 보고했고
  전부 거짓이었다(트리 안에서 재실행하니 위반 4파일).
- **왜 안 걸렸나:** 성공 메시지가 「검사했고 통과」와 「검사할 게 없었다」를 **구별하지 않는다.**
  같은 회차에 [BL-616](backlog.md) 으로 pre-commit 훅까지 안 돌고 있었으므로 2차 방어도 없었다.
- **해결:** ⑴ 검사는 **그 트리 안에서(cwd 를 옮겨) 상대 경로로** 실행한다 ⑵ 성공 메시지 대신
  **검사한 개수**를 확인한다 — 없으면 **존재하지 않는 경로를 대조군**으로 넣어 같은 출력이 나오는지
  본다(1분이면 판별된다) ⑶ ignore 규칙을 가진 도구(prettier · eslint · ruff · grep --exclude)는
  **대상 경로가 ignore 대상인지부터** 묻는다.
- **1차 누적.** ★이 레포의 반복 주제와 같은 축이다 — 「전체에서 가드 발화 0」은 창이 닫혀 있으면
  아무 증명도 아니고, **적중은 판별 표면이 아니다.**

### LESSON-073 — 문서를 정규식으로 수술할 때 링크 매치는 줄 경계를 강제하라 (1/3)

- **상황:** docs 대개편(fix-doc)에서 `\[[^\]]*\]\(([^)]+)\)` 로 링크를 일괄 강등하다 `[UTC 자정, +1d)`
  처럼 짝 없는 대괄호가 매치를 열어 **개행을 넘어 30줄(BL-451/452 전체)을 삼켰다**. docs-audit 는
  링크 실존만 보므로 못 잡았고, bl-audit 총계 감소(172→170)로만 드러났다.
- **해결:** ⑴ 문자클래스에서 개행 제외(`[^\]\n]*` / `[^)\n]+`) ⑵ 수술 전후 불변량(섹션 수·헤딩
  목록)을 기계 대조 ⑶ 복구 판정은 **수술 당시와 같은 디스크 상태 기준**이어야 한다 — 삭제 후에
  돌린 복구가 `is_dir()` 의존 판정으로 정당한 변경까지 되돌렸다(오탐 3파일).
- **1차 누적.**

### LESSON-075 — 「미룬다」를 판정 자리에 넣으면 그 판정은 다시 안 온다 (1/3)

- **상황:** 2026-08-07 [BL-622]. 공백 재동기 판정이 원장보다 먼저 뛰어 정상 세션을 죽였고,
  수리는 「미확정 주문이 있으면 판정을 미룬다」였다. 자연스러운 자리는 판정 직전
  (`_positions_are_aligned` 앞)인데, 거기서 `return` 하면 **이미 지나온 `try_claim_bar` 가
  `last_evaluated_bar_time` 을 전진시켜 놓은 뒤**다. 다음 tick 의 공백은 5분 임계 안으로 줄고
  `requires_gap_resync` 는 **다시는 True 가 안 된다** — 세션은 낡은 엔진 포지션을 든 채 조용히
  계속 돈다. 죽는 것보다 나쁜 상태를 「수리」로 만들 뻔했다.
- **해결:** 되돌릴 수 없는 상태 전진(claim·워터마크·epoch)이 판정과 `return` 사이에 있으면
  **미루기는 그 전진 앞으로 옮긴다.** 옮길 수 없으면 전진을 되돌리거나 sticky 플래그로 재진입을
  강제해야 하는데, 둘 다 새 상태를 만든다 — 자리를 옮기는 쪽이 언제나 싸다. 회귀 단언은
  결과값이 아니라 **「그 전진 함수가 안 불렸다」**여야 한다(`try_claim_bar.assert_not_awaited()`).
- **1차 누적.** ★★★**이 카드의 초판 결론이 리뷰에서 반증됐다.** 처음엔 「상한은 새 상수로
  만들지 마라 — 이미 있는 `_SCAN_STUCK_THRESHOLD_MINUTES`(30분)를 재사용했다」로 닫았다.
  그러나 그 상수는 **다른 양을 재는 자**였다: janitor 문턱은 「주문이 얼마나 오래 고착됐나」인데
  내게 필요한 것은 「**내가 몇 번 미뤘나**」였다. 실측이 그 차이를 드러냈다 — 조건부 진입은
  트리거를 기다리며 정상적으로 쉬므로 **벽시계의 95.1%** 를 덮고(118건·평균 563초), 나이로
  끊으면 「거의 항상 미룰 수 있음」이 되어 진짜 발산까지 30분 미뤄진다. ⇒ **재사용의 대가는
  「새 상수를 안 만든 것」이 아니라 「틀린 양을 잰 것」이다.** 상한을 미룬 횟수(3 tick)로
  바꿨고, 그러느라 감수한 상태 1개(JSONB 카운터)가 정직한 값이었다.
  **교훈은 뒤집힌다 — 상수를 재사용하기 전에 그 상수가 재는 양이 내가 재려는 양과 같은지 물어라.**

### LESSON-076 — 같은 값의 리터럴이 둘이면 「기본값을 바꿨다」가 거짓이 된다 (1/3)

- **상황:** 같은 회차 [BL-603]. 백테스트 비용 기본값이 엔진(`engine/types.py`)과 API 스키마
  (`backtest/schemas.py`)에 **같은 숫자의 별개 리터럴**로 있었다. Pydantic 기본값은 요청에
  값이 없어도 **항상 채워지므로**, 엔진만 고치면 골든·내부 호출만 바뀌고 **사용자 제출 경로는
  옛 값을 그대로 쓴다.** 두 SSOT 가 어긋난 채 「비용 가정을 실측으로 고쳤다」가 됐을 것이다.
  화면 쪽에도 같은 값의 미러가 **4곳**(폼 기본값 · 카드 상수 · 재실행 fallback · 안내 문구)
  있었고, 그중 재실행 fallback 은 사전 조사가 놓쳤다 — 직접 grep 해서 찾았다.
- **해결:** 기본값을 옮길 때는 ⑴ 그 값의 **리터럴 전수**를 먼저 세고(주석·안내 문구 포함)
  ⑵ 「이 경로로 들어오면 어느 리터럴이 이기나」를 실행으로 확인한다(요청 객체를 실제로 만들어
  기본값을 찍어봤다) ⑶ **런타임에 읽는 소비자**(여기선 `_house_default_assumption()`)와
  **복사해 둔 미러**를 구분한다 — 전자는 따라오고 후자는 안 따라온다.
- **1차 누적.** ★숫자만 고치고 산문을 두면 화면이 반증된 주장을 계속 한다 — 테스트 **이름**에도
  옛 주장이 박혀 있었다(`..._match_bybit_taker_standard`).

### LESSON-079 — 관측량이 **0** 이 되면 먼저 「관측 대상이 살아 있나」를 물어라 (1/3)

- **상황:** 2026-08-07 backtest-fidelity. A-1 카운터가 21분간 **완전히 멈췄다**(세 번 읽어 동일값).
  내 첫 해석은 **「발화가 버스트라 표본이 안 모인다」**였고, 그래서 창을 더 키우려고 대기했다.
  실제로는 소크 세션이 그 사이 **`position_divergence` 로 자동 사망**해 있었다 — 이벤트를 만들 주체가
  없어졌으니 카운터가 0인 것이 당연했다. 소크 게이트를 돌려보고서야 알았고, 그때는 이미
  「소크 무중단」이라고 적은 문서가 세 개였다.
- **해결:** 관측량이 예상보다 낮거나 0 이면 **분자를 더 기다리기 전에 분모의 생존을 확인**해라.
  이 레포는 그 규율을 이미 갖고 있다 — `status.md` 의 「**③④가 방어선이다. ③이 무너지면 기계가 멈춘
  것이지 고쳐진 게 아니다**」. 그 문장은 사전등록 표 안에 있었고, **사전등록 표를 안 쓴 이번 측정에는
  그 방어선이 없었다.** ⇒ 사전등록 표를 안 쓰더라도 **양성 대조 한 줄은 항상 붙여라**
  (여기서는 「세션이 살아 있는가」).
- **1차 누적.** ★부수 — 「소크 무중단」은 **회차 시작 시점의 사실**이었고 회차 도중 거짓이 됐다.
  **긴 회차의 문서는 쓰는 시점과 참인 시점이 다르다** — 소크·배포처럼 회차 밖에서 움직이는 것은
  **커밋 직전에 다시 재라.**

### LESSON-080 — 사전등록한 문턱은 **그 문턱이 막을 때** 값을 한다 (1/3)

- **상황:** 같은 회차 A-1. 착수 전에 `D < 30 ⇒ 판정 불가`(rule of three, `3/30 = 10%`)를 동결했다.
  창이 준 것은 `N=3 / D=24` 였다. 문턱이 없었다면 **`3/24 = 12.5%` 를 「백테스트가 현실을 얼마나
  예측하나」의 첫 실측치**로 적었을 것이고, 그 숫자는 `status.md`·`dev-log`·`INDEX`·보고서로 복제돼
  다음 회차의 기준선이 됐을 것이다. n=24 에서는 참값이 10% 문턱 밖이어도 이 표본이 나온다.
- **해결:** 문턱은 **측정 전에** 박고, **발화하면 그대로 따라라.** 문턱이 한 번도 안 막으면 그것은
  「통과했다」가 아니라 **「그 문턱이 판별력이 있는지 아직 모른다」**이다. 이번은 반대로 **첫 적용에서
  막았고**, 그것이 이 회차 A-1 의 실질 산출이다 — 값이 아니라 **값을 안 적은 것**이 산출이다.
- **1차 누적.** ★같이 지켜야 하는 것 — **분해도 인용하지 마라.** 형A 18 · 형B 3 은 같은 표본에서
  나온다. 「비율은 판정 불가지만 분해는 인상적이다」로 새면 문턱을 우회한 것이다.

### LESSON-077 — 원인이 둘인데 축을 하나씩 되돌리면 **전건 미확정**으로 떨어진다 (1/3)

- **상황:** 2026-08-07 backtest-fidelity, [BL-621]. 골든 `expected.json` 의 손익 3지표가 낡았는데
  원인이 무엇인지가 물음이었다. BL 본문은 「비용 기본값([BL-603]) 교체 **전** 값으로 돌려도 안 맞는다」를
  근거로 "이번 회차 이전부터 낡았다"까지만 적어 두고 멈춰 있었다. 이번 회차의 codex 워커도 같은 실험을
  반복해 같은 값(`-0.000979728…`)을 얻고 **「⑵ 후보까지 좁혔으나 미확정」**으로 보고했다.
  **같은 관측이 두 번 「미확정」을 만들었다.** 실제 원인은 **둘**이었다 — ⑴ `cda575f2` 의
  `ta.atr` rolling SMA → Wilder RMA ⑵ 비용 기본값 인하. **두 축을 동시에** 되돌리자
  `total_return`·`max_drawdown`·`win_rate`·`num_trades` 가 **전건 byte-identical** 로 재현됐다.
- **해결:** 「낡은 기준값이 왜 그 값인가」를 물을 때는 후보 축을 **하나씩**이 아니라 **곱집합**으로 재라.
  축이 k개면 조합은 2^k 이고, 여기서는 4개 조합 중 **3개가 불일치**라 한 축씩만 보면 전부 기각된다.
  축을 되돌리는 비용이 싸야 이게 가능하다 — 체크아웃 대신 **그 함수 하나만 monkeypatch** 하면
  워킹 트리를 안 건드리고 조합을 다 돌 수 있다.
- **1차 누적.** ★부수 교훈 하나가 더 있다 — 이 골든이 유일하게 assert 하던 값 `num_trades` 는
  **네 조합 전부 14** 였다. **판별력 0 인 값 하나를 보고 있으면 「테스트가 있다」가 「감지된다」를
  뜻하지 않는다.** 비용은 체결 **집합**을 안 바꾸고 손익만 바꾼다(같은 성질이 [BL-603] 코퍼스
  재생성에서도 관측됐다 — `num_trades` 7 코퍼스 전건 불변).

### LESSON-078 — 아무도 부르지 않는 검사기는 **죽은 줄도 모르고** 죽는다 (1/3)

- **상황:** 같은 회차 갈래 B. `runtime-check.mjs`(프로토타입 대비·포커스·오버플로 검사기)를
  「캘리브레이션된 임계값을 물려받는 자산」으로 전제하고 재조준을 지시했는데, 실제로는
  `docs/` 재편 커밋 `fcc36bf7` 이 파일을 두 단계 깊은 곳으로 옮기면서 playwright import 의 상대
  깊이가 안 따라와 **`ERR_MODULE_NOT_FOUND` 로 즉사**하고 있었다. ⇒ 핸드오프에 적힌
  **「다크 17벌 17/17 PASS」는 그 커밋 이후 한 번도 재현된 적이 없는 숫자**였다. 그 사이 라이트
  테마는 **WCAG AA 하드 실패 116건**(공개 4라우트)을 실은 채 배포돼 있었고, 검사기가 살아 있었어도
  못 봤다 — 그 도구는 **프로토타입 html 만** 겨누고 앱을 한 번도 안 봤기 때문이다.
- **해결:** 검사기를 만들면 **부르는 자리**를 같은 커밋에 만들어라(`pnpm test` 스크립트 · CI 잡 ·
  `docs-audit` 의 기동 확인 중 하나). 부르는 자리가 없으면 파일 이동 한 번에 조용히 죽고,
  그 도구가 산출한 **과거 숫자가 문서에 살아남아** 현재 상태로 읽힌다. 그리고 검사기의 **대상**이
  실물인지 프록시인지 문서에 적어라 — 프로토타입 통과는 앱 통과가 아니다.
- **1차 누적.** ★이 레포는 같은 계열을 이미 한 번 적었다(LESSON-074 — 검사 도구를 그 트리 밖에서
  겨누면 ignore 규칙이 대상을 통째로 삼킨다). **「도구가 무엇을 실제로 보고 있나」를 재는 습관**이
  두 번째로 값을 했다.

### LESSON-081 — 「무관하다」는 **공유 자원을 전부 세고 나서** 말해라 (1/3)

- **상황:** 2026-08-07 backtest-fidelity 회차가 서버 소크 세션 `39484a2c` 의 자동 사망을
  **「이 회차와 무관하다」**로 적었다. 근거는 서버 HEAD 불변 · 고정 커밋 불변 · 배포 0건 ·
  독립 클론이었고 **셋 다 참이었다.** 그런데 결합은 코드가 아니라 **거래소 계정**이었다 —
  서버 세션과 맥 로컬 세션 `fcf1dcbe` 가 같은 `exchange_account_id` · 같은 `BTC/USDT` ·
  같은 `1m` · 같은 `strategy_id` 로 **동시에** 돌고 있었다. 두 호스트는 각자 DB 를 가지므로
  `live_signal_sessions` 의 unique index 는 **각 DB 안에서 정상 성립했고**, 둘을 합친 상태를
  아는 주체가 없었다. 2026-08-08 회차가 두 원장을 대조해 뒤집었다 — 서버 `exchange_exits` 의
  고유 `order_link_id` 27 중 **7 건이 로컬 원장에만** 있고 귀속 불가는 0 이다.
- **해결:** 「무관하다」를 쓰기 전에 **두 실행이 공유할 수 있는 자원을 목록으로 적고 하나씩 지워라**
  (코드·커밋 / DB / 거래소 계정 / 심볼·주기 / 캐시 / 포트 / 파일락). 코드 축만 확인한 「무관」은
  **그 축에 한해서만** 참이고, 문서에는 축을 명시해서 적어야 다음 사람이 확대해석하지 않는다.
  배타성은 **가장 바깥 공유점**에서 재라 — 여기서는 DB 가 아니라 거래소 쪽 상태다(신규 BL-634).
- **1차 누적.** ★부수 — 오염은 소크 세션보다 **먼저** 시작돼 있었다(로컬 체결이 세션 생성
  이전에 5건). **재기동 시점 검사만으로는 늦다** — 배타성 preflight 는 세션을 만들기 **전에** 건다.

### LESSON-082 — 잔차를 설명하는 식에 **그 잔차를 그대로 넣으면** 항진명제가 된다 (1/3)

- **상황:** 2026-08-08 bl003-unblock. 이중 호스트 오염을 증명하려고 CONTROL 이
  「거래소 포지션 = 서버 엔진 포지션 + **로컬 순포지션**」을 판정식으로 동결하고 검사점 **3/3** 으로
  닫혔다고 적었다. 그 「로컬 순포지션」은 로컬 원장에서 계산한 값이 아니라 **잔차
  R = exchange − engine 그 자체**였다. 식은 `exchange = engine + (exchange − engine)` 이고
  **어떤 데이터에서도 닫힌다 — 반증 불가능하다.** 로컬 원장에서 독립 계산해 대조하니 **1/3** 이었다.
  같은 회차의 또 다른 판정식은 반대 방향으로 무너졌다 — `matched_order_id IS NULL` 이
  대상 27건을 **전량** 고르므로 「미조인 6건」의 분모는 **판별력이 0** 이었다(BL-605 의 2배 중복 탓).
- **해결:** 판정식을 동결하기 전에 **「이 식이 거짓이 되는 세계」를 한 문장으로 적어라.**
  못 적으면 항진명제이고, 분모가 전량을 고르면 판별력 0 이다. 교체판은
  `exchange(t) = P0 + Σ(양쪽 호스트 체결)` 이다 — `P0` 를 **독립 결정**하고(reduce-only 매수 한 건이
  직전 포지션을 확정한다. 파라미터 1개 · 방정식 4개 = 과결정) **반사실을 같이 돌렸다**:
  양쪽 **4/4** 대 **한쪽만 최대 1/4**(서버전량 0/4 · 서버만 1/4 · 로컬전량 1/4 · 로컬만 0/4).
  ★★**반사실도 정의를 적어야 한다** — 초판은 「0/4 · 0/4」만 적고 공유 주문을 어떻게 셀지를 안 적었는데,
  그 정의에 따라 0/4 도 1/4 도 나온다. **판정식에 적히지 않은 필터로 얻은 숫자는 재현 가능한 관측이 아니라는
  이 카드 자신의 규율을 반사실에도 적용해야 한다**(같은 회차의 적대 검증이 이걸 잡았다).
  **반사실이 실제로 떨어져야 판별력이다.**
- **1차 누적.** ★LESSON-072(사전등록 지표는 기각 영역이 도달 가능한지 먼저 그려라)의 재발이다 —
  그때는 기각 영역이 **원격**이었고 이번은 **공집합**이었다. 같은 병의 극단이다.
  ★부수 반증 하나 더 — 「서버는 세션당 고정 sizing 이라 그 수량을 못 만든다」도 거짓이었다
  (서버 발주 `0.029×9 · 0.058×45 · 0.116×2 · 0.174×3`). **수량은 호스트 판별자가 아니다.**

### LESSON-083 — 관측 도구가 **자기 관측 대상을 오염**시키고, 그 오염이 FAIL 과 같은 코드로 샌다 (1/3)

- **상황:** 같은 회차 갈래 B. `soak-gate.sh` 가 로그 경계를 `docker logs --timestamps` 출력의
  첫 토큰으로 뽑는데, 스택이 내려가 있으면 에러 문구의 첫 토큰 `Error` 가 **타임스탬프 자리에**
  들어간다. 가드는 「비어 있지 않다」만 봤다. 그 아카이브를 먹은 판정기가
  `ValueError: Invalid isoformat string: 'Error'` 로 죽었고 **`exit 1` 은 FAIL 과 구분되지 않는다** —
  「측정 못 했다」가 「측정했고 떨어졌다」로 읽혔다. ★그리고 이것은 과거의 흔적이 아니라
  **진행 중인 과정**이었다 — 맥 launchd 타이머가 30분마다 게이트를 돌려 스택 부재 시 오염본을
  하나씩 찍고 있었다(오염 8벌 → 워커 생존 구간 정상 9벌 → 다시 오염 1벌). 게이트를 **읽으려고**
  건 장치가 게이트의 입력 디렉터리를 계속 바꾸고 있었다.
- **해결:** ⑴ 파서가 먹는 값은 **모양을 검사**해라 — 「비어 있지 않다」는 검사가 아니다
  ⑵ **측정불가를 FAIL 과 다른 종료 코드**로 내보내라(여기서는 `exit 2` + `UNKNOWN / 측정불가`)
  ⑶ 판독 불가 구간에 **시간을 credit 하지 마라** — fail-closed 가 기본이다
  ⑷ 주기 실행 장치가 있으면 **그 장치가 만드는 부작용**을 조사 대상에 넣어라. 「없어진 로그를
  누가 지웠나」를 묻기 전에 「무엇이 30분마다 도는가」를 먼저 세는 것이 빨랐다.
- **1차 누적.** ★수리 검증 순서도 함께 남긴다 — 먼저 **오염 없는 페이로드에서 판정이
  byte-identical** 임을 보이고(수리가 정상 경로를 안 바꿨다), 그 다음 오염 입력에서 `exit 2` 를
  확인했다. 이 순서가 아니면 「엄격해졌다」와 「망가졌다」가 구분되지 않는다.

---

## 확장 시점 판단 기준 (변경 없음)

> 아래 조건이 충족되면 해당 패턴 도입을 검토한다. 그 전까지는 도입하지 않는다.

| 패턴                               | 도입 트리거                                                                                | 현재 상태 |
| ---------------------------------- | ------------------------------------------------------------------------------------------ | --------- |
| 코드 내 중첩 AGENTS.md             | 도메인 3 개 이상 + 각각 반직관적 비즈니스 규칙 3 개 이상 누적                              | 미해당    |
| Action-Based Routing (Context Map) | (구 `.ai/rules/domain.md` 구상 — 부재) 도메인 규칙 파일이 200 줄 초과 + 섹션 분리로도 부족 | 미해당    |
| 모노레포 규칙 분기                 | `apps/` 하위에 독립 `package.json` 이 2 개 이상 존재                                       | 미해당    |
