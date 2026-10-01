# ADR-044 — PWA(설치 · 오프라인 안내 · 웹 푸시)를 도입한다. 데이터는 캐시하지 않는다

- **상태:** Accepted (2026-10-02, 사용자 결정 — 범위 「설치 + 오프라인 안내 + 웹 푸시」)
- **결정자:** 사용자(범위) · 오케스트레이터 세션(구현 방식)
- **관련:** [PRD](../PRD.md) §3·§4(「모바일 네이티브 앱 — 반응형 웹만」 줄 개정) · [ADR-035](./035-fe-component-ownership.md)(`features/pwa/`) ·
  [ADR-034](./034-auth-self-host-better-auth.md)(JWT 검증) · 구현 계약 = [`architecture/pwa.md`](../architecture/pwa.md)

## Context

- PRD §5⑵ 실사용 축은 「만든 사람이 진짜 사용자가 된다」다. 그런데 백테스트·데모 체결·Kill Switch 는 **화면을 열어 둬야만** 결과를 안다.
  사용자 대상 알림 경로는 0개다 — 있는 것은 운영자용 Slack/Telegram 단일 채널(`src/common/alert.py`)뿐이다.
- 네이티브 앱은 PRD §4 가 닫았고([BL-850] 은 DEFERRED), 별도 모바일 코드베이스도 없다. PWA 는 같은 웹 코드로 설치·푸시를 얻는다.

## Decision

1. **설치 가능한 PWA** — 정적 `public/manifest.webmanifest` + 루트 `<link rel="manifest" crossOrigin="use-credentials">`.
   `app/manifest.ts` 는 쓰지 않는다 — Next 가 `crossOrigin` 없는 링크를 자동 주입하고(Vercel preview 에서만 붙임), FE 는 Cloudflare Access 뒤라 쿠키 없는 manifest 요청이 302 된다.
2. **서비스 워커는 직접 쓴다(`public/sw.js`)** — 페이지 이동 실패 시 `/offline` 안내만 하고 **`/api/*`·RSC·인증 응답은 캐시하지 않는다**.
3. **웹 푸시** — VAPID + `push_subscriptions` 테이블 + Celery `notifications.send_push`. 트리거 = 주문 체결·거부 · Kill Switch(`publish_realtime` 한 곳) · 백테스트 종료.
   **VAPID 키가 없으면 기능 전체가 꺼진다**(`GET /push/config` → `enabled:false`).

## Consequences

- 좋은 점: 결과를 기다리며 화면을 지키지 않아도 된다. 네이티브 앱 없이 설치·알림을 얻는다. 서버 키를 넣기 전까지 운영 영향 0.
- 나쁜 점: **오프라인에서 볼 수 있는 데이터는 없다**(의도). iOS 는 홈 화면 설치 후에만 푸시를 받는다. Playwright e2e 가 CI 에서 돌지 않아([BL-845]) PWA e2e 는 로컬 증거다.
- 프로덕션 설치 가능성(Access 뒤)은 **배포 후에만** 잰다.

## 버린 대안

| 대안 | 버린 이유 |
| --- | --- |
| Serwist / next-pwa | 기본 런타임 캐시가 RSC·API 응답까지 담는다 — 낡은 금융 숫자를 최신처럼 보이고 로그아웃 후에도 남는다. 필요한 SW 는 60줄 안팎 |
| Next `experimental.useOffline` | canary 기능 · SW 가 아니라 설치·푸시를 못 준다 |
| 오프라인 데이터 캐시(마지막 결과 열람) | 「결과와 가정이 얼마나 정직하게 보이는가」(PRD §1)와 정면 충돌 |
| 이벤트별 알림 설정 | 실사용자 1명 단계에서 근거 없는 설정 — 「이 기기에서 받기」 하나로 시작 |

## 재평가 트리거

- 외부 사용자를 연다(결정 ⑵) → 이벤트별 설정·발송량 상한이 필요해진다.
- 네이티브 앱 결정([BL-850]) → 푸시 채널을 FCM/APNs 로 옮길지 다시 본다.
