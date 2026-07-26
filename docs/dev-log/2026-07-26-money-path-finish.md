# 2026-07-26 — money-path-finish 스프린트 회고

> 머니-패스 정확도 마감 팩. **BL-457 + BL-454 + BL-458(부분) + 신규 BL-464.** 마이그레이션 **0**.
> 계약 = [`../money-path-finish/operating-contract.md`](../archive/sprints/money-path-finish/operating-contract.md) · 결정 = [`../money-path-finish/context-notes.md`](../archive/sprints/money-path-finish/context-notes.md)

---

## 무엇을 고쳤나

트레이딩/머니-패스 축 6스프린트(#472~#478)가 기능을 붙이는 동안 남긴 **세 종류의 서로 다른 거짓말**을 닫았다.

1. **원장이 "우리 것" 이라고 거짓말했다** — `classify_exit` 의 `ours` 가 `orderLinkId` 가 UUID 로 **파싱되는지만** 봤다. UUID 모양 client id 를 단 외부 청산이 운영자 알림에서 조용히 빠졌다.
2. **세션 스코프가 심볼 표기 하나로 조용히 빌 수 있었다** — #477 이 스코프에 `symbol` 정확 문자열 동등을 넣었는데 두 ingress 가 심볼을 정규화하지 않았다.
3. **화면이 추정값과 확정값을 구분하지 않았다** — `realized_pnl_synced_at` 이 출처 마커로 존재하는데 소비처 5곳 어디도 읽지 않았다.

---

## ★교훈 1 — 픽스처의 기본값이 경계 버그를 한 스프린트 동안 가렸다

백로그에 없던 결함을 찾았다(**BL-464**). `attribute_exit` 이 `order.symbol`(우리 canonical `BTC/USDT`)을 `snapshot.symbol`(Bybit 원문 `BTCUSDT`)과 정확 문자열 동등으로 비교한다 → **어떤 표본에서도 매칭 불가, `inferred` 귀속 축이 구조적으로 사망.**

직전 스프린트는 `attributed_strategy_id NOT NULL 0` 을 관측했지만 **"0행 위에서 0"** 으로 해석했다. 데이터가 없어서 0 인 것과 **데이터가 있어도 0** 인 것은 다른 진단이다.

왜 안 보였나 — `test_closed_pnl_sweep.py::_snapshot` 의 기본 심볼이 `"BTC/USDT"` 였다. 우리가 다루기 편한 표기다. 실제 Bybit closed-pnl 은 `BTCUSDT` 를 준다(DB 4행이 증거).

> **승격 후보 규칙** — 외부 시스템을 흉내내는 픽스처의 기본값은 "우리가 다루기 편한 형태" 가 아니라 **그 시스템이 실제로 주는 형태**여야 한다. 편한 형태로 두면 경계 변환 버그가 테스트를 통과한다.

C-red 의 첫 동작이 픽스처 정정이었고, 그 다음에야 죽은 축이 **테스트로** 드러났다(`ExitAttribution.none` vs `inferred`).

## ★교훈 2 — 백로그의 "권장 접근" 도 틀릴 수 있다. 코드로 검증하라

BL-457 본문은 `attribution_facts` 를 재사용하면 "새 쿼리가 필요 없다" 고 적었다. 코드를 보면 그 목록은 `limit=500` + `state==filled` 로 좁혀졌고, 실재 확인이 필요한 행은 **정의상 `state==filled` 매칭에 실패한 주문**이다. 즉 필요한 행이 그 목록에 구조적으로 없다. 따랐다면 **진짜 우리 청산이 `external_manual` 로 뒤집혀** 운영자 알림이 헛발화했을 것이다.

핸드오프 문서는 자기가 쓰인 시점의 이해를 담고 있다. 이번엔 그게 실행 가능한 조언의 형태로 틀려 있었다. **백로그 본문에서 제자리 정정**했다 — 안 하면 다음 독자가 같은 버그를 재도입한다.

## ★교훈 3 — 게이트 목록에 있는 게 통과 가능한 게이트라는 뜻은 아니다

킥오프 §5 가 `pnpm format:check` 를 게이트로 넣었다. 실측하니 main 에서 이미 **356 파일 red** 였다. 원인은 `package.json:14-26` — lint-staged 가 FE `{ts,tsx,js,jsx}` 에 **eslint 만** 돌린다(prettier 없음). 내가 만질 `hooks.ts` 조차 baseline 에서 dirty 였다.

356 파일 일괄 포맷은 거대 diff 라 스코프 밖이므로 기준을 "주변 스타일 일치 + baseline 대비 불변" 으로 바꿨다. **게이트를 통과하지 못했다고 보고하는 것보다, 그 게이트가 애초에 무엇을 재고 있는지 재는 게 먼저다.**

---

## 설계에서 가장 중요했던 결정 3건

### canonical 은 선택이 아니라 이미 강제되어 있었다

`_to_bybit_linear_symbol`(`providers.py:692`)이 `if "/" not in symbol: return symbol` 이다. 즉 원문 `BTCUSDT` 는 **linear 어댑터를 우회**해 조용히 잘못된 market 으로 라우팅된다. "정규화가 provider 를 깰까" 라는 make-or-break 리스크가 그 한 줄로 반대 방향으로 해소됐다 — 지금 위험한 포맷은 canonical 이 아니라 **원문 쪽**이었다.

사용자가 "업계 권장 · TV 는 어떻게 · 10년차 아키텍트라면" 을 물어 1차 출처를 조사했다. CCXT 자체 계약("항상 unified, market id 는 `markets_by_id` 로 되돌린다") · TV 문서(`{{ticker}}` = 거래소 원문, 지연 심볼은 `_DLY` 접미) · TV→브로커 브리지 업계의 1순위 실패 모드가 정확히 이 포맷 불일치 · Parse-don't-validate. 결론은 **경계에서 한 번 파싱해 타입이 보장을 지니게 하는 것**이었고, 레포에 이미 그 선례가 있었다(`strict_decimal_input.py`).

**★확인 못 한 것을 코드로 단정하지 않았다** — TV 가 Bybit 퍼프에서 `BTCUSDT` 를 주는지 `BTCUSDT.P` 를 주는지 1차 출처로 확인하지 못했다. 그래서 `.P`/`PERP` 장식 제거를 추측으로 넣는 대신 **fail-closed + 관측**으로 갔다. 카운터는 "일어나고 있나" 에만 답하고, 로그가 실제 포맷을 알려준다. 첫 실사용이 답을 준다.

### "모른다" 를 말할 자리를 만들었다

UUID 모양이지만 실재 확인이 안 된 행을 단순 fall-through 시키면 `external_manual` = "사람이 거래소 UI 에서 Close 를 눌렀다" 가 된다. **사람은 UUID4 를 타이핑하지 않는다.** 그 문자열은 운영자가 알림 본문에서 읽는 값이라 유령 수동거래를 찾아 헤매게 만든다. 분기 8 을 신설해 `unknown` 을 돌려준다.

3번째 enum 값(`ours_unverified`)은 만들지 않았다. 비용은 논거가 아니었다 — `classification` 은 `String(24)` 이라 값 추가도 마이그레이션 0 이다. 진짜 이유는 `ours` 술어가 영구히 두 값으로 쪼개져 **모든 미래 소비처가 둘 다 기억해야 한다**는 것이고, 그게 BL-453·BL-457 을 만든 결함 형태다. "우리 DB 가 행을 잃었다" 는 청산의 속성이 아니라 우리 운영 사실이므로 Prometheus 카운터가 올바른 집이다. **탈출구를 명시**했다 — 그 카운터가 프로덕션에서 오르면 그때 값을 추가한다.

### 병합 커브에는 포인트별 출처를 실을 수 없다

`mergeCumulativeCurves` 를 읽고 확인했다 — 시각 합집합을 훑으며 각 세션의 **마지막 누적값을 carry-forward** 해 더한다. 병합 지점의 값은 N개 기여의 합이고 통상 N−1 개가 과거 거래에서 실려온 stale 값이다. 그걸 "이 시점의 출처" 로 칠하면 **적극적으로 틀린다.**

→ 포인트별 출처는 단일 세션 고도 전용, 포트폴리오 곡선은 집계 수준 라벨. 와이어가 두 형태(포인트 `source` + 평면 소계)를 다 싣는 이유가 그 비대칭이다. **표현할 수 없는 것을 표현하지 않기로 한 결정**이 이 스프린트에서 가장 정직한 한 줄이다.

---

## 검증

- **codex G0** — BLOCKING 0 · P1 4 · P2 1. 전건 코드 대조(§7.3) 후 **P2 수용**(`context` 는 5키가 아니라 6키이고 인용한 real-DB 테스트는 두 값만 단정 — 내 플랜이 양쪽 다 틀렸다) · **P1-1/2/3 수용** · **P1-4 절반 기각**(내 _신규_ nullable 필드와 _기존_ non-null 필드를 혼동).
- **`/vercel-react-best-practices`** — 이 레포의 알려진 함정(새 배열 identity 가 chart setData effect 를 재실행해 사용자 줌 리셋)이 재발하지 않음을 memo 사슬과 effect deps 로 확인. 지적 1건(빈 객체 스프레드) 수정.
- **독립 오라클** — 손익을 2의 거듭제곱 × 서로 다른 소수부로 심어 어떤 부분집합 합계도 유일하게 만들었다(직전 스프린트 기법 재사용). Site 3·4 가 각각 유일한 숫자를 내는지 확인.
- **가드레일 강화** — 대조군 seed 에 `synced_at` 을 심어 Site 1/2/5 값이 불변인지 확인 = **출처 마커가 게이트 술어로 새지 않았다는 증명**. 이제 누가 게이트를 `synced_at IS NOT NULL` 로 좁히면 그 세 숫자가 즉시 변한다.
- **게이트** — BE **3000 passed / 46 skipped**(baseline 2972, +28) · FE **1124 / 194 files**(baseline 1115, +9) · ruff·mypy·tsc·lint 0 · design-canon **32 불변** · build ok · alembic head 불변 → **마이그레이션 0**.

**정직한 한계** — `orders`/`sessions` 0행이라 실화면 종단 dogfood 는 seed 없이 불가했다. 실DB 종단 테스트(Site 3·4)와 독립 오라클로 대체했고, 실주문 dogfood 는 사용자 요청이 선행돼야 한다.

---

## 남은 것

- **BL-446** — 로드맵 #2 팩의 유일한 잔여. `cumulative_loss` 분자·분모 시간축 불일치.
- **BL-458 잔여** — Site 1·2 게이트 혼재(의도) · Site 5 미표면화 · 병합 커브 집계 라벨 한정 · Site 4 `unrecorded_count` 미계상.
- **BL-464 후속** — `inferred` 부활은 휴리스틱 승인이 아니다. `qb_exchange_exit_attribution_total{confidence}` 로 실제 비율을 재고 나서야 BL-438 ② 가 이걸 머니-패스로 승격할 수 있다.
