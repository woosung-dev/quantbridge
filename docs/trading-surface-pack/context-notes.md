<!-- trading-surface-pack 의사결정·발견 기록 (append-only). 상속 체인 = tier-c → opspack-ws2 → perf-surface → position-cockpit → trading-surface-pack -->

# trading-surface-pack context-notes

> position-cockpit(#472) 후속. 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 완성 + 부채 4종. 마이그레이션 0.

## #1. 인터뷰 3건 확정 (미결정 부분만 — 나머지 설계 D1~D7 은 grounding 세션 동결)

1. **청산 멱등성 = 재조회-409** (발주 직전 fetch_open_positions 재조회, 없으면 409; FE pending disabled 병행; pending-락·신규 영속 상태 없음).
2. **청산 응답 = 비동기 202** (pending Order 즉시 반환, flat 반영은 WS position_update + 15s 폴링).
3. **잔여 조건부 TP/SL 스윕 = 후속 BL 이연** (이번은 reduce-only 청산만; 포지션-부착 TP/SL 은 Bybit flat 시 자동취소).

## #2. codex G0 = 14 finding, 코드 대조 후 반영 (§7.3)

- **BLOCKING 반영 3**: ① close req `leverage=None` 은 spot provider 로 오라우팅(registry `(bybit,demo,False)`→BybitDemoProvider) → **leverage=validated.leverage 필수**. ② `flatten` 이 reduce_only 강제 불변식 없음 → **`flatten and not reduce_only → raise`**. ③ hedge 2-leg(fetch_open_positions 가 long/short 둘 다 보존) → **>1 leg 409 hedge_unsupported**(임의 leg 청산 금지).
- **MAJOR 반영 4**: ⑥ OrderResponse 는 `id`/detail 없음 → **신규 ClosePositionResponse**. ⑦ settings_unset 은 execute() 밖 → **canonical validate_strategy_settings 재사용**(None→422 unset / ValidationError→422 invalid). ⑧ Partial/Full 구분 불가 → **각주를 "포지션-보고값" 프레이밍**(mode 구분 주장 금지). ⑨ 수동 청산 후 세션 active 재진입 → **모달 정직 고지**. ⑫ ccxt TP/SL 은 numeric 0/None(raw '' 도) → **0→None + 테스트 fixture 갱신**.
- **CONFIRMED-CORRECT 5**: 가드 목록 정확(②~⑧ bypass, ①ownership 유지) / pre_existing downstream 의존 없음 / P-METRIC 컨벤션·삽입점 / session 필드 완비 / execute 202 async 의미.
- **수용(설계/사용자 확정, 미수정)**: #5 동시 이중클릭 중복 pending(Q1 재조회-409 수용, reduce_only 가 거래소단 캡) / #4 account+symbol 순포지션은 다전략 세션 공유(one-way demo, 모달이 "계정 단위" 고지 + 후속 BL).

## #3. ★함정 (상속 + 신규)

- **상속**(position-cockpit §3): BE pytest 3-env 필수 / **ruff format 은 게이트 아님**(ruff check+mypy+pytest / typecheck+test+lint) / worktree pytest=worktree src(pythonpath) / codex stray checklist·context-notes rm / 5436·3100·8100·6380 / 3000=nexus-core(정체성 프로브) / em-dash 래칫 / QB_PRE_PUSH_BYPASS=1.
- **★codex resume 문법**: `-s workspace-write` 는 `resume` **앞**(codex exec -s workspace-write resume <id> <prompt>). resume 뒤에 두면 "unexpected argument '-s'". `-C` 는 여전히 거부 → cd 후 실행. worktree 는 venv 없음 → codex 가 ruff/mypy 자체 실행 불가(평가기가 main venv 로 실행).
- **★worktree 커밋 husky "lint-staged not found"**: 워크트리엔 frontend node_modules 해석 안 됨 → 무해(커밋 성공). 메인 트리 커밋은 lint-staged 정상 동작(eslint --fix).
- **★DB 스키마 prefix**: trading.\* (exchange_accounts/live_signal_sessions/alert_rules/orders/kill_switch_events), public.strategies, killswitchtriggertype enum = **소문자**(daily_loss). 오라클 SQL 에 trading. prefix 의무.
- **★next build ↔ dev server .next 공유**: build 를 dev(3100)와 동시 실행 지양(순차). build 후 dev 헬스 재확인.
- **★신선 JWT**: storageState 는 20:44 stale(Clerk 60s 만료) → playwright chromium storageState 컨텍스트에서 `Clerk.session.getToken()` 로 신선 발급. e2e user(jetaime.jang@gmail.com) = DB user 0d5abe67(데모 세션 소유).

## #4. dogfood — 2계통 오라클 (앱↔독립 curl HMAC) 전 PASS

- **독립 오라클** = `bybit_oracle.py`(Fernet 복호화 + api-demo.bybit.com HMAC). balance 190679 USDT(retCode 0) + positions.
- **READ 대조**: 데모 Buy 0.001 → set-trading-stop TP=66000/SL=62000 → 코크핏 §03 실드라이버(storageState) **롱 0.001 / entry 63911.3 / 익절 66000.0 / 손절 62000.0 / 청산가 — / lev 2.0 / verdict "확인할 수 없습니다"(정직)** = 오라클 정확 일치. TP/SL 없는 재진입 포지션은 익절/손절 **—** (0→null 정직). 콘솔 error 0.
- **청산 종단**: 청산 버튼→모달(정직 고지 verbatim)→청산 실행→오라클 flat(size 0)+앱 Order row(`sell reduce_only=true state=filled`)+§03 빈복귀(폴 지연 후). 콘솔 0.
- **★kill-switch 활성 청산 성공(가드 bypass 실증)**: active daily_loss KS 삽입 → 청산 → **flat + Order filled + KS 여전히 active**(정상 주문은 차단됐을 것, flatten 이 우회, KS 미소비). 머니-패스 핵심 증명.
- BL-416/425 = vitest 커버 + 전 상호작용 콘솔 0(409 노이즈 부재).
- 상태 복구: 세션 601e56eb 비활성(last_eval NULL) + KS resolved + active 세션/KS 0 + alert_rules 615f63e1 무변경(loss_limit/watchdog active) + 포지션 flat, psql 재검증.

## #5. 게이트 / 검증 체인

- generator(codex 2워커 병렬, backend/frontend 교집합 0) ↔ **evaluator(Claude 서브에이전트 per-worker, 게이트 직접 실행)** 엄격 분리(사용자 필수). W2 PASS(즉시). W1 FAIL(RUF059 1건)→codex resume→PASS.
- 게이트: BE **2601**(+18)·FE **1083**(+8)·ruff/mypy/tsc/lint 0·canon **32**·authed **66**(+2 코크핏 §03 구조)·build ✓·alembic 무변경.
