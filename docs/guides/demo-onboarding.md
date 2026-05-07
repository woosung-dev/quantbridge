# QuantBridge Demo Onboarding — 5분 시나리오

> Sprint 42 1-2명 micro-cohort 데모용 1 페이지 가이드.
> 본인 dogfood (Phase 1.1) 자동 검증 + 외부 첫인상 polish 9건 적용 후 작성 (2026-05-08).

QuantBridge = TradingView Pine Script 전략을 백테스트→스트레스테스트→데모/라이브 트레이딩으로 연결. 본 데모는 **Bybit Demo Trading** (실거래 X, 테스트 자금) 으로 진행.

---

## 1단계 · QuantBridge 가입 (1분)

1. https://qb.local — 또는 데모 진행자가 보낸 링크 — 접속.
2. "Sign up" → 이메일 또는 Google 로그인 (Clerk 인증).
3. 로그인 후 자동으로 `/strategies` 페이지 이동.

---

## 2단계 · Bybit Demo Trading 계정 + API key (2분)

1. https://www.bybit.com/en/help-center/article/Bybit-Demo-Trading 가이드 따라 **Demo Trading 모드 활성화** (실계정 우측 상단 토글, 별도 가입 X).
2. Demo Trading 진입 후 **API Management** → "Create API Key" → System-generated → Read/Trade 권한 부여.
3. 생성된 **API Key + Secret** 임시 메모 (재조회 X — Bybit Demo 는 1회 노출).

---

## 3단계 · QuantBridge 거래소 계정 연결 (1분)

1. QuantBridge 사이드바 → **트레이딩** 탭 클릭.
2. "거래소 계정" 섹션 → **계정 추가** button.
3. Dialog 에서:
   - Exchange: **Bybit**
   - Mode: **Demo** (★ 중요 — Live 선택 시 실거래 위험)
   - Label: 본인 식별용 (예: `bybit-demo-1`)
   - API Key / Secret: 2단계에서 메모한 값 paste.
4. 등록 완료 후 `DEMO` 배지 표시 확인.

---

## 4단계 · 첫 백테스트 실행 (1분)

1. **전략** 탭 → "새 전략" → Pine Script v5 코드 paste (예: 데모 진행자가 공유한 EMA Cross 전략).
2. 파싱 성공 확인 → 우상단 **백테스트** button.
3. **백테스트** 페이지 → "새 백테스트" → Symbol/TF/기간 선택 → **실행**.
4. ~10초 후 완료. 결과 페이지 = 4개 탭 (개요 / 성과 지표 / 거래 분석 / 거래 목록 / 스트레스 테스트).

---

## 5단계 · 결과 공유 (선택)

1. 백테스트 상세 페이지 우상단 **공유** button.
2. share link clipboard 자동 복사 → 1-2명에게 카톡/슬랙 DM.
3. share link 페이지 = 공개 (로그인 X), og:image 1200×630 미리보기.

---

## Demo 트레이딩 (선택)

1. **트레이딩** 탭 → **테스트 주문** button.
2. Symbol / 수량 / 방향 입력 → 주문 발송 (Bybit Demo 가상자금 차감).
3. **최근 주문** 섹션에 status 표시 (`submitted` → `filled` 등).

> ⚠️ 데모 자금이지만 KillSwitch (Kill Switch) 가 작동하므로 부주의한 큰 주문은 주문 차단 가능.

---

## 다음 / 문의

- 데모 자유롭게 사용 → 마찰/오류/UX 의견 **카톡 DM 으로 직접 회신** (Sprint 42 = 1-2명 micro-cohort 직접 인터뷰 dogfood).
- 1주 사용 후 30분 인터뷰 가능 시점 알려주시면 일정 조율.
- 발견한 bug / "이런 게 있으면 좋겠다" 자유롭게.

---

## 메시지 템플릿 (1-2명 카톡 DM 발송용)

```
안녕 ○○야, 내가 만들고 있는 QuantBridge 데모 한 번 써봐줄 수 있어?

TradingView Pine Script 전략을 백테스트하고 가상 자금으로 데모 트레이딩까지 해보는 도구야.
가이드 링크: <repo>/docs/guides/demo-onboarding.md (또는 별도 공유)

대략 5분 가입 + 1주일 정도 가볍게 써보면서 마찰/UX 의견 직접 카톡으로 회신해주면 큰 도움 됨.
실거래 아니고 Bybit Demo (가상 자금) 만 써. 1-2명에게만 먼저 공유 중이야.

URL: https://qb.local (또는 staging URL)
```
