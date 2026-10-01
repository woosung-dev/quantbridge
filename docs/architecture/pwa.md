# QuantBridge — PWA (설치 · 오프라인 안내 · 웹 푸시)

> **목적:** PWA 도입의 구현 계약. 제너레이터·이밸류에이터가 이 문서 하나를 기준으로 구현·판정한다.
> **결정 근거:** [ADR-044](../adr/044-pwa-web-push.md) · **범위:** [`PRD.md`](../PRD.md) §3.
> **상태:** 2026-10-02 스펙 고정(구현 전). 구현 후 「현행」으로 바뀐다.

---

## 0. 한 줄 요약

브라우저에 **설치**할 수 있고, 연결이 끊기면 **오프라인 안내 화면**을 보여 주고, 백테스트·주문 체결·Kill Switch 를
**웹 푸시**로 알린다. ★**데이터는 캐시하지 않는다** — 오프라인에서 시세·잔고·결과를 보여 주는 일은 구조적으로 없다
(낡은 금융 숫자를 최신처럼 보이는 것이 이 제품이 가장 피해야 할 결함이다 — PRD §1).

## 1. 경계 — 무엇을 안 하나

| 안 함 | 이유 |
| --- | --- |
| `/api/*` · RSC · 인증 응답 캐시 | 낡은 금융 숫자 표시 위험 · 로그아웃 후 잔존 |
| PWA 라이브러리(Serwist·next-pwa) | 기본 런타임 캐시가 위 금지를 어긴다. SW 는 60줄 안팎이라 직접 쓴다 |
| `app/manifest.ts` | Next 가 `crossOrigin` 없는 `<link rel="manifest">` 를 **자동 주입**한다(§2.2 와 중복) |
| 이벤트 종류별 알림 설정 | v1 은 「이 기기에서 받기」 토글 하나 |
| 스트레스 테스트·옵티마이저 완료 푸시 · publish 없이 끝나는 주문 거부 | 후속 BL(§6) |

## 2. FE — `apps/web`

새 코드는 `src/features/pwa/` 에 둔다([ADR-035]). 규칙 본문 = `apps/web/AGENTS.md`.

### 2.1 manifest — 정적 파일

- 경로: `public/manifest.webmanifest` (루트 — `proxy.ts` matcher 가 루트의 `.webmanifest` 만 통과시킨다)
- 필드: `name: "QuantBridge"` · `short_name: "QuantBridge"` · `description` · `id: "/"` · `start_url: "/dashboard"` · `scope: "/"` ·
  `display: "standalone"` · `background_color` = `theme_color` = `BRAND_PALETTE.dark.bg`(`src/lib/brand-palette.ts` 의 값, 기본 테마가 dark) · `lang: "ko"`
- 아이콘(전부 **루트 경로**, 하위 폴더 금지 — proxy 가 `/sign-in` 으로 보낸다):
  `/icon-192.png`(192, `any`) · `/icon-512.png`(512, `any`) · `/icon-maskable-512.png`(512, `maskable`, 안전 영역 80%) · `src/app/apple-icon.png`(180)
  — 원본 = `src/app/icon.svg`
- 드리프트 방지: vitest 1건 — manifest 의 두 색 == `BRAND_PALETTE.dark.bg`

### 2.2 manifest 링크

루트 `src/app/layout.tsx` 가 `<link rel="manifest" href="/manifest.webmanifest" crossOrigin="use-credentials" />` 를 직접 렌더한다.
**이유:** 프로덕션 FE 는 Cloudflare Access 뒤다. manifest 는 기본적으로 쿠키 없이 요청돼 Access 로그인으로 302 → 설치 불가.
Next 는 이 속성을 Vercel preview 에서만 붙인다. **문서 안 `<link rel="manifest">` 는 정확히 1개.**

### 2.3 서비스 워커 — `public/sw.js` (직접 작성)

| 이벤트 | 동작 |
| --- | --- |
| `install` | `CACHE = "qb-shell-v1"` 에 `/offline` + §2.1 아이콘만 precache → `skipWaiting()` |
| `activate` | `CACHE` 외 `qb-shell-*` 삭제 → `clients.claim()` |
| `fetch` | **`request.mode === "navigate"` 만** 처리: network-first → 실패 시 캐시의 `/offline`. 그 외 요청(`/api/*`·RSC·정적 자산)은 `respondWith` 하지 않는다 |
| `push` | `event.data.json()` = §4.3 페이로드 → `showNotification(title, {body, tag, icon: "/icon-192.png", badge: "/icon-192.png", data: {url}})`. 파싱 실패 시 기본 문구 |
| `notificationclick` | `url` 이 **같은 origin** 일 때만 사용(아니면 `/dashboard`) → 그 url 의 열린 창 focus, 없으면 `clients.openWindow(url)` |

- SW 를 바꾸면 `CACHE` 버전을 올린다.

### 2.4 `/offline` 페이지

- `src/app/offline/page.tsx` — 정적(서버 fetch 0 · 인증 0). 문구: 제목 **「오프라인 상태입니다」** + 「연결되면 다시 시도하세요」 + 새로고침 링크.
  ★새로고침은 **JS 0** 으로 동작해야 한다 — SW 가 돌려준 캐시 HTML 에는 하이드레이션이 안 붙어 클릭 핸들러가 죽는다. 현재 URL(쿼리 포함)을 그대로 다시 연다
- `src/proxy.ts` `isPublicRoute` 에 `/offline` 추가 + `src/__tests__/proxy-gate.test.ts` 1건

### 2.5 `next.config.ts` 헤더

`/sw.js` 에: `Cache-Control: no-cache, no-store, must-revalidate` · `Content-Type: application/javascript; charset=utf-8`.
기존 `"/(.*)"` 5종(`next.config.ts:57-64`)은 그대로.

### 2.6 클라이언트 구성 요소

| 구성 요소 | 자리 | 계약 |
| --- | --- | --- |
| `PwaBootstrap` | 루트 `layout.tsx` 1개 | 모듈 레벨 가드로 **앱 로드당 1회** `navigator.serviceWorker.register("/sw.js", {scope: "/"})`. `load` 이후(첫 렌더를 막지 않음). 미지원 브라우저는 아무것도 안 함. dev 포함 |
| 설치 버튼 | `DashboardHeader` 의 `actions` 슬롯(`dashboard-shell.tsx` 가 주입) — 화면상 `ThemeToggle` 바로 앞. ★`components/` 는 `features/` 를 import 못 한다(biome) | `beforeinstallprompt` 를 **모듈 단일 구독** + `useSyncExternalStore`. 이벤트 보유 ∧ `display-mode: standalone` 아님일 때만 렌더. 클릭 → `prompt()` → 결과와 무관하게 이벤트 폐기. `appinstalled` 시 숨김 |
| 오프라인 배너 | `DashboardShell` | `online`/`offline` **단일 구독**. 문구 「오프라인 상태입니다. 화면의 숫자가 최신이 아닐 수 있습니다」(em-dash 는 `design-canon-source` 래칫이 막는다). 기존 `src/features/realtime/ws-client.ts:69` 리스너는 건드리지 않는다 |
| 푸시 벨 | 같은 `actions` 슬롯, 설치 버튼 옆 | 아래 §2.7 |

### 2.7 푸시 벨

- 렌더 조건: `serviceWorker` ∧ `PushManager` ∧ `Notification` 지원 ∧ `GET /api/v1/push/config` 의 `enabled === true`. 아니면 **렌더하지 않는다**
- 열면 팝오버: 스위치 「이 기기에서 알림 받기」 + 버튼 「테스트 알림 보내기」(구독 중일 때만 활성)
- 켜기 — **클릭 핸들러 안에서만**: `Notification.requestPermission()` → `granted` 일 때 `registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: <config.public_key>})`
  → `POST /api/v1/push/subscriptions` (`subscription.toJSON()` + `user_agent`)
- 끄기 — `subscription.unsubscribe()` + `DELETE /api/v1/push/subscriptions` `{endpoint}`
- 권한 `denied` → 스위치 비활성 + 「브라우저 설정에서 알림이 차단되어 있습니다」
- **로그아웃 · 계정 삭제 시** — `src/components/layout/account-button.tsx` 의 `signOut()`·`deleteAccount()` **앞에서** 이 기기 구독 해제 + `DELETE`.
  연결은 등록식이다 — `PushBell` 이 `src/lib/before-sign-out.ts` 에 정리 함수를 등록하고 `AccountButton` 이 그것을 부른다(같은 import 경계 이유).
  계정 삭제가 서버에서 거부돼도 기기 구독은 이미 풀린 채다(다시 켜면 된다 — 남는 것보다 안전).
  best-effort, 최대 2초 — 실패해도 로그아웃은 진행(공용 기기에서 이전 사용자의 알림을 받지 않게)
- **소유자 맞추기(로그아웃을 안 거친 계정 전환)** — 세션 만료로 `/sign-in` 에 튕긴 뒤 다른 계정이 들어오면 위 정리가 안 돈다.
  그래서 벨이 마운트될 때(사용자 ID 가 바뀔 때마다) 권한 `granted` ∧ 기기 구독 있음이면 그 구독을 `POST` 로 **다시 등록**한다 —
  서버 upsert 가 같은 endpoint 를 현재 사용자로 재할당한다(§3.2). 권한은 묻지 않는다. 실패는 경고 로그만(G6 codex 지적, 2026-10-02)
- API 응답은 feature 내 Zod 스키마로 파싱 + `contracts/openapi/openapi.json` 계약 테스트(본보기 = `src/features/trading/__tests__/register-account-openapi-contract.test.ts`)

## 3. BE — `apps/api`

새 도메인 `src/notifications/` — 7파일 표준(router · service · repository · schemas · models · dependencies · exceptions), 본보기 = `src/waitlist/`.
규칙 본문 = `apps/api/AGENTS.md`.

### 3.1 모델 `push_subscriptions`

| 컬럼 | 타입 | 비고 |
| --- | --- | --- |
| `id` | UUID PK | |
| `user_id` | UUID FK `users.id` `ON DELETE CASCADE` | 인덱스 |
| `endpoint` | TEXT **UNIQUE** | 푸시 서비스 URL |
| `p256dh` · `auth` | TEXT | 구독 키 |
| `user_agent` | TEXT NULL | |
| `created_at` | timestamptz | |
| `last_success_at` | timestamptz NULL | 발송 성공 시 갱신 |

- 같은 `endpoint` 가 **다른 사용자**로 다시 오면 그 행을 **현재 사용자로 재할당**한다(공용 기기).
- Alembic: `alembic/versions/YYYYMMDD_0001_push_subscriptions.py`, `down_revision = "20260817_0002"`.
- 모델 등록 2곳: `alembic/env.py` 와 `tests/conftest.py` 의 모델 import(`tests/test_metadata_table_coverage.py` 가 검사).

### 3.2 엔드포인트 — `APIRouter(prefix="/push", tags=["push"])`, `src/main.py` 에 `/api/v1` 로 등록, 전부 `get_current_user` 필수

| 메서드 · 경로 | 요청 | 응답 |
| --- | --- | --- |
| `GET /api/v1/push/config` | — | `200 {enabled: bool, public_key: str \| null}` — VAPID 3종 중 하나라도 없으면 `enabled: false, public_key: null` |
| `POST /api/v1/push/subscriptions` | `{endpoint, keys: {p256dh, auth}, user_agent?}` — `endpoint` 는 **푸시 서비스 호스트 허용 목록만**(`fcm.googleapis.com` · `updates.push.services.mozilla.com` · `*.push.apple.com` · `*.notify.windows.com`, 그 외 `422`). API 는 Access 밖 + 개방 가입이라 임의 https 호스트를 받으면 내부 SSRF·`/push/test` 응답 오라클이 된다 | `201` 생성 / `200` 기존(upsert) — `{id, endpoint, created_at}` |
| `DELETE /api/v1/push/subscriptions` | `{endpoint}` | `204` · **남의 endpoint 또는 없는 endpoint = 404**(존재 여부를 흘리지 않는다) |
| `POST /api/v1/push/test` | — | `200 {sent: int, removed: int}` — 내 구독 전부에 §4.3 테스트 페이로드. 비활성이면 `409` |

- 기존 slowapi 패턴을 쓰면 **`response: Response` 파라미터 필수**(빠뜨리면 성공 전건 500 — 2회 재발).
- 엔드포인트를 추가했으니 `scripts/export_openapi.py` 로 `contracts/openapi/openapi.json` 재생성(CI 가 `--check`).

### 3.3 설정 — `src/core/config.py`

```text
vapid_public_key: str | None        # base64url (applicationServerKey)
vapid_private_key: SecretStr | None # base64url
vapid_subject: str | None           # "mailto:..." 
```

- 빈 문자열 → `None` validator(기존 `slack_webhook_url` 패턴).
- `apps/api/.env.example` 에 **주석이 아닌** `VAPID_PUBLIC_KEY=` · `VAPID_PRIVATE_KEY=` · `VAPID_SUBJECT=` (`tests/common/test_env_example_contract.py` 가 양방향 검사).
- **키가 없으면 기능이 꺼진다** — 서버에 키를 넣기 전까지 푸시는 자동 비활성(§2.7 벨 미렌더).

### 3.4 발송

- 의존성: `pywebpush`(uv).
- Celery 태스크 `notifications.send_push(user_id: str, payload: dict)` — `src/tasks/notifications.py`, `tasks/celery_app.py` 의 `include` + 라우트에 등록.
- 사용자 구독 전부에 발송. `webpush` 는 동기라 `asyncio.to_thread` 로 감싼다. 타임아웃 10초. **TTL 24시간**(pywebpush 기본 0 이면 잠든 기기가 못 받는다).
- VAPID 가 없으면 **enqueue 자체를 안 한다**(`notifications/dispatcher.py` `enqueue_push`) — 그래서 `tests/conftest.py` 가 `VAPID_*` 를 비운다.
- 응답 **404 · 410 → 그 구독 삭제** · 성공 → `last_success_at` 갱신 · 그 외 실패 → 로그만(재시도 없음).
- 발신 함수는 주입 가능하게(테스트가 실제 네트워크를 안 탄다).

### 3.5 트리거 — enqueue 만, **본 경로를 절대 깨뜨리지 않는다**(try/except + 로그)

| 이벤트 | 훅 자리 | 페이로드 |
| --- | --- | --- |
| 주문 체결 · 거부 | `src/trading/realtime_publisher.py` `publish_realtime(user_id, event_type, payload)` — `event_type == "order_update"` ∧ `state` ∈ {filled, rejected}(키 이름은 `realtime/schemas.py` `OrderUpdatePayload`) | `주문 체결` / `주문 거부` · 본문 = 심볼 + 방향 · `url="/trading"` · `tag="order:{order_id}"` |
| Kill Switch 발동 | 같은 함수 — `event_type == "kill_switch"` | `킬 스위치 발동` · 본문 = `trigger_type` 한국어 라벨(FE `features/trading/labels.ts` `KS_TRIGGER_LABELS` 와 같은 3종, 모르는 값은 원문) · `url="/trading"` · `tag="kill_switch"` |
| 백테스트 종료(성공·실패) | `BacktestService.run`(`src/backtest/service.py`) **한 곳** — 본문은 `_run` 이 「이 호출이 기록한 종료 상태」를 돌려줄 때만 enqueue(재전달·취소 수습은 `None`), 종료 1회당 1번 | `백테스트 완료` / `백테스트 실패` · 본문 = 전략 이름 · `url="/backtests/{id}"` · `tag="backtest:{id}"` |

- realtime 스키마 검증에 실패해 발행을 버린 페이로드는 **푸시도 보내지 않는다**.
- 크래시·미처리 예외로 `reclaim_stale` 이 FAILED 로 만든 백테스트(`src/tasks/backtest.py`)는 푸시가 **없다** — 알려진 공백, [BL-867].
- 같은 주문의 체결 이벤트가 두 경로(워치독 · WS)로 와도 `tag` 가 같아 **화면에는 하나로 합쳐진다**.
- 잠금 화면 노출 대비 **금액·잔고·손익은 본문에 넣지 않는다**(심볼·방향·상태만).

### 3.6 BE 테스트 — 이름까지 계약 (`apps/api/tests/notifications/`)

| 테스트 | 무엇을 |
| --- | --- |
| `test_get_config_disabled_when_vapid_unset` | 키 없음 → `enabled: false` |
| `test_get_config_returns_public_key_when_configured` | 키 있음 → 공개 키 반환 |
| `test_endpoints_require_auth` | 4개 엔드포인트 비인증 401 |
| `test_subscribe_creates_row` · `test_subscribe_same_endpoint_is_upsert` | 생성 201 · 재요청 200, 행 1개 |
| `test_subscribe_endpoint_reassigned_to_current_user` | 다른 사용자 endpoint → 현재 사용자로 이동 |
| `test_unsubscribe_own_endpoint_204` · `test_unsubscribe_other_users_endpoint_404` | 본인 삭제 · 남의 것 404 |
| `test_send_push_deletes_subscription_on_410` · `..._on_404` | 410/404 → 행 삭제 |
| `test_send_push_keeps_subscription_on_500` | 그 외 실패 → 유지 |
| `test_send_push_noop_when_vapid_unset` | 키 없음 → 발송 0 |
| `test_publish_realtime_enqueues_push_for_filled_order` · `..._rejected_order` · `..._kill_switch` | 각 1회 enqueue |
| `test_publish_realtime_skips_push_for_submitted_order` | 다른 상태 → 0회 |
| `test_publish_realtime_survives_push_enqueue_failure` | enqueue 예외 → publish 정상 |
| `test_backtest_completion_enqueues_push_once` · `test_backtest_failure_enqueues_push_once` | 종료 1회당 1번 |
| `test_backtest_survives_push_enqueue_failure` | enqueue 예외 → 백테스트 결과 정상 |
| `test_push_test_endpoint_reports_sent_and_removed` | `{sent, removed}` 정확 |

## 4. 공통 계약

### 4.1 브라우저 지원

- 설치·SW·오프라인: Chromium 계열 · Safari 16.4+ · Firefox(설치 버튼은 Chromium 만 — `beforeinstallprompt` 는 비표준).
- **iOS 는 홈 화면에 설치한 PWA 에서만 푸시를 받는다**(iOS 16.4+).

### 4.2 프로덕션

- FE(`qb.woosung.dev`)는 Cloudflare Access 뒤 — §2.2 의 `use-credentials` 가 그 대응이다. **설치 가능성은 배포 후에만 잴 수 있다**(로컬 검증 불가).
- 서버 VAPID 키 주입 = 사람 작업([`operations/backend-deploy.md`](../operations/backend-deploy.md) §3 · [BL-866]). 넣기 전까지 푸시는 꺼져 있다.
- 키 생성(개인 키 = P-256 `d` 32바이트 base64url · 공개 키 = 비압축 점 65바이트 base64url — `pywebpush` 가 둘 다 이 형식을 받는다):

```bash
cd apps/api && uv run python -c "import base64 as b;from cryptography.hazmat.primitives.asymmetric import ec;from cryptography.hazmat.primitives import serialization as s;k=ec.generate_private_key(ec.SECP256R1());e=lambda x:b.urlsafe_b64encode(x).rstrip(b'=').decode();print('VAPID_PUBLIC_KEY='+e(k.public_key().public_bytes(s.Encoding.X962,s.PublicFormat.UncompressedPoint)));print('VAPID_PRIVATE_KEY='+e(k.private_numbers().private_value.to_bytes(32,'big')))"
```

### 4.3 푸시 페이로드 (BE → SW)

```json
{ "title": "백테스트 완료", "body": "EMA Crossover", "url": "/backtests/<id>", "tag": "backtest:<id>" }
```

- `url` 은 `/` 로 시작하는 같은 origin 경로만. 테스트 알림 = `{"title": "QuantBridge 테스트 알림", "body": "알림이 정상 동작합니다", "url": "/dashboard", "tag": "test"}`.

## 5. 수용 기준 (AC) — `apps/web/e2e/pwa.spec.ts`, 구현 전 고정

| AC | 무엇을 | 어떻게 |
| --- | --- | --- |
| AC-1 | 설치 가능 | CDP `Page.getInstallabilityErrors` → `[]` |
| AC-2 | manifest 정합 | 200 · 필수 필드 · 아이콘 전부 200(리다이렉트 0) · `<link rel=manifest>` 정확히 1개 ∧ `crossorigin="use-credentials"` |
| AC-3 | SW 등록·헤더 | `navigator.serviceWorker.ready` scope `/` · `/sw.js` `Cache-Control` 에 `no-store` |
| AC-4 | 오프라인 안내 | SW 활성 후 `context.setOffline(true)` → `/dashboard` 이동 → 「오프라인 상태입니다」 |
| AC-5 | API 무캐시 | `caches` 전수 → `/api/` 를 포함한 URL 0건 |
| AC-6 | 푸시 표시 | 알림 권한 부여 + CDP `ServiceWorker.deliverPushMessage` → `registration.getNotifications()` 의 title·`data.url` 일치 |
| AC-7 | 비인증 경로 | 로그아웃 상태에서 manifest·`/sw.js`·`/offline`·아이콘이 `/sign-in` 으로 안 감 |

**변이(평가 단계)** — ⑴ SW `fetch` 에 「모든 GET 응답을 `cache.put`」 주입 → AC-5 red(현 설계는 런타임 캐시가 0 이라 AC-5 는 회귀 감시용 음성 대조다) ⑵ `crossOrigin` 제거 → AC-2 red ⑶ `isPublicRoute` 의 `/offline` 제거 → AC-7 red
⑷ 410 처리 제거 → `test_send_push_deletes_subscription_on_410` red. 하나라도 안 죽으면 그 테스트는 게이트가 아니다.

## 6. 후속 (범위 밖)

- [BL-867] 스트레스 테스트·옵티마이저 완료 푸시 + `reclaim_stale` 이 실패로 만든 백테스트 푸시
- [BL-868] publish 없이 끝나는 주문 거부 경로(`src/tasks/trading.py`)에 realtime·푸시 둘 다 없음
- [BL-866] 프로덕션 활성화 — 서버 VAPID 키 주입 + Access 뒤 설치 가능성 실측
