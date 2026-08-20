# Step 0: canon-invariants

## 읽어야 할 파일

- `apps/web/src/lib/marketing-canon.ts` — **이번 테스트의 대상** (64줄)
- `apps/web/src/lib/legal-links.ts` — 함께 재는 대상 (7줄)
- `apps/web/src/components/exchange-support-table.tsx` — 표를 렌더하는 소비자
- `apps/web/src/features/marketing/components/landing-performance.tsx` — 성능 3값 소비자
- `apps/web/src/lib/__tests__/geo.test.ts` — 이 디렉터리의 테스트 관용구

## 배경

이 파일은 **마케팅 화면 공동 원장**이다. 헤더가 존재 이유를 적고 있다:

> screen-14(랜딩)·screen-16(요금제)·screen-17(웨이트리스트)가 셀 단위로 같은 값을 렌더한다.
> 값을 여기 한 곳에만 두어 **화면마다 지어내는 것**(LESSON-063 크로스페이지 우회)을 막는다.

**테스트는 0건이다.** `legal-links.ts` 는 **어떤 테스트도 import 하지 않는다**(전이 폐포 실측).

★**이 lane 의 함정은 항진명제다.** 상수를 그대로 베껴 단언하면 「소스 = 소스」를 재는 것이고
판별력이 0 이다. **파생 관계**와 **불변식**만 재라 — 아래 목록이 그것이다.

## 작업

`apps/web/src/lib/__tests__/marketing-canon.test.ts` 를 신설한다.
두 모듈을 직접 import 해 부른다(mock 없음 — 상수와 타입뿐이다).

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★★**성능 3값의 파생 관계** — `PERF_FIGURES` 의 세 `value` 를 숫자로 파싱해
   **`round(20064 / 3.24) === 6193`** 을 단언한다(봉 수 ÷ 소요 시간 = 초당 처리 봉 수).
   ★**세 값을 상수로 베껴 적지 마라** — `PERF_FIGURES` 에서 읽어 파싱하고 **셋 사이의 산술**을 재라.
   숫자 하나가 바뀌면 나머지 둘과 어긋나 red 가 난다. 이것이 이 파일의 유일한 진짜 계산이다
2. ★**로드맵 행은 무데이터 쌍이다** — `EXCHANGE_SUPPORT` 에서 `status === "roadmap"` 인 행은
   **`environment` 와 `scope` 가 둘 다 `null`**. 하나만 null 이면 표가 반쪽 셀을 렌더한다
3. ★**지원 행은 그 반대다** — `status === "supported"` 인 행은 `environment`·`scope` 가 **둘 다
   non-null 이고 빈 문자열이 아니다**
4. ★**양성 대조 — 두 종류가 모두 실재한다** — roadmap 행 ≥1 · supported 행 ≥1.
   **이것이 없으면 2·3 은 빈 배열에도 통과하는 항진명제다**
5. ★★**OKX 는 「연결해 본」 목록에 없다** — `EXCHANGE_SUPPORT` 에서 `exchange === "OKX"` 인 행이
   존재하고 그 `status` 가 **`"roadmap"`** 이다. 헤더가 「OKX 를 "연결해 본" 목록에 넣지 않는다」로
   못박은 것이고, `supported` 로 올라가면 **하지 않은 일을 했다고 적는 것**이 된다.
   ★일반화해서 함께 재라: `supported` 인 행의 `exchange` 는 **전부 `"Bybit"`** 이다
   (「Bybit 데모·메인넷만 지원」 — 계정 모드 계약과 같은 문장이다)
6. ★**고지 3종이 비어 있지 않고 서로 다르다** — `ROADMAP_DISCLAIMER` · `PERF_DISCLAIMER` ·
   `EXCHANGE_TABLE_CAPTION` 이 각각 길이 > 0 이고 **세 문자열이 서로 다르다**(복사 실수 방지).
   ★**전문을 베껴 단언하지 마라** — 문구 수정마다 무의미하게 red 가 난다
7. ★**조건 없는 성능 형용사 금지 — 음성 대조** — `PERF_FIGURES` 의 각 항목은 `note` 가
   **비어 있지 않다**(\_KIT.md §4.8: 성능 3값은 **조건과 함께만** 쓴다).
   note 가 빈 항목이 하나라도 있으면 화면에 조건 없는 숫자가 나간다
8. ★**`EMPTY_CELL` 이 무데이터 관례를 지킨다** — `EMPTY_CELL` 이 한 글자이고 공백이 아니다.
   그리고 `EXCHANGE_NO_ENV_TITLE`·`EXCHANGE_NO_SCOPE_TITLE` 이 **서로 다른** 비어있지 않은 문장이다
   (로드맵 셀의 `title` 이 이유를 밝히는 자리다)
9. ★**`LEGAL_LINKS`** — 키가 정확히 `disclaimer`·`terms`·`privacy` **셋**이고, 값이 전부
   **`/` 로 시작하는 앱 내부 경로**이며 서로 다르다. ★외부 URL(`http`)이 섞이면 안 된다
10. ★**양성 대조 — 실제로 모듈을 부르고 있는지 재라.** `EXCHANGE_SUPPORT` 길이 ≥5 ·
    `PERF_FIGURES` 길이 === 3 · `Object.keys(LEGAL_LINKS).length === 3`.
    빈 배열에 초록이 나는 모양을 배제한다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run src/lib/__tests__/marketing-canon.test.ts
cd apps/web && test "$(pnpm exec vitest list src/lib/__tests__/marketing-canon.test.ts 2>/dev/null | grep -c ' > ')" -ge 8
cd apps/web && pnpm exec eslint src/lib/__tests__/marketing-canon.test.ts
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **케이스 1 의 파생식이 실제로 맞았는지**(round(20064/3.24) 의 실측값)를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/lib/marketing-canon.ts` · `src/lib/legal-links.ts` 를 **수정하지 마라.**
  결함은 `summary` 한 줄로
- ★★**고지 문장·hint 문장의 전문을 테스트에 복사해 오지 마라. 이유:** 소스를 그대로 베낀 단언은
  **항진명제**(소스 = 소스)라 판별력이 0 이고, 문구를 고칠 때마다 의미와 무관하게 red 가 난다.
  **파생 관계와 불변식**만 재라
- ★**화면 컴포넌트를 렌더하지 마라** — 이 lane 은 원장 모듈만 잰다. 화면 대조는 e2e 의 몫이다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
