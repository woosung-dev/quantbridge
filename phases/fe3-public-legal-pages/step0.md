# Step 0: public-legal-pages

## 읽어야 할 파일

- `apps/web/src/app/disclaimer/page.tsx` · `terms/page.tsx` · `privacy/page.tsx` ·
  `not-available/page.tsx` — **이번 테스트의 대상 4개** (85·101·121·29줄)
- `apps/web/src/components/legal/legal-page-shell.tsx` — 넷이 공유하는 셸
- `apps/web/src/lib/legal-links.ts` — 링크 상수 SSOT (이미 테스트가 있다 — 고치지 마라)
- `apps/web/src/app/__tests__/not-found.test.tsx` — ★**이 디렉터리의 관용구다.
  `render` + `screen` 사용법을 여기서 보고 같은 모양으로 써라**

## 배경

이 넷은 **로그인 이전에 실제 사용자가 보는 화면**이다 — `proxy.ts` 의 공개 라우트 목록에 들어 있고
(2026-08-21 `fe2-proxy-gate` lane 이 그것을 테스트로 고정했다), `/not-available` 은 **geo-block L2 의
착지점**이다. 그런데 **어떤 테스트도 이 넷을 import 하지 않는다**(전이 폐포 실측 2026-08-21).

★**법무 페이지가 조용히 비면 규제 프레이밍이 사라진다.** 이 회차는 **화면이 실제로 무엇을 말하는지**를
고정한다 — 문구 전문이 아니라 **구조와 링크**를 잰다.

★**넷 다 서버 컴포넌트지만 async 가 아니다**(`export const metadata` + 순수 JSX). RTL 의 `render` 로
그대로 렌더된다 — 데이터 페칭도 `headers()` 호출도 없다(착수 전 확인).

## 작업

`apps/web/src/app/__tests__/public-legal-pages.test.tsx` **하나**를 신설한다.
네 페이지를 각각 default import 해서 렌더한다(mock 없이).

### 최소한 이 아홉을 덮어라 (케이스 ≥9)

1. ★**넷 다 던지지 않고 렌더된다** — parametrize 로 넷을 돌려 `render()` 가 성공하고
   **`document.body.textContent` 가 비어 있지 않다**. ★**이것이 양성 대조다** — 셸이 깨져
   빈 화면이 나가는 것을 잡는다
2. **각 페이지가 자기 제목을 갖는다** — 넷 각각에서 `heading` role 요소가 **1개 이상** 있고
   텍스트가 비어 있지 않다. ★문구 전문을 단언하지 마라(개정될 문서다)
3. ★**`metadata` — 관측된 사실을 그대로 박아라(고치지 마라).**
   ★**CONTROL 이 2026-08-21 에 직접 실측했다:**

   | 페이지 | `export const metadata` |
   | --- | --- |
   | `disclaimer` · `terms` · `privacy` | **있다** (`title` = Disclaimer / Terms of Service / Privacy Policy) |
   | **`not-available`** | ★**없다** — `<title>` 이 비어 나간다 |

   ⇒ **넷 다 갖는다고 단언하지 마라 — red 가 난다(실측).** 대신 이렇게 재라:
   ⑴ 법무 3종은 `metadata.title` 이 **비어 있지 않다**(각각 import 해서),
   ⑵ 세 `title` 이 **서로 다르다**,
   ⑶ ★**`not-available` 은 `metadata` 를 export 하지 않는다**를 **지금 동작으로 고정**하고
   「이것은 결함이다 — [BL-816] · 대상 무변경이 이 lane 의 계약이라 고정만 한다」 주석을 달아라.
   ★고쳐지면 이 케이스가 red 로 뒤집힌다 — **그것이 [BL-816] 의 종결 신호다.**
4. ★★**`/not-available` 은 geo-block 의 착지점이다** — 「이 지역에서는 이용할 수 없다」는 뜻이
   화면에 있고(문구 전문이 아니라 **연락 수단**), ★**이메일 링크(`mailto:`)가 있다**를 단언해라.
   막힌 사용자가 나갈 문이 그것뿐이다
5. ★**법무 3종은 서로 다른 내용이다** — `disclaimer`·`terms`·`privacy` 의
   `document.body.textContent` 가 **셋 다 다르다**(Set 크기 3). 셸만 렌더되고 본문이 빠지면
   셋이 같아진다 — 그것이 이 케이스가 잡는 것이다
6. ★**법무 3종의 길이 하한** — 각각 본문 텍스트가 **200자 이상**. 셸만 남고 본문이 사라지는
   회귀를 잡는다(숫자는 하한이지 목표가 아니다)
7. ★**외부 링크가 있으면 `rel` 이 안전하다** — 렌더된 `a[target="_blank"]` 가 있다면
   전부 `rel` 에 `noopener` 를 포함한다. **하나도 없으면 이 케이스는 그냥 통과한다** —
   그것을 명시적으로 주석에 적어라(0건 통과는 판별력이 없다는 뜻이다)
8. ★**`LEGAL_LINKS` 3경로가 실재하는 라우트를 가리킨다** — `lib/legal-links.ts` 를 import 해
   세 값이 `/disclaimer`·`/terms`·`/privacy` 이고, **이 테스트가 렌더한 페이지 집합과 일치**하는지.
   상수만 고치고 페이지를 안 만드는 드리프트를 잡는다
9. ★**`cleanup()` 을 `afterEach` 에 걸어라** — 넷을 연속 렌더하므로 안 걸면 앞 페이지의 DOM 이
   남아 5번 케이스가 거짓 통과한다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/app/__tests__/public-legal-pages.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/app/__tests__/public-legal-pages.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 9
cd apps/web && pnpm exec eslint 'src/app/__tests__/public-legal-pages.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=1 (red) 다
(CONTROL 실측 2026-08-21).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **7번 케이스가 실제로 잰 링크 개수**를 남겨라(0이면 0이라고 적어라).
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/web/src/app/{disclaimer,terms,privacy,not-available}/page.tsx` 와
  `src/components/legal/**` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★★**법무 문구 전문을 테스트에 복사해 오지 마라. 이유:** 개정될 문서라 **항진명제**가 되고
  개정마다 의미와 무관하게 red 가 난다. **구조·링크·길이 하한**만 재라
- ★**`src/lib/__tests__/marketing-canon.test.ts` 를 고치지 마라** — 이미 있고 이 lane 소유가 아니다
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 헬퍼는 이 테스트 파일 안에 둬라
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
