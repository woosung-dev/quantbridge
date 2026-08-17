# 원장 초안 — 레인 α (BL-797)

★CONTROL 이 `docs/backlog.md` 에 옮겨 적을 초안이다. 수치의 정본은 `A-REPORT.md` 이고 여기서는
그것을 참조한다 — 같은 수를 두 문서에 각각 적지 않는다(직전 회차에 9회/15회로 갈린 사고).

---

### BL-797

**Title:** 화면을 바꾼 PR 이 그 변화를 스스로 증명하게 만든다 — before/after 화면 + 번들·요청 델타를 PR 코멘트로
**Category:** 테스트 / 인프라 (FE)
**Priority:** P2
**상태:** 🟡 **PARTIAL** — 로컬 산출 경로(갈래 ⑴) 완료·게이트 배선 완료. **CI 게시(갈래 ⑵)는 미착수**
**Est:** 완료분 M / 잔여 M (CI 배선 + 리눅스 baseline)
**출처:** 2026-08-17 야간 3회차 레인 α

**원인 / 영향:** `apps/web/` 을 바꾼 PR 이 머지될 때 리뷰어가 얻는 것이 **코드 diff 뿐**이었다.
화면이 어떻게 달라졌는지도, 그 대가가 얼마인지도 어디에도 안 남았다. [BL-662~665] 가
`/dashboard` 를 −181.5kB 줄인 수치가 PR 에 없고, [BL-786] 의 static 라우트 16→8 감소는 CONTROL 이
대조 빌드를 두 번 돌려 겨우 찾아냈다 — **그 회차 레인 보고서는 「추가 비용 없음」이라 적고 있었다.**
이 레포는 「측정 없이 판단하지 마라」를 원칙으로 쓰는데 화면 축에는 측정 자체가 없었다.

**처방(완료분):** `pnpm screen-evidence` — `next build` → `next start` → playwright 캡처 →
**before(`origin/main` 의 git blob) ↔ after(브랜치의 커밋된 baseline)** 를 마크다운 표 하나로.
`final-gates.sh` §4b 에 `has_fe` 로 배선했고 레그 실측 25초. 판정·변이 결과는 `A-REPORT.md` §3·§4.

**★이 회차가 실측으로 반증한 것 4건** (전문 = `A-REPORT.md` §5):

- 레인 지시가 준 「전 레포에 `toHaveScreenshot` 1건」이 **테스트에는 0건**이었다. 그 1건은
  「전부 0건」이라 적은 **문서 산문**이고 grep 이 그것을 센 것이다.
- 「`next build` 출력 파싱」이 **성립하지 않는다** — Next 16 Turbopack 출력에 `Size`·`First Load JS`
  컬럼이 없다. 대체 경로인 라우트별 `build-manifest.json` 도 **모든 라우트에서 내용이 동일**하다.
  ⇒ 번들 축을 **브라우저 실측**(전송 바이트)으로 갈아탔다.
- `content-length` 로는 못 잰다 — Next 의 gzip 이 청크 전송이라 그 헤더가 **자산 13/13 전부**에서
  안 붙는다. `request().sizes().responseBodySize` 를 쓴다.
- ★**공개 라우트의 API 요청은 실측 0/0/0 이라 AC 가 지정한 축만으로는 판별력이 0 이었다.**
  계수기를 통째로 떼어내도 `0 → 0 (0)` 으로 초록이다 — 소크 게이트 C4 · `tool-pin-audit` 에 이은
  「볼 것이 없으면 통과」 3번째 재현. **전체 요청 수**를 생존 앵커로 추가해 닫았다.

**★비율 임계값을 쓰면 안 된다** — fullPage 는 약 256만 픽셀인데 글자 한 자 변경은 **31 픽셀**이라
흔히 쓰는 `maxDiffPixelRatio: 0.001`(2,560 픽셀 허용)이 **그것을 통째로 삼킨다**. 절대 개수(`maxDiffPixels: 0`)로
잡았고 근거는 빌드 6회 전부 차이 0 픽셀이라는 실측이다.

**잔여 — 다음 회차 트리거:**

1. **CI 게시(갈래 ⑵)** — 리눅스 baseline 을 굽고 워크플로에 프로덕션 서버 스텝을 넣은 뒤
   `actions/github-script` 로 코멘트. 그때 `e2e-project-wiring.test.ts` 의
   `LOCAL_ONLY["chromium-screen-evidence"]` 를 걷는다. 선례 = `nightly-real-broker.yml:207`.
2. **authed 라우트의 번들·요청 축** — 스크린샷 없이 수치만이면 실데이터 흔들림을 피한다.
   `/dashboard`·`/backtests` 가 [BL-662~665]·[BL-786] 이 실제로 다룬 라우트다.
3. **오프라인 취약** — `next/font/google` 이 빌드 시 네트워크를 타서 13회 중 1회가 그것으로 죽었다.

**★확인하지 못한 것(중요):** 이 게이트가 **레인 β·γ 의 PR 에서 실제로 무엇을 인쇄하는지는 모른다** —
그들의 브랜치는 내 것이 아니다. 보인 것은 **내 브랜치에서 동작한다**는 것까지다.
또한 `origin/main` 에는 아직 baseline 파일이 없어 기본 참조로 돌리면 라우트 3건이 전부
**「신규」**로 나온다. 델타 증명은 `SCREEN_EVIDENCE_BASE_REF` 로 했고, 머지 후 한 회차가 지나면
기본 경로가 자연히 정상 델타를 낸다.

---

## 함께 손대야 할 곳

- `docs/reference/operations/gates-and-traps.md` — 게이트 목록에 「화면 증거 팩」 한 줄.
  실행 조건 `has_fe`, 유예 대상 **아님**, 레그 25초, 실패 시 처방은 `pnpm screen-evidence:update`.
- [BL-789] — `LOCAL_ONLY` 에 4번째 항목이 늘었다. 그 BL 이 「CI 실행 표면」을 다루므로 교차 참조.
