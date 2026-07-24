<!-- position-cockpit 스프린트의 의사결정·발견 기록 (append-only). 상속 체인 = tier-c → opspack-ws2 → perf-surface → position-cockpit -->

# position-cockpit context-notes

> Phase B(perf-surface #471 후속). WS position 채널 + 코크핏 잔고/포지션 완성. 마이그레이션 0(비영속).

## #1. 인터뷰 6건 확정 (2 라운드)

1. 잔고 카드 = **활성 세션 계정만**(전 계정 아님). 2. WS 자극 = **내가 데모 소액 주문**. 3. 생성/평가 = **codex 생성 + Claude 평가**(분리). 4. **B1~B4 한 스프린트**. 5. 포지션 = **표로 통합 + §06 진단 카드 제거**(의도적 IA 변경 — 캐논은 §06 카드 유지하므로 "캐논 충실" 아님). 6. 배치 = **상단 승격 §02잔고/§03포지션**(기존 §02~06 → §04~08 renumber).

## #2. codex G0 = 12건 전부 CONFIRMED (기각 0) → 전건 반영

- **[P1 실버그]** short 수익률 부호 반대(`(mark−entry)/entry` 는 롱 전용 → short `(entry−mark)/entry`). / 같은 계정+심볼 여러 전략 공유 가능(`uq_live_sessions_active_unique`=(user,strategy,account,symbol)) → 포지션 행 중복 → **세션(전략) 열 추가**. / 청산 후 "열린 포지션 0건" 빈상태 누락. / 캐시 DEL 이 debounce 뒤 → 억제 이벤트 stale → **DEL 을 debounce 앞으로**. / **`session-diagnostics.tsx` 경로 오류**(내 Explore 가 features/ 로 오인, codex 가 app-local `_components/` 로 정정). / 잔고 오라클 다른 양 비교(CCXT USDT total/free vs account totalEquity) → coin[USDT] walletBalance/available 로 정정.
- **[P2]** subscribe negative-ack 관측 / §06 카드 제거 = 의도적 IA(캐논 §06 카드 유지) / balance null·0·clamp / 비활성 계정 invalidate 억제(list_active_by_account 비면 no-op).
- **CONFIRMED CORRECT**: message_handler bypass·handler 제거 안전·position_update 3-site 등재·positionsPrefix·Bybit demo 한정·404/supported.

## #3. ★함정 대장 (신규 발견)

- **★BE pytest = 3-env 전체 필수**: `DATABASE_URL` + `TEST_DATABASE_URL`(…5436/quantbridge_test) + `TEST_REDIS_LOCK_URL`(redis://localhost:6380/3). **DATABASE_URL 누락 시** worker-engine 이 `.env.local` stale 패스워드 잡아 `InvalidPasswordError` → market_data_backfill 2건 거짓 실패(격리 실행). 3-env 전체로 baseline = BE **2557** 정확 재현.
- **★`ruff format` 은 이 레포 게이트 아님**(perf-surface 상속 함정 부정확). `.husky/pre-push` = BE `ruff check .` + `mypy src/`(pytest 는 QB_RUN_PYTEST=1 opt-in), FE `typecheck` + `test`. `ruff format` 은 590중 349파일 미채택(baseline 포함) → 강제 금지. **BE 게이트 = ruff check + mypy + pytest / FE = typecheck + test + lint**.
- **★worktree pytest 는 main src 아닌 worktree src 사용**(editable install 없음, `pythonpath=["."]`) → 평가기가 worktree/backend 에서 main venv python 으로 실 pytest 가능(격리 게이트 온전).
- **★codex 워커 stray 산출물**: 3 워커 전부 `backend|frontend/checklist.md`·`context-notes.md` 를 잘못 생성(요청 밖) → cherry-pick 전 `rm` 필수.
- **★codex exec resume 문법**: `-C` 플래그 거부(usage 에러, events:0) → resume 은 cd 후 `-C` 없이 실행.
- **★caplog 전역전파 격리 취약**: 전체 스위트의 다른 테스트 `logging.disable` 오염 → caplog.text 빈값(격리 실행선 통과). **logger.warning 직접 monkeypatch** 로 내성화.
- **★debounce 테스트 = 클럭 주입**: `time.monotonic` 전역 패치 시 asyncio 루프가 iterator 소진→StopIteration. 생성자 `clock: Callable=time.monotonic` 주입으로 결정론화.
- ★BE 8100 = 로컬 uvicorn --reload(메인 레포) / ws-stream = `backend/src` bind-mount + watchfiles → cherry-pick 코드 자동 반영(§7.2 충족). 스트림 새 코드 확실히 하려면 `docker restart quantbridge-ws-stream`(reconciler 300s 후 재기동).
- ★활성-비평가 안전창: 세션 활성화 시 `is_active=true, last_evaluated_bar_time=now()+2h` 로 beat 평가 회피(dogfood 후 전량 복구).
- ★독립 오라클: 데모 creds = Fernet(MultiFernet, TRADING_ENCRYPTION_KEYS) 복호화 → raw HMAC(api-demo.bybit.com, sign=HMAC(secret, ts+key+recv+query|body)). 앱 코드 경로 미사용.

## #4. dogfood — 2계통 오라클 + WS 4점 전 PASS

- **READ(curl ↔ 브라우저)**: §02 잔고 **190679.22692395 USDT** 정확 일치(사용가능 100% clamp) / §03 flat → "열린 포지션이 없습니다" + 각주(마침표). 콘솔 error 0.
- **WS 4점(데모 주문 자극)**: Buy 0.001 → 브라우저 §03 이 빈→포지션(BTC/USDT 롱 0.001 진입 64963.1 **↔ curl avgPrice 64963.1 정확**, lev 2, 세션열 "Dogfood Roundtrip 1m", verdict=확인불가(로컬 미인지 정직)) → Sell reduceOnly → **redis 채널 `qb:rt:user:0d5abe67` 에서 발행 프레임 직접 포착** `{"v":1,"type":"position_update","ts":...,"payload":{"symbol":"BTCUSDT","side":"flat","size":"0"}}`(P1 계약 정확, side flat=size0 정규화 실증) → §03 빈상태 복귀.
- 하드닝 라이브 실증: #3(size0→flat)·#4(세션열)·#5(빈상태)·#6(롱 부호)·#10(각주)·#11(100% clamp).
- 상태 복구: 세션 601e56eb 비활성 + alert_rules 2건(615f63e1) is_active=true 원복, 활성 세션 0 psql 재검증.
