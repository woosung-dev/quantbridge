# Step 2: StrEnum 가드가 스스로 적어 둔 사각 — 별칭과 `getattr`

## 읽어야 할 파일

- `apps/api/tests/trading/test_no_strenum_value_access.py` — 특히 **헤더 주석 23행**:
  「못 잡는 것: 별칭(`c = row.channel; c.value`), getattr 같은 동적 접근, 그리고 스코프 밖 파일이다.」
  그리고 `_ALLOWLIST`(31~41행 근처) · 대상 5쌍(65~69행)
- step 1 의 `summary`

## 배경

가드가 **자기 사각을 문장으로 적어 뒀다.** 적어 뒀다는 것은 알고 있다는 뜻이지 막고 있다는 뜻이 아니다.
지금 아래는 통과한다:

```python
alias = row.classification      # 별칭
alias.value                     # ← 안 잡힌다

getattr(row, "classification").value   # ← 안 잡힌다
```

★파일 243~248행 근처에 **이 형태들이 이미 픽스처로 존재**한다(`row.classification.value` ·
`alias = row.classification` · `getattr(row, "classification").value`). 즉 **재료는 이미 있다** —
없는 것은 그것을 위반으로 세는 단언이다.

## 작업

같은 파일에 축을 추가한다. **새 파일을 만들지 마라** — 이 축의 검사기가 둘이 되면 안 된다.
**테스트 이름에 `strenum_alias` 를 포함시켜라**(AC 가 `-k strenum_alias` 로 잡는다).

### ⑴ 별칭 1홉 추적

**같은 함수 스코프 안에서** `<name> = <expr>.<대상필드>` 대입을 수집하고, 그 `<name>` 에 대한
`.value` / `.name` 접근을 위반으로 센다. **1홉만 한다** — 재대입 추적·분기 해석·함수 경계 넘기를
하지 마라(이유는 아래 금지사항).

### ⑵ `getattr` 동적 접근

`getattr(<any>, "<대상필드 문자열 리터럴>")` 의 결과에 대한 `.value`/`.name` 접근을 위반으로 센다.
문자열이 리터럴이 아니면(변수·f-string) **대상이 아니다** — 셀 수 없다는 사실을 주석으로 남겨라.

### ⑶ 동결과 대조

`_FROZEN_ALIAS_VIOLATIONS: dict[str, int]`(경로→건수)로 **정확 동등** 비교한다.
**수치는 직접 측정해서 넣어라.** 빈 결과면 `{}` 로 동결하고, ★**빈 동결에 「아직 남아 있다」쪽
대칭 검사를 두지 마라**(항진명제 — `tests/common/test_repository_boundary_guard.py:128` 주석 참조).

### ⑷ 테스트 3건

1. `test_strenum_alias_access_matches_the_frozen_map` — 실측 == 동결
2. `test_strenum_alias_scanner_detects_synthetic_violations` — ★**양성 대조.**
   합성 소스(파일에 이미 있는 픽스처 문자열 패턴 재사용)에서 별칭·`getattr` 두 형태가 검출된다
3. `test_strenum_alias_scanner_ignores_safe_comparisons` — ★**음성 대조.**
   `alias == X` · `str(alias)` · 대상 아닌 필드의 별칭은 잡히지 **않는다**

### ⑸ `src` 에서 위반이 나오면 — 고치지 마라

좌표를 `summary` 에 남기고 동결 맵에 넣어라. **이유는 lane 격리다** — `src/trading/**` 의
동작 코드 수정은 이 lane 의 범위 밖이고, 다른 lane 이 같은 트리를 건드릴 수 있다.
동결에 넣을 때는 **왜 지금 안 고치는지**를 주석 한 줄로 남겨라(`_ALLOWLIST` 의 기존 형식을 따라라 —
그 파일은 allowlist 항목마다 사유를 요구하는 검사를 이미 갖고 있다).

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/trading -k strenum_alias -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/trading -k strenum_alias --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/trading -q
cd apps/api && uv run ruff check tests/trading
```

세 번째는 **무회귀**다 — 기존 가드 단언을 약화시키지 않았는지 본다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **실파일 판별력을 1회 재라** — `src/trading` 어딘가에 별칭 형태를 임시로 심고 red 를 확인한 뒤
   **반드시 원복**해라(`git diff --stat`). 합성 픽스처만으로는 스캔 경로가 실파일에 닿는지 모른다.
3. 기존 테스트 수가 **줄지 않았는지** 확인해라(`--collect-only` 로 전후 비교).
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **별칭을 다홉·분기·함수 경계 너머로 추적하지 마라.** 이유: 정적 해석의 끝이 없는 구간이고,
  그 모델링 자신이 결함을 만든 선례가 있다(2026-08-17). **1홉 + 대조 2종**이 범위다.
- **`src` 의 동작 코드를 고치지 마라**(임시 변이는 원복). 이유: lane 격리 — 다른 lane 과 diff 가 겹친다.
- **빈 동결에 대칭 검사를 두지 마라.** 이유: 항진명제라 판별력 0 인데 통과 수만 늘린다.
- **`_ALLOWLIST` 의 기존 3건을 지우지 마라.** 이유: 그것은 메모리 dataclass 값에 대한 제어군이고,
  파일 안 테스트가 그 개수를 직접 단언한다.
- **`tests/common/**` · `tests/scripts/**` · `.github/**` 를 만지지 마라.**
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
