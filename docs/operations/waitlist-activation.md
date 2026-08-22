# QuantBridge — Waitlist 활성화 런북 (Beta 초대 파이프라인)

> **대상:** `qb-api.woosung.dev`(BE) 의 waitlist 도메인과 `qb.woosung.dev`(FE) 의
> `/waitlist` · `/invite/[token]` · `/(dashboard)/admin/waitlist` 세 표면.
> **정본:** 이 문서 + `apps/api/src/waitlist/` + `apps/api/tests/waitlist/test_activation_rehearsal.py`.
> 배포 절차 자체는 [`backend-deploy.md`](./backend-deploy.md) · [`frontend-deploy.md`](./frontend-deploy.md) 가 정본이고
> 이 문서는 **그 위에 얹는 env 4종과 판정 기준**만 다룬다.
> **첫 도입:** 2026-08-23 `beta-unlock`. 종전에는 `RESEND_API_KEY` 가 레포 전체에서
> `apps/api/.env.example:166` **한 줄**로만 존재했고 `docs/operations/` 에 waitlist 항목이 **0건**이었다.
> 코드·테스트·화면은 완비인데 **「키를 어디 넣고 무엇을 보면 됐다고 하나」가 없었다.**

---

## 0. 이 문서가 무엇이고 무엇이 아닌가

**맞다** — 이미 배포돼 도는 waitlist 코드에 운영 값을 넣어 **초대 파이프라인을 켜는** 절차와,
켜졌는지를 **무엇을 보고 판정하는가**, 실패 시 무엇이 막히고 어떻게 되돌리는가다.

**아니다** — 기능 개발 문서가 아니다. 코드·테스트·화면은 2026-08-16([BL-072])에 이미 완성됐다.
가입을 초대 토큰으로 게이트하는 일([BL-776])도 **이 문서의 범위가 아니다** — 사용자 결정으로
Cloudflare Access 가 그 관문 역할을 유지한다(§4.0).

### 0.1 착수 전 실사 (2026-08-23 실측) — 무엇이 이미 서 있나

| 축                    | 실측                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| BE 코드               | `apps/api/src/waitlist/` **10 모듈** (router·service·repository·models·schemas·token_service·email_service·dependencies·exceptions·`__init__`) |
| BE 테스트             | `apps/api/tests/waitlist/` **8 파일 · 49 passed** (리허설 3건 포함, 2026-08-23)                        |
| FE 화면               | `/waitlist` · `/invite/[token]` · `/(dashboard)/admin/waitlist` — 전부 존재, vitest 커버 있음           |
| 라우터 마운트         | `apps/api/src/main.py:436-438` — `prefix="/api/v1"`                                                     |
| celery 의존           | **0건** (`apps/api/src/tasks/` 에 waitlist 참조 없음) ⇒ **워커 재배포 불필요, API 재기동만 필요**       |
| `docs/operations/`    | waitlist 항목 **0건** ← 이 문서가 메우는 공백                                                          |

★**「waitlist 테스트를 짓자」는 반증된 처방이다**([LESSON-111] 계열). 낱개 홉은 이미 다 재고 있었다.
실제로 없던 것은 **사슬** 하나였고 그것만 지었다 — `test_activation_rehearsal.py`(§4.5).

---

## 1. 환경 변수 4종 — 발급처 · 형식 · 주입 위치

네 값 모두 **BE 전용**이다. FE 는 이 중 아무것도 읽지 않는다(FE 는 `NEXT_PUBLIC_API_URL` 로 BE 를 부를 뿐).

| 변수                    | 발급처                                                          | 형식                                                    | 주입 위치                          | 미설정 시                                            |
| ----------------------- | --------------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| `RESEND_API_KEY`        | https://resend.com/ → API Keys (**도메인 인증 후**)             | 단일 문자열 · 접두 `re_` `[가정]`                        | 서버 `~/quantbridge/apps/api/.env.local` | **부팅은 통과** · 승인 시 502 (§5.2)               |
| `RESEND_FROM_ADDRESS`   | 같은 Resend 계정에서 **인증한 도메인**의 주소                    | RFC 5322 · `QuantBridge <noreply@woosung.dev>`           | 같음                               | 기본값 `…@quantbridge.app` 이 남아 **발송 실패** (§5.3) |
| `WAITLIST_TOKEN_SECRET` | 직접 생성 — `openssl rand -hex 32`                              | hex 64자 (**최소 16자 강제**, `token_service.py:49-52`)  | 같음                               | `APP_ENV=production` 이면 **부팅 거부** (§5.1)         |
| `WAITLIST_ADMIN_EMAILS` | 운영자가 정한다 (Beta 초기 수동 운영)                            | 콤마 구분 소문자 이메일 · `a@x.com,b@y.com`              | 같음                               | 승인·목록 엔드포인트 **전원 403** (§5.4)              |

★**다섯 번째가 있다 — `WAITLIST_INVITE_BASE_URL`.** `.env.example:175` 이 `[기본값 OK]` 라 적고 있어
넷만 세기 쉽지만, `APP_ENV=production` 에서는 이 값이 localhost 면 **부팅이 거부된다**
(`core/config.py:_enforce_production_safety` 의 `localhost_defaults` 블록). 값은
`https://qb.woosung.dev/invite` 이고, 메일 본문 링크가 `{이 값}/{token}` 으로 조립된다
(`waitlist/service.py:119`). **도메인을 바꾸면 여기도 함께 바꿔야 한다.**

### 1.1 왜 이 넷만 검증되지 않는가 — production validator 의 사각

`core/config.py` 의 `_enforce_production_safety` 가 `app_env=production` 에서 **강제하는 것**은
`SECRET_KEY` · `WAITLIST_TOKEN_SECRET` · `PROMETHEUS_BEARER_TOKEN` · 그리고 `FRONTEND_URL` ·
`WAITLIST_INVITE_BASE_URL` · `BETTER_AUTH_URL` 의 localhost 잔존뿐이다.

⇒ ★**`RESEND_API_KEY` 와 `WAITLIST_ADMIN_EMAILS` 는 비어 있어도 API 가 정상 부팅한다.**
**부팅 성공은 활성화의 증거가 아니다.** 그래서 §4 의 판정 기준이 필요하다.

---

## 2. 주입 절차 (서버)

`backend-deploy.md` §3.2 가 정한 자리와 **같은 파일**이다 — 새 파일을 만들지 마라.

```bash
# 서버에서. 값은 셸 히스토리에 남지 않도록 편집기로 넣는다 (argv 로 넘기지 마라).
ssh truewords-oracle
cd ~/quantbridge
cp apps/api/.env.local apps/api/.env.local.bak.$(date -u +%Y%m%dT%H%M%SZ)   # 되돌릴 자리 (§6)
vi apps/api/.env.local
```

넣을 네 줄 (기존 줄이 있으면 **덧붙이지 말고 교체**한다 — 중복 키는 뒤가 이긴다):

```
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_ADDRESS=QuantBridge <noreply@woosung.dev>
WAITLIST_TOKEN_SECRET=<openssl rand -hex 32 의 출력>
WAITLIST_ADMIN_EMAILS=<운영자 이메일>
```

반영:

```bash
# waitlist 는 celery 를 안 쓴다 (§0.1) — 소크 워커는 건드리지 않는다.
# ★따라서 이 반영은 소크 창을 끊지 않는다. `pin`/`down` 은 부르지 마라.
systemctl --user restart quantbridge-api.service
sleep 8
curl -s https://qb-api.woosung.dev/health      # {"status":"ok","env":"production"}
```

★**`.env` 의 값에 인라인 주석을 붙이지 마라** — `KEY=value  # 주석` 을 그대로 읽어
401 이 아니라 **500** 이 난다([BL-625] 전례). `RESEND_FROM_ADDRESS` 의 `<>` 는 값의 일부이므로
따옴표 없이 그대로 둔다(pydantic-settings 가 `=` 뒤 전체를 값으로 읽는다).

---

## 3. 되짚어 읽는 법 — 값이 실제로 도착했나

`.env.local` 은 **선언**이고 실행 중 프로세스가 **실측**이다(`backend-deploy.md` §3.2 와 같은 원칙).

```bash
# 서버에서. 값 자체를 찍지 않고 **설정 여부만** 본다.
ssh truewords-oracle 'bash -lc "cd ~/quantbridge/apps/api && \
  grep -c \"^RESEND_API_KEY=.\\+\" .env.local; \
  grep -c \"^WAITLIST_ADMIN_EMAILS=.\\+\" .env.local"'
# 기대: 1 / 1. 0 이면 비어 있거나 줄이 없다.
```

★위는 **파일**을 본 것이다. 프로세스가 그 값을 쥐었는지는 §4 의 ②·③ 이 답한다.

---

## 4. 판정 기준 — 무엇을 보면 「활성화됐다」인가

네 단계 각각에 **관측점**이 하나씩 있다. 넷을 다 통과해야 활성화다.
어느 하나라도 못 보면 **「됐다」고 적지 마라** — 부팅 성공은 셋 중 아무것도 증명하지 않는다(§1.1).

### 4.0 ★단계 0 — Cloudflare Access (env 로는 못 여는 관문)

**2026-08-23 실측** — `qb.woosung.dev` 의 네 경로가 **전부** Access 로그인으로 302 된다:

| 경로               | 응답                                                    |
| ------------------ | ------------------------------------------------------- |
| `/`                | 302 → `woosung.cloudflareaccess.com/cdn-cgi/access/login` |
| `/waitlist`        | 302 → 같음                                              |
| `/invite/<token>`  | 302 → 같음                                              |
| `/sign-up`         | 302 → 같음                                              |

⇒ ★★★**초대 메일의 링크는, 받는 사람의 이메일이 Access 정책에 들어가기 전까지 열리지 않는다.**
`/waitlist` 신청 폼조차 **브라우저로는** 외부인에게 닿지 않는다. 이것은 결함이 아니라
사용자 결정의 결과다 — Access 를 걷으면 [BL-776](개방 가입)이 즉시 발현하므로 유지한다.
[BL-776] 의 **권장 접근 ⑷** 가 이미 이 운영 형태를 적어 뒀다: 「Beta 사용자 이메일을 Access
정책에 추가한다. 수십 명까지는 이쪽이 더 안전하다(문이 둘로 유지된다)」.

**⇒ 승인 절차에 수동 단계가 하나 더 있다.** `POST …/approve` 로 메일을 보내기 **전에**
Zero Trust → Access → Applications → `qb.woosung.dev` 정책에 그 이메일을 추가한다.
빠뜨리면 초대받은 사람이 링크를 눌러도 Access 로그인 화면만 본다.

★**BE 는 Access 밖이다**(설계 — `frontend-deploy.md:50`). 그래서 아래 ②③④ 의 API 관측점은
Access 없이도 그대로 잰다.

### 4.1 단계 ① 대기자 등록 — `POST /api/v1/waitlist`

- **관측점:** 202 + `{"id": <uuid>, "status": "pending"}`
- **DB:** `waitlist_applications` 에 행 1건, `status='pending'`, `invite_token IS NULL`
- **레이트리밋:** `5/hour` (`router.py:34`). 6번째는 429다 — 그것도 정상 동작의 증거다.
- ★이 단계는 **키가 하나도 없어도 통과한다.** 여기까지만 보고 「됐다」고 하지 마라.

### 4.2 단계 ② 관리자 승인 자격 — `GET /api/v1/admin/waitlist`

- **관측점:** 200 + `items` 배열. **401 이면 인증**, **403 이면 `WAITLIST_ADMIN_EMAILS`** 문제다.
- ★**이것이 `WAITLIST_ADMIN_EMAILS` 가 프로세스에 도착했는지의 유일한 원격 관측점이다.**
  로그인한 운영자 계정으로 200 이 나오면 그 이메일이 화이트리스트에 있다는 뜻이다
  (`dependencies.py:65-68` — 소문자 정규화 후 멤버십 비교).

```bash
# 인증 없이 치면 401 이어야 한다 (2026-08-23 실측 401 — 인증 층이 살아 있다).
curl -s -o /dev/null -w "%{http_code}\n" https://qb-api.woosung.dev/api/v1/admin/waitlist
```

### 4.3 단계 ③ 메일 발송 — `POST /api/v1/admin/waitlist/{id}/approve`

- **관측점(성공):** 200 + `{"status":"invited","invite_sent_at":"<ISO8601>"}`
- **관측점(실패):** 502 + `detail.code == "waitlist_email_send_failed"` ⇒ Resend 축(§5.2/5.3)
- **외부 증거:** Resend 대시보드 → Emails 에 발송 1건. **`invite_sent_at` 이 채워졌다는 것은
  Resend 가 2xx 를 줬다는 뜻**이다(§6 의 순서 때문에 그 역이 성립한다).
- **DB:** 그 행이 `status='invited'` · `invite_token` 채워짐 · `invited_at`·`invite_sent_at` 동일 시각

### 4.4 단계 ④ 초대 검증 — `GET /api/v1/waitlist/invite/{token}`

- **관측점:** 200 + `{"email": "...", "status": "invited"}`
- **음성 대조(지금 바로 칠 수 있다):** 아무 문자열이나 넣으면 400 + `waitlist_invite_token_invalid`

```bash
# 2026-08-23 실측 — 400 + {"detail":{"code":"waitlist_invite_token_invalid",...}}
curl -s https://qb-api.woosung.dev/api/v1/waitlist/invite/aaaaaaaaaaaaaaaa
```

★**이 400 이 「waitlist 라우터가 실제로 배포돼 살아 있다」의 증거다.** 404 가 나오면 라우터가
안 올라간 것이고, 302 가 나오면 API 호스트에 Access 가 잘못 걸린 것이다(`frontend-deploy.md:50`).

- **화면:** `https://qb.woosung.dev/invite/{token}` 이 **「QuantBridge Beta 에 초대되었습니다」**
  를 렌더한다. 「초대 링크를 확인할 수 없습니다」면 400/404 갈래이고, 「지금은 확인할 수
  없습니다」면 BE 에 못 닿은 것이다(`features/waitlist/invite-view.ts`).
  ★단계 0 을 안 밟았으면 여기서 **Access 로그인 화면**이 뜬다 — 그건 위 세 갈래 중 어느 것도 아니다.

### 4.5 ★같은 판정을 로컬에서 1회 통과시키는 법 (리허설)

위 ①~④ 를 **한 사슬로** 재는 실행 가능한 증거가 있다. Resend 의 HTTP 표면만 가짜이고
라우터·서비스·리포지터리·토큰·DB·`require_admin` 화이트리스트는 전부 실경로다.

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/waitlist -q
# 기대: 49 passed (2026-08-23 기준선 — 테스트가 늘면 이 숫자를 갱신해라)
```

`tests/waitlist/test_activation_rehearsal.py` 가 하는 일:

1. `POST /api/v1/waitlist` → 202, 행이 `pending`
2. `GET /api/v1/admin/waitlist` → 화이트리스트를 **실경로로** 통과 (override 하지 않는다)
3. `POST …/approve` → 200 · Resend 요청 1건 · `Authorization: Bearer <키>` · `from` 이 설정값
4. ★**메일 본문에서** 토큰을 꺼내 `GET /api/v1/waitlist/invite/{token}` → 200 `invited`
   (DB 에서 꺼내면 「메일에 실린 링크가 열리는가」를 안 재는 것이 된다)

**판별력 실측 (2026-08-23, 변이 3종 · 전건 앵커 1건 확인 후 주입 · sha256 복원 대조):**

| 변이                                          | 기대   | 실측                                            |
| --------------------------------------------- | ------ | ----------------------------------------------- |
| `admin_approve` 순서 반전 (DB 전환 → 메일)    | red    | ✓ `test_activation_fail_closed_resend_rejects_key` |
| `require_admin` 빈 화이트리스트 = 전원 허용   | red    | ✓ `test_activation_fail_closed_admin_emails_unset` |
| `invite_url` 에 토큰 미첨부                   | red    | ✓ `test_activation_rehearsal_signup_to_invite_verify` |

---

## 5. fail-closed 지점 — 무엇이 막히고 어디서 드러나나

### 5.1 `WAITLIST_TOKEN_SECRET` 미설정 → **부팅 거부** (production 한정)

`core/config.py` 의 `_enforce_production_safety` 가 빈 값을 placeholder 로 보고 raise 한다.
dev/test 에서는 `dependencies.py:27-30` 이 placeholder 를 주입하므로 **부팅된다** — 그 분기는
production 에서 도달 불가다(validator 가 먼저 죽인다).

★**2026-08-23 추론 (확인된 사실 2건에서):** `https://qb-api.woosung.dev/health` 가
`{"status":"ok","env":"production"}` 를 낸다 ⇒ validator 를 통과했다 ⇒ **서버의
`WAITLIST_TOKEN_SECRET` 과 `WAITLIST_INVITE_BASE_URL` 은 이미 채워져 있다.**
남은 미지수는 `RESEND_API_KEY` · `RESEND_FROM_ADDRESS` · `WAITLIST_ADMIN_EMAILS` 셋뿐이다.

⚠️**이 비밀을 바꾸면 이미 발송된 초대 토큰이 전부 무효가 된다** — 서명이 안 맞아 400 이다.
회전하려면 미사용 `invited` 행이 없을 때 하거나, 회전 후 그 행들을 다시 승인해야 한다.

### 5.2 `RESEND_API_KEY` 미설정 → **승인 시 502** (부팅은 통과)

`dependencies.py:40` 이 `api_key or "dev-empty-key"` 로 감싸므로 **부팅은 조용히 지나간다.**
결함은 승인 요청 시점에 드러난다 — Resend 가 401 을 주고, 401 은 재시도 대상이 아니므로
(`email_service.py:33-34` — 5xx·429 만 재시도) **시도 1회 후** `EmailSendError`(502)다.

### 5.3 `RESEND_FROM_ADDRESS` 기본값 잔존 → **승인 시 502**

기본값은 `QuantBridge Waitlist <waitlist@quantbridge.app>` 인데 이 배포의 도메인은
`woosung.dev` 다. Resend 는 **인증된 도메인에서만** 보내므로 그대로 두면 거부된다([BL-072]).
`tests/waitlist/test_email_from_address_wiring.py` 가 「기본값이 곧 배포 준비 완료가 아니다」를
음성 대조로 고정해 두고 있다.

### 5.4 `WAITLIST_ADMIN_EMAILS` 미설정 → **승인·목록 403** (전원 거부)

`dependencies.py:67` — `if not allowed or not user_email or user_email not in allowed:` .
★**빈 화이트리스트를 「전원 허용」이 아니라 「전원 거부」로 읽는다.** 이 방향이 뒤집히면
admin 엔드포인트가 로그인한 아무에게나 열린다. 리허설의 변이 2가 그 방향을 고정한다(§4.5).

응답: 403 + `detail.code == "waitlist_admin_only"`.

### 5.5 요약 — 어느 증상이 어느 키를 가리키나

| 증상                                    | 원인                                     | 고칠 곳            |
| --------------------------------------- | ------------------------------------------ | ------------------ |
| API 가 부팅 못 함 (`env` 확인 불가)     | `WAITLIST_TOKEN_SECRET` 빈 값              | §5.1               |
| 승인이 403 `waitlist_admin_only`        | `WAITLIST_ADMIN_EMAILS` 빈 값 또는 불일치  | §5.4               |
| 승인이 502 `waitlist_email_send_failed` | `RESEND_API_KEY` 또는 `RESEND_FROM_ADDRESS` | §5.2 · §5.3       |
| 메일은 왔는데 링크가 Access 로그인      | Access 정책에 그 이메일이 없다             | §4.0               |
| 메일 링크가 404 (FE 「확인할 수 없습니다」) | `WAITLIST_INVITE_BASE_URL` 이 다른 도메인  | §1 다섯 번째 항목  |

---

## 6. ★승인 순서(메일 → DB) — 의도인가 결함인가

`waitlist/service.py:112-132` 의 `admin_approve` 는 이 순서다:

```
find_by_id → token issue → send_invite_email → mark_invited → commit
```

발송이 실패하면 `EmailSendError`(502)가 전파되고 **DB 전이가 일어나지 않는다.**
주석(`service.py:120`)이 그렇게 적혀 있고, 리허설이 그 방향을 단언한다.

**판정: 의도이고, 두 순서 중 옳은 쪽이다.** 근거:

- **뒤집으면(DB → 메일)** 발송 실패가 **「받은 사람이 없는 `invited`」** 를 만든다. 관리자
  목록에서는 초대된 것으로 보이므로 **재시도 신호가 사라지고**, 신청자는 영구히 멈춘다.
- **지금 순서**는 실패가 행을 `pending` 에 남긴다 ⇒ 운영자가 `?status=pending` 목록에서
  그 행을 **다시 본다**. 복구가 관측 가능하고, 재승인 한 번이면 끝난다.

**남는 창(작지만 실재한다):** 발송은 성공했는데 `mark_invited`/`commit` 이 실패하면,
신청자는 **서명이 유효한 토큰**을 메일로 받았지만 DB 에는 없다. 이때
`verify_invite_token` 은 서명 검증을 통과한 뒤 `find_by_invite_token` 에서 `None` 을 만나
404 를 내고(`service.py:86-89`), 화면은 「초대 링크를 확인할 수 없습니다」다.
⇒ **증상은 「메일은 왔는데 링크가 안 열린다」**이고, 처방은 **그 행을 다시 승인**하는 것이다
(새 토큰이 발급되고 새 메일이 나간다). 이 창은 한 번의 flush+commit 폭이라, 뒤집었을 때의
창(HTTP 왕복 + 최대 3회 재시도)보다 **구조적으로 작다.**

⚠️**재승인은 멱등이 아니다.** `mark_invited` 가 `invite_token` 을 덮어쓰므로(`repository.py:80`)
**이전 토큰은 그 순간 무효**가 된다(서명은 유효하나 조회가 0건 → 404). 같은 사람에게 두 번
승인했다면 **마지막 메일의 링크만** 열린다고 안내해라.

---

## 7. 되돌리는 절차

### 7.1 env 롤백 (파이프라인을 다시 끈다)

```bash
ssh truewords-oracle 'bash -lc "cd ~/quantbridge/apps/api && \
  cp .env.local.bak.<타임스탬프> .env.local"'
ssh truewords-oracle 'systemctl --user restart quantbridge-api.service'
sleep 8; curl -s https://qb-api.woosung.dev/health
```

★**`WAITLIST_TOKEN_SECRET` 을 지운 채 되돌리지 마라** — production validator 가 부팅을 거부해
API 가 통째로 죽는다(§5.1). 「끄고 싶다」면 지울 것은 **`WAITLIST_ADMIN_EMAILS`** 다 —
승인 경로만 403 으로 닫히고 나머지는 그대로 산다. 그것이 가장 싼 킬 스위치다.

### 7.2 잘못 승인한 행 되돌리기

**DB 행 수정은 사전 승인 대상이다**(`docs/status.md` ⓹). 승인 없이 실행하지 마라.
되돌릴 것이 있다면 그 행의 `status`·`invite_token`·`invited_at`·`invite_sent_at` 넷을 함께
되돌려야 한다 — 토큰만 지우면 `invited` 인데 검증이 404 인 상태가 된다.
**이미 나간 메일은 회수할 수 없다.** 토큰을 지우면 그 링크는 404 로 죽는다(그것이 사실상의 취소다).

### 7.3 배포 롤백

waitlist 는 celery 를 안 쓰므로(§0.1) 소크 스택과 무관하다. 코드 롤백이 필요하면
`backend-deploy.md` §3.4 ⑴ 을 그대로 따르고, **이 문서의 env 는 롤백 대상이 아니다**
(`.env.local` 은 `git archive` 로 고정되는 `apps/api/src` 밖에 있다).

---

## 8. 함정

★**부팅 성공을 활성화의 증거로 읽지 마라.** 네 값 중 둘(`RESEND_API_KEY`·`WAITLIST_ADMIN_EMAILS`)은
validator 가 **안 본다**(§1.1). 이 레포는 「있다고 여겨진 것이 그 경로를 안 지났다」를 반복해 겪었다.

★**단계 ①만 보고 끝내지 마라.** `POST /waitlist` 는 키가 하나도 없어도 202 다. 랜딩에서
신청이 들어온다는 사실은 초대가 나간다는 증거가 **아니다.**

★**Access 는 env 로 못 연다**(§4.0). 네 키를 다 넣어도 초대받은 사람은 링크를 못 연다 —
Cloudflare 대시보드에서 그 이메일을 정책에 넣는 **수동 단계**가 파이프라인의 일부다.

★**`.env` 값에 인라인 주석 금지** — 401 이 아니라 500 이 난다([BL-625]).

★**비밀 회전은 미사용 초대를 죽인다**(§5.1). 회전 전에 `status='invited'` 이면서 아직
가입 안 한 행이 있는지 먼저 봐라.

---

## 9. [확인 필요]

1. 서버 `.env.local` 의 `RESEND_API_KEY`·`RESEND_FROM_ADDRESS`·`WAITLIST_ADMIN_EMAILS` 실제 설정 여부
   — §3 의 명령으로 CONTROL 이 잰다. `/health` 로는 안 보인다(§1.1).
2. Resend 계정의 **도메인 인증 상태** — `woosung.dev` 가 인증돼 있는지. 미인증이면
   `RESEND_FROM_ADDRESS` 를 무엇으로 넣어도 발송이 실패한다.
3. Resend API key 의 접두 `re_` 는 `[가정]` 이다 — 레포에 근거가 없다. 발급 화면의 실제 값을 따른다.
4. Cloudflare Access 정책의 현재 허용 이메일 목록 — 대시보드에서만 읽을 수 있다.
   §4.0 의 302 는 **정책이 걸려 있다**는 것만 증명하고 **누가 들어 있는지**는 말하지 않는다.

---

## 10. 관련 문서

- [`backend-deploy.md`](./backend-deploy.md) — `.env.local` 의 자리(§3.2) · 배포·롤백 절차
- [`frontend-deploy.md`](./frontend-deploy.md) — Access 설정(§3.1) · 호스트 2개 구조(§2 ⑶)
- [`better-auth-setup.md`](./better-auth-setup.md) — 로그인 축([ADR-034]). ★이 문서는 그것을 건드리지 않는다
- `docs/backlog-deferred.md#bl-776` — 가입이 초대로 게이트되지 않는 이유와 **권장 접근 ⑷**(Access 정책 운용)
- `apps/api/tests/waitlist/test_activation_rehearsal.py` — §4 판정 기준의 실행 가능한 증거
