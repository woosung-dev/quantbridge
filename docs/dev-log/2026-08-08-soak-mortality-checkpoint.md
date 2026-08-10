# 2026-08-08 soak-mortality-repair 체크포인트 — 위상 진행 기록

> `docs/status.md` 에서 강등(2026-08-10 bl-trigger-triage). 원문 = `git show 7db0d426:docs/status.md` 234-374줄.
> 브랜치 `stage/soak-mortality-repair` 는 푸시·PR·머지 없이 남아 있다.

**브랜치 `stage/soak-mortality-repair`** — 커밋 4개. 푸시 안 함 · PR 없음 · 머지 없음.
`4c32c803` status 진입점 · `170c6ee4` [BL-610] 10곳 · `29106a39` [BL-619] 재관측 + [BL-653] 등재.

| 위상                  | 상태                                                                     | 확인 방법                                                       |
| --------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------- |
| P0 소크 down          | ✅ **C1 15.3007h 보존** · 실격 0 · pin `3f8af9dfe78e`                    | `scripts/soak-gate.sh`(서버)                                    |
| P5b [BL-610]          | ✅ DANGLING 0건                                                          | 백로그 `#bl-610` 의 재검출 명령                                 |
| P4 [BL-619]           | ✅ 디스패치 정지 0건 · 상태 축은 [BL-653] 로 분리                        | 위 ★P4 문단                                                     |
| P1 오라클             | ✅ **stage 머지 완료**(`b12b3059`) — tick 차분 오라클 427줄 + 픽스처 7건 | `backend/tests/tasks/test_live_signal_tick_oracle.py`           |
| P5 백테스트           | ✅ **stage 머지 완료** — [BL-460] net equity · [BL-466] (c) 고지         | `backend/tests/strategy/pine_v2/test_margin_gate_net_equity.py` |
| P3 배타성             | ✅ **stage 머지 완료** — [BL-605]·[BL-651]·[BL-634]                      | `backend/src/trading/services/account_exclusivity.py`           |
| P2 킬 가드            | ✅ **stage 머지 완료** — strike TTL 3봉 · 공백 유예 · §⑧ 미룸            | `backend/tests/tasks/test_live_signal_direction_strike.py`      |
| P6 게이트 · P7 재기동 | ✅ 게이트 **8/8** · PR #570 머지(`fdc53c04`) · **재기동 완료**           | `scripts/soak-gate.sh`(서버)                                    |

★★**2026-08-08 워커 2개가 API 오류(`Not logged in`)로 죽었고, 체크포인트가 예측한 그대로였다** —
**생성은 남고 검증이 날아갔다.** `wt/btfix` 는 커밋 2개를 남겼지만 red 실증·codex·전체 테스트를
못 했고, `wt/excl` 은 `trading.py:1909` 가 **정의 없는 헬퍼를 호출하는 중간 상태**로 멈췄다.
⇒ **미커밋 파일을 산출물로 신뢰하지 마라. 테스트를 직접 돌려라.**
워크트리 = `.claude/worktrees/{oracle,btfix,excl,killguard}`.

★★★**환경 함정 — 이 레포는 `make up` 이 아니라 `make up-isolated` 다.**
`backend/.env.local` 이 **5433/6380**(격리 포트)을 가리킨다. `make up` 을 돌렸다가 ⑴ 포트 5432 를
**다른 프로젝트 `nexus_db` 가 이미 점유**해 db 기동이 실패하고 ⑵ 그 와중에 redis 가 **6379 로
재생성**돼 env(6380)와 어긋났다. 수습 = `make down` → `make up-isolated`.
★**워크트리 pytest DB 는 `--skip-db` 부트스트랩이 안 만든다.** slot 9~12 를 손으로 만들었다:
`docker exec quantbridge-db psql -U quantbridge -d postgres -c "CREATE DATABASE quantbridge_w<N>_test"`.
없으면 DB 의존 테스트가 **전량 error** 라 회귀처럼 보인다(P1 워커가 44건을 그렇게 봤고, 그 44건은
baseline 과 동일했다).

★**P3 계정 축 결정이 함께 닫혔다** — 소유권 집합은 **`exchange_uid` 형제 행 전량**이고
근거는 `backend/src/trading/services/account_exclusivity.py:_ownership_scope` 주석에 있다
([BL-639] 실패 모드 3 종결). 스코프가 없으면 거부율이 원장 크기를 따라가 **판별력 0** 이 되고,
반대로 행 하나로 좁히면 [BL-605] 의 2행 때문에 **우리 주문을 FOREIGN 으로 판정**해 정상 재기동을
영구 차단한다. 양쪽 실패 모드 사이가 형제 행 전량이다.

★★**P3a 의 유일한 미측정 항목 — P7 재기동 전에 눈으로 확인해라.** `live_session_admin.py status`
의 `RESTING_CONDITIONAL` 이 **실제 미체결 주문 수와 일치하는지**(2배가 사라졌는지).
이번 회차는 거래소 접촉 금지 제약으로 못 쟀다. ★비교 기준은 down 직전 CONTROL 실측이다 —
`RESTING_CONDITIONAL=2` 인데 실제 **1건**, flatten 직후 `=4` 인데 실제 **2건**(둘 다 정확히 2배).

★**P2 가 닫은 것 3종** — ⑴ direction strike 에 **3봉 TTL**(벽시계가 아니라 **봉 수**로 잰다 —
고정 초로 재면 1h 세션에서 매 tick 만료돼 가드가 통째로 꺼진다) ⑵ 직전 평가와 **1봉 초과**로
떨어지면 strike 창 재시작 ⑶ [ADR-025] §⑧ — 원장 못 읽은 tick 은 리컨사일을 **1 tick 미룬다**
(취소는 비가역, 미룸은 가역). ★codex 가 잡은 것: `requires_gap_resync` 고정 5분을 공백 술어로
쓰면 **15m·1h 은 정상 다음 봉도 문턱을 넘어** direction 킬이 영원히 안 걸린다 — 세션 봉 길이 기준으로 교체.

★★★**P7 집행 완료 (2026-08-08T23:16Z) — 착수 전 논거가 실측으로 확인됐다.**
PR #570 머지(`fdc53c04`) → 서버 main ff → `pin fdc53c04` → `up` → `stop` → `flatten` →
`start` → `soak-observe --baseline` → 게이트. **C1 이 이어졌다: 15.3007h → down → up →
`15.3167h`** · 창 시작 `2026-08-07T15:10:49` 그대로 · 실격 **0** · C5 전건 ✓.
⇒ **down 은 리셋이 아니라 미계상**이라는 전제가 참이었다. 새 세션 `de3db35a` · T0 `23:16:52Z`.

★★**미측정 2건 중 하나가 닫혔다** — [BL-651] 2배가 **사라졌다.** 수리본으로 status 를 돌리니
`RESTING_CONDITIONAL=1`(실제 1건)이고 계정이 **한 행만** 출력된다. 수리 전에는 `bybit demo` 와
`bybit demo- aaa` 가 **둘 다** 나오며 `=2`(실제 1건) · flatten 직후 `=4`(실제 2건)였다.
★[BL-634] 도 **프로덕션 음성 대조**를 얻었다 — 정상 상태에서 `register()` 가 세션을 통과시켰다.

★★**P7 이 새 결함 2건을 드러냈다 ⇒ [BL-656].** ⑴ dry-run 이 **자기 설명문을 실행**했다
(unquoted heredoc 안 백틱 ⇒ `countable: command not found`, ⑻ 문장이 잘려 출력) — 수리했다.
⑵ `soak-restart.sh` 는 **완전 down 에서 못 돈다**(⑴ status 가 DB 를 읽는데 스택이 down 이면
DB 도 없다 · ⑷ 는 이미 돌고 있는 스택을 전제) — 문서화만 했고 코드 방어는 미수리.
★**`stop` 이 `flatten` 보다 먼저인 것이 실측으로 갈렸다** — P0 에서 세션을 살린 채 flatten 만
했더니 엔진이 **재무장**해 `EXCLUSIVE=NO`·`FOREIGN_RESTING=2` 가 됐고, P7 에서 순서를 지키니
`FLAT=YES · RESTING_CONDITIONAL=0 · QUIET=YES` 로 깨끗했다.

★★★**P0 의 본체가 미착수인 채로 남아 있고, 그것은 소크와 병렬이다.** [BL-003] 은 소크가
아니다 — **「Bybit mainnet 진입 runbook + smoke 스크립트」**이고 소크 168h 는 그것의 **Trigger** 다.
백로그 본문이 `🔴 열려 있다. mainnet runbook·smoke 스크립트 미착수` 라고 적고 있다(Est **M 4~5h**).
★**Trigger 가 막는 것은 산출물의 「실행」이지 「작성」이 아니다** — runbook 을 쓰는 데 168h 가
필요하지 않다. 지금 안 하면 창이 찬 뒤에 4~5h 를 **더** 기다린다.

~~**다음 행동 = [BL-657] — 게이트가 어느 DB 를 보는지 출력(0.5~1h) — 을 먼저 닫고, 남은 시간을
[BL-003] 본체(runbook + `scripts/bybit-smoke.sh` + `.env.production` 절차)에 써라.**~~
→ **2026-08-09 사용자 결정으로 회차 성격이 바뀌었다** — [BL-657] 은 **살아서 W1 레인의 첫 항목**이
됐고(위 ⓷), [BL-003] 본체는 **다음 회차로 미뤘다.** 근거 = 이번 회차는 **XS/S 대량 종결**이 테마이고
[BL-003] 은 M(4~5h) 단건이라 **레인 하나를 통째로 먹는다.** ★순서 논리 자체는 유효하다 — 게이트를
못 믿으면 168h 판정이 무의미하므로 [BL-657] 이 여전히 **W1 의 첫 항목**이다.

★**소크는 상시 배경이다 — 매 세션 첫 명령으로 게이트를 돌리되, 살아 있으면 그냥 둬라.**
새 창 `de3db35a`(T0 `2026-08-08T23:16:52Z`)가 [BL-595]/[BL-634] 수리 뒤 **첫 창**이고,
「사망률이 실제로 내려갔나」는 이 회차가 남긴 유일한 미판정이다. 직전 39세션 24h 도달 **0건** ·
최장 19.42h. ★**점추정을 인용하지 마라**([BL-641] — 층화 CI 가 6쌍 전부 겹친다).
★**죽어도 하던 일을 멈추지 마라** — `backend/src` 를 고치는 것은 창과 무관하다(위 ★★★ 참조).
죽으면 **사인만 기록**하고, 그 사인이 [BL-653]/[BL-654]/[BL-656] 중 무엇을 여는지 다음에 정해라.

★**P1 이 관문이다.** `_evaluate_session_with_engine`(`live_signal.py:3174-3753`, 580줄)은 **직접
호출 테스트가 0건**이고 비결정 5축(`uuid4` `:3384` · `datetime.now` · ccxt `:3283` · DB · prometheus)을
갖는다. 부착 지점은 **`_evaluate_session_inner`(`:3756`)** — 기존 테스트 5파일이 이미 여기로 들어오므로
5축을 새로 봉할 필요가 없다. ★`backend/tests/fixtures/bl595/` 5건은 **이미 존재한다**(신설 아님,
생성기 `capture_bl595_death_fixtures.py:388`) — P1 전반부는 회귀 확인이고 실질 산출은 차분 오라클이다.

★**P4 [BL-619] — 2026-08-08 집행 완료. 「미상」이 아니라 「한 축은 답했고 한 축은 못 잰다」였다.**
★★**착수 전 내 전제가 틀렸다** — [BL-619] 는 게이트 실격 목록의 07-26 `tick_stall 0e15c3c0` 이
**아니다**. 08-06 세션 `c160a1a9` 의 ~17분 정지이고, 닫는 조건은 「로그가 남은 창에서 재관측」이다.
그 조건이 이번 창에서 **처음 성립했다**(로그 3.5MB).
결과 — **디스패치 축 정지 0건**(`evaluate_all` 919건 · 간격 최소=중앙=최대 **60.0초** · 2분 이상
공백 0). 원 사건 ~17분은 이 해상도로 확실히 잡히므로 **유효한 음성 대조**다. **그래도 안 닫는다** —
재발 0은 뿌리를 밝히지 않는다. ★★★**상태 축은 못 쟀다** — `last_evaluated_bar_time` 10분 이상
정체 35구간이 보이는데 그 값들이 **표본 최대 간격 31.0분과 정확히 같아** 정지인지 관측 공백인지
구분이 안 된다(게이트 표본 간격 중앙 13.9분). **측정 도구 자신이 반증됐다** ⇒ 신규 [BL-653]
(fail-open — 성긴 표본은 실격을 안 낸다). DB 축은 스택을 내린 채라 **조회하지 않았다**.

**[BL-598] ② 착수 지침** (백로그 `#bl-598` 전문을 열어라):

- ★**「캐시가 있을 것이다」로 시작하지 마라** — 백로그가 이미 찾아봤고 없었다(`pine_v2/*.py` 에
  캐시 데코레이터 0건). **관측부터 해라.**
- 닫는 자리는 **하나** — `conftest.py` 에서 `pynescript.ast.parse` 를 소스 해시 키 디스크 캐시로
  감싸면 `pine_v2` 7 진입점이 한꺼번에 덮인다. `classify_script()` 만 캐시하면 **안 닫힌다**
  (코퍼스를 읽는 테스트가 30 파일 · `i3_drfx` 를 건드리는 것만 10 파일).
- ★**같이 열어야 하는 것 = 신규 [BL-652] — cold 축**. ①의 결론은 전부 **warm 프로세스 한정**이고
  CI 러너는 매 잡이 cold 다. ②의 디스크 캐시는 **파싱 비용만** 지우므로 import·bytecode 는 남는다.
- ★**규모 대조는 아직 안 됐다** — ①의 실측은 **로컬 9프로세스**(+52.89s)이고 CI 3샤드(+519s)와
  **직접 대조되지 않았다**(약 10배 차). 「+519s **전부**가 이 중복」은 **여전히 미검증 가정**이다
  (셈: 「샤드마다 코퍼스 프리미엄 한 번」 모형이 이 맥에서 주는 값은 2×65.48 ≈ **131s** = 519s 의
  25%). 최신 CI 실측(2026-08-08 PR #567): backend **(a) 13m34s · (b) 10m6s · (c) 8m17s**.
  이 축을 닫으려면 **CI 에서** 샤드 수를 바꿔 가며 재라.

**⑴~⑸ — 열린 창**(`backend/src` 를 여는 비용이 0인 구간. 24h 도달 **0/39** · 최장 19.42h).
★★**2026-08-08 ⑴이 맨 뒤로 갔다** — 「죽는 순간에만 열린다」가 아니라 **승인으로 열었다**.
재기동은 **마지막**이다. ★**순서를 지켜라 — [BL-605] 가 `RESTING_CONDITIONAL` 2 → 1 을
고쳐야 [BL-634] 가 쓸 「개수」의 신뢰도가 산다:**

1. **(마지막에)** `scripts/soak-restart.sh`(dry-run) → **사용자 승인** → `--confirm`.
   ★★**머지 없이는 수리가 서버에 안 간다** — `soak-stack.sh:171-174` 의 `_pin` 은 기본값 `HEAD` 이고
   **`assert-main-checkout.sh` 를 요구**한다. 브랜치 tip 은 pin 할 수 없다. ⇒ PR 을 머지해야
   수리본으로 재기동된다. 안 하면 소크는 **수리 전 코드로 돈다**.
   ★★**down 이 조건부 주문을 남겼다** — 2026-08-08 flatten 후 `FLAT=YES` 인데 엔진이 재무장해
   `d655f560`(FOREIGN sell) + `8d4272fe`(ours buy)가 거래소에 남았고 `EXCLUSIVE=NO` 다.
   `soak-restart.sh:288-304` 가 `EXCLUSIVE≠YES` 면 die 하므로 **재기동 전에 정리해야 한다**.
2. **[BL-605]** 스윕 계정 루프에 `exchange_uid` dedup — `backend/src/tasks/trading.py:1904-1906`.
   선례를 베껴라: `:507-512` · `:851` · `websocket/position_fanout.py:69-80`.
   음성 대조 = 수리 전 574행/287해시가 수리 후 신규 적재에서 1배가 되는지.
3. **[BL-651]** 같은 축을 **거래소 조회 루프**에서도 — `backend/scripts/live_session_admin.py:206-234`.
   커밋을 ⑵ 와 나눠라(회귀 시 어느 축인지 갈린다). 검증 = `RESTING_CONDITIONAL` 이 2 → **1**.
4. **[BL-634]** 가드 구현 — `live_session_admin.py:206-256` 의 `EXCLUSIVE` 를 세션 기동 전제조건으로
   승격. ★결정할 것 하나: 소유권 집합 `SELECT id FROM trading.orders` 의 **계정 축**([BL-639] 실패
   모드 3). ★`fetch_open_conditional_orders(..., reduce_only=None)` 는 협상 불가 계약이다.
5. 재기동 + 새 창 시작. 게이트로 C1/C2 가 **0 부터 다시** 시작하는지 확인.
