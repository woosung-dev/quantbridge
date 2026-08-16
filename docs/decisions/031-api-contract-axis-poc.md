# ADR-031: API 계약축 PoC — OpenAPI export 정착 + 생성 client 후보 판정 (BL-717)

**날짜:** 2026-08-13
**상태:** Accepted (PoC 범위) — 전면 전환은 별도 결정
**관련:** [ADR-029](029-monorepo-standard-layout.md)(표준 7축 중 계약축 부재 확인) · [BL-717]

## 컨텍스트

FE↔BE 타입 공유가 전무했다. 실측(2026-08-13, BL-717 등록 시): FE codegen 의존성 0 ·
openapi export 스크립트/CI 스텝 0 · FE 는 수기 `apps/web/src/lib/api-client.ts` + Zod v4
스키마 142개(14파일 2,259줄)가 BE Pydantic 97모델/63엔드포인트를 **주석 좌표 + 정규식
vitest 1건**(`deactivation-reason.test.tsx`)으로만 동기화. ADR-029 가 이 축을 [BL-717]
PoC 로 미뤘고, PR #619 머지로 트리거가 도래했다.

## 결정

### 1. 결정적 OpenAPI export 를 계약 SSOT 로 커밋한다

- `apps/api/scripts/export_openapi.py` — `create_app().openapi()` 를 키 정렬 + indent 2 +
  개행 고정으로 `contracts/openapi/openapi.json` 에 덤프. `APP_ENV=development` 를 스크립트
  안에서 강제해 호스트 환경이 계약에 새지 않는다.
- **AC 실증:** 2회 실행 sha256 동일(byte-identical) · `--check` 양성(일치 → exit 0) ·
  음성(1바이트 훼손 → exit 1) 모두 통과.
- PoC 부분집합은 `tools/scripts/openapi-poc-filter.py` → `contracts/openapi/poc/openapi.poc.json`
  (health + strategies list + backtest detail, $ref 폐포 17스키마).
- ★**`contracts/openapi/` 는 `.prettierignore` 면제** — 1차 커밋에서 pre-commit `prettier --write`
  가 짧은 배열을 한 줄로 접어(797줄 diff) 커밋본 ≠ export 출력이 됐고 `--check` 가 영구
  빨강이 될 뻔했다. 생성물의 포맷은 생성기(json.dumps)가 소유한다 — bl595 픽스처와 같은 축.
  「검사는 커밋 뒤에」(AGENTS.md 게이트 규칙)가 산출물 파일에도 성립함의 실증.

### 2. 후보 판정 — orval(zod client) 채택, 나머지 탈락 사유 명기

| 후보                          | 실행                                                                                                                                    | tsc strict | zod v4                                                     | 판정                                                             |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------- | ---------------------------------------------------------------- |
| `openapi-typescript@7.13`     | ✅ 569줄                                                                                                                                | ✅         | — (타입 전용, 런타임 검증 0)                               | 차점 — 수기 Zod 체계와 병행하면 경계 검증이 이중화되지 않는 반쪽 |
| **`orval@7.21` client:'zod'** | ✅ 203줄                                                                                                                                | ✅         | ✅ **v4 API 직접 출력**(`zod.uuid()`·`zod.iso.datetime()`) | **채택**                                                         |
| `@hey-api/openapi-ts`         | ❌ 0.99.0·0.98.0 모두 자체 TypeScript 7 의존과 비호환 크래시(`ts.SyntaxKind` undefined — pnpm dlx·npx 재현, 외부 피어 고정으로 못 막음) | —          | —                                                          | 탈락 (도구 성숙도 리스크 실측)                                   |

> **묘비 (2026-08-16)** — 탈락한 hey-api 의 설정 파일 `apps/web/openapi-ts.config.ts` 를 삭제했다.
> 그 `output` 이 가리키던 `src/lib/api-contract-poc/generated/hey-api` 는 크래시로 **한 번도 생긴 적이
> 없고**, 부르는 npm script 도 CI 스텝도 없었다. 원문 = `git show 7eda1dea:apps/web/openapi-ts.config.ts`.

**zod v4 공존 실증** (`src/lib/api-contract-poc/__tests__/zod-v4-coexist.test.ts`, 3/3):
수기(`import { z } from "zod/v4"`)와 생성(`import * as zod from "zod"`)이 같은 zod@4.3.6
런타임에서 같은 표본을 통과시키고, 깨진 uuid 를 양쪽 모두 거부한다(생성물이 실제로
검증함의 판별). `apps/web/AGENTS.md` §8 의 `zod/v4` 규칙과 충돌 없음 — zod@4 패키지에서
두 import 경로는 같은 v4 구현이다.

### 3. drift 게이트 = `export_openapi.py --check` (~~CI 배선은 다음 회차~~ → **2026-08-16 배선됨**)

> **2026-08-16 후속.** 아래 스케치를 실제로 붙였다 — `ci.yml` `backend_static` 잡의 스텝 ·
> `make openapi-check` · `final-gates.sh` 의 `BE openapi drift`(BE 영역 판정 안).
> **배선 첫 실행이 실제 drift 1건을 잡았다** — 2026-08-17 ADR-034 회차에서 `DELETE /auth/me` 의
> 독스트링이 바뀌었는데 계약을 재생성하지 않아, 그 사이 계약이 코드보다 낡아 있었다.
> 즉 「다음 회차」로 미룬 3일 동안 게이트 없는 계약이 실제로 새고 있었다.

CI 스케치 — backend 계열 잡에 1스텝:

```yaml
- name: OpenAPI drift check
  working-directory: apps/api
  run: uv run python scripts/export_openapi.py --check
```

주의 2건: ① Settings 의 `trading_encryption_keys` 가 필수라 backend 잡의 기존 env 주입을
그대로 전제한다 ② `.github/workflows/**` 가 backend paths-filter 에 이미 포함돼 있어
게이트 자신을 고치는 PR 도 발화한다(ADR-029 canary 와 같은 축). ~~**이번 회차는 ci.yml 을
건드리지 않는다**~~ → **2026-08-16 에 배선했다**(위 후속 블록). 남은 비결정은 **수기 스키마
대체 범위**뿐이다 — 생성물은 아직 `api-contract-poc/` 안에만 있고 프로덕션 경로는 수기 Zod 다.

## 구조 diff — 수기 vs 생성 (AC ⑶ 핵심 발견)

1. **Decimal→string 이 계약에 충실히 실린다** — metrics 필드(`sharpe_ratio` 등)가
   `zod.string()|null` 로 생성. 수기 주석(「BE 는 Decimal 을 문자열로 직렬화」)이 계약
   차원에서 기계 검증 가능해진다.
2. **datetime 엄격도 역전** — 생성은 `zod.iso.datetime({})`(Z-only), 수기는
   `{ offset: true }`(+09:00 허용). 공존 테스트 3번이 이 차이를 고정했다.
   ★[확인 필요] BE 실직렬화가 Z 표기인지 offset 표기인지 실측 전에는 생성 스키마를
   런타임 경계에 꽂지 마라 — 수기의 `offset: true` 가 실데이터 근거였을 가능성이 있다.
3. **deprecated 가 계약에 산다** — `page` 쿼리 파라미터의 「Sprint 6+ 제거 예정」 주석이
   생성물 `.describe()` 로 전파된다. 수기 레이어에는 이 정보가 없다.
4. 응답 골격(items/total/page/limit/total_pages)은 5/5 필드 일치 — 이번 표본에서 구조
   드리프트는 없었다. 단 optionality 뉘앙스(BE default 필드가 계약에선 optional)는
   필드 단위 대조가 도입 회차에서 필요하다.

## 번들 영향 (AC ⑸ — 측정 방식 변경 사유 명기)

생성물은 앱 코드가 import 하지 않으므로 현재 번들 delta = 0 이고, ANALYZE=1 전후 대조는
판별력이 없다. 대신 한계비용을 esbuild 로 실측했다: 3엔드포인트 zod 스키마 = **11,114 B
min / 2,902 B min+gzip** (zod external — zod 는 기존 의존이라 한계비용은 스키마뿐).
`openapi-typescript` 산출물은 타입 전용이라 0 B.

## 도입 범위 (이 ADR 이 결정하는 것 / 안 하는 것)

- **결정:** `contracts/openapi/openapi.json` 을 커밋 산출물로 유지하고, 후보는 orval
  (client:'zod') 로 고정한다. 수기 스키마의 **대조 기준**으로 즉시 사용 가능.
- **비결정(다음 회차):** CI drift 게이트 배선 · 수기 스키마를 생성물로 대체할 도메인
  범위 · datetime 직렬화 실측([확인 필요] 해소) · 전면 전환 여부.

## 롤백

PoC 산출물은 전부 추가 파일(+ eslint ignore 1줄)이라 커밋 revert 로 무손실 제거된다.
런타임 경로는 이 회차에서 1바이트도 바뀌지 않았다.
