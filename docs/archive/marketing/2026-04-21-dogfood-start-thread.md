# QuantBridge Dogfood Start — Twitter/X Thread 초안

> 작성일: 2026-04-21  
> 상태: 초안 (사용자 검토 후 게시)  
> 전략: Dogfood-first indie SaaS 철학 중심

---

## 한국어 Thread (3 트윗)

---

**Tweet 1/3 — 훅 (Hook)**

```
퀀트 전략 자동화 플랫폼을 혼자 만들고 있습니다.

TradingView Pine Script로 백테스트 → 실 계좌 자동 주문까지 연결하는 도구.

오늘부터 testnet 라이브로 달립니다. 내 코드를 내가 제일 먼저 쓰는 dogfood-first 방식으로요.

(Bybit testnet, 1달 롱런, 시작 🧪)
```

---

**Tweet 2/3 — 기술 근거 (Why it works)**

```
왜 팔기 전에 직접 쓰냐고요?

- 실제로 쓰면 "없어서 불편한 기능"이 바로 보임
- 라이브 주문이 실패하면 진짜 버그를 잡을 수 있음
- Kill Switch가 실제로 켜지면, 리스크 관리 코드를 믿게 됨

H1 (2026년 4월): 820+ 테스트, KS/AES-256/Advisory Lock 전부 통과.
H2 목표: 3~4주 testnet → 극소액 mainnet → Beta.

"내가 돈 내고 쓰고 싶은가" 가 기준입니다.
```

---

**Tweet 3/3 — CTA**

```
스택: FastAPI · Next.js 16 · Celery · Bybit/OKX CCXT · TimescaleDB · Clerk

일주일에 한 번씩 testnet 결과 공개할 예정.

QuantBridge 오픈 베타는 testnet 통과 후 → 관심 있으시면 팔로우.

#Quant #AlgoTrading #IndieHacker #BuildInPublic #TradingView
```

---

## English Thread (3 tweets)

---

**Tweet 1/3 — Hook**

```
I'm building a quant strategy automation platform — solo.

The idea: connect TradingView Pine Script to live exchange orders through backtest → stress test → live trading pipeline.

Today I'm starting a 1-month testnet live run. Dogfood-first: I use it before I sell it. 🧪

(Bybit testnet, let's go)
```

---

**Tweet 2/3 — Why dogfood-first**

```
Why run it myself before opening to others?

- Real usage reveals "I wish this existed" features instantly
- Live order failures surface actual bugs (not mocked ones)
- When Kill Switch fires, I actually trust my risk management

H1 (April 2026): 820+ tests, KS / AES-256 / advisory lock all green.
H2 target: 3~4 weeks testnet → tiny mainnet pilot → Beta.

Quality bar: "Would I pay for this?"
```

---

**Tweet 3/3 — CTA**

```
Stack: FastAPI · Next.js 16 · Celery · Bybit/OKX CCXT · TimescaleDB · Clerk

Planning weekly testnet PnL reports.

QuantBridge open beta after testnet passes — follow if interested.

#AlgoTrading #Quant #IndieHacker #BuildInPublic #TradingView #Python
```

---

## 게시 체크리스트

- [ ] 트윗 1 한 → 영 순서로 게시 (같은 날)
- [ ] 스크린샷: Bybit testnet 첫 주문 진입 시 첨부
- [ ] 첫 주 결과 요약 트윗 예약 (2026-04-28)
- [ ] 반응 보고 "기능 요청" 댓글 docs/TODO.md에 수집
