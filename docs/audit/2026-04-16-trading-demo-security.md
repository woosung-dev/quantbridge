# Security Audit: Sprint 6 Trading 데모 (Pre-Implementation)

> **일자:** 2026-04-16
> **스킬:** `/cso` daily mode (8/10 confidence gate)
> **범위:** Sprint 6 Trading 데모 (구현 전) + Sprint 1-5 기존 코드
> **관련 PR:** [#8](https://github.com/woosung-dev/quantbridge/pull/8) — commits `ebaa9b3` → `0842fa9`
> **관련 ADR:** [006-sprint6-design-review-summary.md](../dev-log/006-sprint6-design-review-summary.md)
> **원본 JSON 리포트:** `.gstack/security-reports/20260416-daily.json` (로컬, gitignored)

---

## 감사 컨텍스트

Sprint 6 Trading 도메인(`backend/src/trading/`)은 현재 **Phase 0 스캐폴딩 stub**만 있고 실제 구현 코드는 없는 상태. 본 감사는:

1. 기존 Sprint 1-5 구현 코드의 운영 security posture
2. Sprint 6 **plan + spec**의 security 설계 검증 (실행 전 방지)

를 대상으로 했다. `/autoplan`이 이미 식별한 findings(HMAC timing side-channel, credential lifetime in worker, idempotency DoS 등)는 **중복 검증 없이 confirmed**로 표시하고, `/cso` 관점에서 새롭거나 formal decision이 필요한 항목에 집중했다.

## 실행 Phase 요약

| Phase | 결과 |
|-------|------|
| P0 Mental model + stack detection | FastAPI + Next.js + Celery + PostgreSQL. 4 기존 도메인 + Sprint 6 trading 신규 |
| P1 Attack surface census | 9 신규 REST + 1 webhook + Celery task + FE dashboard |
| P2 Secrets archaeology | **PASS** — `.env` gitignored, git history 깨끗, AWS/OpenAI/GitHub/Slack 키 미노출 |
| P3 Supply chain | `backend/uv.lock` tracked ✓, frontend 2 moderate dev-only CVEs |
| P4 CI/CD security | 3 unpinned third-party actions (CSO-3). No `pull_request_target`/script injection/secrets in env |
| P5 Infrastructure | `backend/Dockerfile` USER 미지정 (CSO-2). `docker-compose` `ENCRYPTION_KEY` 변수명 drift (CSO-4) |
| P6 Webhook audit | Clerk webhook has signature verify (`auth/router.py:39`). Sprint 6 trading webhook plan review 완료 |
| P7 LLM security | N/A — Sprint 6 LLM 미사용 (Pine parser는 deterministic interpreter) |
| P8 Skill supply chain | gstack 본체만 (trusted source) + 프로젝트 로컬 skill 없음 |
| P9 OWASP Top 10 | A01(cancel ownership, autoplan E15 중복), A02(Fernet — autoplan E4로 해결), A07(Clerk JWT 실사용 ✓) |
| P10 STRIDE | plan autoplan dual-voices가 대부분 커버 |
| P11 Data classification | RESTRICTED: API Key/Secret (AES-256 ✓). **webhook secret (원안: 평문 TEXT → CSO-1로 해소)** |
| P12 FP filter + verification | 9 candidates → 3 autoplan 중복 → 6 reported |
| P13 Findings report | 본 문서 |
| P14 Save | 원본 JSON: `.gstack/security-reports/20260416-daily.json`, 공개 리포트: 본 문서 |

---

## Findings Summary

| # | Sev | Conf | Status | Category | Title |
|---|-----|------|--------|----------|-------|
| CSO-1 | HIGH | 9/10 | VERIFIED | Data Classification | webhook_secrets.secret 평문 TEXT → 암호화 필수 |
| CSO-2 | HIGH | 9/10 | VERIFIED | Infrastructure | backend/Dockerfile USER directive 없음 (root 실행) |
| CSO-3 | HIGH | 8/10 | VERIFIED | CI/CD | CI 3 third-party actions unpinned |
| CSO-4 | MEDIUM | 8/10 | VERIFIED | Configuration | docker-compose ENCRYPTION_KEY 기본값 + Sprint 6 MultiFernet 변수명 drift |
| CSO-5 | MEDIUM | 7/10 | VERIFIED | Supply Chain | Frontend 2 moderate dev-only CVEs |
| CSO-6 | MEDIUM | 8/10 | VERIFIED | Webhook | T19 webhook Content-Length cap 없음 (autoplan E14 confirmed) |

**Critical 0 / High 3 / Medium 3 / Total 6**

---

## Finding CSO-1: webhook_secrets.secret 평문 TEXT 저장

* **Severity:** HIGH
* **Confidence:** 9/10
* **Status:** VERIFIED
* **Phase:** 11 (Data Classification)
* **Category:** Secrets / OWASP A02 Cryptographic Failures
* **File:** `docs/superpowers/specs/2026-04-16-trading-demo-design.md` §2.4

### Description

Brainstorming spec §2.4는 `trading.webhook_secrets` 테이블의 `secret` 컬럼을 `TEXT NOT NULL` 평문으로 설계했다. spec §8 Open Item 1 "webhook_secret 추가 암호화 여부"는 `/cso` audit에서 결정하는 것으로 이연됨.

### Exploit Scenario

1. 공격자가 DB backup/replica/dump에 읽기 접근 획득 (misconfigured S3 bucket, stolen DB snapshot, compromised dev env with prod copy, insider threat 등)
2. `SELECT secret FROM trading.webhook_secrets WHERE revoked_at IS NULL` 쿼리로 모든 활성 webhook 서명 키 추출
3. 공격자가 target `strategy_id`에 대해 `hmac_sha256(secret, attacker_payload)` 서명 생성
4. `POST /v1/webhooks/{strategy_id}?token=<forged>`로 위조 주문 요청
5. `OrderService`가 HMAC 검증 통과 → Celery → Bybit demo/live 주문 집행
6. 공격자가 피해자의 exchange account에서 임의 주문 실행 (매수/매도/청산 가능)

### Impact

- **전체 webhook 위조** 가능 → 피해자 연결된 거래소 계정에서 임의 주문 집행
- AES-256으로 API Key는 보호되지만 HMAC secret 평문 저장은 동일 공격 표면의 약한 고리
- Sprint 6 Premise 4 ("demo도 실전 경로") 철학과 불일치 — credentials는 암호화하면서 HMAC 키는 평문이면 일관성 파괴

### Recommendation

**EncryptionService (MultiFernet)로 암호화 저장 필수.**

1. 컬럼 타입 변경: `secret TEXT` → `secret_encrypted: bytes` (`Column(LargeBinary, nullable=False)`)
2. `WebhookSecretService.issue/rotate` → plaintext 생성 후 `EncryptionService.encrypt()` 결과 저장
3. `WebhookService.verify` → 각 candidate `secret_encrypted` 복호화 후 `hmac.compare_digest`
4. `WebhookSecretRepository`는 암호문 bytes만 다룸

**Decision:** spec §8 Open Item 1을 "암호화 필수"로 공식 해소. Sprint 6 plan T1 스키마에 즉시 반영 완료 (commit `0842fa9`).

EncryptionService는 이미 T4에서 `MultiFernet` 기반으로 존재 (ADR-006 결정 1) → 통합 cost near-zero.

---

## Finding CSO-2: backend/Dockerfile USER directive 없음

* **Severity:** HIGH
* **Confidence:** 9/10
* **Status:** VERIFIED
* **Phase:** 5 (Infrastructure)
* **Category:** OWASP A05 Security Misconfiguration
* **File:** `backend/Dockerfile`

### Description

`backend/Dockerfile`에 `USER` directive 부재. 컨테이너 내 FastAPI/Celery 프로세스가 UID 0(root)로 실행됨. Container escape 취약점 발견 시 host root로 직접 상승.

### Exploit Scenario

1. 공격자가 FastAPI 앱에서 RCE 취약점 발견 (예: pickle deserialization, 미검증 file upload 후 실행)
2. Container 내부에서 root 권한으로 임의 명령 실행 가능
3. Kernel CVE 또는 mount misconfig를 이용한 container escape 시도
4. Host machine에 root 권한으로 상승 → production 인프라 횡이동

### Impact

- Container escape 발생 시 containment boundary 상실 → prod infra 전반 compromise
- Defense-in-depth 원칙 위반 — 단일 취약점으로 모든 것 함락

### Recommendation

`backend/Dockerfile` 말미에 추가:

```dockerfile
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
# ... 이후 CMD/ENTRYPOINT
```

배포 전 `docker compose up -d` 검증. alembic migration이 `appuser`로 실행되는지 별도 확인 필요.

---

## Finding CSO-3: CI workflow 3 third-party actions unpinned

* **Severity:** HIGH
* **Confidence:** 8/10
* **Status:** VERIFIED
* **Phase:** 4 (CI/CD)
* **Category:** Supply Chain / CI Integrity
* **File:** `.github/workflows/ci.yml:27,45,90`

### Description

CI workflow에 다음 3개 third-party actions가 mutable tag(v3/v4)로 핀됨.

```yaml
line 27:  uses: dorny/paths-filter@v3
line 45:  uses: pnpm/action-setup@v4
line 90:  uses: astral-sh/setup-uv@v3
```

Action 저장소 소유자가 tag를 악성 커밋으로 force-push하면 다음 CI run에 자동 반영됨.

### Exploit Scenario

1. 공격자가 `dorny/paths-filter` 등 action 저장소 소유자 계정 탈취 (credential stuffing, phishing)
2. `v3` 태그를 악성 코드가 포함된 커밋으로 force-push
3. QuantBridge의 다음 CI run이 `@v3` resolve → 악성 코드 pull
4. CI job 내에서 `$GITHUB_TOKEN`, repository secrets, environment secrets(Clerk/Bybit keys) 접근 가능
5. 공격자 제어 서버로 secret 유출 또는 repo에 backdoor commit

### Impact

- CI 내 모든 secrets (GITHUB_TOKEN + repository/environment secrets) 유출
- Potential backdoor injection via CI-triggered deploy

### Recommendation

각 action의 현재 tag가 가리키는 SHA로 pin:

```yaml
- uses: dorny/paths-filter@<40-char-sha> # v3.0.2
- uses: pnpm/action-setup@<40-char-sha>  # v4.0.0
- uses: astral-sh/setup-uv@<40-char-sha> # v3.2.0
```

업데이트 시 Dependabot이 SHA 업데이트 PR 자동 생성하도록 `dependabot.yml` 설정 권장. First-party `actions/*`은 MEDIUM이라 Sprint 6 범위 외.

---

## Finding CSO-4: docker-compose ENCRYPTION_KEY 기본값 + Sprint 6 변수명 drift

* **Severity:** MEDIUM
* **Confidence:** 8/10
* **Status:** VERIFIED
* **Phase:** 5 (Infrastructure)
* **File:** `docker-compose.yml:66`

### Description

```yaml
ENCRYPTION_KEY: ${ENCRYPTION_KEY:-dev_aes_256_key_change_in_production_xxxxxxxxxxxxxx}
```

두 가지 문제:

1. Default value `dev_aes_256_key_change_in_production_xxxxxxxxxxxxxx`는 44자가 아니라 Fernet init 시 실패함 — 개발 편의상 crash를 방지하는 의도지만 실제로는 Fernet validator에서 `ValueError`
2. Sprint 6 ADR-006 결정 1로 env 변수명이 `TRADING_ENCRYPTION_KEYS`(복수)로 rename됐으나 docker-compose에 반영 안 됨

### Exploit Scenario

`dev_aes_256_key...` 기본값이 Fernet invalid라 fail-fast하는 건 실제로는 안전하지만, 변수명 drift로 Sprint 6 배포 시 정상 키를 주입해도 읽지 못해 프로덕션 장애 가능.

### Impact

- 배포 시 FastAPI lifespan 초기화 실패 → 서비스 기동 불가
- 또는 운영자가 당황해서 docker-compose default를 44자 플레이스홀더로 편집 → 프로덕션 weak default 위험

### Recommendation

Sprint 6 T3 config rename과 함께 docker-compose도 수정:

```yaml
# 변경 전
ENCRYPTION_KEY: ${ENCRYPTION_KEY:-dev_aes_256_key_change_in_production_xxxxxxxxxxxxxx}

# 변경 후
TRADING_ENCRYPTION_KEYS: ${TRADING_ENCRYPTION_KEYS:?required — generate via Fernet.generate_key()}
```

`${VAR:?msg}` 문법으로 기본값 없이 명시 설정 요구. 미설정 시 `docker compose up`이 명확한 에러 메시지 출력.

---

## Finding CSO-5: Frontend 2 moderate dev-only CVEs

* **Severity:** MEDIUM
* **Confidence:** 7/10
* **Status:** VERIFIED
* **Phase:** 3 (Supply Chain)
* **File:** `frontend/package.json`

### Description

`pnpm audit` 결과 2건 moderate CVEs:

- `esbuild`: 개발 서버 CORS로 임의 origin이 dev server 응답 읽기 가능
- `Vite`: optimized deps `.map` handling path traversal

### Exploit Scenario

개발자의 로컬 dev server가 실행 중일 때 악성 웹페이지 방문 시 dev 환경 정보 읽기 가능. **Production build 영향 없음** — dev-only.

### Impact

- 로컬 dev 환경 compromise only
- Prod 사용자에게 영향 0

### Recommendation

`pnpm update --latest`로 패치 버전 취득. Major 버전 bump가 breaking change를 수반하면 Sprint 7로 이연 OK (prod impact zero이므로).

---

## Finding CSO-6: T19 webhook endpoint Content-Length cap 없음

* **Severity:** MEDIUM
* **Confidence:** 8/10
* **Status:** VERIFIED (autoplan Eng E14 confirmed)
* **Phase:** 6 (Webhook Audit)
* **Category:** OWASP A04 Insecure Design
* **File:** `docs/superpowers/plans/2026-04-16-trading-demo.md:4288` (T19 `receive_webhook`)

### Description

```python
async def receive_webhook(strategy_id, request, token, idempotency_key, ...):
    body_bytes = await request.body()  # ← no size limit
    await webhook_svc.ensure_authorized(strategy_id, token=token, payload=body_bytes)
```

`await request.body()`는 전체 body를 메모리에 읽고 나서야 HMAC 검증. 크기 제한 없음.

### Exploit Scenario

1. 공격자가 `strategy_id` 획득 (enumeration, social leak)
2. `POST /v1/webhooks/{strategy_id}?token=random` + 100MB body
3. Server가 100MB body를 메모리에 읽기 시작
4. HMAC 검증 전에 worker OOM 또는 극심한 slowdown
5. 여러 concurrent request로 worker pool 고갈 → service DoS

### Impact

- FastAPI worker OOM kill
- Celery broker 간접 영향 없지만 webhook 수신 중단

### Recommendation

FastAPI middleware 또는 router-level 검사:

```python
MAX_WEBHOOK_BODY = 64 * 1024  # 64KB

@router.post("/webhooks/{strategy_id}", ...)
async def receive_webhook(..., request: Request):
    content_length = int(request.headers.get("content-length", 0))
    if content_length > MAX_WEBHOOK_BODY:
        raise HTTPException(status_code=413, detail=f"body too large (max {MAX_WEBHOOK_BODY}B)")
    body_bytes = await request.body()
    if len(body_bytes) > MAX_WEBHOOK_BODY:  # content-length 헤더 없거나 거짓일 경우
        raise HTTPException(status_code=413, detail="body too large")
    ...
```

TradingView 표준 alert payload는 ~1KB 이하이므로 64KB는 충분한 여유.

---

## `/cso`가 확인한 `/autoplan` 기존 findings

| autoplan | /cso 확인 | 비고 |
|----------|-----------|------|
| Eng E3 (HMAC short-circuit timing side-channel) | Phase 9 A02 확인 | plan에 이미 documented |
| Eng E4 (single Fernet) | Phase 11 확인 | **ADR-006 결정 1로 해결됨** — MultiFernet 전환 |
| Eng E5 (credential lifetime in worker) | Phase 9 A02 확인 | plan TODO |
| Eng E14 (webhook body size DoS) | **CSO-6로 승격** | 심각도 MEDIUM 유지 |
| Eng E15 (cancel endpoint ownership skip) | Phase 9 A01 확인 | plan에 fix TODO 명시 |

## 실행 전 체크리스트 (SDD 시작 시 처리)

| Finding | 처리 위치 | 공수 |
|---------|-----------|------|
| CSO-1 webhook_secret 암호화 | T10/T11/T17 구현 시 EncryptionService 배선 | +0.3d (plan T1 스키마는 반영됨) |
| CSO-2 Dockerfile USER | Sprint 6 배포 준비 (T16 또는 T23) | +0.05d |
| CSO-3 CI SHA pin | T23 문서 동기화 전 | +0.15d |
| CSO-4 docker-compose env rename | T3 config 구현 시 병행 | +0.1d |
| CSO-6 body size cap | T19 webhook router 구현 시 | +0.1d |
| CSO-5 frontend CVEs | Sprint 7 이연 OK | — |

**Total SDD 추가 공수: +0.7d**

## Trend

**First run** — 이전 `/cso` 실행 기록 없음. 향후 감사는 본 문서의 finding id (CSO-N)를 기준으로 resolve/persist/new 추적.

## Disclaimer

본 `/cso` 감사는 AI 보조 스캔이며, **프로페셔널 침투 테스트의 대체가 아님**. LLM은 미묘한 인증 로직 또는 timing-based 취약점을 놓칠 수 있다. 실자본 집행이 본격화되는 Sprint 7+ 라이브 주문 전환 전 전문 security firm의 pentest 권장.

본 문서는 low-hanging fruit catch 및 design phase safety net 목적. 상세 JSON 리포트는 `.gstack/security-reports/20260416-daily.json` (로컬, gitignored) 참조.
