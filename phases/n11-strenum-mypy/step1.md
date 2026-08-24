# Step 1: [BL-453] 5필드 선언부 주석 정합 — 「금지」가 한 곳에만 적혀 있다

## 읽어야 할 파일

- `apps/api/tests/trading/test_no_strenum_value_access.py` — **이미 존재하고 green 인 가드.**
  대상 5필드가 65~69행에 있다. 헤더 주석 23행이 **못 잡는 것**을 스스로 적어 뒀다
- `apps/api/src/trading/models.py` — `interval`(543행) · `rule_type`(763행) 및 나머지 3필드
- `docs/backlog.md` [BL-453] 섹션 — **읽기만 해라. 수정 금지**

## 배경 — 이 항목의 원장 기술 두 절이 반증됐다

[BL-453] 은 「StrEnum + 평문 String 컬럼 필드에 `.value`/`.name` 을 쓰면 크래시한다」이고,
원장의 권장 접근 (b)「AST 기반 테스트로 정적 금지」는 **이미 구현돼 있다** —
`test_no_strenum_value_access.py`(n7 PR #797)가 5필드 전부를 대상으로 green 이다.
원장 표의 「mypy 가 선행」도 거짓이다 — mypy 는 이 축을 못 잡으므로 AC 로 쓰면 항진명제다.

**따라서 남은 실질은 권장 접근 (a) 하나다:** 5필드 **선언부 주석의 정합**.
현재 「`.value`/`.name` 금지, `==`/`!=`/`str()` 만 사용」 취지의 주석은 **`interval` 필드에만** 있고
나머지 4필드에는 없다. 즉 **코드를 읽는 사람에게 규칙이 안 보인다.**

★왜 주석이 값을 갖나: 이 결함은 **실제로 프로덕션에서 한 번 발생**했고(2026-07-25 exit-attribution),
가드는 **새로 추가되는 접근**을 막지 새 필드가 같은 패턴으로 선언되는 것을 막지 않는다.

## 작업

### ⑴ 5필드 전부에 동일한 주석을 단다

대상은 가드의 65~69행이 정의한 그 5쌍이다. **파일에서 직접 좌표를 찾아라** — 이 문서의 줄 번호는
`[가정]`이고 낡을 수 있다.

주석은 **한 형태로 통일**하고 세 가지를 담아라: ⑴ 왜 평문 `String` 컬럼인가(Sprint 26 워크어라운드),
⑵ 금지되는 접근(`.value`/`.name`), ⑶ 허용되는 접근(`==`/`!=`/`str()`), ⑷ 이것을 집행하는 파일 경로.
**기존 `interval` 주석이 이미 그 형태면 그것을 정본으로 삼아 복사해라 — 새 문구를 발명하지 마라.**

★**서사를 쓰지 마라** — 「종전에는 주석이 하나뿐이었다」 류는 커밋 메시지가 갖는다. 참인 문장만 남긴다.

### ⑵ 주석 부재를 기계로 막는다

가드 파일에 테스트를 추가한다 — **이름에 `strenum` 이 들어가야 한다**(AC 가 `-k strenum` 으로 잡는다).

`test_strenum_string_column_fields_carry_the_ban_comment`
- 대상 5쌍 각각에 대해, 그 필드 선언의 **앞 또는 같은 줄**에 금지 주석이 있는지 AST + 소스 줄로 확인
- ★**양성 대조** — 검사 대상 필드 수가 **정확히 5** 임을 함께 단언해라. 대상 목록이 비면
  「전부 통과」가 항진명제가 된다

### ⑶ 원장 인계

`summary` 에 다음을 적어라(CONTROL 이 [BL-453] 재기술에 쓴다):
- 5필드의 실제 좌표(파일:줄)
- 「(b) AST 가드는 이미 존재·green」·「mypy 는 이 축을 못 잡는다」 두 사실
- step 2 의 측정 결과가 나오기 전이므로 **RESOLVED 라고 단정하지 마라**

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/trading -k strenum -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/trading -k strenum --collect-only -q 2>/dev/null | grep -c '::')" -ge 12
cd apps/api && uv run mypy src
cd apps/api && uv run ruff check src tests/trading
```

세 번째는 step 0 의 **무회귀 확인**이다 — `models.py` 를 건드리므로 타입이 되돌아가면 안 된다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력을 재라** — 5필드 중 하나의 주석을 임시로 지워 `-k strenum` 이 red 가 되는지 보고
   **반드시 원복**해라(`git diff --stat`).
3. 주석에 적은 경로가 **실재하는지** 확인해라(죽은 좌표 금지).
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`sa_column` 을 `sa.Enum` 으로 바꾸지 마라**(원장의 권장 접근 (c) 근본안).
  이유: DB 타입 변경이라 migration 이 따라붙고, **이름 없는 native enum 은 PG 가 컴파일을 거부한다**
  (이 레포가 실제로 밟았다). 이 lane 의 범위 밖이다.
- **`docs/backlog.md` 를 수정하지 마라.** 이유: 원장은 CONTROL 소관이고 단일 파일이라 충돌한다.
- **`models.py` 의 동작 코드를 바꾸지 마라** — 이 step 은 주석과 테스트만이다.
- **`tests/common/**` · `tests/scripts/**` · `src/tasks/**` · `src/common/**` 를 만지지 마라.**
- **`CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
