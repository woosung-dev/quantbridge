# Step 0: observe-args-and-failclosed

## 읽어야 할 파일

- `tools/scripts/soak-observe.sh` — **이번 테스트의 대상** (227줄 전량). 특히 상단
  「설계 원칙」(10~22행) · `q()`(65~73행) · 세션 앵커 블록(110~132행)
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구

## 배경

이 스크립트의 존재 이유는 **fail-closed** 다 — 「조회 실패는 이상 없음이 아니라 UNKNOWN +
비-0 종료」. 앞선 감시 스크립트가 fail-open 이라 **죽은 세션을 「생존」으로 보고한 전례**가
있었고, 그 뒤로 이 규약이 파일 상단에 박혔다. ★그 규약을 지키는 테스트가 0건이다.

같은 파일에 fail-open 이 실제로 한 번 더 숨어 있던 기록도 있다 — `deactivated_reason` 으로
생존을 판정하면 실측 25세션 중 **12세션이 `is_active=false` 인데 `deactivated_reason IS NULL`**
이라 죽은 세션이 「살아있음」으로 찍혔다. 그래서 판정은 `deactivated_at` 으로 옮겼다.

## 작업

`apps/api/tests/scripts/test_soak_observe.py` 를 신설하고 **인자 계약 + fail-closed rc** 를
단언하라.

### 호출 방식 (이 lane 의 유일한 방식 — 여기서 벗어나지 마라)

★**`STATE_DIR="${REPO_ROOT}/.soak"` 는 env 로 못 바꾼다.** `--baseline` 을 진짜 스크립트로
돌리면 **이 레포의 `.soak/session` 을 덮어쓴다** — 소크 관측의 세션 앵커다.
그래서 **`tmp_path` 아래 가짜 레포로 복사해서** 돌린다.

```python
import os, shutil, subprocess
from pathlib import Path

REAL = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "soak-observe.sh"

def _fake_repo(tmp_path) -> Path:
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL, scripts / "soak-observe.sh")
    return scripts / "soak-observe.sh"
```

`docker` 는 PATH 스텁으로 갈아끼운다. 스크립트가 부르는 형태는 둘뿐이다 —
`docker exec <컨테이너> psql …`(`q()` 와 T0 조회). 스텁이 stdout 과 rc 를 결정한다.

```python
def _env(tmp_path, stub_bin):
    return {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ['PATH']}",
        "QB_DB_CONTAINER": "qb-test-db",
    }
```

★가짜 레포에 `apps/api/.env.local` 을 만들지 마라 — 스크립트가 그 파일에서
`PROMETHEUS_BEARER_TOKEN` 을 읽는데, 없으면 헤더 없이 가고 그것이 이 step 의 정상 경로다.
(진짜 레포 파일은 `REPO_ROOT` 가 tmp 라 애초에 안 보인다.)

### 최소한 이 다섯을 덮어라

인자 계약 — **rc 값까지 정확히 단언해라.** 이 스크립트는 `64`(사용법 오류)와 `3`(측정 불가)를
다르게 쓴다:

1. **알 수 없는 인자 → rc=64** 이고 stderr 에 `unknown arg`
2. **`--baseline` 인데 `--session` 이 없으면 rc=64** — stderr 에 `--session <uuid> 가 필요하다`
3. **`--baseline --session <uuid>` 는 `.soak/session` 에 `SESSION_ID=<uuid>` 를 쓴다**
   (가짜 레포의 `.soak/` 아래. 파일 내용을 읽어 단언해라)

fail-closed — **이 스크립트의 존재 이유**:

4. **앵커 파일이 없으면 rc=3** 이고 stderr 에 `UNKNOWN` + `--baseline` 안내.
   ★rc=0 이 아님이 아니라 **정확히 3** 을 단언해라
5. **세션 앵커 조회가 실패하면 rc=3** (docker 스텁이 rc≠0) · **세션이 DB 에 없으면 rc=3**
   (스텁이 빈 stdout) — 둘은 다른 분기다. 각각 stderr 문구까지 재라
6. ★**psql 이 실패하면(=`q()` 가 실패) 최종 rc=3 이고 stdout 에 `UNKNOWN` 이 있다.**
   T0 조회는 성공시키고 **그 뒤의 `q()` 호출만** 실패시켜라(스텁이 호출 횟수를 파일에
   기록해 2번째 이후에 rc=1 을 내는 식). ★그리고 stdout 에
   `일부 조회가 실패했다` 가 실리는지도 함께 단언해라 — 「rc≠0」만으로는
   **스크립트가 아예 죽은 것**과 구분되지 않는다

★6 의 **양성 대조**를 붙여라 — 모든 psql 이 성공하고 지표 취득도 성공하면 rc=0 이고
stdout 에 `✓ 전 항목 조회 성공` 이 찍힌다. 이 케이스는 다음 step 에서 지표 스텁까지
갖춘 뒤 완성해도 되지만, **최소한 「항상 rc=3」이 아님을 이 step 에서 한 번은 증명해라.**

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_observe.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_observe.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 5
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 레포의 `.soak/` 가 안 생겼는지 확인해라** — `ls .soak` 가 없거나 원래 내용
   그대로여야 한다. 하나라도 바뀌었으면 가짜 레포 복사가 안 걸린 것이다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/soak-observe.sh` 를 **수정하지 마라.** 결함을 찾으면
  `@pytest.mark.xfail(reason="…")` + `summary` 한 줄
- ★**진짜 레포 루트에서 이 스크립트를 돌리지 마라** — `STATE_DIR=${REPO_ROOT}/.soak` 가
  env 로 안 바뀌어 이 레포의 세션 앵커를 덮어쓴다. 반드시 `tmp_path` 가짜 레포로 복사해라
- ★**진짜 docker 데몬에 닿게 하지 마라** — 반드시 PATH 스텁. 이 머신에 진짜
  `quantbridge-db` 가 떠 있을 수 있다
- **`uv run python` 지표 직독 경로를 타지 마라** (`QB_METRICS_DIR` 이 실재하면 그 경로가
  120초 타임아웃으로 돈다). 이 step 은 지표 취득 실패(UNKNOWN)를 정상 경로로 쓴다 —
  다음 step 이 `QB_METRICS_URL` + `curl` 스텁으로 그 축을 연다
- `awk`·`sed`·`grep`·`find`·`du` 를 스텁하지 마라. 스텁 대상은 `docker`(다음 step 은 `curl`
  추가) 뿐이다
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- macOS bash 3.2 · ubuntu bash 5 양쪽에서 통과해야 한다
