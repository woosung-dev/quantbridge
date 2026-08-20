# Step 1: poc-filter-check

## 읽어야 할 파일

- `tools/scripts/openapi-poc-filter.py` — 특히 직렬화(106행)와 `--check` 블록(108~124행)
- `apps/api/tests/scripts/test_openapi_poc_filter.py` — **앞 step 이 만든 파일. 이어 붙인다**

## 배경

`--check` 는 「커밋된 부분집합이 현재 전량 export 에서 다시 뽑은 것과 같은가」를 묻는다.
이것이 CI 에서 빠진 지금([ADR-037] 로 OpenAPI drift 잡 철거) 이 판정은 **손으로 돌리는
것 하나뿐**이다. 그 판정기가 조용히 고장나면 drift 가 다시 쌓인다.

drift 판정은 **바이트 동일성**이다 — 결정적 직렬화(키 정렬 · indent 2 · 끝 개행 고정)가
전제다. 그 전제가 깨지면 내용이 같아도 매번 drift 로 뜬다.

## 작업

`apps/api/tests/scripts/test_openapi_poc_filter.py` 에 **직렬화 계약 + `--check` 3분기**를
이어 붙여라. 앞 step 의 `_fake_repo`/`run` 헬퍼를 재사용한다(새 헬퍼 모듈 금지).

### 최소한 이 넷 + 앞 step 6건 = 10건을 채워라

직렬화 계약:

1. **키가 정렬돼 있고 indent 2 이며 파일이 개행 하나로 끝난다** — 산출물 텍스트를
   `json.dumps(json.loads(text), sort_keys=True, indent=2, ensure_ascii=False) + "\n"` 과
   **바이트 동일**한지로 재라. 그리고 원본에 키를 뒤섞어 넣어도 산출물이 같은지(결정성)
2. **`info.title` 에 ` (BL-717 PoC subset)` 접미가 붙고 나머지 `info` 필드는 보존된다**
3. **인자 없이 실행하면 `OUTPUT` 부모 디렉터리까지 만든다** (`poc/` 가 없어도 rc=0) ·
   stdout 에 `작성:` 과 경로·스키마 개수

`--check` 3분기 — **rc 를 정확히 단언해라**:

4. **산출물이 없으면 rc=1** 이고 stderr 에 `먼저 인자 없이 실행해라`
5. **동일하면 rc=0** 이고 stdout 에 `drift 없음`
6. ★**한 바이트라도 다르면 rc=1** 이고 stderr 에 `재생성:` 안내.
   ★공백 하나만 바꾼 산출물로 재라 — 「JSON 으로 파싱하면 같은데 바이트는 다른」 형태가
   이 판정이 잡아야 하는 것이다
7. ★**`--check` 는 파일을 쓰지 않는다** — drift 상태에서 `--check` 를 돌린 뒤
   산출물 내용이 **그대로**인지 단언해라. 쓰면 「검사하면 고쳐진다」가 되어 drift 가 은폐된다

★양성 대조 — 5(동일 → rc=0)와 6(다름 → rc=1)을 **같은 픽스처에서 연달아** 재라.
한쪽만 재면 「항상 rc=0」/「항상 rc=1」 구현이 통과한다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_openapi_poc_filter.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_openapi_poc_filter.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★`git status --porcelain contracts/` 가 비어 있는지 확인해라(가짜 레포 격리 증명).
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/openapi-poc-filter.py` 를 **수정하지 마라**
- ★**진짜 레포의 `contracts/openapi/**`를 겨누지 마라** — 반드시`tmp_path` 가짜 레포
- `conftest.py`·공용 헬퍼 모듈·`shards.json`·`docs/**` 무변경. DB 픽스처 금지. 커밋하지 마라
- 앞 step 이 만든 테스트를 지우거나 이름을 바꾸지 마라 — AC 수집 하한이 누적값(≥10)이다
