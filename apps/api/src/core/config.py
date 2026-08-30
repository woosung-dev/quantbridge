import re
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Sprint 30 ε B2 — `app_env` 동치 enum (production gating 명시화).

    기존 `Literal[...]` 정의는 backward-compat 위해 그대로 유지. 본 enum 은
    production guard / log level 결정 용 helper. 비교는 `settings.is_production`
    property 권장 (직접 비교 시 `Environment.PRODUCTION.value` 사용).
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def secret_value(value: SecretStr | str | None) -> str:
    """설정 경계에서만 `SecretStr` 원문을 꺼낸다.

    테스트의 `SimpleNamespace`와 기존 운영 스크립트가 주입하는 문자열도 지원한다.
    연결 factory 밖에서는 이 helper를 쓰지 않아 설정 덤프·로그가 DSN을 마스킹한 채 남는다.
    """

    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "QuantBridge"
    app_env: Literal["development", "staging", "production"] = "development"
    # ★기본값은 False 다 — 안전한 쪽이 기본이어야 한다(2026-08-15 surface-truth).
    #   종전 기본값 True 는 `APP_ENV` 를 안 넣은 배포 호스트에서 그대로 살아남았고,
    #   실측으로 `qb-api.woosung.dev` 가 `{"env":"development"}` + `/docs` 200 을 냈다.
    #   `_enforce_production_safety` 는 `app_env != production` 이면 조기 반환하므로
    #   그 호스트를 보호하지 못한다 — 보호를 env 이름이 아니라 **기본값**에 둔다.
    #   ★이 값은 「신뢰된 로컬 개발」 단일 스위치다: docs 노출·HSTS 미부착·traceback 이
    #   전부 여기에 묶인다(`main.py:create_app`). 로컬은 `.env.local` 이 DEBUG=true 를 준다.
    debug: bool = False
    secret_key: SecretStr = SecretStr("change-me")

    # BL-561 — root logger 레벨. celery worker / uvicorn 이 **같은** 값을 쓴다.
    # 실제 배선은 `src/common/logging_config.py`.
    log_level: str = Field(
        default="INFO",
        description="root logger level (DEBUG/INFO/WARNING/ERROR/CRITICAL). BL-561.",
    )

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        """오타를 조용히 INFO 로 삼키지 않는다 — 기동 시점에 명시 실패."""
        upper = v.strip().upper()
        if upper not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(
                "LOG_LEVEL must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL, got " + repr(v)
            )
        return upper

    # Better Auth (ADR-034) — 인증 서버는 FE 앱 안에서 돈다. 백엔드는 그 JWT 를 JWKS 로 검증만 한다.
    # ★시크릿이 하나도 없다. 검증은 **공개 키**로 하므로 백엔드가 쥘 비밀이 없는 것이 이 구조의
    #   본질적 이득이다(구 Clerk 은 `CLERK_SECRET_KEY` 를 백엔드·워커 4벌에 뿌려야 했다).
    better_auth_url: str = Field(
        default="http://localhost:3000",
        description=(
            "Better Auth 서버(= FE 앱)의 공개 origin. JWT 의 iss/aud 검증 기준이며 "
            "JWKS 는 `<이 값>/api/auth/jwks` 에서 받는다. FE 의 BETTER_AUTH_URL 과 같아야 한다."
        ),
    )
    better_auth_jwks_url: str = Field(
        default="",
        description=(
            "JWKS 취득 URL 을 직접 지정한다(선택). 비우면 better_auth_url 에서 파생. "
            "★서버 배포에서는 터널을 왕복하지 않도록 컨테이너 내부 주소를 넣는다."
        ),
    )

    @property
    def jwks_url(self) -> str:
        """JWKS 엔드포인트 — 명시값 우선, 없으면 `better_auth_url` 에서 파생."""
        explicit = self.better_auth_jwks_url.strip()
        if explicit:
            return explicit
        return f"{self.better_auth_url.rstrip('/')}/api/auth/jwks"

    # Database — TimescaleDB extension은 동일 DB의 ts schema에 위치 (M2)
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://quantbridge:password@db:5432/quantbridge"
    )

    # Redis / Celery
    # ★2026-08-15 surface-truth (S4) — `redis_url`(DB 0 「캐시」) 를 **삭제**했다.
    #   선언·주입은 돼 있었지만 `src/` 전체에서 참조가 **0건**인 죽은 설정이었다. 죽은 설정은
    #   비용이 0 이 아니다 — compose·CI·`.env.example` 6곳이 그 값을 실어 나르면서
    #   「캐시 DB 가 따로 있다」는 그림을 유지했고, 그 그림이 아래 격리 오해를 떠받쳤다.
    celery_broker_url: SecretStr = SecretStr("redis://redis:6379/1")
    celery_result_backend: SecretStr = SecretStr("redis://redis:6379/2")
    redis_lock_url: SecretStr = Field(
        default=SecretStr("redis://redis:6379/3"),
        description=(
            "분산 락 + slowapi rate-limit storage 전용 Redis URL (DB 3). "
            "★논리 DB 분리는 **키 이름 충돌만** 막는다 — eviction 격리가 아니다. "
            "`maxmemory-policy` 는 인스턴스 전역이라 DB 번호는 축출 대상 선정에 관여하지 "
            "않는다. 락이 축출되지 않는 근거는 DB 번호가 아니라 compose 의 `noeviction` 이다. "
            "Sprint 10 Phase A1 · 2026-08-15 surface-truth S4."
        ),
    )

    # --- Sprint 10 Phase B: Rate limiting (TRUSTED_PROXIES whitelist) ---
    # pydantic-settings v2 는 list[str] 환경변수를 JSON 배열로만 파싱.
    # 콤마 구분 문자열 지원을 위해 str 로 저장 후 property 에서 파싱.
    trusted_proxies_raw: str = Field(
        default="",
        alias="trusted_proxies",
        description=(
            "신뢰 가능한 reverse proxy IP 화이트리스트 (콤마 구분 문자열). "
            "trusted_proxies property 에서 list[str] 로 변환. Sprint 10 Phase B."
        ),
    )

    @property
    def trusted_proxies(self) -> list[str]:
        """콤마 구분 문자열 → list[str]. 빈 값 → []."""
        return [s.strip() for s in self.trusted_proxies_raw.split(",") if s.strip()]

    # --- [BL-784] e2e authed 스위트 전용 rate limit 면제 신원 ---
    # 스위트는 **한 신원으로 90 테스트**를 돌고 페이지마다 BE 요청 4~8건을 내므로 60초 창의
    # 100건을 상시 소진한다. 걸린 요청이 단언 대상이면 red 라서 실패 지점이 실행마다 갈렸다.
    # ★기본값은 빈 문자열이고, 값이 있으면 **development 가 아닌 모든 환경에서**
    #   `_enforce_production_safety` 가 **부팅을 막는다**(staging 포함 — 2026-08-17 적대 리뷰 P1).
    #   완화 판정 본문은 `src/common/rate_limit.py`.
    e2e_rate_limit_exempt_email: str = Field(
        default="",
        description=(
            "rate limit 을 면제할 e2e 전용 계정 이메일 (로컬/CI 전용). "
            "비어 있으면 아무도 면제되지 않는다. "
            "app_env 가 development 가 아닌데 값이 있으면 부팅 실패(staging 포함). BL-784."
        ),
    )

    # Backtest (Sprint 4)
    backtest_stale_threshold_seconds: int = Field(
        default=1800,
        description=(
            "running/cancelling 상태가 몇 초 초과 시 stale로 판정 "
            "(worker startup reclaim + GET /:id/progress의 stale 플래그). 기본 30분."
        ),
    )
    # CF3 (Phase C-1) — optimizer/stress_test 도 동일 stale-RUNNING reclaim.
    optimizer_stale_threshold_seconds: int = Field(
        default=1800,
        description="RUNNING optimizer run 이 몇 초 초과 시 stale → FAILED reclaim. 기본 30분.",
    )
    stress_test_stale_threshold_seconds: int = Field(
        default=1800,
        description="RUNNING stress test 가 몇 초 초과 시 stale → FAILED reclaim. 기본 30분.",
    )
    ohlcv_fixture_root: str = Field(
        default="apps/api/data/fixtures/ohlcv",
        description="FixtureProvider가 OHLCV CSV를 읽는 루트 경로. 프로세스 CWD 기준.",
    )

    # --- Sprint 6 Trading ---
    trading_encryption_keys: SecretStr = Field(
        ...,
        description=(
            "Comma-separated Fernet keys (newest first) for MultiFernet. "
            "Rotation: prepend new key, keep old keys for grace period. "
            "ADR-006 결정 1 / autoplan CEO F3 + Eng E4."
        ),
    )
    exchange_provider: Literal["fixture", "bybit_demo", "bybit_futures", "okx_demo"] = Field(
        default="fixture",
        description=(
            "[DEPRECATED Sprint 22 BL-091 — dispatch path 에서 미사용] "
            "Sprint 21 까지는 process-wide global 로 ExchangeProvider 결정. "
            "Sprint 22 부터는 (account.exchange, account.mode, has_leverage) 3-tuple "
            "기반 dynamic dispatch (`tasks/trading.py:_provider_for_account_and_leverage`). "
            "본 필드는 H2 동안 test_config.py + funding.py 의 legacy 호환용 dead config. "
            "Sprint 23+ 에서 제거 예정."
        ),
    )
    kill_switch_cumulative_loss_percent: Decimal = Field(
        default=Decimal("10.0"),
        description=(
            "Cumulative loss % of capital_base가 이 값 초과 시 strategy-scoped "
            "kill switch 발동. autoplan CEO F4: MddEvaluator → CumulativeLossEvaluator."
        ),
    )
    kill_switch_daily_loss_usd: Decimal = Field(
        default=Decimal("500.0"),
        description="당일 누적 손실(USD) 초과 시 account-scoped kill switch 발동.",
    )
    kill_switch_api_error_streak: int = Field(
        default=5,
        description="연속 API error N회 도달 시 account-scoped kill switch 발동.",
    )
    kill_switch_capital_base_usd: Decimal = Field(
        default=Decimal("10000"),
        description=(
            "cumulative loss % 산출용 기준 자본 fallback. Sprint 8+ (2026-04-20): "
            "ExchangeAccountService.fetch_balance_usdt() 동적 바인딩 완료 — 실제 "
            "계좌 USDT 잔고 우선, fetch 실패 시 본 값 fallback."
        ),
    )
    webhook_secret_grace_seconds: int = Field(
        default=3600,
        description="Webhook secret rotation 후 구 secret 수락 grace period (초).",
    )

    # --- pine_v2 AST 디스크 캐시 (BL-832) ---
    pine_ast_cache_dir: str = Field(
        default=".ast-cache",
        description=(
            "pynescript AST 디스크 캐시 디렉토리 (apps/api 상대 경로). "
            "빈 문자열이면 비활성 — 프로세스 지역 lru_cache만 남는다."
        ),
    )
    pine_ast_cache_max_bytes: int = Field(
        default=512 * 1024 * 1024,
        ge=0,
        description=(
            "AST 캐시 총 용량 상한. 초과 시 mtime이 오래된 항목부터 지운다. "
            "파스 엔드포인트에 소스 길이 상한이 없어(BL-831) 캐시 표면이 임의 입력으로 "
            "채워질 수 있으므로 디스크 증가를 여기서 막는다."
        ),
    )

    # --- Dogfood Daily Report ---
    dogfood_report_output_dir: str = Field(
        default="docs/reports/dogfood",
        description="Dogfood 일일 리포트 HTML 출력 디렉토리 (프로젝트 루트 상대 경로).",
    )

    # --- Sprint 7a Bybit Futures ---
    bybit_futures_max_leverage: int = Field(
        default=20,
        ge=1,
        le=125,
        description=(
            "OrderRequest.leverage 상한. 초과 시 422. "
            "Bybit USDT Perp 이론 상한 125x이나 리스크 관리로 20x 기본."
        ),
    )

    @field_validator("trading_encryption_keys")
    @classmethod
    def _validate_keys(cls, v: SecretStr) -> SecretStr:
        """comma-separated Fernet keys — 1개 이상, 각각 44-char URL-safe base64."""
        from cryptography.fernet import Fernet

        raw = v.get_secret_value()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            raise ValueError("TRADING_ENCRYPTION_KEYS must contain at least 1 Fernet key")
        for k in keys:
            try:
                Fernet(k.encode())
            except ValueError as e:
                raise ValueError(f"Invalid Fernet key: {e}") from e
        return v

    # --- Sprint 9 Phase D: Observability ---
    prometheus_bearer_token: SecretStr | None = Field(
        default=None,
        description=(
            "Bearer token for GET /metrics. 값이 설정되면 Grafana Cloud Agent 의 "
            "bearer_token 과 일치해야 허용. "
            "★2026-08-11 계약 변경 — **비어 있으면 /metrics 는 401 이다**(fail-closed). "
            "종전 서술 「비어 있으면 인증 없이 접근 가능(로컬 개발용)」은 이제 거짓이다. "
            "Sprint 9 Phase D · Sprint 60 S5 BL-246. "
            "★아래 validator 는 app_env=production 일 때만 이 값을 강제한다 — 기본값 "
            "development 로 도는 호스트는 토큰 없이도 부팅하고 그때 /metrics 는 401 이다 "
            "([BL-704])."
        ),
    )

    # --- Sprint 12 Phase A: Slack alerts ---
    slack_webhook_url: SecretStr | None = Field(
        default=None,
        description=(
            "Slack incoming webhook URL for critical alerts (Kill Switch / daily_loss). "
            "None or empty = silent skip (alert.py best-effort policy). "
            "발급: Slack workspace → Apps → Incoming Webhooks → Add to Slack."
        ),
    )

    @field_validator("slack_webhook_url")
    @classmethod
    def _validate_slack_webhook(cls, v: SecretStr | None) -> SecretStr | None:
        """codex G1 #10 — https://hooks.slack.com/ prefix 검증. 빈 값은 None 으로."""
        if v is None:
            return None
        raw = v.get_secret_value()
        if not raw:
            return None
        if not raw.startswith("https://hooks.slack.com/"):
            raise ValueError("SLACK_WEBHOOK_URL must start with https://hooks.slack.com/")
        return v

    # --- Wave 0 W2: Telegram alerts (critical 이벤트 미러) ---
    telegram_bot_token: SecretStr | None = Field(
        default=None,
        description=(
            "Telegram Bot API token for critical alerts (Kill Switch / 주문 stuck 등). "
            "None or empty = silent skip (telegram_alert.py best-effort policy). "
            "발급: @BotFather → /newbot → token. 형식: <digits>:<alphanumeric>."
        ),
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description=(
            "Telegram chat id (또는 @channelusername) — alert 수신 대상. "
            "None or empty = silent skip. 숫자 id / @channel 양식 모두 허용."
        ),
    )

    @field_validator("telegram_bot_token")
    @classmethod
    def _validate_telegram_token(cls, v: SecretStr | None) -> SecretStr | None:
        """@BotFather token 형식(<digits>:<rest>) 검증. 빈 값은 None 으로."""
        if v is None:
            return None
        raw = v.get_secret_value()
        if not raw:
            return None
        if not re.match(r"^\d+:[\w-]+$", raw):
            raise ValueError(
                "TELEGRAM_BOT_TOKEN must match @BotFather format <digits>:<alphanumeric>"
            )
        return v

    @field_validator("telegram_chat_id")
    @classmethod
    def _normalize_telegram_chat_id(cls, v: str | None) -> str | None:
        """빈 문자열 → None (silent skip 일관성)."""
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    # --- Experiment: Pine Script → Strategy 변환 (Claude API) ---
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "Claude API key for Pine Script → Strategy auto-conversion (indicator 분석용). "
            "발급: https://console.anthropic.com/ → API Keys. 미설정 시 convert 엔드포인트 비활성."
        ),
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description=(
            "Claude 모델 ID for convert endpoint. Sonnet (4-6) 권장 (속도+비용 최적). "
            "Opus (3) 도 지원하나 비용 3배."
        ),
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "Google Gemini API key — Anthropic 호출 최종 실패 시 fallback. "
            "발급: https://aistudio.google.com/apikey. 미설정 시 fallback 비활성."
        ),
    )
    gemini_model: str = Field(
        default="gemini-3.7-flash",
        description=(
            "Gemini 모델 ID. ★종전 기본값 `gemini-2.0-flash` 는 **폐기돼 404** 를 낸다 "
            "(2026-08-28 실측 — `generateContent` 지원 39종 목록에 부재). "
            "실측 확인된 대안: `gemini-3.7-flash`(기본) · `gemini-3.6-flash` · "
            "`gemini-3.5-flash` · `gemini-3.5-flash-lite`(5/5 성공 · 평균 1.11초). "
            "★기본값 3.7 은 2026-08-28 시점 **503 high demand 로 0/10** 이었다 — "
            "`_call_gemini` 에는 tenacity 재시도가 없어(anthropic 에만 있다) 그대로 올라오고, "
            "`complete_json` 이 다음 provider 로 넘긴다. 그 사이 확실히 도는 값이 필요하면 "
            "`GEMINI_MODEL` 로 갈아라 — 서버는 `gemini-3.5-flash-lite` 로 뒀다."
        ),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "OpenAI API key. 발급: https://platform.openai.com/api-keys. "
            "★구조화 출력은 Structured Outputs(strict)를 쓴다 — 세 provider 중 스키마 보증이 가장 강하다."
        ),
    )
    openai_model: str = Field(
        default="gpt-4.1-mini",
        description=(
            "OpenAI 모델 ID. 브리핑 해설·전략 생성은 짧은 JSON 이라 mini 가 비용 대비 합리적. "
            "정확도 우선이면 gpt-4.1."
        ),
    )
    # ★provider 를 **설정으로 고른다**([ADR-040]/[ADR-041] 후속). 종전에는 「anthropic 우선 →
    #   gemini fallback」이 코드에 박혀 있었고 그 사실이 `AGENTS.md` 에도 하드코딩돼 있었는데,
    #   키를 가진 provider 가 환경마다 다르다(2026-08-28 실측: 로컬은 openai 만 유효).
    #   쉼표 목록이며 **앞에서부터 시도**한다. 키가 없는 provider 는 조용히 건너뛴다.
    llm_provider_order: str = Field(
        default="openai,gemini",
        description=(
            "LLM provider 시도 순서(쉼표 구분). 유효 값: anthropic · openai · gemini. "
            "하나만 적으면 그 provider 만 쓴다(fallback 없음). "
            "★기본에서 **anthropic 은 뺐다**(2026-08-28 사용자 결정) — 어댑터는 그대로 있으니 "
            "키를 넣고 이 목록에 이름을 되돌리면 다시 돈다. "
            "★무효한 키를 목록에 남기지 마라: `available_providers` 는 **키 존재만** 보므로 "
            "매 호출이 그 provider 를 시도하고 실패한 뒤에야 다음으로 넘어간다."
        ),
    )

    # --- Sprint 11 Phase C: Waitlist ---
    resend_api_key: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Resend API key (Email provider). "
            "발급: https://resend.com/ → API Keys. Free tier 100/일."
        ),
    )
    resend_from_address: str = Field(
        default="QuantBridge Waitlist <waitlist@quantbridge.app>",
        description=(
            "초대 메일 발신 주소. ★[BL-072] — Resend 는 **인증된 도메인**에서만 발송을 허용한다. "
            "기본값의 `quantbridge.app` 은 이 배포의 도메인이 아니므로(`qb.woosung.dev`) "
            "그대로 두면 발송이 403 으로 실패한다. 배포 시 실도메인으로 바꿔라."
        ),
    )
    waitlist_token_secret: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Waitlist invite token HMAC-SHA256 서명 비밀. "
            "최소 32바이트. openssl rand -hex 32 로 생성."
        ),
    )
    waitlist_admin_emails_raw: str = Field(
        default="",
        alias="waitlist_admin_emails",
        description=(
            "Admin 권한 이메일 화이트리스트 (콤마 구분). "
            "admin endpoint 접근 시 CurrentUser.email 과 비교. 빈 값 = admin 엔드포인트 차단."
        ),
    )
    waitlist_invite_base_url: str = Field(
        default="http://localhost:3000/invite",
        description="Invite landing page base URL — email 본문에 token 이 append 됨.",
    )

    @property
    def waitlist_admin_emails(self) -> list[str]:
        """콤마 구분 문자열 → lowercase list[str]. 빈 값 → []."""
        return [s.strip().lower() for s in self.waitlist_admin_emails_raw.split(",") if s.strip()]

    # CORS / URLs
    frontend_url: str = "http://localhost:3000"

    # Exchange / OHLCV provider
    default_exchange: str = "bybit"
    ohlcv_provider: Literal["fixture", "timescale"] = Field(
        default="fixture",
        description=(
            "OHLCV 데이터 소스. 'fixture'=Sprint 4 CSV, "
            "'timescale'=CCXT+TimescaleDB cache (Sprint 5 M3+)."
        ),
    )

    # ----------------------------------------------------------------
    # Sprint 30 ε B2 — production guard
    # ----------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """production 환경 판정 helper."""
        return self.app_env == Environment.PRODUCTION.value

    @property
    def is_staging(self) -> bool:
        """staging 환경 판정 helper."""
        return self.app_env == Environment.STAGING.value

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """production 환경 진입 시 SecretStr 정합 + debug 강제.

        - ``app_env=production``: ``debug=False`` 강제.
        - ``secret_key`` 가 placeholder (``change-me`` / 빈 값) 이면 raise (운영 노출 사전 차단).
        - ``waitlist_token_secret`` 빈 값 raise.
        - ``frontend_url`` / ``waitlist_invite_base_url`` / ``better_auth_url`` 이 localhost
          기본값이면 raise — 종전 validator 는 이 셋을 안 봐서 「부팅은 됐는데 CORS 가 조용히
          실 FE 를 거부」하는 상태가 production 에서 통과했다(2026-08-17 ADR-034 회차 실측).
        - dev/test 환경은 모두 통과 (기존 동작 유지).

        본 validator 는 backward-compat 위해 staging 은 강제하지 않음 (warning 만).
        """
        # 0. [BL-784] e2e rate limit 면제는 **development 밖 어디에도** 있어서는 안 된다.
        # ★이 검사만 조기 반환 **앞**에 둔다. 아래 검사들은 「backward-compat 위해 staging 은
        #   강제하지 않음」이 방침이지만, 이 값은 다르다 — 런타임 판정
        #   (`is_rate_limit_exempt_identity`)이 화이트리스트(`app_env == development`)라
        #   staging 에서는 판정이 막지만, **값이 거기 있다는 것 자체가 배포 실수의 신호**다.
        #   그리고 블랙리스트 시절에는 staging 에 두 층이 모두 없었다(2026-08-17 적대 리뷰 P1).
        if (
            self.app_env != Environment.DEVELOPMENT.value
            and self.e2e_rate_limit_exempt_email.strip()
        ):
            raise ValueError(
                f"{self.app_env} app_env must not set E2E_RATE_LIMIT_EXEMPT_EMAIL "
                "(BL-784 — e2e rate limit 면제는 로컬/CI 전용이다)"
            )

        if self.app_env != Environment.PRODUCTION.value:
            return self

        # 1. debug 강제 OFF
        if self.debug:
            object.__setattr__(self, "debug", False)

        # 2. SecretStr placeholder 감지 — 빈 값 + 알려진 dev default 전부 차단.
        # 'dev-secret-change-in-prod' 는 .env.example 의 SECRET_KEY default →
        # prod 로 그대로 복사하는 footgun 을 validator 에서 fail-fast.
        placeholders: list[str] = []
        if self.secret_key.get_secret_value() in (
            "",
            "change-me",
            "dev-secret-change-in-prod",
        ):
            placeholders.append("SECRET_KEY")
        if not self.waitlist_token_secret.get_secret_value():
            placeholders.append("WAITLIST_TOKEN_SECRET")

        if placeholders:
            raise ValueError(
                "production app_env requires non-placeholder secrets: " + ", ".join(placeholders)
            )

        # 2b. localhost 기본값 잔존 검사 (ADR-034 신설).
        # ★이 셋은 「비어 있으면」이 아니라 「기본값 그대로면」이 결함이다 — 값이 있어 보여서
        #   종전 검사가 통과시켰고, 그 결과가 CORS 침묵 거부다.
        localhost_defaults = {
            "FRONTEND_URL": self.frontend_url,
            "WAITLIST_INVITE_BASE_URL": self.waitlist_invite_base_url,
            "BETTER_AUTH_URL": self.better_auth_url,
        }
        stale = [k for k, v in localhost_defaults.items() if "localhost" in v or "127.0.0.1" in v]
        if stale:
            raise ValueError(
                "production app_env requires real URLs (localhost default left in place): "
                + ", ".join(stale)
            )

        # 3. Sprint 60 S5 BL-246 — production env 시 PROMETHEUS_BEARER_TOKEN 의무
        # /metrics endpoint 가 public 노출 방지 (Beta 외부 노출 audit fail risk).
        if (
            self.prometheus_bearer_token is None
            or not self.prometheus_bearer_token.get_secret_value()
        ):
            raise ValueError(
                "production app_env requires PROMETHEUS_BEARER_TOKEN "
                "(Sprint 60 S5 BL-246 — /metrics endpoint public 노출 차단)"
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
