# ADR-003: Pine 런타임 안전성 + 파서 범위 결정

> **상태:** 확정
> **일자:** 2026-04-13 (ADR 작성: 2026-04-15)
> **출처:** `/office-hours` + `/autoplan` (CEO + Design + Eng 리뷰, Codex+Claude 듀얼 보이스 검증)
> **관련 커밋:** autoplan 세션 `49001-1776090935` (완료 `81381-1776092684`)
> **gstack 원본:** `~/.gstack/projects/quant-bridge/learnings.jsonl`, `woosung-main-design-20260413-231543.md`

---

## 컨텍스트

Pine Script 전략을 Python으로 변환해 실행하는 핵심 아키텍처 결정. `/autoplan` 종합 리뷰에서 **4가지 critical 이슈**가 발견됨.

각 이슈는 Codex와 Claude subagent가 **독립적으로 동일한 결론**에 도달 (CONSENSUS CONFIRMED).

---

## 결정 1: Pine → Python 트랜스파일 시 `exec()`/`eval()` 절대 금지

### 문제

초기 설계에서 Pine Script를 Python 코드 문자열로 변환한 뒤 `exec()`로 실행하는 방식을 검토함.

### 위험

**코드 인젝션 취약점** — 사용자 입력(Pine Script 문자열)이 그대로 Python 런타임에서 실행됨.

```python
# 위험한 예시 (절대 하지 말 것)
pine_code = user_input  # 사용자가 제출한 Pine Script
python_code = transpile(pine_code)  # Python으로 변환
exec(python_code)  # ⚠️ 인젝션 가능 — `__import__('os').system('rm -rf /')` 삽입 가능
```

공격 시나리오:
- Pine 코멘트, 문자열 리터럴에 Python 코드 인젝션
- 트랜스파일러 버그 악용으로 임의 코드 실행
- 악성 사용자가 서버 장악 → 다른 사용자 API Key 탈취

### 해결

**인터프리터 패턴** 또는 **RestrictedPython/sandbox** 사용 강제.

| 방식 | 설명 | 적합성 |
|------|------|:-----:|
| **인터프리터 패턴** | Pine AST를 직접 순회하며 vectorbt/pandas 연산에 매핑 | ⭐⭐⭐⭐⭐ 권장 |
| **RestrictedPython** | `exec()`를 제한된 네임스페이스에서 실행 | ⭐⭐⭐ 보조 |
| **Docker sandbox** | 실행을 컨테이너로 격리 | ⭐⭐ 오버헤드 큼 |
| **raw `exec()`** | 직접 실행 | ❌ **금지** |

### 신뢰도

**10/10** — Codex + Claude subagent 모두 **critical** 등급으로 평가. 이견 없음.

---

## 결정 2: Pine Script 미지원 함수 포함 시 전체 "Unsupported" 반환

### 문제

Pine Script의 `security()`, `request.*`, `barstate`, `var`, 배열, MTF 등 복잡한 기능을 **부분적으로 지원**할지, **전체 거부**할지 결정.

### 위험 (부분 실행 시)

미지원 함수가 스크립트 전체 의미를 바꿀 수 있음:

```pine
// security()가 멀티 타임프레임 데이터 가져오기
htf_close = security(symbol, "1D", close)  // ← 미지원

// 시그널 판단이 HTF close에 의존
long_signal = close > htf_close  // ← HTF 없이 실행하면 결과 완전히 다름
```

미지원 함수를 무시하고 실행 → **잘못된 백테스트 결과 제공** → 사용자가 이 결과 믿고 실전 매매 → **실제 손실**.

**QuantBridge의 핵심 가치 "trust layer"와 정면 충돌.**

### 해결

**All-or-nothing 정책**:
- Pine 스크립트에 지원 패턴 외 함수가 **1개라도** 있으면 전체를 "Unsupported"로 반환
- 어떤 함수가 미지원인지 사용자에게 명시 (투명성)
- 부분 실행 금지

### 지원 패턴 (MVP)

```
✅ 지표: SMA, EMA, RSI, MACD, Bollinger Bands, Supertrend
✅ 시그널: ta.crossover, ta.crossunder
✅ 주문: strategy.entry, strategy.exit, strategy.close
✅ 입력: input.int, input.float, input.bool, input.string

❌ security(), request.*, request.security()
❌ barstate.*, var, varip
❌ 배열 (array.*), 매트릭스
❌ 멀티 타임프레임 (HTF 참조)
❌ 사용자 정의 함수 (f(), method())
❌ strategy.position_size 복잡 로직
```

### 선행 검증

**TV 상위 50개 전략 분류 테스트** 필수 — 실제 커뮤니티 전략에서 지원 범위가 현실적인지 확인. 80%+ 커버리지 주장은 과대평가로 판명.

### 신뢰도

**10/10** — 양 모델 모두 "trust layer 핵심 가치 침해" 지적.

---

## 결정 3: Celery worker zombie task 방지 인프라

### 문제

백테스트/최적화가 Celery 워커에서 비동기 실행. 워커가 **OOM crash** 또는 **강제 종료**되면:
- DB의 `backtest.status = 'running'` 상태 영구 잔류
- 사용자는 결과를 영원히 기다림
- 재실행해도 "이미 실행 중"으로 차단

### 해결 (3개 계층)

**1. `on_failure` 핸들러**

```python
@app.task(bind=True, on_failure=mark_backtest_failed)
def run_backtest(self, backtest_id: str):
    ...

def mark_backtest_failed(task, exc, task_id, args, kwargs, einfo):
    backtest_id = args[0]
    Backtest.objects.filter(id=backtest_id).update(
        status='failed',
        error_message=str(exc),
        failed_at=timezone.now()
    )
```

**2. Celery Beat periodic cleanup (30분 기준)**

```python
# celerybeat schedule
'cleanup-zombie-backtests': {
    'task': 'src.tasks.cleanup_zombie_tasks',
    'schedule': crontab(minute='*/5'),  # 5분마다
}

def cleanup_zombie_tasks():
    # 30분 이상 running 상태인 백테스트 → failed로 전환
    cutoff = timezone.now() - timedelta(minutes=30)
    Backtest.objects.filter(
        status='running',
        started_at__lt=cutoff
    ).update(
        status='failed',
        error_message='Worker timeout or crash (auto-recovered)',
    )
```

**3. 수동 취소 엔드포인트**

```
POST /api/v1/backtests/:id/cancel
  → Celery task revoke + DB status update + 사용자 알림
```

### 신뢰도

**9/10** — Eng 리뷰에서 "명시적 복구 전략 없으면 프로덕션 위험" 지적.

---

## 결정 4: Pine 파싱 커버리지 80%+ 가정 폐기

### 문제

초기 PRD는 "MVP에서 Pine 스크립트의 80%+ 지원 가능"을 가정함.

### 발견

`/autoplan` Eng 리뷰 + 학습 데이터:
- `security()`, `request.*`: 커뮤니티 전략의 ~30% 사용
- `var`, `varip`: ~40% 사용
- MTF: ~25% 사용
- 사용자 정의 함수: ~50% 사용

**실제 커버리지는 20~40%** 선이 현실적.

### 해결

**TV 상위 50개 전략 분류 테스트 선행** (Phase 1 Week 2):

1. TradingView 커뮤니티에서 인기 상위 50개 Pine Script 수집
2. 각각 Go/Adjust/Pivot 판단:
   - **Go**: 현재 지원 패턴만 사용 → 즉시 파싱 가능
   - **Adjust**: 1~2개 미지원 함수 → 지원 확장 검토
   - **Pivot**: 구조적으로 불가능 → Unsupported 처리
3. 결과 기반으로 MVP 지원 범위 재조정

**솔직한 마케팅:** "80% 지원"이 아니라 "검증된 40% 전략 패턴 지원, 나머지는 투명하게 Unsupported 반환".

### 신뢰도

**10/10** — CEO 리뷰에서 "과대평가가 사용자 신뢰 훼손" 지적.

---

## 영향 범위

### 코드

- `backend/src/domains/strategy/parser.py` — 지원 패턴 정의 + Unsupported 검증
- `backend/src/domains/strategy/transpiler.py` — 인터프리터 패턴 구현 (exec 금지)
- `backend/src/domains/backtest/tasks.py` — Celery on_failure 핸들러
- `backend/src/tasks/cleanup.py` — Beat periodic cleanup (신규)
- `backend/src/api/backtests.py` — cancel 엔드포인트

### 테스트

- `tests/security/test_pine_injection.py` — 인젝션 시도 거부 검증
- `tests/integration/test_zombie_recovery.py` — 워커 crash 시 복구 검증
- `tests/fixtures/tv_top_50_strategies/` — 상위 50개 분류 테스트 (Phase 1 Week 2)

### 문서

- CLAUDE.md — 보안 규칙 2줄 (이 ADR 요약)
- docs/README.md — 핵심 의사결정 섹션에 이 ADR 링크

---

## 기각된 대안

| 대안 | 기각 사유 |
|------|---------|
| `exec()` + 입력 검증 | 검증은 우회 가능. 보안은 단일 장애점 금지 원칙 위반 |
| 부분 실행 + 경고 표시 | trust layer 핵심 가치 침해. 사용자가 경고 무시할 위험 |
| Celery 없이 동기 백테스트 | API 타임아웃, 워커 확장 불가 |
| 인메모리 상태만 사용 (DB 기록 없이) | 프로세스 재시작 시 상태 손실 |

---

## 검증 기록

**/autoplan 리뷰 결과 (2026-04-13 15:04):**

| 리뷰 | 상태 | 미해결 | Critical | 모드 |
|------|:---:|:---:|:---:|------|
| CEO Review | issues_open | 3 | 0 | SELECTIVE_EXPANSION |
| Design Review | issues_open | 7 | 0 | — |
| Eng Review | issues_open | 5 | **5** | FULL_REVIEW (31 issues) |

**듀얼 보이스 합의:**

| Phase | Consensus Confirmed | Disagree |
|-------|:-------------------:|:--------:|
| CEO | 8 | 3 |
| Design | 7 | 0 |
| Eng | 13 | 3 |

---

## 참고

- `.ai/project/lessons.md` — LESSON-001, 002, 003 (이 ADR의 요약, 승격 루프용)
- `~/.gstack/projects/quant-bridge/learnings.jsonl` — 원본 학습 기록 (JSONL)
- `~/.gstack/projects/quant-bridge/woosung-main-design-20260413-231543.md` — /office-hours 디자인 문서
