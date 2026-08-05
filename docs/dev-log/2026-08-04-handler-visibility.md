# 2026-08-04 — handler-visibility + nightly-real-broker (함대 2워커 + 적대 검증 2벌)

> 한 회차에 두 갈래를 병렬로 돌렸다. 파일 집합이 서로소라 통합 충돌이 **0** 이었다.
> **갈래 A** = `live_signal.py` 해체(행위 변경 0) · **갈래 B** = [BL-024] nightly real-broker 신뢰성 복구.
> 체계 = Generator ×2 (claude 워크트리 워커) / Evaluator ×2 (codex + 별도 claude) / CONTROL = 메인 체크아웃.

---

## 1. 헤드라인

|                                         |                                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------ |
| `_reconcile_conditional_entries`        | 876줄 · **try 본문 845줄** · 중첩 3 → **46줄 · 8줄 · 1**                       |
| `_evaluate_session_inner`               | 796줄 · **try 본문 770줄** · 중첩 2 → **17줄 · 1줄 · 1**                       |
| 본체 운반자 (`_inner` · `_with_engine`) | **`try` 0개 · 중첩 0** — 모든 핸들러가 이름 붙은 헬퍼로                        |
| 함수 수 / 신규 `.py` 소스 파일          | 45 → **71개** / **0개**                                                        |
| nightly real-broker                     | **10/10 실패(07-25~08-03)** → 원인 확정·수리 + 계약 감사 13테스트              |
| 게이트                                  | BE **4030 / 45** · ruff 0 · mypy 0(216) · census **40/84 불변** · bl-audit 154 |

---

## 2. ★착수 전제가 실측으로 뒤집힌 것 3건

**2.1 nightly 는 E2E 로직이 아니라 자기 자신 때문에 죽고 있었다.**
[BL-024] 는 「skeleton 을 채운다」로 등재돼 있었다. 실측은 달랐다 —
`gh run list` **10/10 failure**, `gh issue list --label flaky-real-broker` **89건 전부 OPEN**,
그리고 `gh run view --log` 의 실패 지점은 pytest 가 아니라 **`alembic upgrade head`** 였다:

```
TRADING_ENCRYPTION_KEYS:                      ← secrets.TRADING_ENCRYPTION_KEYS_TEST 부재 → 빈 문자열
File ".../alembic/env.py", line 24, in <module>
pydantic_core...ValidationError: TRADING_ENCRYPTION_KEYS must contain at least 1 Fernet key
```

⇒ **pytest 는 한 번도 실행된 적이 없다.** 89건은 broker flakiness 의 증거가 **아니다.**
★그리고 이 고장은 **alembic 스텝에만** 해당한다 — `tests/conftest.py:25-28` 이 pytest 에서는
빈 키를 즉석 Fernet 로 채운다. 「빈 secret 이면 무조건 죽는다」로 일반화하면 틀린다.

**2.2 함대가 `origin/main` 을 base 로 잡았다.**
`herdr-fleet.sh` 기본 `BASE="origin/main"` 이라 워크트리 3벌이 통합 브랜치보다 **14커밋 뒤**로 생성됐다.
안 잡았으면 `deepen` 이 **census 96 시절의 낡은 파일**을 해체했다. ★**`--base` 를 명시해라.**

**2.3 「BL-024 에 상태 줄이 없어 bl-audit 이 UNKNOWN 으로 떨군다」는 거짓.**
`scripts/bl-audit.sh` 판정 우선순위 **규칙 5 = 「아무 신호 없음 → ACTIVE(백로그 기본값)」**.

---

## 3. ★★★내 검증 도구가 세 번 틀렸다 — 그 과정이 이 회차의 최대 수확

「행위 변경 0」은 도구 하나에 걸려 있었다. 그 도구를 **믿지 않는 절차**를 세 겹으로 돌렸다.

**3.1 1차 — 가드 사이트 59개를 통째로 못 봤다.**
가드 형태가 `_count_safely(qb_metric, label=…)` 라 `.labels().inc()` 가 **AST 에 아예 없다**
(`metrics_multiproc.py:40` 이 counter 를 객체로 받아 안에서 mutate 한다).
`guarded: 0` 이 그 증거였다. 교차검증 2건(가드 59 = grep 59 · 비가드 34 = census 34)으로 닫았다.

**3.2 2차 — 적대 검증에서 42건 주입 중 16건 거짓 음성.**
별도 평가자에게 반증을 시켰다. 통과해 버린 것들:

| 구멍              | 통과한 변이                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| **try 구역**      | 「체결 확정 **성공**」 counter 를 「거래소 조회 **실패**」 `except` 로 이동 · `finally` 밖으로 빼 영구 사문화 |
| **라벨 값**       | 값 맞바꾸기(`stage=A,category=B`→`B,A`) · f-string 화 · 동적 값 치환                                          |
| **mutation 인자** | `.set(len(pending))` → `.set(0)`                                                                              |
| **제어 흐름**     | `return` 뒤로 이동 · 감싸는 `if` 반전 · 3회 루프 안으로                                                       |

뿌리: `in_try_body` 가 **`body` 만** 인정해서 site 가 `except`/`else`/`finally` 구역이면
**감싸는 `try` 가 사슬에서 통째로 사라졌다** — ★**93개 중 24개(25.8%)**.
수리 후 예전에 통과하던 변이 재주입 → **4/4 CAUGHT**.

**3.3 3차 — 고친 도구가 이번엔 거짓 양성 7/7.**
`control_context` 에 폐포를 안 걸어서, 헬퍼로 빼면 호출부의 `for`/`with` 가 사라져 diff 가 났다.
★codex 가 라운드 1 에서 지적한 A5(한 홉 콜그래프 부족)와 **똑같은 병을 내가 나중에 추가한 필드에서 반복**했다.

**3.4 그 과정에서 적대 검증도 못 찾은 구멍을 하나 더 찾았다(Z1).**
`if rows != 1: return None` 같은 **선행 조기-return 가드**의 조건을 뒤집으면 계측이 정반대 경우에
발화하는데, 그 `if` 는 site 를 **감싸지 않아** `control_context` 에 안 잡힌다.
필드를 추가했으나 **정상 추출마다 발화**해서(헬퍼가 None 반환 → 호출부가 검사 = 이번 리팩터의 표준 형태)
**정규 동치에서 빼고 별도 델타로 보고**하게 했다.
★**따라서 그 축은 정규 동치가 아니라 `git diff` 와 codex 가 잡는다. 합쳐서 말하면 안 된다.**

---

## 4. ★codex 가 「행위 변경 0」을 반증했다 — 내 도구가 **구조적으로 못 보는 축**

**MAJOR — lazy import 를 헬퍼 안으로 옮겨 실패 시점이 커밋 뒤로 밀렸다.**

| 심볼                            | baseline                            | 변경본(수리 전)                                                                        |
| ------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `get_ccxt_provider_for_worker`  | `:1096` — outer `try` 진입 **직후** | `:1130` — 헬퍼 안. 호출은 `_confirm_exchange_terminals`(→`order_repo.commit()`) **뒤** |
| `run_live` (★CONTROL 추가 발견) | `:2165` — 블록 최상단               | `:2567` — 헬퍼 안. 호출은 `try_claim_bar` **뒤**                                       |

⇒ import 실패 시 baseline 은 **커밋 전에** 빠지고, 변경본은 **terminal 전이를 커밋하고 bar 를 claim 한 뒤** 빠진다.
**MINOR** 는 그 결과로 두 헬퍼 docstring 의 「이 함수가 핸들러를 소유한다」가 거짓이 된 것 —
★**이번 과제의 정중앙**이다(산출물이 바로 그 docstring 이므로).

수리 = **최상단 블록 복원 + 헬퍼 안 중복 import**. 두 제약을 동시에 만족한다 —
조기 실패 시점이 보존되고, `test_live_signal_import_blast_radius` 는 **모듈 top-level 만** 금지한다.
★수리 후 실측: 두 함수 모두 **부작용 뒤 import 0개**.

**codex 가 확인해 준 것:** `_PROTECTED_SITES` 재앵커 정확 · **중복 삼중항 2개가
`_place_planned_entry` / `_resolve_current_position` 으로 분리**(계획이 노린 순이득 실현) ·
조기 종료 9조건 보존 · `converted_defer` 만 전체 루프 중단 · outbox 경계 유지 ·
`finally: engine.dispose()` 유지 · 새 동어반복 테스트 없음.

---

## 5. ★갈래 B 적대 검증 — 고장 주입 21종, MAJOR 3

- **F1** `_no_op_enqueue` 는 **function-scope** autouse 인데 자기정리는 session finalizer 이후에 돈다
  ⇒ **청산 시점엔 monkeypatch 가 이미 원복돼 있다.** 실측 `TEST-BODY BLOCKED → LAYER1 REAL → LAYER2 REAL`.
  로컬 워커가 **앱(개발) DB** 를 보므로 `sweep_conditional_entries` 가 소크 중 실세션을 훑는다.
  수리 = 차단을 `run_cleanup` 이 **자기 구간에서 직접** 건다.
- **F2** RESIDUAL 보고가 `sys.stderr` 인데 워크플로는 `| tee` — **stdout 만 받는다.**
  이슈 본문 triage 항목이 **도달 불가**였다. 수리 = `2>&1 | tee`, 그리고 **감사가 그걸 잠근다.**
- **F3** `_harness.py` 함수 본문 295줄 중 **273줄(93%) 미실행**. 사용 테스트 0개 ⇒ **깨진 게 아니라 미검증**.
  ★코드 주석이 **존재하지 않는 리허설**을 주장하고 있었다 → 정정.
- 평가자가 **자기 가설 3건을 스스로 반증**했다(sessionfinish 순서 · `exitstatus` 무시 · 주석 앵커) — phantom 아님.

---

## 6. celery 실주행 검증 — **재적재의 지문을 잘못 알고 있었다**

md5 일치만으로는 부족하다(파일의 증거이지 **프로세스**의 증거가 아니다). `watchfiles` 로그를 찾았는데
**24시간 0건**이라 「재적재 안 됨」으로 오판할 뻔했다. 실제 지문은 **celery 기동 배너**다:
`Connected to redis` → `mingle` → `celery@… ready.` — **`watchfiles` 는 조용하다.**

통합 코드로 재기동 확인 후: `evaluate_all` **2회** · `sweep_conditional_entries` **12회** 성공 ·
에러 **0** · `live_signal.*` **4태스크 전부 등록**.
⇒ 「함수-지역 import 를 올리면 celery 태스크 미등록」 위험이 닫혔다.
★**단 `due_count: 0` 이라 `_evaluate_session_inner` 본체는 미검증**이다(활성 세션 0).

---

## 6-b. ★교훈을 문서가 아니라 **게이트**로 동결했다

`backend/tests/tasks/test_live_signal_handler_visibility.py` (4테스트, 커밋 `15bb91d0`).
2026-08-04 오독의 뿌리는 판단력이 아니라 **모양**이었다 — 845줄짜리 `try` 본문 + 3겹 중첩이면
「이 계상이 어느 핸들러에 잡히나」를 사람이 안정적으로 못 읽는다. 그 모양이 **다시 자라는 것을 막는다**:

| 테스트                                                            | 무엇을 red 로 만드나                                                          |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `test_every_declared_helper_actually_exists`                      | ★**공허화 방지** — 헬퍼 이름이 바뀌면 나머지 셋이 **검사 대상 없이 통과**한다 |
| `test_the_split_families_have_no_nested_try`                      | 해체한 **28개 함수**에 `try` 중첩이 다시 생기면                               |
| `test_remaining_nested_try_functions_are_exactly_the_frozen_list` | 잔여 중첩 **5개를 정확값으로 동결** — 늘 수도, **조용히 줄 수도** 없다        |
| `test_no_try_body_exceeds_the_frozen_maximum`                     | `try` 본문 천장 **845 → 225** 초과 시                                         |

★워커가 **변이로 판별력을 증명**했다(`_positions_are_aligned` 의 `try` 안에 `try` 를 넣어 red 확인).
★동반한 `live_signal.py` 43줄 변경은 **전부 docstring**(`_evaluate_session_with_engine` 의 9단계
서술을 **헬퍼 이름 지도**로 교체)이고, CONTROL 재측정에서 정규 동치는 `control_context` 제외 시 **0/0**.

---

## 7. 남은 것 (합치지 않고 갈라 적는다)

**증명한 것** — 핸들러 가시성(최대 `try` 본문 845→8) · 계측 인벤토리 93 site 의 핸들러 사슬·라벨 원문·
mutation 인자·가드 플래그 전건 동일 · 모의 상호작용 트레이스 바이트 동일 · celery 적재·태스크 등록 ·
nightly 계약 13항목 감사(판별력 주입으로 실증) · DSN 하드가드 · 자기정리 순서 계약.

**증명 못 한 것** — ★**실거래소는 1바이트도 검증되지 않았다**(자격증명 부재) ·
`_evaluate_session_inner` 본체 실주행 · W1 수리가 실제 nightly 를 green 으로 만드는 것 ·
`_harness.py` 의 93% · 문장 순서 축(도구가 아니라 codex·`git diff` 가 본다).

**남은 구조 부채** — `_evaluate_session_with_engine` 506줄(Kind B 추출 E8~E14 미완) ·
`_place_planned_entry` 236 · `_reconcile_conditional_entries_inner` 203 ·
`_async_dispatch_event` 256줄/`try` 본문 225줄(★**이번 범위 밖**, 이제 이게 최대다).
