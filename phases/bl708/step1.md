# Step 1 — 감사 코어에 서브리소스 도달 증거를 싣는다 (관측 전용, 판정 변경 0)

[BL-708] 은 `design-canon-calibration.spec.ts` 의 「하드 실패 0」 단정이 **같은 커밋에서
회차마다 다른 파일에서** 깨지는 문제다. 이 step 은 **고치지 않는다.** 무엇이 갈리는지
리포트에 남게 만드는 것까지가 이 step 의 전부다.

## 읽어야 할 파일

- `frontend/e2e/design-canon-audit.ts` — 감사 코어. 특히 `NavProbe`(`:105-118`) ·
  `auditUrl`(`:396-513`) · `hardFailCount`(`:520-528`) · `formatCanonResult`(`:562-597`)
- `frontend/e2e/design-canon-calibration.spec.ts` — 이 코어를 쓰는 대상 spec (**읽기만** 한다)
- `docs/backlog.md` 의 `### BL-708` 섹션 — 문제 정의와 3회 실측
- `docs/reference/design/prototypes/shotgun-2026-07/screen-10-optimizer-detail.html` 의 **1~25줄**

## 이미 실측된 관측 (CONTROL, 2026-08-12) — 인과 판정은 아직 없다

1. 프로토타입 `screen-*.html` 은 16~19줄에서 **원격 서브리소스 4건**을 받는다 —
   `fonts.googleapis.com` (Archivo · IBM Plex Mono, `display=swap`) 과
   `cdn.jsdelivr.net` (Pretendard). 대상 페이지 자체는 `file://` 다.
2. `res.console` 은 `hardFailCount()` 의 5개 항 중 하나다 (`design-canon-audit.ts:520-528`).
   즉 **콘솔 에러 1건이 곧 하드 실패 1건**이다.
3. 전량 22건 1회 실행에서 `screen-10-optimizer-detail.html` 이 red 였고, 그 내역은
   `overflow=0 contrast=0 focus=0 motion=0 canon=31 console=1 tiny=0` 이었다.
   콘솔 줄 원문 = `768px Failed to load resource: the server responded with a status of 404 ()`.
   **어느 리소스인지는 그 줄에 없다** — `page.on("console")` 이 `m.text()` 만 담기 때문이다.
4. ★같은 파일을 **단독으로** 3회(독립 프로세스) 돌리면 **3/3 PASS · console=0** 이다.
   전량 실행(워커 6)에서만 재현됐다. ⇒ **단독 실행으로 재현을 시도하지 마라. 헛초록이 난다.**

★ 위 4건은 관측이다. 「그래서 원인이 무엇인가」는 네가 실측으로 정해라.

## 작업

`frontend/e2e/design-canon-audit.ts` **한 파일만** 고친다.

1. 회차 사이에서 무엇이 갈리는지 **독립 프로세스 3회 이상**을 직접 돌려 관측해라
   (커맨드는 아래 AC 의 것을 그대로 쓴다). 1회 관측은 귀속이 아니다.
2. 감사 결과에 **서브리소스 실패의 도달 증거**를 싣는다. 계약은 이렇다:
   - `NavProbe` 에 폭마다 채워지는 필드 `subresourceFail: number` 를 추가한다 —
     그 폭에서 실패한 서브리소스 요청 건수. **실패가 0건이어도 `0` 으로 항상 채운다.**
   - `formatCanonResult()` 의 `reached:` 줄에 `subresourceFail=[...]` 를 폭마다 출력한다.
     (`examined=` 와 같은 자리·같은 형식. 예: `subresourceFail=["1440px:0","1024px:0", …]`)
   - 콘솔로 집계되는 실패에는 **어느 리소스인지**가 사람에게 보여야 한다.
3. 코드 주석에 **관측한 사실만** 적어라. 확정 안 된 인과는 `[가정]` 으로 표기한다.

## AC (Acceptance Criteria) — 그대로 실행해서 전건 통과해야 한다

```bash
cd frontend

# AC-1 타입/린트
pnpm typecheck            # rc=0
pnpm lint                 # rc=0 (경고는 허용, 에러 0)

# AC-2 도달 증거가 **항상** 나온다 (실패 0건인 화면에서도)
PLAYWRIGHT_BASE_URL=http://localhost:3100 pnpm exec playwright test \
  e2e/design-canon-calibration.spec.ts --project=chromium-design-canon --no-deps \
  --grep "screen-15-login" --reporter=line 2>&1 | tee /tmp/bl708-s1.txt
grep -aq 'subresourceFail='   /tmp/bl708-s1.txt      # rc=0 이어야 한다
! grep -aq 'subresourceFail=\[\]' /tmp/bl708-s1.txt # 빈 배열이면 rc=1 (헛초록 차단)

# AC-3 spec 파일은 한 글자도 안 바뀌었다
cd .. && test -z "$(git diff main -- frontend/e2e/design-canon-calibration.spec.ts)"
```

## 검증 절차

1. AC-2 의 `/tmp/bl708-s1.txt` 를 눈으로 읽고 `reached:` 줄에 4폭 전부 값이 있는지 확인
2. `git diff main --stat -- frontend/e2e/` 가 **`design-canon-audit.ts` 한 줄만** 나오는지 확인
3. `phases/bl708/index.json` 의 step 1 을 `completed` + `summary` 에
   **① 추가한 필드명 ② 3회 관측에서 실제로 갈린 것** 을 한 줄로 적는다

## 금지사항

- `hardFailCount()` 의 합산 항목을 바꾸지 마라. 이유: 이 step 은 관측만 한다. 판정을 같이
  바꾸면 다음 step 에서 「고쳐서 초록인지 세는 걸 그만둬서 초록인지」를 구분할 수 없다.
- `CANON_BASELINE` · `LIGHT_BASELINE` 의 숫자를 바꾸지 마라. 이유: 원인을 모르는 채 표를
  맞추면 검사기가 자기 자신을 정당화한다 (`design-canon-calibration.spec.ts:22-30` 이
  그 금지를 이미 적어 뒀다).
- `design-canon-calibration.spec.ts` 를 수정하지 마라. 이유: spec 계약은 step 3 몫이다.
- 단독 파일 실행 결과로 「재현 안 됨」이라 판정하지 마라. 이유: 위 관측 4번 — 단독은 3/3 초록이다.
- 새 스크립트·새 파일을 만들지 마라. 이유: 반복 실행은 위 AC 의 셸 루프로 충분하다.
