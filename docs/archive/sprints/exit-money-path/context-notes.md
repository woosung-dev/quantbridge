# exit-money-path 컨텍스트 노트 (append-only)

> 결정과 그 근거. **덮어쓰지 말고 아래에 덧붙인다.** 다음 세션이 여기만 읽고도 왜 이렇게 됐는지 재구성할 수 있어야 한다.

---

## §1 스코프가 정해진 방식 — 측정이 먼저였다

이 도메인은 **네 번 연속** 측정이 전제를 뒤집었다(money-path-accuracy → exit-attribution → 킥오프 작성 중 → 이번 §0.5). 그래서 설계보다 측정을 먼저 했다.

§0.5 실측 (2026-07-25, read-only):

```
trading.orders 0 | live_signal_sessions 0 | live_signal_events 0 | strategies 0
trading.exchange_accounts 1 | trading.exchange_exits 4
소비처 5곳 전부: 0행 위에서 0 합산
원장: ours/none 3행(-0.04367079) · external_manual/none 1행(-0.08025458)
      bracket_tp/bracket_sl/trailing/liquidation = 0행
      matched_order_id NOT NULL = 0 · attributed_strategy_id NOT NULL = 0
```

여기서 두 가지가 강제됐다.

1. **BL-438 ②(거래소 exit 머니-패스 계상)는 스코프 밖.** 원장 행을 머니-패스에 넣으려면 행마다 "어느 세션의 자본인가"에 답해야 하는데, 쓸 수 있는 등급은 `exact`(0행)와 `inferred`(하드 제약으로 금지)뿐이고 남는 건 `none` = 귀속 불가. **미룬 게 아니라 현재 데이터로는 정직하게 구현이 불가능하다.**
2. **BL-444 본문의 규모 근거는 재현 불가.** "확정 3건은 이벤트 없음 / 이벤트 있는 4건은 pine 시뮬값"은 DB 전소 이전 데이터다. 이 PR 이 서 있는 것은 **코드 경로 논증**(`close_service` 는 `LiveSignalEvent` 를 만들지 않는다 — 코드로 확실)이지 규모 실측이 아니다.

---

## §2 사용자 확정 결정 7건

| #   | 결정                               | 근거                                                                                                                                                                                                                                                                                                                        |
| --- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | BL-444 = **읽기 스코프만 교체**    | 안 (b)(`close_service` 이벤트 기록)는 실측 확인 — beat(5분) `dispatch_pending_live_signal_events_task` 가 `list_pending(limit=50)` 으로 pending 을 무조건 재발행 → **중복 청산 발주**. `OrderService.execute` 가 내부 commit 하므로 "주문 커밋 → 이벤트 커밋" 사이 원자성 구멍도 못 막는다. 비상 청산 버튼 위의 쓰기 경로다 |
| D2  | 소비처 = **Site 3·4 만**           | Site 1·2 는 발주를 막는 실행 게이트라 blast radius 가 다르고, Site 5 는 전 테넌트 리포트(사용자 1명, 미도래)                                                                                                                                                                                                                |
| D3  | 대조군 = **fixture 단독**          | 실거래 dogfood 없음 → 사용자 조치 불필요                                                                                                                                                                                                                                                                                    |
| D4  | 세션 창 = **`filled_at` 반열림**   | 백로그 BL-445 권장안 유지. Plan 의 `created_at` 이탈 제안은 기각                                                                                                                                                                                                                                                            |
| D5  | **`symbol` 술어 추가**             | `uq_live_sessions_active_unique` 에 symbol 이 포함돼 심볼만 다른 활성 세션 2개가 합법 → 대시보드 §01 KPI 가 같은 손익을 두 번 더한다. FE 변경 없이 백엔드에서 닫힘                                                                                                                                                          |
| D6  | 필러 = **BL-453 부분만**           | `tasks/trading.py:1698` 1줄 + StrEnum 6필드 주석                                                                                                                                                                                                                                                                            |
| D7  | dogfood = **브라우저 회귀 확인만** | 개발 DB 0행이라 값 판별력은 fixture 담당                                                                                                                                                                                                                                                                                    |

---

## §3 Plan 압박검증이 낸 반론 4건 — 전건 코드 대조 결과

§7.3 대로 판정 전에 전부 코드로 확인했다.

- **(A) 확인** — `dispatch_pending_live_signal_events_task`(`tasks/live_signal.py:756`)가 beat 5분 주기로 `list_pending(limit=50)` 을 무조건 재발행한다. 세션 필터가 없다. 안 (b)를 택했다면 `close_service` 가 넣은 pending 이벤트를 이 beat 이 집어 **두 번째 reduce-only 시장가 청산**을 발주했을 것이다. D1 의 결정적 근거.
- **(B) 확인** — `uq_live_sessions_active_unique(user_id, strategy_id, exchange_account_id, symbol) WHERE is_active`. symbol 이 키에 있으므로 심볼만 다른 활성 세션 2개가 합법이다. D5 의 근거.
- **(E) 확인** — `close_service.py:78` 의 `OrderRequest` 에 `realized_pnl` 필드가 **아예 없다**. 수동 청산은 NULL 로 들어가고 스윕이 나중에 채운다.
- **(①은 과장 — 정정)** Plan 은 "심볼 형식이 어긋나면 **모든** 세션 커브가 조용히 빈다"고 했으나, dispatch(`tasks/live_signal.py:926` `symbol=sess.symbol`)와 수동 청산(`close_service.py:81` `symbol=session.symbol`)은 세션 값을 **그대로 복사**한다. 즉 그 두 경로는 구조적으로 항상 일치하고, 위험은 **TV 웹훅 주문 하나로 한정**된다. 이 정정 덕에 D5 를 택할 수 있었다.

---

## §4 codex G0 = REVISE, [P1] 2건 — 둘 다 코드로 확인 후 수용

**[P1-1] symbol 정확 동등이 TV 웹훅 주문을 조용히 제외한다.** 확인했고 **codex 가 말한 것보다 나빴다** — `RegisterLiveSessionRequest.symbol` 은 `Field(min_length=1, max_length=32)` 뿐이라 형식 검증도 정규화도 없고(`schemas.py:183`), `live_session_service.py:118` 이 `req.symbol` 을 그대로 저장한다. TV 는 `webhook.py:89` 가 `str(payload["symbol"])` 원문. 그리고 `normalize_symbol`(`market_data/constants.py:18`)이 존재하는데 **`src/trading/`·`src/tasks/` 어디서도 호출되지 않는다**(grep 0건). 즉 세션 심볼과 TV 심볼은 서로 독립된 자유 문자열 두 개다.

D5 는 사용자가 이 위험을 명시적으로 고지받고 선택했으므로 뒤집지 않고 **완화 3종**을 넣었다 — ① fixture 에 형식 불일치 주문 O11 을 넣어 제외를 계약으로 고정 ② `SessionScope` docstring 에 전제 명시 ③ ingress 정규화 부재를 신규 BL 로 등재(★**지금 orders/sessions 가 0행이라 백필 비용이 0 인 유일한 창**).

**[P1-2] 개명으로 기존 테스트 3곳이 깨지는데 플랜의 변경 목록에 없다.** 확인했고 더 넓었다 — `test_alert_rules_task.py:44` 의 fake `live_session` 은 `SimpleNamespace(id, exchange_account_id)` 뿐이라 `SessionScope.from_live_session` 에 필요한 `strategy_id`·`symbol`·`created_at`·`deactivated_at` 이 **전부 없고**, `:107` 은 이번에 바꿀 문구를 그대로 assert 하고 있었다. 플랜에 3파일을 명시하고 전부 갱신했다.

codex 가 함께 확인해준 것 — prod 호출부 정확히 2곳 · 동적 접근 없음 · Site 1·2·5 독립 쿼리라 간접 영향 없음 · 반열림/NULL/타임존은 `AwareDateTime`/UTC 기반으로 타당. 추가로 **`Order.filled_at` 은 거래소 체결시각이 아니라 우리 관측시각**이라는 한계를 짚었다 — 계약 문서에 반영했다.

---

## §5 대조군 설계 — "0 → 0" 을 깨는 방법

`0 → 0` 이 아무것도 증명하지 못하는 이유는 **틀린 술어와 맞는 술어가 같은 답을 내기 때문**이다. 그래서 손익을 2의 거듭제곱 × 서로 다른 소수부로 심어 **어떤 부분집합 합계도 유일**하게 만들었다 — 틀린 답이 나오면 그 숫자가 어느 술어를 잘못 넣었는지 스스로 지목한다.

세션 3개(같은 (strategy, account) 위 S1 비활성 · S2 활성 · S3 심볼만 다름) + 주문 11건. 기대값은 착수 전 손으로 계산해 검증했다.

| 사이트          | before                                  | after                                              |
| --------------- | --------------------------------------- | -------------------------------------------------- |
| Site 3 S1       | −1.00000001                             | **−3.00000003**                                    |
| Site 3 S2       | −8.00000008                             | **−28.00000028**                                   |
| Site 3 S3       | 0                                       | **−32.00000032**                                   |
| Site 4 S1/S2/S3 | −1151.00001151 (셋 다 동일 = BL-445)    | −3.00000003 / −28.00000028 / −32.00000032 (서로소) |
| Site 1 가드레일 | −1407.00001407                          | 동일                                               |
| Site 2 가드레일 | −1663.00001663                          | 동일                                               |
| Site 5 가드레일 | −1919.00001919 (filled 10 / rejected 1) | 동일                                               |

가드레일 세 값을 서로 다르게 배치한 이유 — 누가 Site 1 에 계정 필터를, Site 2 에 전략 필터를, Site 5 에 테넌트 필터를, 혹은 아무 데나 심볼 필터를 "친절하게" 넣으면 **어느 것을 넣었는지가 숫자로 드러난다.**

### ★판별력을 실제로 증명한 방법

fixture 를 쓰고 나서 **프로덕션 코드를 `git stash` 로 되돌린 뒤 before 값으로 실행해 5 passed** 를 확인했다. 이게 "이 테스트가 실제로 판별력을 갖는가"를 아는 유일한 방법이다. 그다음 stash 를 복원하고 after 값으로 뒤집었다.

### fixture 가 원리적으로 못 잡는 것 (정직성 의무)

1. **백필 체인 실작동** — fixture 는 `realized_pnl` 을 손으로 심으므로 `refresh_closed_pnl_task` → 스윕 → `backfill_exchange_realized_pnl` 이 통째로 망가져도 통과한다. 그런데 **수동 청산이 값을 갖는 유일한 경로가 그 체인**이다.
2. **`filled_at − created_at` 실제 간극** — D4 상한이 늦은 체결을 얼마나 자주 흘리는지.
3. **심볼 문자열 동일성** — 양쪽을 같은 리터럴로 심으므로 TV 웹훅 경로의 실제 정규화 불일치를 못 잡는다.
4. **배포 직후 알림 폭발** — `qb_rule_alert:{rule_id}` throttle 은 TTL 1h, first-run 억제가 없다. 스코프가 넓어지면 첫 평가에서 그동안 안 보이던 수동 청산이 한꺼번에 분자에 들어와 임계를 넘길 수 있다. **개발 DB 이력이 0행이라 dogfood 로도 관측 불가 → 사용자 실계정 첫 배포에서 처음 나타난다.**

---

## §6 인프라 사고 2건 (코드 무관, 그러나 시간을 가장 많이 먹었다)

**① 3-env 미export.** baseline 첫 실행이 `5 failed / 2280 passed / 422 errors`. 셸에 `DATABASE_URL`/`TEST_DATABASE_URL`/`TEST_REDIS_LOCK_URL` 이 하나도 없어 conftest 가 기본값 `localhost:5432` 로 폴백했다. 우리 DB 는 **5433**. `set -a; source backend/.env.local; set +a` 로 해결. `.env.local` 은 3개를 모두 담고 있으므로 **개별 export 대신 통째로 source 하는 것이 안전**하다(DATABASE_URL 만 주면 파괴적 마이그레이션 테스트가 개발 DB 를 향한다).

**② Docker VM 디스크 100% 포화.** env 를 고쳐도 `5 failed / 417 errors` 가 남았다. 단독 재현 결과 `asyncpg.exceptions.CannotConnectNowError: the database system is in recovery mode`. 컨테이너 로그를 읽으니 —

```
PANIC:  could not write to file "pg_logical/replorigin_checkpoint.tmp": No space left on device
checkpointer process (PID ...) was terminated by signal 6: Aborted
all server processes terminated; reinitializing
```

무한 크래시-복구 루프였다. 호스트는 49Gi 여유였지만 **Docker Desktop VM 가상 디스크가 58.4G 중 0 available**. 데이터 볼륨이 위험한 상태라 즉시 조치하되 **가장 안전한 것만** 건드렸다 — `docker builder prune -f`(빌드 캐시만, 데이터 0). 10GB 회수 → 8.9G 여유 → 체크포인트 성공 → `database system is ready to accept connections`. 원장 4행 유지 확인, 데이터 무손실.

★교훈 — 볼륨(33GB, "reclaimable 17GB")과 이미지는 **건드리지 않았다.** 이 레포는 파괴적 정리로 개발 DB 를 한 번 잃은 전력이 있다(BL-451). 캐시는 정의상 재생성 가능하지만 볼륨은 아니다.

---

## §7 정직성 문구 (PR 본문 의무)

- 세션 스코프 **관측**(Site 3·4)이 정정됐다. 실행 게이트(Site 1·2)는 무변경이며 여전히 전 기간(BL-446)·계정 전역이다. 일일 리포트(Site 5)도 여전히 전 테넌트 전역이다(BL-450).
- BL-444 본문의 규모 실측은 DB 전소로 재현 불가하며, 이 PR 은 **코드 경로 논증**에 근거한다.
- 수동 청산은 삽입 시 `realized_pnl` 이 NULL 이라 이 PR 후에도 **스윕이 백필하기 전까지는** 여전히 0 으로 보인다. BL-444 는 "보이느냐"를 고쳤지 "언제 보이느냐"를 고치지 않았다.
- **라이브 손익에 펀딩이 한 푼도 반영되지 않는다**(BL-186).
- 이번 범위에서 원장(`trading.exchange_exits`)을 읽는 소비자를 만들지 않았으므로 **"합성 Order 금지" 제약은 시험되지 않았다.**

---

## §8 최종 codex 누적 diff 리뷰 — REVISE [P2] 1건, 회귀 아님으로 판정

codex 가 `main...HEAD` 전체를 읽고 낸 유일한 finding은 **TOCTOU** 였다. 두 소비처 모두 세션 행을 먼저 읽어 `SessionScope` 를 만들고 **별도 SELECT** 로 주문을 조회하는데, 그 사이 `LiveSignalSessionRepository.deactivate`(`:155`)가 커밋되면 스코프는 여전히 무상한(`ended_at=None`)이라 종료 후 체결이 그 한 번의 계산에 섞인다. `deactivate` 호출 지점은 4곳이다(`tasks/live_signal.py:433/503/539` beat + `router.py:442` 사용자 DELETE) — 코드 대조로 실재를 확인했다.

**그런데 등급 판단은 codex 와 다르게 했다. 이건 회귀가 아니다.**

- 변경 **전에는** Site 4 에 창이 아예 없었다(전 기간 무조건 포함). Site 3 도 event-join 이라 창이 없었다.
- 즉 이 레이스는 새 코드가 **한 번의 계산 동안만** 옛 동작을 하게 만드는 것이고, 다음 평가/요청에서 자가 교정된다. 변경 전의 **영구적** 동작보다 엄격하다.
- 두 경로 모두 발주를 막지 않는 **읽기 전용 관측**이다(Site 1·2 만 게이트).
- 올바른 수정(세션↔주문 단일 조인)은 쿼리 구조 변경이고, codex 스스로 "새 테스트는 순차 실행뿐이라 이 경쟁 조건을 잡지 못한다" 고 적었다 — 즉 고쳐도 검증할 수단이 이번 범위에 없다.

→ 수정 대신 [BL-459](../../../backlog.md#bl-459) 등재 + `operating-contract.md` §3.3 에 계약으로 명시. **codex 판정을 그대로 받지도, 그냥 무시하지도 않았다** — 실재를 확인하고 등급만 근거와 함께 조정했다.

codex 가 함께 확인해준 것 — 구 메서드/문자열·동적 참조 잔존 0 · 술어의 NULL/반열림/UTC/Decimal/`where(*list)` 정확 · Site 1/2/5 와 응답 스키마 간접 변경 없음 · 기대값 산술 정확.

---

## §9 게이트 결과와 한 번 red 였던 것

| 게이트         | 결과                                                                   |
| -------------- | ---------------------------------------------------------------------- |
| `ruff check .` | All checks passed (pre-commit `ruff format` 후 재게이트 포함)          |
| `mypy src/`    | Success, 203 source files                                              |
| BE pytest      | **2717 passed / 0 failed** (baseline 2707 → +10 = 신규 테스트 수 일치) |
| FE `pnpm test` | **1094 = baseline 정확 일치** (FE 변경 0)                              |
| alembic        | 무변경, head `20260725_0002` 유지                                      |
| canon          | 27 / 32 — 5 실패는 **main 기존 결함**(아래)                            |

**★한 번 red 였던 항목.** BE 첫 전량 실행에서 `test_redis_client.py::test_get_pool_safe_across_event_loops` 1건 실패. 단독·clean main·2회차 전량 모두 통과 → **순서 의존 flake**. 내 변경 파일은 `tests/tasks`·`tests/trading` 이라 알파벳 순으로 `tests/common` **뒤에** 돌아 원인이 될 수 없다. 숨기지 않고 기록한다.

---

## §10 dogfood 가 못 돈 이유 — 환경 2건 (둘 다 이 브랜치와 무관)

### ① 로컬 백엔드가 죽은 DB 포트를 향하고 있다

`/dashboard` 를 실제 브라우저로 열었더니 렌더는 정상인데 **콘솔 error 48건이 전부 CORS/`ERR_FAILED`** 였다. 파고들었더니 CORS 설정은 멀쩡했다 — `OPTIONS` 프리플라이트가 `access-control-allow-origin: http://localhost:3100` 을 정상 반환한다.

진짜 원인은 8100 백엔드 프로세스가 **2026-07-24 08:22 기동**이고 인라인 env 가 `DATABASE_URL=...localhost:5436` 이라는 것. **5436 은 닫혀 있다** — 2026-07-25 포트 정렬(5436 → 5433) **이전**에 뜬 stale 프로세스다. DB 를 건드리는 요청이 전송 단계에서 실패해 브라우저가 CORS 로 보고할 뿐이었다.

사용자가 띄운 프로세스라 임의로 죽이지 않았다. **5433 으로 재기동해야 브라우저 dogfood 가 의미를 갖는다.**

### ② main 에서 차트 토큰 9/10 이 런타임 미해석

canon 5 실패의 실체 = `해석되지 않은 변수 — chart-tokens.ts 가 폴백으로 조용히 떨어진다`. `--border` 하나만 해석되고 나머지 9개가 빈 문자열이다.

확인한 것 — 토큰은 `src/styles/globals.css` 의 `:root`(43·55…)와 `.dark`(416~)에 실재하고 dev 서버가 내려주는 CSS 청크에도 각 2회 존재한다. **`--border`(55)와 `--bullish`(43)가 같은 `:root` 블록인데 하나만 해석된다** 는 것이 핵심 단서다. `frontend/` 이 main 과 **바이트 동일**이라 이 브랜치가 만들 수 없는 결함이므로 특성 파악까지만 하고 멈췄다.

### ③ 그래서 dogfood 는 무엇을 증명했나

**아무것도 증명하지 못했다** — 정직하게 그렇게 적는다. 다행히 D3 에서 대조군을 fixture 단독으로 잡았으므로 **값 판별력은 애초에 dogfood 몫이 아니었다**. dogfood 는 회귀 안전망이었고 그 안전망이 환경 때문에 못 돌았다.
