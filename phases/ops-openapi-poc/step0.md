# Step 0: poc-filter-closure

## 읽어야 할 파일

- `tools/scripts/openapi-poc-filter.py` — **이번 테스트의 대상** (133줄 전량)
- `apps/api/tests/scripts/test_soak_gate_predicate.py` — 이 디렉터리의 테스트 관용구
  (특히 「스크립트를 경로로 로드한다」 선례)

## 배경

이 필터는 [BL-717] PoC 산출물(`contracts/openapi/poc/openapi.poc.json`)을 만든다.
2026-08-16 적대 리뷰가 여기서 **무게이트 2단**을 잡았다 — `export_openapi.py --check` 는
1단(전량 파일)만 보고, orval 이 실제로 읽는 것은 이 2단 산출물인데 아무도 안 봤다.
그래서 실제로 drift 해 있었다(`warnings` 필드 누락). `--check` 는 그 수리로 생겼고,
**그 `--check` 자신의 테스트가 0건이다.**

판정의 핵심은 `$ref` **폐포(transitive closure)** 다 — 새로 편입된 스키마가 또 참조하는
스키마까지 수렴할 때까지 도는 `while` 루프. 한 바퀴만 돌면 손자 스키마가 빠지고,
산출물은 **참조가 깨진 채로 정상처럼 보인다.**

## 작업

`apps/api/tests/scripts/test_openapi_poc_filter.py` 를 신설하고 **폐포 + 전제 거부**를 단언하라.

### 호출 방식 (이 lane 의 유일한 방식 — 여기서 벗어나지 마라)

★**스크립트의 `SOURCE`/`OUTPUT` 은 `Path(__file__).parents[2]` 에서 파생되고 env 로 못 바꾼다.**
그래서 **`tmp_path` 아래 가짜 레포로 복사해서** 돌린다. 진짜 레포 경로를 겨누면 테스트가
커밋된 `contracts/openapi/poc/openapi.poc.json` 을 **덮어쓴다**.

```python
import json, shutil, subprocess, sys
from pathlib import Path

REAL = Path(__file__).resolve().parents[3] / "tools" / "scripts" / "openapi-poc-filter.py"

def _fake_repo(tmp_path, source_doc: dict | None) -> Path:
    """tmp_path/tools/scripts/openapi-poc-filter.py + tmp_path/contracts/openapi/openapi.json"""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL, scripts / "openapi-poc-filter.py")
    if source_doc is not None:
        src = tmp_path / "contracts" / "openapi" / "openapi.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(json.dumps(source_doc, ensure_ascii=False), encoding="utf-8")
    return scripts / "openapi-poc-filter.py"

def run(script: Path, *args):
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=60)
```

원본 스키마는 **손으로 만든 최소 문서**다. `KEEP` 이 요구하는 세 경로를 그대로 넣어라 —
`/health`(get) · `/api/v1/strategies`(get) · `/api/v1/backtests/{backtest_id}`(get).
`openapi` · `info.title` · `info.version` · `paths` · `components.schemas` 가 필요하다.

### 최소한 이 여섯을 덮어라

1. **원본 부재 → rc=2** 이고 stderr 에 `export_openapi.py 를 먼저 돌려라`
2. **`KEEP` 경로가 원본에 없음 → rc=2** (`/health` 를 뺀 문서) — stderr 에 그 경로
3. **메서드 누락 → rc=2** (`/health` 는 있는데 `get` 이 없고 `post` 만 있을 때)
4. ★**`$ref` 폐포가 전이적이다** — `/health` 응답이 `A` 를 참조하고, `A` 가 `B` 를,
   `B` 가 `C` 를 참조하는 사슬을 만들어라. 산출물 `components.schemas` 에
   **A·B·C 가 전부 있고**, 아무도 참조하지 않는 `D` 는 **없다**.
   ★이것이 이 lane 의 핵심 케이스다 — 한 바퀴만 도는 구현은 `C` 를 빠뜨린다
5. **`$ref` 대상이 `components.schemas` 에 없으면 rc=2** — stderr 에 그 이름
6. **`securitySchemes` 는 있으면 보존되고 없으면 키 자체가 없다** (두 방향 다 재라 —
   한 방향만 재면 「항상 넣는다」와 「항상 뺀다」 중 하나가 초록으로 통과한다)

★4·6 은 산출물 JSON 을 **읽어서** 단언해라(stdout 문자열이 아니라). 산출 경로는
`tmp_path/contracts/openapi/poc/openapi.poc.json` 이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_openapi_poc_filter.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_openapi_poc_filter.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 레포 파일이 안 바뀌었는지 확인해라** — `git status --porcelain contracts/` 가
   비어야 한다. 하나라도 바뀌었으면 가짜 레포 복사가 안 걸린 것이다.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/openapi-poc-filter.py` 를 **수정하지 마라.** 결함을 찾으면
  `@pytest.mark.xfail(reason="…")` + `summary` 한 줄
- ★**진짜 레포의 `contracts/openapi/**`를 겨누지 마라.** 반드시`tmp_path`가짜 레포로
복사해서 돌려라. 이유: 인자 없이 실행하면 스크립트가`OUTPUT` 을 **쓴다** —
  진짜 경로면 커밋된 산출물을 덮어쓴다
- `importlib` 로 import 해서 `SOURCE`/`OUTPUT` 을 monkeypatch 하는 방식을 쓰지 마라.
  이유: 이 lane 은 `sys.exit(main())` 까지 포함한 **rc 계약**이 산출이다. subprocess 로 재라
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
