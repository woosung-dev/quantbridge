# Sprint 35 Slice 1a — BL-178 root cause spike (Docker worker stale 확정)

**날짜:** 2026-05-05
**Sprint:** 35 (Slice 1a, master plan `~/.claude/plans/quantbridge-sprint-35-anchored-oracle.md`)
**판정:** **root cause 확정 — Docker worker container STALE (PR #150 BL-175 머지 후 rebuild 안 됨)**
**소요:** ~1시간 (Slice 1a estimated 30min-1h, 정합)
**Action:** worker rebuild 후 BL-178 자동 해소 검증 완료 (BL-175 회귀 test 8/8 GREEN)

---

## 1. 진단 6항목 결과 (codex iter 1 P1-1 + iter 2 P2-2 surgery 정합)

### 1.1 SQL 진단 (local TimescaleDB, port 5433)

```sql
SELECT timeframe, COUNT(*), COUNT(*) FILTER (WHERE close::text='NaN' OR close<=0) AS invalid_count, ...
```

| timeframe | total_bars | invalid_count | nan_count | zero_or_negative | min_valid_close | first_invalid_ts |
| --------- | ---------- | ------------- | --------- | ---------------- | --------------- | ---------------- |
| 1h        | 1490       | **0**         | 0         | 0                | 38770.49        | (none)           |
| 4h        | 547        | **0**         | 0         | 0                | 38842.66        | (none)           |

**결과:** local DB 안 invalid bar **0건**. codex P1-1 가정 ("OHLCV 안 NaN/<=0 invalid bar 존재") = **false premise**.

### 1.2 Python 진단 (`_to_dataframe()` + `_v2_buy_and_hold_curve()`)

`/tmp/bl178-diagnose.py` 실행 결과:

| 항목            | BTC/USDT 1h          | BTC/USDT 4h         |
| --------------- | -------------------- | ------------------- |
| df.shape        | (1490, 5)            | (547, 5)            |
| index type      | DatetimeIndex        | DatetimeIndex       |
| close dtype     | float64              | float64             |
| close NaN count | **0**                | **0**               |
| close <=0 count | **0**                | **0**               |
| close min/max   | 38770.49 / 94359.78  | 38842.66 / 73351.97 |
| BH curve result | **정상** length=1490 | **정상** length=547 |
| BH first / last | $1000 / $1945.59     | $1000 / $1667.10    |

**결과:** 직접 호출 시 `_v2_buy_and_hold_curve()` GREEN 정상 반환. codex iter 2 P1-2 가정 ("v2_adapter quarantine policy 안 NaN 도입") = **wrong premise**.

---

## 2. mid-dogfood Day 6.5 시점 backtest 검증

### 2.1 DB 안 metrics field 검증

```sql
SELECT id, symbol, timeframe, metrics ? 'buy_and_hold_curve' AS bh_field_present FROM backtests WHERE symbol='BTC/USDT' ORDER BY created_at DESC LIMIT 10;
```

| backtest_id   | symbol   | timeframe | bh_field_present |
| ------------- | -------- | --------- | ---------------- |
| `04559fb1...` | BTC/USDT | 4h        | **false**        |
| `1c09c372...` | BTC/USDT | 1h        | **false**        |
| `ea94e52f...` | BTC/USDT | 1h        | **false**        |

**결과:** mid-dogfood Day 6.5 backtest 3건 모두 metrics JSON 안 `buy_and_hold_curve` **key 자체 부재** (NOT null = key absence).

### 2.2 serializer 분석

`backend/src/backtest/serializers.py:103-104`:

```python
if m.buy_and_hold_curve is not None:
    d["buy_and_hold_curve"] = [[ts, str(v)] for ts, v in m.buy_and_hold_curve]
```

**chain:** BH=None → serializer if-not-none 분기 → dict 안 key 자체 제외 → DB JSONB 안 field 부재.

### 2.3 mid-dogfood 결과 vs 직접 호출 모순

같은 OHLCV (BTC/USDT 4h 547 bars):

- **mid-dogfood (worker task)**: BH = None (DB metrics 안 field 부재)
- **직접 호출 (Python script)**: BH = curve 정상 1667 last value

**모순 = worker 가 사용한 코드 ≠ 메인 세션이 사용한 코드**.

---

## 3. root cause 확정

### 3.1 worker container 시점 분석

```bash
docker inspect quantbridge-worker --format '{{.State.StartedAt}}'
# 2026-05-05T09:01:42 UTC = 18:01:42 KST
```

**chain:**

| 시점                    | event                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------- |
| 2026-05-05 18:01:42 KST | worker container 시작 (PR #150 머지 약 2시간 50분 전 코드)                             |
| 2026-05-05 20:49:58 KST | PR #150 머지 (`a796725` BL-175 본격 fix)                                               |
| 2026-05-05 21:01:04 KST | mid-dogfood backtest #1 실행 (worker = stale, BH 계산 함수 자체 부재)                  |
| 2026-05-05 21:04:25 KST | mid-dogfood backtest #2/3 실행 (worker 여전히 stale)                                   |
| 2026-05-05 21:11:10 KST | PR #149 (BL-177 dense text shorten) main 머지                                          |
| 2026-05-05 23:11:10 KST | Sprint 35 transition (`a0cc18f`) main merge                                            |
| 2026-05-05 23:17:59 KST | worker `docker compose restart` — **여전히 stale** (image baked-in, restart 효과 없음) |
| 2026-05-05 23:24+ KST   | `make up-isolated-build` (rebuild) → worker fresh code                                 |

### 3.2 worker stale 검증

```python
# Before rebuild (worker container started 09:01:42 UTC, before PR #150)
docker exec quantbridge-worker python -c "import src.backtest.engine.v2_adapter as m; print(hasattr(m, '_v2_buy_and_hold_curve'))"
# False ← PR #150 미적용 명백한 evidence

# After `docker compose restart` (image 그대로)
# False ← 여전히 stale, restart 효과 없음

# After `make up-isolated-build` (image rebuild)
# True ← fresh code
```

### 3.3 docker-compose.yml 안 ops gap

`docker-compose.yml` 의 `backend-worker:`:

```yaml
backend-worker:
  build:
    context: ./backend
  container_name: quantbridge-worker
  command: uv run celery -A src.tasks.celery_app worker ...
  # volumes: 부재 ← code 가 image 안 baked-in
```

**결정적 ops gap:** `volumes` mount 없음 = 모든 코드 image 안 baked-in = **PR 머지 후 `make up-isolated-build` (또는 동등한 rebuild) 의무**. `make up-isolated` 또는 `docker compose restart` 만으로는 새 코드 적용 안 됨.

### 3.4 root cause 1줄 요약

**BL-178 = Docker worker container stale = PR #150 머지 후 rebuild 안 됨 = `_v2_buy_and_hold_curve` 함수 자체가 worker 안 부재 = metrics 안 BH field 자체 부재 = serializer if-not-none 분기로 key drop.**

OHLCV 자체는 깨끗하고, v2_adapter 코드도 정상이며, schema 도 정합. **운영 (ops) issue, not code issue.**

---

## 4. 검증 — worker rebuild 후 BL-175 회귀 test 8/8 GREEN

```bash
docker exec quantbridge-worker uv run pytest tests/backtest -k 'buy_and_hold or bh_curve' -v
# tests/backtest/engine/test_v2_adapter.py .....           [62%]
# tests/backtest/test_serializers.py ..                    [87%]
# tests/backtest/test_service.py .                         [100%]
# === 8 passed, 191 deselected, 3 warnings in 4.52s ===
```

8 test all GREEN = PR #150 BL-175 회귀 test 모두 fresh worker 안 정상 작동. 즉 worker rebuild 만으로 BL-178 production-quality 자동 해소 가능.

---

## 5. Sprint 35 master plan 재평가 의무

### 5.1 wrong premise 위에 작동한 surgery

codex G.0 surgery 18건 중 다수가 BL-178 = "OHLCV NaN 도입 path" 가정 위에 작동:

| Surgery                                                  | 정합성                                                                                             |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| iter1-P1-1 (Slice 1a 6항목 진단)                         | **wrong premise** — DB 안 invalid 0건. 진단 자체는 valid (rapid root cause detection)              |
| iter1-P1-2 (Day 7 (b) Path B escape FAIL/UNKNOWN)        | **valid (general)** — gate fairness, but BL-178 자체가 5분 fix                                     |
| iter1-P1-3 (BL-180 hand-computed oracle)                 | **valid (general best practice)** — engine outside trust mechanism                                 |
| iter1-P1-4 (vectorbt 폐기)                               | **valid (separate finding)** — codex code reading 결과 정확                                        |
| iter1-P1-5 (BL-176 schema required)                      | **valid (separate finding, BL-176)**                                                               |
| iter1-P1-6 (Slice 1.5 sequencing 독립)                   | **valid (best practice)**                                                                          |
| iter1-P1-7 (mandatory + stretch)                         | **valid (best practice)**                                                                          |
| iter1-P2-2 (reject/quarantine policy)                    | **wrong premise** — quarantine 시나리오 자체 발생 X                                                |
| iter1-P2-4/P2-5/P2-7                                     | **valid** (Worker write-set / named assertion / Day 7 (d))                                         |
| iter2-P1-1 (BL-180 JSON checked-in + BacktestConfig pin) | **valid (best practice)**                                                                          |
| iter2-P1-2 (quarantine fail-closed propagate)            | **wrong premise** — quarantine 자체 불필요                                                         |
| iter2-P2-1/P2-2/P2-3/P2-4/P2-5                           | **valid** (resetField "" / SQL canonical / DB fallback / Playwright fallback / PR 별 BACKLOG 갱신) |

**wrong premise = 3건** (P1-1 진단 자체는 valid mechanism 으로 인정 / P2-2 + iter2-P1-2 quarantine 정책 = 자체적 폐기 의무).

**valid 11건** (BL-180 oracle + vectorbt 폐기 + BL-176 schema + Day 7 gate + Worker write-set + named assertion + DB fallback + Playwright fallback + PR 별 BACKLOG 갱신 + best practices).

### 5.2 BL-178 fix scope 재정의

원래 plan: Slice 1b "code fix path 2-3h or escape hatch (backfill)"

**실제 fix scope = ~5분 (worker container rebuild)**. 단 ops gap (auto-rebuild on code change) 자체는 별도 BL.

### 5.3 신규 BL 후보

- **BL-181 (P1, ops gap, Sprint 35 active candidate)** — Docker worker auto-rebuild on code change. PR 머지 후 worker container rebuild 자동화 mechanism. 가능성: (i) docker-compose.yml volumes mount 으로 dev mode 만 (`docker-compose.dev.yml` override) / (ii) GitHub Actions 안 image push 후 환경 안 image pull + restart 자동화 / (iii) Makefile 안 PR 머지 후 의무 step 명시 + post-merge hook
- **BL-182 (P2, monitoring)** — worker container code version 자동 감지 + alert. e.g. `_v2_buy_and_hold_curve` 같은 sentinel 함수 존재 검증 startup health check

### 5.4 master plan 재구성 결정 옵션

본 발견은 Sprint 35 master plan 의 mandatory scope 자체를 흔듦. 사용자 결정 필요:

| 옵션                                                                                                 | 의미                                                                                                        |
| ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| (i) plan 재작성 (codex iter 3 trigger)                                                               | wrong premise 제거 + BL-181/182 신규 등록 + mandatory 재정의 (이젠 BL-180 oracle + BL-176 + BL-181 ops gap) |
| (ii) plan 그대로 유지 + Slice 1b cancel (BL-178 자동 해소) + BL-181 신규 active                      | 빠른 적응. plan 안 wrong premise 부분 footnote 추가                                                         |
| (iii) Sprint 35 cancel + 본 발견을 Sprint 36 의 진짜 trigger 로 사용 (BL-005 본격 mainnet 직접 진입) | 가장 ambitious. Day 7 4중 AND gate (b) 자동 통과 → Sprint 36 = BL-003 mainnet runbook + BL-005 본격         |

---

## 6. lesson 후보

### 6.1 LESSON-038 (영구 규칙 후보) — Docker worker auto-rebuild on PR merge 의무

**문제:** docker-compose.yml 안 backend-worker volumes mount X → image baked-in → PR 머지 후 `make up-isolated-build` 의무. 운영 진행 안 자동화 안 됨 → "왜 BL-175 fix 안 작동하는가" silent failure.

**규칙:** 모든 worker process (celery worker / beat / ws-stream) 코드 변경 영향 받음 + PR 머지 후 자동 rebuild 의무. docker-compose dev override 또는 Makefile post-merge target 권장.

### 6.2 LESSON-039 (영구 규칙 후보) — Surface Trust 차단 ≠ 실제 fix 작동

**문제:** mid-dogfood Day 6.5 PASS = "거짓말 안 함" PASS (Surface Trust 차단 = BH null → 미렌더 + Legend hide 작동) 였지만 **실제 fix 가 작동하지 않은 상태**. 본인 직관 ("기능 다 안 돌아간다") 이 정확.

**규칙:** Surface Trust 차단 작동 여부와 별도로 **실제 기능 작동 직접 검증 의무** (codex iter 1 P1-3 BL-180 hand oracle = 정확히 이 mechanism 의 codex 의 사전 detection. 본 발견 사후 retroactive validation).

### 6.3 LESSON-040 (영구 규칙 후보) — codex G.0 wrong premise risk

**문제:** codex G.0 surgery 18건 중 3건이 wrong premise (DB invalid / quarantine policy) 위에 작동. 누적 1.34M tokens 소비. 코드 reading 만으로 ops gap detection 불가능.

**규칙:** codex G.0 master plan validation 직후 **rapid prereq verification spike (10-30분)** 의무. Slice 1a 같은 spike 가 plan validation 안 포함되거나 plan validation 후 fastest 진단으로 분리. 또한 worker/runtime version 검증 (sentinel function 존재 여부) Sprint 진입 첫 step 추가.

---

## 7. 다음 step

- [x] root cause 확정 (Docker worker stale)
- [x] worker rebuild + BL-175 회귀 test 8/8 GREEN
- [x] dev-log 작성 (본 파일)
- [ ] **사용자 Sprint 35 plan 재구성 결정** (옵션 i/ii/iii — § 5.4)
- [ ] BL-181 (Docker auto-rebuild) 등록 + Sprint 35 active 후보
- [ ] LESSON-038/039/040 영구 규칙 승격 후보 → `.ai/project/lessons.md` 추가
- [ ] commit + PR (Slice 1a 결과)

---

## Cross-link

- Sprint 35 master plan: `~/.claude/plans/quantbridge-sprint-35-anchored-oracle.md`
- 5-step 운영 플랜: `~/.claude/plans/1-git-push-melodic-brook.md`
- mid-dogfood Day 6.5: [`docs/dev-log/2026-05-05-dogfood-day-6.5.md`](2026-05-05-dogfood-day-6.5.md)
- PR #150 (BL-175): https://github.com/woosung-dev/quantbridge/pull/150
- PR #149 (BL-177): https://github.com/woosung-dev/quantbridge/pull/149
- PR #152 (Sprint 35 office-hours): https://github.com/woosung-dev/quantbridge/pull/152
- PR #153 (Sprint 35 transition): https://github.com/woosung-dev/quantbridge/pull/153
- codex G.0 session: `019df85d-bcbf-7d63-a6cc-ce106de4ace1` (`.context/codex-session-id`)
- Sprint 33 BL-166 (similar pattern — Makefile reload assumption noop): [`docs/dev-log/2026-05-05-sprint33-master-retrospective.md`](2026-05-05-sprint33-master-retrospective.md)
