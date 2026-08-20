# Step 1: observe-counter-diff

## 읽어야 할 파일

- `tools/scripts/soak-observe.sh` — `scrape_metrics()`(83~106행) · `metrics_source()`(77~81행) ·
  ★**「4. counter 차분」 블록(161~192행)의 awk** · 「6. /metrics 디렉터리」(212~221행)
- `apps/api/tests/scripts/test_soak_observe.py` — **앞 step 이 만든 파일. 이어 붙인다**

## 배경

counter 차분은 「출생일이 다른 counter 는 절대값이 126 vs 99 로 어긋나도 차분은 일치한다」는
관찰에서 나왔다 — **절대값 비교 금지, 차분만**. 그리고 세 가지 표기를 구분한다:
`Δ`(둘 다 있고 값이 다름) · **`NEW`**(이전 스냅샷에 없던 series — `after-0` 이 아니다) ·
**`MISSING`**(이전엔 있었는데 사라짐 = 스냅샷 유실 의심).

★그리고 **취득과 필터를 분리한 이유**가 주석에 박혀 있다 — 붙여 두면 「매치 0건」(counter 가
아직 안 발화)이 파이프 rc 로 「스크레이프 실패」와 같아진다. **취득 실패만 UNKNOWN 이고
series 0 은 표본 없음이다.** 이 구분이 이 블록의 전부인데 테스트가 0건이다.

## 작업

`apps/api/tests/scripts/test_soak_observe.py` 에 **지표 취득 · counter 차분 · 전량 성공 rc=0**
을 이어 붙여라. 앞 step 의 가짜 레포/docker 스텁 헬퍼를 재사용한다(새 헬퍼 모듈 금지).

### 이 step 에서 추가되는 배선

지표 취득은 두 갈래다. **`QB_METRICS_URL` 갈래를 써라** — 직독 갈래는 `uv run python` 을
120초 타임아웃으로 돌려 테스트가 느리고 환경에 의존한다.

- `QB_METRICS_URL="http://stub/metrics"` + PATH 에 **`curl` 스텁** (원하는 본문/rc 를 낸다)
- `QB_METRICS_DIR=<tmp 디렉터리>` — 「6. /metrics 디렉터리」 절이 `-d` 로 존재만 본다.
  없으면 그 절이 `FAILED=1` 을 세워 rc=3 이 되므로, **전량 성공 케이스에서는 반드시 만들어라**

스냅샷은 가짜 레포의 `.soak/snap-*.txt` 로 쌓인다. 「이전 스냅샷」은 **파일을 직접 써서**
만들거나 스크립트를 두 번 돌려 만든다. 형식은 prometheus 텍스트에서 `qb_…` 로 시작하는 줄을
`grep -E` 로 거른 뒤 `sort` 한 것이다 — awk 가 **마지막 칸을 값으로, 나머지를 키로** 본다.

★본문에 넣을 series 이름은 스크립트의 `grep -E` 패턴에 **실제로 걸리는 것**이어야 한다
(`qb_live_signal_dispatch…` 등). 패턴을 읽고 맞춰라 — 안 걸리면 스냅샷이 비어 전부
「변화 없음」으로 통과한다.

### 최소한 이 넷 + 앞 step 5건 = 9건을 채워라

1. **첫 스냅샷은 「차분 없음」** — stdout 에 `첫 스냅샷` 과 series 개수
2. **값이 오르면 `Δ` 와 부호가 찍힌다** (`Δ` 와 `+` 그리고 `이전값 -> 현재값`)
3. ★**이전에 없던 series 는 `NEW`** — `after-0` 이나 `Δ +N` 이 아니다.
   (출생일이 다른 counter 를 0 에서 올라온 것으로 세면 안 된다는 것이 이 표기의 이유다)
4. ★**이전에 있다 사라지면 `MISSING`** 과 `스냅샷 유실 의심`
5. **아무것도 안 변하면 「변화 없음」** 문구 + `세션 생존을 먼저 의심해라`
6. ★**스크레이프 실패는 `UNKNOWN` + 최종 rc=3 이고, 「series 0건」과 구분된다** —
   두 케이스를 나란히 재라:
   ⑴ `curl` 스텁이 rc≠0 → stdout 에 `UNKNOWN` 과 `스크레이프 실패`, 최종 rc=3
   ⑵ `curl` 스텁이 rc=0 인데 `qb_` 로 시작하는 줄이 **하나도 없는 본문** → `UNKNOWN` 이
   **아니고** 스냅샷 0 series 로 정상 진행(최종 rc=0). ★이 둘이 같아지는 것이
   주석이 경고한 결함이다
   ⑶ `curl` 스텁이 rc=0 인데 **본문이 빈 문자열** → 취득 실패로 센다(rc=3).
   「200 + 빈 본문」을 「이상 없음」으로 읽지 않는다는 계약이다
7. **`metrics_source()` 가 갈래를 구분해 찍는다** — `QB_METRICS_URL` 이 있으면 URL 이,
   없으면 `(직독)` 이 UNKNOWN 줄에 실린다
8. ★**양성 대조 — 전량 성공 시 rc=0** 이고 stdout 에 `✓ 전 항목 조회 성공`.
   psql 스텁이 6절 전부 성공 + `curl` 성공 + `QB_METRICS_DIR` 실재.
   이것이 없으면 위 rc=3 단언들이 「항상 죽는 스크립트」로도 전부 통과한다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_observe.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_observe.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 9
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**스냅샷이 실제로 비어 있지 않은지 확인해라** — 1번 케이스의 series 개수가 0 이면
   `grep -E` 패턴에 안 걸린 것이고, 그 뒤 2~5번은 전부 무증거다.
3. ★진짜 레포의 `.soak/` 가 안 생겼는지 확인해라.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/soak-observe.sh` 를 **수정하지 마라**
- ★**진짜 레포 루트에서 돌리지 마라** — `.soak/` 를 덮어쓴다. 반드시 `tmp_path` 가짜 레포
- ★**지표 직독 갈래(`uv run python` + `prometheus_client`)를 타지 마라** — 반드시
  `QB_METRICS_URL` + `curl` 스텁. 이유: 직독은 120초 타임아웃이고 환경 의존이라
  CI 에서 간헐 red 가 된다
- ★**진짜 docker 데몬에 닿게 하지 마라** — 반드시 PATH 스텁
- `awk`·`sed`·`grep`·`sort`·`find`·`du` 를 스텁하지 마라 — 차분 판정 자체가 그 awk 다.
  스텁 대상은 `docker`·`curl` 뿐이다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- 앞 step 이 만든 테스트를 지우거나 이름을 바꾸지 마라 — AC 수집 하한이 누적값(≥9)이다
