# 라이브 청산 유실 진단 (BL-530)

> **무엇을 위한 문서인가.** `GET /live-sessions/{id}/outcome-parity` 표면은 청산이 **얼마나** 안 잡혔는지를 버킷으로 보여 준다(`expected_only_*`). 이 문서는 그 버킷을 **사유별로 여는** 읽기 전용 SQL 이다. 새 계측기가 아니라 기존 계측기의 하위 진단이다.
>
> 계기(스팟 vs perp) 함정 자체는 [`gates-and-traps.md`](gates-and-traps.md) §3 「계기」가 SSOT.

---

## 0. 전제

- 스키마는 `trading` 이다. `live_signal_events` 가 아니라 **`trading.live_signal_events`**.
- 개발 스택 DB 는 **5433**. 컨테이너 안에서 도는 예시는 `docker exec quantbridge-db psql -U quantbridge -d quantbridge`.
- ★**창을 반드시 걸어라.** 아래 쿼리를 기간 없이 돌리면 여러 스프린트가 섞인다. 실제로 BL-530 의 최초 헤드라인(71%)이 그렇게 나왔고, 수리 이후 창만 보면 값이 달랐다. **수리 전후를 가르는 시각을 명시하지 않은 비율은 읽지 마라.**

---

## 1. close 이벤트가 어디서 죽었는가

엔진이 낸 청산 신호의 종착지를 한 장으로 본다.

```sql
SELECT e.status,
       coalesce(substring(e.error_message from 1 for 60), '(null)') AS err,
       count(*)
FROM trading.live_signal_events e
WHERE e.action = 'close'
  AND e.bar_time >= '<T0>'          -- ★창 필수
GROUP BY 1, 2
ORDER BY 3 DESC;
```

`status='failed'` 는 **발주까지 못 간 것**이고 `error_message` 가 사유다. 가장 흔한 값:

| `error_message`       | 뜻                                                                           |
| --------------------- | ---------------------------------------------------------------------------- |
| `close_position_flat` | 우리 사전검사가 거래소 포지션 0 을 확인하고 발주를 막았다 (`live_signal.py`) |
| `kill_switched`       | 리스크 게이트가 막았다                                                       |
| `session_inactive`    | 이벤트가 큐에 있는 사이 세션이 꺼졌다                                        |

## 2. 발주된 close 가 거래소에서 어떻게 됐는가

`status='dispatched'` 는 주문 행까지 갔다는 뜻일 뿐 **확정이 아니다.** 확정 여부는 `realized_pnl_synced_at` 이 판정한다(NULL = 엔진 추정값).

```sql
SELECT o.state,
       (o.realized_pnl_synced_at IS NOT NULL) AS confirmed,
       substring(o.error_message from 'retCode":([0-9]+)') AS code,
       substring(o.error_message from 'retMsg":"([^"]{0,50})') AS msg,
       count(*)
FROM trading.live_signal_events e
JOIN trading.orders o ON o.id = e.order_id
WHERE e.action = 'close'
  AND e.status = 'dispatched'
  AND e.bar_time >= '<T0>'
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC;
```

### 거절 코드 읽는 법

| 코드     | 메시지                                | 무엇을 뜻하는가                                                                                                                                                      |
| -------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `110017` | `current position is zero`            | 엔진만 포지션을 믿는다(**유령 진입**). close 는 무해하게 거절된다. §1 의 `close_position_flat` 과 **같은 뿌리**이고 우리가 먼저 잡았느냐 거래소가 잡았느냐의 차이다. |
| `110017` | `reduce-only order has same side ...` | ★**위험** — 엔진과 거래소가 **반대 방향**을 들고 있다. `reduce_only=True` 가 없었으면 포지션이 **증가·반전**한다.                                                    |
| `10005`  | `Permission denied`                   | read-only 계정 행으로 발주했다 (BL-501 계열).                                                                                                                        |

★`110017` 두 갈래를 **코드로만 묶지 마라.** 같은 코드인데 하나는 무해하고 하나는 머니-패스 위험이다. 반드시 `retMsg` 까지 갈라서 세라.

## 3. 진입 쪽 원장 — 유령이 어디서 생겼는가

close 유실의 대부분은 **진입이 라이브에서 완결되지 않은 것의 하류**다. 조건부 진입은 `idempotency_key` 로 갈린다(`cond:` = 조건부 등재, `condmkt:` = 시장가 전환, 나머지 = 일반 신호).

```sql
SELECT split_part(o.idempotency_key, ':', 3) AS kind,
       o.reduce_only, o.state,
       substring(o.error_message from 'retCode":([0-9]+)') AS code,
       count(*)
FROM trading.orders o
WHERE o.idempotency_key LIKE 'live:<session_id>%'
GROUP BY 1, 2, 3, 4
ORDER BY 5 DESC;
```

읽는 법 — `reduce_only=false` 가 진입, `true` 가 청산이다. **`cancelled` 가 많고 `filled` 가 적으면** 조건부 스톱이 트리거되지 못하고 매 tick 재등재되고 있다는 뜻이고, 그 trade 의 close 는 곧 유령이 된다.

## 4. 시계열로 보기 — 수리 전후를 가르는 데 쓴다

```sql
SELECT date_trunc('hour', o.created_at) AS h,
       o.reduce_only, o.state,
       substring(o.error_message from 'retCode":([0-9]+)') AS code,
       count(*)
FROM trading.orders o
WHERE o.created_at >= '<T0>'
GROUP BY 1, 2, 3, 4
ORDER BY 1, 5 DESC;
```

## 5. 실시간 관측 (SQL 아님)

세션이 도는 동안에는 metric 이 더 빠르다. 워커 안에서:

```bash
docker exec quantbridge-worker python -c "
from prometheus_client import CollectorRegistry, multiprocess
reg = CollectorRegistry(); multiprocess.MultiProcessCollector(reg)
for m in reg.collect():
    if 'divergence' in m.name:
        for s in m.samples:
            if s.value: print(s.name, s.labels, s.value)
"
```

| metric                                                    | 뜻                                               |
| --------------------------------------------------------- | ------------------------------------------------ |
| `qb_live_position_divergence_total{category=engine_only}` | 엔진만 포지션을 믿는다 (관측만, 차단 안 함)      |
| `..{category=exchange_only}`                              | 거래소에만 남은 고아 포지션                      |
| `..{category=size}`                                       | 방향은 같고 크기가 다르다 (부분체결·수량 step)   |
| `..{category=probe_failed}`                               | 거래소를 못 읽어 판정 자체를 못 했다 (fail-open) |
| `qb_live_signal_divergence_total{stage=position}`         | ★방향 불일치 — 세션을 **비활성화**했다           |

★로그(`live_signal_position_divergence`)의 `extra` 필드는 현재 포매터가 렌더하지 않는다. **수치는 metric 에서 읽어라.**

## 6. 실측 기록 (2026-07-28, 계기 수리 전)

| 갈래                               |   n | 비고             |
| ---------------------------------- | --: | ---------------- |
| 거래소 확정                        |  21 |                  |
| `close_position_flat`              |  16 | 우리가 먼저 막음 |
| `110017 current position is zero`  |  30 | 거래소가 막음    |
| `110017 reduce-only ... same side` |   4 | ★위험 갈래       |
| `10005 Permission denied`          |   1 | read-only 계정   |

합 72 · 확정 29%. **단 이 값은 3일·3스프린트 누적이다**(reduce-only 거절 35건 중 31건이 07-26). BL-511 이후 창만 보면 close 6건 중 확정 3건 = **50%(n=6)** 였다. §0 의 경고가 바로 이 사례에서 나왔다.
