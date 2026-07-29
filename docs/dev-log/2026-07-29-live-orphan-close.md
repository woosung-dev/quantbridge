# live-orphan-close — 고아는 이미 닫혔고, 대신 계측기가 셋 다 틀렸다 (BL-537 / BL-536)

> 2026-07-29 · 브랜치 `feat/live-orphan-close` · main@`65ee1871` 기준 · **마이그레이션 0 · 새 엔드포인트 0**

## 한 줄

BL-537 이 "고아 포지션을 앱에서 못 닫는다" 고 했는데 **실제로 만들어서 눌러보니 닫혔다.** 대신 그 재현이 진짜 결함 하나(누르면 실패하는 버튼)와, 이번 스프린트의 계측 전제를 **세 번** 무너뜨린 발견 하나(BL-543)를 내놨다.

---

## 무엇을 고쳤나

`backend/src/trading/services/close_service.py` — **1 파일**. settings 게이트 제거 + leverage/margin_mode 폴백 체인. 테스트 2 파일.

```python
# before — 청산을 전략 설정으로 막았다
except ValidationError as exc:
    raise HTTPException(status_code=422, detail="settings_invalid") from exc
if validated_settings is None:
    raise HTTPException(status_code=422, detail="settings_unset")

# after — 흘려보내고 폴백으로 채운다
except ValidationError:
    validated_settings = None
```

---

## ★핵심 발견

### ★★★ BL-537 의 전제가 실측으로 반증됐다

BL 은 "세션이 꺼지면 포지션이 앱에서 **보이지도 닫히지도 않는다**" 고 적었다. 계정 스코프 표면에서는 틀렸다 — BL-498 이 이미 탈출구를 지어 뒀다:

- `DELETE /live-sessions/{id}` 는 행을 지우지 않고 **비활성화만** 한다 (`router.py:486`)
- `list_by_account` 는 `is_active` 를 **의도적으로 안 거른다** (`live_signal_session_repository.py:97`)
- 코크핏은 **등록된 모든 계정**을 순회한다 (`trading-cockpit.tsx:147`)

거래소에만 `long 0.001` 을 남겨 고아를 인위로 만들고, 프로덕션 서비스 배선 그대로 눌렀다:

| 단계             | 실측                                                                     |
| ---------------- | ------------------------------------------------------------------------ |
| 계정 스코프 조회 | `rows=1` · `close_blocked_reason=None` · `closable_session_id=b9e027c5`  |
| 귀속된 세션      | **07-28 fail-closed 로 죽은 바로 그 세션** (`is_active=f`)               |
| 청산             | **202** `order_id=47f3ce52`                                              |
| `trading.orders` | `reduce_only=t` · `state=filled` · `strategy_id` non-null · `leverage=2` |
| 거래소           | **flat**                                                                 |

07-28 에 provider 원시 호출로 내려간 건 앱에 경로가 없어서가 아니라 **그 경로를 안 썼기 때문**이다. BL 은 세션 스코프 API 시그니처만 보고 작성됐다.

★**그래서 계정 스코프 엔드포인트를 짓지 않았다.** 지었으면 이미 되는 것 위에 두 번째 구현을 얹었을 것이고, 그게 이 버그 부류의 원인이다. 세션 행이 **아예 없는** 잔여 케이스(웹훅 경로)는 BL-541 로 이연 — **아직 한 번도 실측된 적이 없다.**

### ★★★ 대신 진짜 결함 — 누르면 실패하는 버튼

`close_service.py:49-54` 가 청산을 `settings_invalid`/`settings_unset` 으로 **422 거부**하는데, `position_service.py:298-306` 의 `close_blocked_reason` 은 **그 게이트를 평가하지 않는다.** BL-498 이 막겠다고 선언한 실패 모드(`position_service.py:284-286` 주석)가 settings 축에 그대로 남아 있었다.

그리고 그 422 는 **아무것도 지키지 않는다.** 코드 대조 3건:

- `providers.py:851` — `if not order.reduce_only:` 가 `set_margin_mode` 와 `set_leverage` 를 **둘 다** 감싼다 → 두 값은 청산에서 **거래소에 도달하지 않는다**
- `providers.py:824-830` — 다만 `None` 이면 fast-fail (NOT NULL 계약)
- ★`_has_leverage`(`tasks/trading.py:148-168`) — `leverage > 0` 이 **futures vs spot provider 판별자**다. `0/None` 이면 청산이 조용히 **스팟**으로 나가 linear 포지션을 못 닫는다

즉 원장 필드 + dispatch 판별자일 뿐이다. 폴백은 **첫 양수**를 취한다(거래소 포지션 → 전략 설정 → `1`) + 스키마 범위 클램프.

### ★★★ BL-543 — 세션은 **태어날 때부터** 갈려 있다

soak 1분차, 신규 세션이 `live_signal_events` **0건** · `orders` **0건**인데 엔진은 이미 `position_size=0.029765` 를 들고 있었고 거래소는 flat 이었다. `engine_only` 카운터는 **55 → 57**(평가 2회, 주문 0건).

원인은 코드로 확정했다 — `run_live` 는 매 평가마다 300 bar 를 재생하는데 dispatch 대상은 **마지막 bar 의 이벤트뿐**이다(`event_loop.py:410` `last_bar_events`). 재생 구간에서 열린 포지션은 **주문이 된 적이 없는데 엔진 상태에는 남는다.**

4분차에 하류까지 이어졌다 — 첫 이벤트가 `close / failed / close_position_flat`:

> **재생이 제조한 포지션 → 엔진이 close 를 emit → 거래소는 flat → `close_position_flat`**

BL-530 분해표에서 `close_position_flat` 16 + `110017 current position is zero` 30 = **46/51(90%)** 이 "유령 포지션" 갈래였고 BL-530 은 잔여 원인을 **진입 유실**로 지목했다. 유령의 **최소한 일부는 진입 유실이 아니라 재생 아티팩트**다.

★**BL-536 이 자기 첫 step 으로 지정한 계측기가 바로 이것이다.** 그대로 따랐다면 "engine_only 가 크게 남았다 → 유실이 크다" 로 오독하고, 사라지지 않을 문제에 새 상태 저장소를 지었을 것이다 — BL-522 가 경고한 그 함정에 **BL-522 가 고른 계측기 때문에** 빠질 뻔했다.

### ★★★ 그 다음 하류는 계측이 아니라 가용성이었다

soak leg 1 이 `gap_resync_position_mismatch` 로 죽었다. 조용한 정상화는 **거래소 flat AND 엔진 flat** 일 때만 탄다(`live_signal.py:1573`). 그 시점 거래소는 **실제로 flat 이었고**(확인), 막은 것은 **엔진의 재생 포지션**이었다.

그 코드의 주석이 직접 이렇게 적어 뒀다 — _"모든 장기 공백이 세션을 죽인다 — 수면·배포 공백이 정확히 그 경로다"_. **그 수리가 겨냥한 실패가 BL-543 때문에 되살아나 있다.** >5분 공백은 세션을 거의 확실히 죽인다.

### ★★ 내 분모가 같은 창에서 두 번 틀렸다

1. `engine_only` — BL-543 으로 무효.
2. 그걸 고쳐 잡은 `live_signal_events WHERE action='entry'` **도 틀렸다.** 조건부 진입은 events 테이블을 **거치지 않고** `_reconcile_conditional_entries` 가 `OrderService` 를 직접 부른다. events 로 보면 창 안 진입이 **0건**인데 원장에는 **16건**이 있었다.

올바른 계측기는 `orders.idempotency_key` 분해뿐이다(`live-close-diagnostics.md` §3). ★**"진입 이벤트" 라는 이름을 믿고 테이블을 골랐다** — 이름이 아니라 **쓰는 쪽 코드**를 따라갔어야 했다.

### ★★ 0 이면 계측기를 먼저 의심 — 또 맞았다

metric 스냅샷이 `계열 0` 을 보고했는데 `.metrics` 에는 파일이 **6798개** 있었다. 원인은 `prometheus_client` 가 Counter 의 **family 이름에서 `_total` 을 뗀다**는 것 — `m.name` 을 `..._total` 로 매칭한 내 필터가 틀렸다. 데이터가 아니라 자를 의심하는 규칙이 또 값을 했다.

### ★ "원장·게이트가 유지된다" 를 잠그는 테스트가 **부분적으로만** 있었다

기존 `test_service_orders_kill_switch.py:116-189` 는 flatten 의 **우회**만 단언한다. 2종을 추가했다. ★**변이 검증이 내 주장을 정정했다** — 처음엔 "둘 다 미커버" 라고 봤는데, M5(reduce-only 원장 미기록)를 넣자 **기존 테스트도 같이 깨졌다**(`response.id` 경유 간접 검출). 진짜 미커버는 **소유 게이트(M4) 하나**였다.

---

## 게이트 (실측, `feat/live-orphan-close`)

BE **3424**(baseline 3415, **+9**) / ruff **clean** / mypy **212 clean** / **마이그레이션 0** / FE **무변경**(H2 미착수라 프론트 0 파일).

변이 **6종 전건 판별** — M1 settings 게이트 복원 · M2 폴백 leverage 0 · M3 클램프 제거 · M4 소유 게이트를 `if not flatten:` 밑으로 · M5 reduce-only 원장 미기록 · M6 `is_finite()` 가드 제거. 변이·복원은 문자열 치환 쌍으로만 했고 복원 후 **grep + 재실행 + `git diff --stat` 로 대상 파일이 diff 에 없음**까지 확인했다.

★mypy 가 실제 결함을 잡았다 — `_FALLBACK_MARGIN_MODE = "cross"` 가 `str` 로 추론돼 `Literal["cross","isolated"]` 계약을 깼다.

★**`ruff format` 에 대한 내 판단을 정정한다.** 세션 중반엔 "이 레포 게이트 아님"으로 적었다(손대지 않은 `router.py`·`position_service.py` 도 "would reformat" 이 뜬다 → **CI 게이트가 아닌 건 맞다**). 그런데 커밋해 보니 **lint-staged pre-commit 훅이 staged 파일에만 `ruff format` 을 돌린다.** 즉 "게이트 아님" 은 CI 축에서만 참이고 커밋 축에서는 거짓이다 — 그래서 내 파일들은 커밋 시점에 재포맷됐다(동작 무변경, 재실행 25 passed 확인). **한 축에서 관측한 것을 전체 진술로 쓰면 안 된다.**

---

## soak (Bybit demo) — 05:51:05Z → 08:48Z

**leg 1** 05:51:05Z → 07:15:22Z (1h24m) — `gap_resync_position_mismatch` 로 종료(위 §가용성).
**leg 2** 07:17:55Z → 08:48Z (1h31m) — **중단 없이 완주.** 종료는 프로덕션 deactivate 경로(sweep 포함), **고아 잔여 0** 확인.

깨끗한 창 = **성공 평가 160회 ≈ 2h40m.** 1분봉이라 평가 수가 창 길이를 **독립 확인**해 준다.

| 채널                          |   합산 |   /시간 | 직전 기준선 |
| ----------------------------- | -----: | ------: | ----------- |
| C1 잔여 거절 (110092/110093)  |  **2** |    0.75 | 1건         |
| C2 `deferred_market_inflight` | **12** | **4.5** | **14/시간** |
| C3 부분체결                   |  **7** |     2.6 | 미측정      |
| C4 취소가 트리거를 이김       |  **0** |       0 | 미측정      |
| C5 사전 게이트 거부           |  **0** |       0 | 미측정      |
| **합**                        | **21** | **7.9** |             |

**진입측 원장 (전량 `cond`):** `filled` **10** · `rejected` **2**(110092·110093) · `cancelled` **25** · `submitted` 1.
★`cancelled` 25 **= `replaced` 25 와 정확히 일치** → 전량 스톱 재등재 churn 이다. **원장과 카운터가 독립적으로 같은 값을 말한다** — 서로를 검산해 준 유일한 지점.

**유실률 = 2 / (10+2) = 16.7%**

### 판정 = **유지** (사전등록 문턱 그대로)

소멸 ✗(유실률 0 아님) · 축소 ✗(최대 채널 C2 **57%** < 70%) · **유지 ✓**(유실률 ≥10% **그리고** 채널 분산 — 두 근거 모두).

★**단 착수 순서가 바뀐다 — BL-543 이 선행이다.** 유실은 실재하지만 BL-543 이 계측기를 오염시키고 세션 가용성까지 깎는다. 정렬 없이 "전환 의도 영속화" 를 지으면 **재생이 계속 제조하는 포지션 위에** 상태를 얹게 된다.

★**C2 감소(14 → 4.5/시간)를 개선으로 주장하지 않는다.** 이 창엔 시장가 전환이 **0건**이었고 C2 는 전부 **청산 시장가 주문이 in-flight 인 동안** 났다. 기전이 "전환이 defer 를 만든다" 에서 **"close 가 진입 reconcile 을 defer 시킨다"** 로 바뀌었으므로 두 값은 같은 것을 세고 있지 않다. 직전 스프린트가 "잡음이라 개선 주장 안 함" 으로 처리한 것과 같은 규율.

### 부수 확인

- **`110017 reduce_only_violation` 2건**(청산측) — 유령 포지션이 여전히 발생한다. BL-543 의 서명과 일치.
- ★**`direction_transient` 2건 — PR #498 의 수리가 실주행에서 작동했다.** 방향 불일치 1차 strike 가 두 번 떴고 **둘 다 자기해소돼 세션을 죽이지 않았다.** #498 이 겨냥한 "한 bar 짜리 skew 로 살아 있는 세션을 죽이는" 회귀가 실제로 막힌 것을 실주행이 확인했다.

---

## 최종 codex 리뷰 (2026-07-29, 머지 전)

**GATE: FAIL → 수리 후 PASS.** P1 1건 + P2 2건, **오탐 0**.

★**진단 자체가 한 번 함정을 밟을 뻔했다** — 이 브랜치는 **커밋이 0개**라 스킬 기본값인 `git diff main...HEAD` 가 **빈 diff** 다. 그대로 돌렸으면 codex 가 아무것도 못 보고 **PASS 를 냈을 것**이다. `git diff main`(워킹트리)으로 명시해 넘겼다. **"리뷰가 통과했다" 는 리뷰가 무엇을 봤는지와 별개다.**

### ★★★[P1] 서사는 고치고 운영 문서는 안 고쳤다

`live-close-diagnostics.md` §7 이 유실률 분모로 **`live_signal_events WHERE action='entry'`** 를 처방하고 있었다. 그런데 **나는 같은 세션 안에서 그 계측기가 틀렸다는 걸 이미 발견했고**(조건부 진입은 events 를 안 거친다 — events 0건 vs 원장 16건), `status.md` 와 dev-log 는 정정했으면서 **정본 reference 는 그대로 뒀다.**

문서가 스스로 모순됐다 — 같은 절이 "유실률은 **진입측 원장**으로 잰다" 라고 써놓고 원장이 아닌 테이블을 쿼리했다. **다음 사람이 여는 것은 서사가 아니라 정본이다.** 원장 기반 SQL + churn 검산(`cancelled` 개수 = `replaced` 차분)으로 교체했다.

> 교훈: **발견을 서사에 적는 것과 절차를 고치는 것은 다른 작업이다.** 계측기가 무효로 판명되면 그 계측기를 처방하는 **모든** 문서를 같은 커밋에서 고쳐야 한다.

### ★[P2] BL-543 을 보편 명제로 과장했다

"엔진 flat 상태는 만들 수 없다" 는 너무 세다. 갈리는 조건은 **재생 종료 시 엔진 non-flat AND 거래소 flat** 이고, 재생이 flat 으로 끝나면 안 갈린다 — 전략·창에 달렸다. 실측 1건(n=1)에서 보편 명제를 뽑았다. 세 문서 전부 범위 한정으로 정정. ★**남는 주장은 여전히 유효하다** — 세션 시작 시점에 그것을 **통제하거나 예측할 수단이 없다.**

### ★[P2] 비유한 leverage 가 🔴 청산을 500 으로 만든다

`_position_snapshot_from_ccxt` 는 leverage 를 **`finite_only` 없이** 파싱한다(`providers.py` `_decimal_or_none(..., strict=True)`). 거래소가 malformed 값을 주면 `Decimal("NaN")` 이 올라오고 **`int(Decimal("NaN"))` → `ValueError`** 로 청산이 500 이 된다. 내가 클램프로 막으려던 실패 부류(필드 하나 때문에 청산이 막히는 것)를 **다른 문으로 그대로 열어 뒀다.** `is_finite()` 가드 + 테스트 2건 추가(변이 M6 판별 확인).

### codex 가 내 자기정정을 확인해 줬다

원장 락 테스트에 대해 — _"It would, correctly, still pass if the ownership guard alone were deleted... The pre-existing flatten test already indirectly detected a missing ledger save, so this is stronger/direct coverage, not wholly new coverage."_ 내가 변이 M5 후 스스로 정정한 내용과 일치한다.

**Q1 검증 통과** — reduce-only 에서 `set_margin_mode`/`set_leverage` 미호출 확인, `_close_leverage` 는 항상 `[1,125]` 정수 반환(NaN 수리 후), `margin_mode` 는 항상 검증된 literal 또는 `"cross"`. **Q3(a)·Q3(c) 코드 대조 통과.**

---

## 신규 BL

- **BL-541 (P2)** 세션 행이 아예 없는 포지션(웹훅 경로·거래소 수동)은 여전히 못 닫는다 — ★아직 실측된 적 없어 **의도적으로 안 지었다**
- **BL-542 (P3)** 계정 포지션 표의 "잘렸다" 경고가 포지션 1건에도 켜진다 (거짓 양성 의심, **n=1**)
- **BL-543 (P1)** `engine_only` 은 진입 유실을 측정할 수 없다 + >5분 공백마다 세션이 죽는다
