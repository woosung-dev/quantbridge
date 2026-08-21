# Step 0: tick-ruler-and-pnl-tape

## 읽어야 할 파일

- `apps/web/src/components/tape/pnl-tape.tsx` — **대상 ⑴** (75줄. 진짜 계산이 여기 있다)
- `apps/web/src/components/tick-ruler.tsx` — **대상 ⑵** (47줄. 순수 장식 계약)
- `apps/web/src/components/__tests__/` — 이 디렉터리의 테스트 관용구

## 배경

둘 다 **Precision Instrument 시그니처** 컴포넌트이고 **테스트가 0건**이다.
둘의 계약은 정반대라 한 lane 에 묶었다 — 하나는 **계산**이고 하나는 **장식(=계산 없음)**이다.

★**`PnlTape` 는 손익을 그리는 유일한 마이크로 시각화**다. `deltas` 는 **누적이 아니라 구간 델타**이고
(양수=이익), 정규화가 틀리면 **손실 구간이 이익처럼 보인다.** 지금 그것을 재는 것이 없다.

★**`TickRuler` 는 `aria-hidden` 이 계약이다** — 파일 주석이 「순수 장식이라 aria-hidden 고정」이라
적었다. 그것이 풀리면 스크린리더가 **의미 없는 눈금을 읽는다.**

## 작업

**테스트 파일 두 개**를 신설한다. 이 lane 이 소유한 파일은 그 둘뿐이다.

### ⑴ `apps/web/src/components/tape/__tests__/pnl-tape.test.tsx` (케이스 ≥6)

바는 `span` 이고 높이는 인라인 `style.height` 다. `container.querySelectorAll("span")` 로 잡아라.

1. ★**바 개수 = `deltas` 길이** — `[1,2,3]` 이면 span 3개
2. ★★**`maxBars` 는 끝에서 자른다** — 길이 10 배열에 `maxBars={3}` 이면 span 3개이고,
   **남은 것이 마지막 3개**다. `[-9,-9,...,1,2,3]` 처럼 앞뒤 부호를 다르게 줘서
   **앞이 아니라 뒤가 남았음**을 색으로 확인해라(`slice(-maxBars)` 계약)
3. ★★**정규화 — 최대 절대값이 100% 다** — `[1, 2, 4]` 이면 가장 큰 바의 `height` 가 `100%`.
   ★**절대값 기준이다** — `[-4, 1]` 이면 **`-4` 쪽이 100%** 다. 두 케이스를 다 재라
4. ★**최소 높이 6% 보장** — `[100, 0]` 에서 `0` 바의 height 가 **6%**(0% 가 아니다).
   주석이 「0 근처도 가시화」라 적은 계약이다
5. ★★**부호가 색을 정한다** — 양수는 `var(--bullish)` · 음수는 `var(--bearish)`.
   ★**`0` 은 어느 쪽인가** — 코드가 `d >= 0` 이므로 **bullish** 다. 그것을 명시적으로 재라
   (경계값이고, 뒤집히면 손익분기 구간이 손실로 보인다)
6. ★★**빈 배열 fallback** — `deltas={[]}` 이면 **40개 baseline 틱**이 나오고
   컨테이너가 **`aria-hidden="true"`** 다(데이터가 없으니 읽을 것도 없다).
   ★반대로 데이터가 **있으면** `role="img"` 에 `aria-label` 이 붙는다 — **두 방향을 다 재라**
7. ★**`size="micro"` 가 클래스를 바꾼다** — `h-4`/`h-6` 분기

### ⑵ `apps/web/src/components/__tests__/tick-ruler.test.tsx` (케이스 ≥6)

1. ★★**`aria-hidden="true"` 가 항상 붙는다** — 두 orientation 다. **이것이 이 파일의 계약이다**
2. ★**`data-slot="tick-ruler"` 가 있다** — 선택자 계약
3. ★**orientation 분기** — 기본값(인자 없음)과 `"horizontal"` 이 **같은 클래스**(`qb-ruler-x w-full`) ·
   `"vertical"` 은 `qb-ruler-y h-full`. ★**기본값이 horizontal 임을 명시적으로 재라**
4. ★**`className` 이 합쳐진다(덮어쓰지 않는다)** — `className="mt-4"` 를 주면
   `qb-ruler-x` 와 `mt-4` 가 **둘 다** 있다. `cn` 이 병합이지 치환이 아니라는 계약
5. ★**접근 가능한 이름이 없다** — 렌더 결과에 `role` 이 없고 텍스트가 비어 있다(순수 장식)
6. ★**양성 대조** — 컴포넌트가 함수이고 렌더 결과 요소가 **정확히 1개**다

## Acceptance Criteria

```bash
cd apps/web && pnpm test -- --run 'src/components/__tests__/tick-ruler.test.tsx' 'src/components/tape/__tests__/pnl-tape.test.tsx'
cd apps/web && test "$(pnpm exec vitest list 'src/components/__tests__/tick-ruler.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && test "$(pnpm exec vitest list 'src/components/tape/__tests__/pnl-tape.test.tsx' 2>/dev/null | grep -c ' > ')" -ge 6
cd apps/web && pnpm exec eslint 'src/components/__tests__/tick-ruler.test.tsx' 'src/components/tape/__tests__/pnl-tape.test.tsx'
cd apps/web && pnpm exec tsc --noEmit
```

★2·3번 AC 는 **파일별** 양성 대조다. 한 파일에 몰아 쓰면 다른 파일이 비어도 통과하므로 갈라 뒀다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 파일별 케이스 수와 **⑴-5 에서 관측한 `0` 의 색**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `pnl-tape.tsx` · `tick-ruler.tsx` 를 **수정하지 마라.** 결함은 `summary` 한 줄로
- ★**CSS 계산 결과를 재려 하지 마라** — jsdom 은 `qb-ruler-x` 의 gradient 를 계산하지 않는다.
  **인라인 `style` 과 클래스 문자열**만 재라
- ★`apps/web/vitest.config.ts` · `tests/setup.ts` 무변경 (8 lane 동시 실행 중 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — 두 파일이 각자 자기 헬퍼를 갖는다(파일을 셋으로 늘리지 마라)
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
