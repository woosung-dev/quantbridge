# 2026-08-03 — gate-trustworthiness

> 「테스트 전부 통과」를 증거로 쓸 수 있게 만든다.
> 진입점: `docs/status.md` 「다음 스프린트」. 브랜치 `stage/gate-trustworthiness`.
> 판정식 정본 = `docs/reference/operations/workflows/generator-evaluator-pipeline.md` §G1.1.

---

## 0. baseline 재측정 (§7.1) — `095823a4`

★status.md 의 baseline 은 대조 대상이다. 실제로 다시 쟀다.

| 축                         | status.md 대조값         | 지금 HEAD 실측               | 판정                             |
| -------------------------- | ------------------------ | ---------------------------- | -------------------------------- |
| BE pytest                  | 3848 passed / 46 skipped | 3848 passed / 46 skipped     | 일치 (259s)                      |
| BE pytest `-p no:randomly` | (같은 값 예상)           | **3848 passed / 46 skipped** | 일치 → §1.1 로 이어진다          |
| ruff                       | clean                    | `All checks passed!`         | 일치                             |
| mypy                       | 214 clean                | 214 source files clean       | 일치                             |
| FE vitest                  | 1242 (205 파일)          | 1242 passed (205 파일)       | 일치                             |
| 마이그레이션 head          | `20260801_0001`          | `20260801_0001`              | 일치                             |
| 가드 밖 mutation           | 129                      | census 테스트 green ⇒ 유지   | 일치                             |
| `/metrics`                 | 10524 파일 · 650MB       | **11277 파일 · 698MB**       | 증가 (BL-581 Trigger 20000 미달) |
| 활성 라이브 세션           | —                        | **0**                        | 편집 안전 (worker bind-mount)    |

---

## 1. ★착수 전제 2건 반증 — 둘 다 「수리 전 측정」에서 나왔다

### 1.1 `pytest-randomly` 는 **설치돼 있지 않다** ⇒ 시드 스윕은 실행 불가

BL-583 원문과 status.md 는 「`pytest-randomly` 가 매 실행 순서를 섞으므로 이 red 는 우연히
나타났다 사라진다」고 적었고, 첫 step 지시도 「시드를 바꿔가며 흔들리는 테스트를 전수 집계」였다.

실측 설치 플러그인: `pytest` 9.0.3 · `asyncio` · `celery` · `cov` · `json-report` · `metadata` ·
`timeout` · `docker_tools`. **randomizer 가 없다.** 그래서

- `-p no:randomly` 는 **no-op** 이다 (없는 플러그인 차단은 조용히 통과한다).
- 두 baseline(`O1` 기본 / `O2` 플래그)이 **같은 3848/46** 을 낸다 — 「두 번 재라」의 답은
  「차이 없음」이지만 그 **이유가 「순서 의존이 없다」가 아니다.**
- 실행 순서는 **결정론적**이고, 바뀌는 것은 **어떤 파일이 함께 수집됐는가**다.

⇒ 시드 스윕을 **결정론적 순열 매트릭스**(§7)와 **수집 집합 실험**(§4)으로 대체했다. 대체한
사실과 이유를 여기 적는다 — 조용히 바꾸지 않는다.

### 1.2 배제 가설의 근거가 **반만** 참이었다

백로그는 `_patch_reconcile` 의 `OrderRepository` monkeypatch 누수를 이렇게 배제했다:

> `tasks/trading.py` 는 모듈 최상단에서 이름으로 import 하므로 그 patch 가 애초에 닿지 않는다.

★**이 진술은 「이미 적재된 모듈」에만 참이다.** 아직 적재되지 않은 모듈은 그 순간 최상단
`from … import X` 를 실행하므로 **가짜를 자기 전역으로 복사**한다. 그리고 `monkeypatch` teardown 은
**정의 모듈만** 되돌린다. 즉 그 근거는 배제가 아니라 **정확히 뿌리를 가리키고 있었다.**

---

## 2. 사전등록과 codex 게이트 2회

판정식 V1~V5 · 표적 변이 · 순열 O1~O7 · 뿌리 한 문장을 동결해 **코드 쓰기 전** 제출(G1),
수리 후 적대 리뷰 1회(G6). 처분표 정본 =
[`.claude/gates/gate-trustworthiness/codex.ok`](../../.claude/gates/gate-trustworthiness/codex.ok).

- **G1: BLOCKING 3 · MAJOR 2 · MINOR 2** — 그중 **3건이 설계를 교체**했다.
- **G6: BLOCKING 0 · MAJOR 4 · MINOR 4** — 그중 **1건은 수리**(훅 순서), **1건은 내 문서가
  코드와 모순된다는 지적**(개수), 나머지는 갭 문서화와 문구 정정.

### G1 이 코드 전에 바꾼 것 3건

1. **O3 의 `--ignore` 집합이 불완전했다.** codex 는 5번째(`test_beat_schedule`)를 지목했고,
   AST 모듈수준 폐포로 세니 **6개**였다 — codex 도 `test_conditional_entry_janitor.py:20` 을
   놓쳤다(`janitor:16 → orphan_scanner:24 → trading`). 그리고 **4개만 빼면 여전히 green(3781)**
   이라 손으로 고른 ignore 집합은 **마스킹된 green** 을 준다. 그래서 O3′ 에 **사전조건 프로브**
   (`pytest_collection_finish` 에서 대상 모듈 미적재를 단언)를 붙였다.
2. **내 변이 M3 가 판별력 0 이었다.** 「스캔 범위를 없앤다」는 변이는 순수 함수를 직접 호출하는
   단위 테스트를 통과한다. → 창 계산을 **별도 순수 함수**로 분리하고, 배선은 **자식 pytest
   세션**으로 따로 고정했다. (지난 회차에 이어 **두 회차 연속** 내 사전등록 변이 하나가 판별력 0)
3. **teardown 예외 경로가 검사를 통째로 건너뛴다.** pluggy 는 예외를 wrapper 의 `yield` 지점에
   재발화하므로 `yield; scan()` 의 scan 이 사라진다. → 예외 경로에서도 스캔하되 `fail` 을 던지지
   않는다(**원인 예외를 가린다**). 최종 형태는 `exc.add_note` 다 — 예외를 만들지 않으므로 원본을
   가리지 않고, `filterwarnings = error` 하에서도 안전하며, pytest 9 가 원인 예외 **바로 아래**에
   출력한다(실측).

### G6 이 수리로 이어진 것 1건 + 문서를 고친 것 3건

- **수리:** `pytest_runtest_setup` 을 `tryfirst` **평범 훅**으로 두면 **다른 플러그인의 setup
  wrapper pre-yield 보다 뒤**다. 실측 순서 `other-wrapper-pre → my-plain-tryfirst`. 그 플러그인이
  pre-yield 에서 패치를 걸고 소비 모듈을 적재하면 창이 그만큼 좁아진다. →
  `wrapper=True, tryfirst=True` 로 바꾸니 실측 순서가 `my-wrapper-tryfirst-pre → other-wrapper-pre`
  로 뒤집힌다. (G1 MINOR 가 「wrapper 는 불필요하다」고 했고 그것을 따랐는데, G6 가 되돌렸다 —
  **같은 evaluator 의 두 라운드가 반대 방향을 가리킬 수 있다.**)
- **문서:** ① 내가 닫은 개수(오염원 3곳·전역 6개)가 **코드와 모순**이었다(네 번째 경로를 이미
  고쳐 놓고 문서를 안 고쳤다) ② 「경고로 남긴다」는 `add_note` 로 바꾼 뒤 **거짓**이 됐다
  ③ 「부분 실행마다 자기 감시」는 `--collect-only` 가 훅을 안 부르므로 문자 그대로는 성립하지 않는다.

★**내 근거 하나가 틀렸다(G1 MINOR)** — 「지연 import 는 실재 순환을 끊는 장치」라고 썼는데
실측하면 `src.tasks.live_signal` 을 모듈수준으로 끌어오는 src 모듈은 **0개**(순환 없음)이고
`src.tasks.trading` 은 `pine_v2.event_loop` 에 **닿지 않는다**(블라스트 래칫도 근거가 아니다).
프로덕션 미수정은 유지하되 근거를 교체했다 — **모듈수준으로 올리면 import 실패 등급이
「평가 1건 실패」에서 「celery 태스크 미등록」으로 올라간다.**

★**독립 검증 3건**(codex 를 기다리지 않고 따로 실측):

- 훅 순서 — 레포 밖 프로브에서 `setup-pre=ORIGINAL / teardown-post=ORIGINAL` ⇒ 검사 지점이
  monkeypatch 되돌림 **뒤**임을 확정. 이것이 「오검출 0」의 전제다.
- 가드 배선 — 합성 오염 재현에서 `ERROR at teardown of test_a_polluter…` ⇒ **오염원 귀속** 확인.
- `add_note` 가시성 — pytest 9 가 원인 예외 바로 아래에 출력하는 것을 실측.

---

## 3. 뿌리 — 한 문장

> **클래스 정의 모듈을 monkeypatch 한 상태에서 소비 모듈이 「처음」 적재되면, 그 소비 모듈
> 최상단의 `from … import X` 가 가짜를 자기 전역으로 복사하고 — `monkeypatch` teardown 은
> 정의 모듈만 되돌리므로 — 그 복사본이 세션 끝까지 남아, 아무것도 패치하지 않은 남의 테스트가
> 남의 대역을 쓴다.**

이 레포에서 그것을 밟는 경로(실측 **4건**):

| 오염원 테스트                                                          | 지연 import 지점                                                 | 오염된 모듈·전역                           | 관측된 피해                              |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------- |
| `…divergence_labels::…exchange_missing_resting_order…`                 | `live_signal.py:834` `_write_back_confirmed_terminal`            | `src.tasks.trading` **전역 5개**           | `test_cancel_order_task.py` **2 failed** |
| `…conditional_reconcile::…submitted_without_exchange_id_is_deferred…`  | `live_signal.py:3027` `_conditional_entry_janitor_delay_minutes` | `src.tasks.orphan_scanner.OrderRepository` | `test_orphan_scanner.py` **3 failed**    |
| `…market_data_backfill::test_backfill_returns_dict_with_required_keys` | `_async_backfill` → TimescaleProvider                            | `…providers.timescale.CCXTProvider`        | 0 (가드가 잡았다)                        |
| `…conditional_entry_sweeper::…cancels_only_inactive_owned_…`           | 스윕의 `src.tasks.trading` 지연 import                           | `src.tasks.trading._dispatch_provider`     | 0 (가드가 잡았다)                        |

`src.tasks.trading` 의 오염 전역 6개 = `OrderRepository` · `ExchangeAccountRepository` ·
`LiveSignalSessionRepository` · `ExchangeAccountService` · `BybitFuturesProvider`(앞 5개는
리컨사일러 하네스) + `_dispatch_provider`(스윕 하네스). 가드가 지목한 앞 5개 목록이 플랜 단계
인프로세스 프로브의 5쌍과 **정확히 일치**했다.

★**「DB·savepoint 문제가 아니라 주입 문제」까지는 직전 회차가 좁혀 놨다. 틀린 것은 「무엇의」
주입인가였다** — 세션이 아니라 **repo 클래스**였다. 백로그 프로브 표의 5행(행은 내내 보임 ·
`in_transaction` True · task 안의 같은 쿼리만 None)이 이 기전으로 전부 설명된다.

---

## 4. 크기 — 수리 **전**에 쟀다

| 지표                                                | 값                                                           |
| --------------------------------------------------- | ------------------------------------------------------------ |
| **S1** 2파일 repro (백로그 재현)                    | **2 failed** (+ 가드 1 error)                                |
| **S2** 전체 − 사전적재원 **6**파일                  | **3 failed + 1 error** / 3765 passed (프로브 `loaded=False`) |
| S2′ 전체 − 사전적재원 **4**파일 (codex 전 판)       | **green 3781** ⇒ **마스킹된 green**                          |
| **S3-a** 디렉터리 **18**벌 census                   | 오염원 **1건** 추가 발견 (market_data)                       |
| **S3-b** 파일 **49**벌 census (정의 모듈 패처 전수) | 오염원 **1건** 추가 발견 (sweeper)                           |
| 오염된 (모듈, 전역) 쌍                              | **8개** / 모듈 3개 / 오염원 테스트 4개                       |
| 관측된 피해 테스트                                  | **5건** (cancel 2 + orphan_scanner 3)                        |
| 전체 스위트 O1 에서의 발현                          | **0** — 알파벳상 앞선 무관한 파일 6개가 가려 준다            |

★**「전체는 green, 부분은 red」의 정체가 이것이다.** 수집은 실행 **전에** 전부 끝나므로, 문제
모듈을 최상단에서 import 하는 파일이 **하나라도** 함께 수집되면 오염이 일어나지 않는다.
그 파일 6개는 이 결함과 아무 관계가 없다(`test_dispatch_snapshot_priority` ·
`test_provider_dispatch` · `test_exchange_order_response_metric` · `test_beat_schedule` ·
`test_conditional_entry_janitor` · `integration/test_auto_dogfood`).
**그러니까 green 은 우연이었다. 시드 운이 아니라 수집 집합 운이다.**

★**census 는 창이 넓은 실행 형태에서 더 나온다** — 디렉터리 단위가 1건, **파일 단위**가 1건을
더 찾았다. 「전체 스위트에서 가드 발화 0」은 **아무것도 증명하지 않는다**(전체에서는 창이 거의
닫혀 있다 — `src.*` 214 모듈 중 수집 시점 미적재가 **9개**뿐이다).

---

## 5. 수리

### 5.1 상시 가드 — `tests/conftest.py`

- `leaked_test_doubles(module_names)` — **술어**. `unittest.mock` 객체(1) **또는 `tests.*` 에서
  정의된 객체**(2)를 `"module.attr"` 로 열거. 술어 2 를 넣은 이유는 하네스가 Mock 이 아닌
  **lambda 도 심기 때문**이다(`tests/` 에 `setattr(..., lambda …)` 126곳).
- `leaked_test_doubles_since(modules_before)` — **창**. 한 항목 안에서 **처음** 적재된 `src.*` 만 본다.
- `_leaked_since_snapshot(item)` — 스냅샷이 **없으면 검사하지 않는다**(창을 모르면 조용히 넘긴다 —
  거짓 지목은 미검출보다 나쁘다).
- 훅 2개: `pytest_runtest_setup`(**wrapper + tryfirst**)에서 스냅샷,
  `pytest_runtest_teardown`(wrapper) **post-yield** 에서 검사 → 발화 시 그 **오염원 테스트가
  teardown ERROR**. teardown 이 이미 터진 경로에서는 `exc.add_note` 로만 붙인다.

★**가드가 못 잡는 5종**(codex G1/G6, 전건 코드 대조) — ① 이미 적재된 모듈의 직접 변조
② 클로저나 객체 내부에 숨은 대역 ③ `sys.modules` 키의 모듈 객체 교체(`patch.dict`)
④ 창 안의 `importlib.reload` / `del sys.modules[…]` 후 재import(이름이 차집합에 없다 — 현재 레포
사용 **0건**) ⑤ **비-Mock 대역**(`SimpleNamespace()`·`object()` 는 `__module__` 이 없고
`functools.partial` 은 `functools` — 실측).
**「가드 발화 0」을 「전역 오염 없음」으로 인용하지 마라.**

★**가드의 실측 비용 = 0.9초**(3855 테스트 전체, 스냅샷 0.084ms + 창 계산 0.143ms per test).
스위트 시간이 259s → 281s 로 늘어 8% 로 보였지만 그것은 **실행 간 변동폭**(픽스 전에도
259/268/266s)과 신규 자식-세션 테스트 때문이다. **추정했으면 15배 틀렸다.**

### 5.2 수술적 픽스 — 「패치를 걸기 전에 그 모듈을 적재한다」 (3파일 · 4모듈)

| 파일                                        | 방식                                                                        |
| ------------------------------------------- | --------------------------------------------------------------------------- |
| `test_live_signal_conditional_reconcile.py` | `_patch_reconcile` 진입부에 **2모듈**(`trading`·`orphan_scanner`) 사전 적재 |
| `test_market_data_backfill.py`              | **모듈 수준 1줄** (같은 패치를 쓰는 테스트가 3개라 한 곳으로 덮인다)        |
| `test_conditional_entry_sweeper.py`         | `_patch_sweeper` 진입부에 1모듈                                             |

프로덕션 `src/` 는 **한 줄도 바꾸지 않았다.** 결함은 하네스의 패치 전략이다.

### 5.3 가드 자체 테스트 — `tests/common/test_module_global_poisoning_guard.py` (8건)

술어 2축 · 창 축 · **배선**(자식 pytest 세션 subprocess) · **예외 경로**(teardown 이 터지며 대역을
남기는 항목) · `src.` 이름공간 필터 · 음성 대조. 자식 세션은 `pytest_plugins = ["pytester"]` 대신
subprocess 를 쓴다 — 그 선언은 rootdir conftest 에서만 허용돼 하드 에러가 될 수 있다.

---

## 6. 판별력 — 표적 변이 (하나씩 · 전체 pytest 와 동시 금지 · 복원 sha256 대조)

사전등록 원문은 실행 **전에** 동결했다(`scratchpad/prereg-mutations.md`). 아래는 예측과 실측이다.

| ID      | 무엇을 껐나                                 | 예측                                    | 실측 (최종 트리)                          | 판정 |
| ------- | ------------------------------------------- | --------------------------------------- | ----------------------------------------- | ---- |
| **M1**  | `trading` 사전 적재                         | O4 red + `trading.OrderRepository` 지목 | **2 failed + 1 error**, 지목 일치         | ✅   |
| **M1b** | `orphan_scanner` 사전 적재                  | 하네스 단독 red + 지목                  | **1 error**, `orphan_scanner…` 지목       | ✅   |
| **M2**  | 술어 1(`NonCallableMock` → `BaseException`) | red, 술어 2 테스트 green 유지           | **5 failed / 3 passed**, 술어 2 green     | ✅   |
| **M3**  | 창(`sys.modules - before` → `()`)           | red, 술어 테스트 green 유지             | **3 failed / 5 passed**                   | ✅   |
| **M5**  | 술어 2(`__module__` 검사 제거)              | 그 축 1건만 red                         | **1 failed / 7 passed**                   | ✅   |
| **M6**  | teardown 예외 경로 제거                     | 예외 경로 테스트 1건 red                | **1 failed / 7 passed**                   | ✅   |
| **M7**  | `startswith("src.")` 필터 제거              | (G6 지적 — 처음엔 **통과했다**)         | 새 테스트 추가 후 **1 failed / 7 passed** | ✅   |
| **M4**  | (음성 대조 · 상시 단언)                     | green                                   | clean 8 passed · 전체 스위트 발화 **0**   | ✅   |

★**내 예측이 두 번 카운트를 틀렸다** — M2 를 「red 3건」으로 적었는데 실측 5건이었고(자식 세션
단언이 **두 테스트로 쪼개져 있는 것**을 셀 때 놓쳤다), M3 의 green 집합도 「3건」이 아니었다.
**방향과 축(어느 테스트가 살아남는가)은 전건 맞았다.** 숫자를 기억으로 적으면 이렇게 된다.

★**M7 은 G6 가 「아직 통과하는 변이」로 지적해 준 것이다** — 합성 모듈이 전부 `src.*` 라서
필터를 없애도 아무 테스트가 죽지 않았다. **비-src 이름으로 같은 오염을 만드는 테스트**를 넣어
닫았다. 즉 가드의 4부품(술어 1·2 · 창 · 예외 경로)과 이름공간 필터가 **각각** 판별력 있는
테스트를 갖는다.

★**M2/M3 는 구별되지만 직교는 아니다**(G6 MINOR) — 창 테스트도 `MagicMock` 을 심으므로 술어 1 을
끄면 창이 정상이어도 그 테스트가 죽는다. **생존 집합이 다르다**는 것이 판별력의 근거이고,
「한 축만 고정한 테스트」는 아니다. 과장하지 않는다.

---

## 7. 순열 매트릭스 — 픽스 후 (최종 트리에서 1회)

| ID      | 수집 집합 / 인수 순서                           | 수리 전                       | 수리 후                                   |
| ------- | ----------------------------------------------- | ----------------------------- | ----------------------------------------- |
| **O1**  | 전체                                            | 3848 passed / 46 skipped      | **3856 passed / 46 skipped** (296s)       |
| **O2**  | 전체 + `-p no:randomly`                         | 3848 / 46 (플래그는 no-op)    | **3856 / 46** (286s) — O1 과 동일         |
| **O3′** | 전체 − 사전적재원 **6**파일 (+ 사전조건 프로브) | **3 failed + 1 error** / 3765 | **3770 passed / 40 skipped** (360s)       |
| **O4**  | `labels` → `cancel_order`                       | **2 failed** (+가드 1 error)  | **14 passed**                             |
| **O5**  | `cancel_order` → `labels` (역순)                | 14 passed                     | **14 passed**                             |
| **O6**  | `tests/tasks tests/trading`                     | (미측정)                      | **1543 passed / 12 skipped**              |
| **O7**  | `tests/trading tests/tasks` (역순)              | (미측정)                      | **1543 passed / 12 skipped** — O6 과 동일 |

★**O3′ 가 이 회차의 핵심 증거다.** 사전조건 프로브가 `수집 직후 src.tasks.trading 적재 = False`
를 확인한 뒤에만 채택했고(그 전제가 깨지면 green 은 마스킹된 green 이다), 같은 수집 집합에서
**수리 전 red → 수리 후 green** 이다. 즉 전체 스위트의 green 이 더 이상 「무관한 파일 6개가
알파벳상 앞에 있다」에 의존하지 않는다.

★**O1/O2 가 같은 값인 것은 「순서 무관」의 증거가 아니다** — `-p no:randomly` 는 이 레포에서
no-op 이기 때문이다(§1.1). 순서/집합 무관의 증거는 **O3′·O4/O5·O6/O7 의 쌍대 비교**다.

★**BE 3848 → 3856(+8)** = 신규 가드 테스트 8건. 그 외 기존 테스트 수치 변화 0.

---

## 8. 게이트

| 게이트                               | 결과                                                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `uv run ruff check .` (전체)         | `All checks passed!`                                                                                                                 |
| `uv run mypy src/`                   | 214 source files clean                                                                                                               |
| BE pytest (O1)                       | **3856 passed / 46 skipped**                                                                                                         |
| BE pytest 순열 O2~O7                 | 전건 green (§7)                                                                                                                      |
| `make docs-audit`                    | clean (링크 · 폐기 경로 · 줄길이 상한)                                                                                               |
| `scripts/bl-audit.sh`                | **3면 정합** · active 151 / 전체 240                                                                                                 |
| FE vitest / typecheck / lint / build | **미실행 — FE diff 0줄**(변경은 `backend/tests/**` + docs 뿐). baseline 대조용으로 착수 시 1회 실행해 **1242 passed(205 파일)** 확인 |
| MCP playwright                       | **미사용** — 이유는 `.claude/gates/gate-trustworthiness/screen.ok` (화면 축이 위험 표면이 아니다)                                    |

★**커밋 후 재측정** — pre-commit 이 `ruff format`(커밋 1: 가드 테스트 파일 재정렬)과
`prettier --write`(커밋 2: 표 정렬)을 돌렸으므로 확정 트리에서 다시 쟀다.

| 커밋 후 게이트        | 결과                                                     |
| --------------------- | -------------------------------------------------------- |
| `uv run ruff check .` | `All checks passed!`                                     |
| `uv run mypy src/`    | 214 source files clean                                   |
| BE pytest             | **3856 passed / 46 skipped** (391s) — 커밋 전과 **동일** |
| `make docs-audit`     | clean                                                    |
| `scripts/bl-audit.sh` | 3면 정합 · active 151 / 전체 240                         |

코드 커밋 `e51b0f86`. 문서 커밋은 **이 파일이 담긴 커밋**이다 — 자기 해시는 적지 않는다
(amend 하면 즉시 틀린 참조가 된다. 실제로 한 번 그렇게 적어 놓고 고쳤다).
★**PR 은 미생성** — 이 브랜치는 `stage/metric-guard-residual`(3커밋) 위에 쌓여 있어 PR 이 두
회차를 함께 담는다.

---

## 9. 남긴 것

- ★**가드가 못 잡는 5종**(§5.1). 특히 ④ reload 계열은 현재 사용 0건이라 **잠재 갭**으로만 남겼다.
- ★**`except BaseException` 의 폭을 고정한 테스트는 없다** — 자식 세션은 `RuntimeError` 만 던지므로
  `except Exception` 으로 좁혀도 통과한다(G6 MINOR). `BaseException` 이 더 정확하다고 판단해
  유지했고, **그 폭이 미검증이라는 사실을 여기 적는다.**
- ★**세션 스코프 fixture 가 의도적으로 유지하는 합법적 대역**이 새 소비 모듈로 복사되면 첫 소비
  항목이 오검출된다(G6 MINOR). 현재 그런 fixture 는 없고(디렉터리 18벌 + 파일 49벌 + 전체 스위트
  오검출 0), 생기면 처방은 같다 — **패치 전 사전 적재**.
- **`pytest-randomly` 는 도입하지 않았다**(사용자 결정). 도입하면 시드 스윕이 가능해지지만
  baseline 수치의 의미가 재정의되고 미지의 red 가 다량 나올 수 있다 — 별도 스프린트 감이다.
- **[BL-580] 잔여 129곳**(order_service 10 · closed_pnl 7)은 착수하지 않았다 → 다음 스프린트.

---

## 10. 회고 — 이번 회차가 실제로 밟은 것

1. ★★★**「측정 먼저」가 전제 두 개를 깼다.** 수리에 손대기 전에 baseline 을 두 번 재라는 지시를
   따랐더니 **그 지시가 가정한 도구(`pytest-randomly`)가 없었다.** 「두 값이 같다」를 「순서 의존이
   없다」로 읽으면 정반대 결론이 됐을 것이다. **같은 값이 나온 이유를 물어라.**
2. ★★★**배제 목록이 뿌리를 가리키고 있었다.** 「최상단 import 라 patch 가 안 닿는다」는 절반만
   참이었고, 나머지 절반이 정확히 이 결함이다. **배제의 근거가 조건부이면 그 조건을 적어라.**
3. ★★★**한 번 고치고 끝난 줄 알았다 — 세 번 더 있었다.** 픽스 1줄로 2파일 repro 가 green 이
   됐지만, 같은 종류가 **다른 오염원·다른 모듈·다른 도메인으로 3건 더** 있었다. 찾은 것은 손
   추론이 아니라 **가드를 먼저 넣고 수집 집합을 좁혀 census 를 돌린 것**이다. 그리고 **디렉터리
   단위 census 로도 부족했다** — 파일 단위가 1건을 더 찾았다. **창이 넓은 실행 형태로 재라.**
4. ★★★**「전체 스위트에서 가드 발화 0」은 아무것도 증명하지 않는다** — 전체에서는 창이 거의
   닫혀 있다(`src.*` 214 모듈 중 수집 시점 미적재 **9개**). 감시 도구를 넣었으면 **그 도구가
   무엇을 볼 수 있는 조건**을 먼저 재라.
5. ★★**green 이 운일 수 있다는 것을 숫자로 보였다** — 무관한 파일 **4개**를 빼면 green(3781),
   **6개**를 빼면 red(3 failed). 차이는 **어떤 파일이 알파벳상 앞에 있는가**였다. 실험의 ignore
   집합을 손으로 고르면 **마스킹된 green** 을 얻는다 ⇒ AST 폐포로 세고, 전제를 프로브로 단언한
   뒤에만 결과를 채택했다.
6. ★★**codex 를 코드 전에 걸어 3건이 설계를 바꿨다** — 그중 하나는 내 변이의 **판별력 0** 이었다.
   두 회차 연속 같은 실수다. 이제 변이를 적을 때 「무엇을 끄는가 / 어느 테스트가 살아남는가」를
   함께 적는다.
7. ★★**codex 도 틀렸고 나도 틀렸다.** G1 은 사전적재원 6개 중 5개만 셌고, 나는 프로덕션 미수정의
   근거를 「순환 import」로 잘못 적었다(실측: 순환 0). 그리고 **G1 MINOR 가 권한 단순화(`tryfirst`
   평범 훅)를 G6 MAJOR 가 되돌렸다** — 같은 evaluator 의 두 라운드가 반대를 가리킬 수 있다.
   **findings 전건 코드 대조**가 규약인 이유다.
8. ★★**문서가 코드보다 늦어 모순이 됐다** — 네 번째 오염원을 고쳐 놓고 backlog/status/dev-log 는
   「3곳·6개」로 닫아 뒀다. G6 가 그것을 잡았다. **수리 뒤에 개수를 다시 세라.**
9. ★★**비용을 추정하지 말고 재라** — 가드가 스위트를 8% 늦춘 것처럼 보였지만 실측은 **0.9초**,
   차이는 변동폭이었다. 추정했으면 15배 틀렸다.
10. ★**내가 추가한 에러 경로에 테스트가 없었다.** G1 지적으로 `except` 분기를 넣고 검증 없이
    지나갈 뻔했다. 자식 세션에 **teardown 이 터지며 대역을 남기는 항목**을 추가해 고정했다.
11. ★**게이트 도중에 트리를 바꿨다** — 전체 매트릭스가 도는 중에 리팩터를 넣어 **혼합 트리**를
    재게 됐다. 두 번 중단하고 확정 트리에서 다시 돌렸다. 이 레포가 이미 아는 함정을 또 밟았다.
12. ★**요약 줄을 통째로 문자열 비교하지 마라** — `"1 passed, 1 error"` 로 단언했더니 실측은
    `1 passed, 6 warnings, 1 error` 였다.
