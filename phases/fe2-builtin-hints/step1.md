# Step 1: catalog-invariants

## 읽어야 할 파일

- `apps/web/src/lib/unsupported-builtin-hints.ts` — 대상. 이번엔 **`_HINTS` 카탈로그 전체**
- `apps/web/src/lib/__tests__/unsupported-builtin-hints.test.ts` — step 0 이 만든 파일. **이어 쓴다**

## 배경

step 0 은 **변환 규칙**(적중/미적중/목록)을 고정했다. 이 step 은 **카탈로그 자체의 불변식**을 고정한다.

★**왜 카탈로그를 재는가** — `_HINTS` 는 모듈 private 이라 밖에서 못 읽는다. 그래서 **알려진
빌트인 이름 목록을 태워서** 성질을 재야 한다. 이 카탈로그는 Sprint 21 → 32 로 두 번 backfill 됐고
(Pine v6 collection types · `request.*` · `syminfo.*` · `ta.*` alternates), 그때마다
**아무 테스트도 없이** 늘어났다.

★**CONTROL 실측(2026-08-21)** — 엔트리 **55개** · `alternative` 26 · `noop` 24 · `corruption` 5.
**이 숫자를 그대로 단언하지 마라** — 카탈로그는 계속 자란다. **하한**으로 써라.

## 작업

`apps/web/src/lib/__tests__/unsupported-builtin-hints.test.ts` 에 케이스를 **추가**한다(새 파일 금지).

### 최소한 이 다섯을 더 덮어라 (파일 전체 케이스 ≥12)

1. ★**category 3종이 전부 실재한다** — 각 category 에 대해 **적중하는 이름을 최소 1개씩** 배열로
   두고 `getUnsupportedBuiltinHint` 로 확인한다. 셋 중 하나라도 카탈로그에서 사라지면 red 다
2. ★★**corruption 목록이 Trust Layer 결정을 지킨다** — `heikinashi` · `security` ·
   `request.security` · `request.security_lower_tf` **넷이 전부 `corruption`** 이다.
   ★이것들은 「조용한 데이터 오염 위험」 때문에 일부러 unsupported 로 남긴 것들이라
   **`noop` 으로 강등되면 사용자가 결과를 믿게 된다.** 이 케이스에 그 근거를 주석으로 달아라
3. ★**모든 적중 항목의 hint 가 성질을 만족한다** — 알려진 이름을 **12개 이상** 배열에 두고
   parametrize 로 돌려, 각각 ⑴ `hint` 가 비어있지 않다 ⑵ `hint` 가 **fallback 문구를 포함하지
   않는다**(`"— 미지원 빌트인"`) ⑶ `category` 가 세 값 중 하나다 ⑷ `name` 이 인자와 같다.
   ★**⑵ 가 핵심이다** — 이름을 오타로 적으면 fallback 이 나와 「통과」가 되고, 그러면 이 케이스는
   **카탈로그를 하나도 안 재게 된다**(0건 초록)
4. ★**정확 일치만 한다 — 음성 대조** — `"Heikinashi"`(대문자) · `"heikinashi "`(뒤 공백) ·
   `"request.securit"`(접두) · `"request.security2"` 넷은 **fallback** 이다.
   조회는 `_HINTS[name]` 직접 인덱싱이라 **정규화가 없다**는 계약이다
5. ★**category 별 대표 이름이 서로 다른 hint 를 준다** — 서로 다른 3개 이름의 `hint` 문자열이
   **모두 다르다**(카탈로그가 한 값으로 뭉개지지 않았다). Set 크기로 재라

★**엔트리 총 개수를 세려고 `_HINTS` 를 export 시키지 마라** — 대상 파일 무변경이 이 lane 의 계약이다.
개수 대신 **위 3번의 「12개 이상 알려진 이름이 전부 적중한다」** 가 카탈로그의 양성 대조다.

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/unsupported-builtin-hints.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/unsupported-builtin-hints.test.ts 2>/dev/null | grep -c ' > ')" -ge 12
cd apps/web && pnpm exec eslint src/lib/__tests__/unsupported-builtin-hints.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 최종 케이스 수와 **케이스 3 에서 태운 이름 개수**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/unsupported-builtin-hints.ts` 를 **수정하지 마라** — `_HINTS` 를 export 로
  바꾸는 것도 수정이다. 결함은 `summary` 한 줄로
- ★**hint 문장 전문을 테스트에 복사해 오지 마라** — 항진명제가 되고 문구 수정마다 red 가 난다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- step 0 이 만든 케이스를 지우거나 약화시키지 마라. 케이스 수는 단조 증가여야 한다
- 새 테스트 파일을 만들지 마라 — 이 lane 이 소유한 파일은 하나다
- 커밋하지 마라(커밋은 러너 소관)
