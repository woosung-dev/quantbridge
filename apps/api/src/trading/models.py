"""trading 도메인 SQLModel 테이블. Sprint 6.

Schema: 모두 `trading` 스키마 격리 (Sprint 5 ts schema 패턴).
DateTime: AwareDateTime + TIMESTAMPTZ 강제 (ADR-005).
Decimal: 금액/수량은 NUMERIC(18, 8) — Sprint 4 D8 교훈.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, LargeBinary, SQLModel

from src.common.datetime_types import AwareDateTime


class ExchangeName(StrEnum):
    bybit = "bybit"
    binance = "binance"  # Sprint 7+
    okx = "okx"  # Sprint 7d — CCXT sandbox, spot only, passphrase required


class ExchangeMode(StrEnum):
    demo = "demo"
    live = "live"


class OrderSide(StrEnum):
    buy = "buy"
    sell = "sell"


class OrderType(StrEnum):
    market = "market"
    limit = "limit"


class OrderState(StrEnum):
    pending = "pending"
    submitted = "submitted"
    filled = "filled"
    rejected = "rejected"
    cancelled = "cancelled"


class KillSwitchTriggerType(StrEnum):
    # autoplan CEO F4: "cumulative_loss"는 peak-based drawdown이 아니므로 semantic-correct naming 사용
    cumulative_loss = "cumulative_loss"
    daily_loss = "daily_loss"
    api_error = "api_error"


class LiveSignalInterval(StrEnum):
    """Sprint 26 — Live Signal Auto-Trading 의 평가 주기.

    1m / 5m / 15m / 1h. evaluate_live_signals_task (1분 Beat) 가 list_active_due
    로 interval 별 due 필터링. 5m session 은 5번째 fire 마다 evaluate.
    """

    m1 = "1m"
    m5 = "5m"
    m15 = "15m"
    h1 = "1h"


class LiveSignalEventStatus(StrEnum):
    """Sprint 26 — Transactional outbox event status (codex G.0 P1 #3).

    pending → dispatched (정상 broker 발주) / failed (KillSwitch / NotionalCap / 기타).
    pending 으로 남으면 worker crash recovery 시 재dispatch.
    """

    pending = "pending"
    dispatched = "dispatched"
    failed = "failed"


class AlertRuleType(StrEnum):
    """세션 알림 규칙의 발화 조건."""

    loss_limit = "loss_limit"
    watchdog = "watchdog"


class AlertChannel(StrEnum):
    """세션 알림 규칙의 전송 채널."""

    slack = "slack"
    telegram = "telegram"
    both = "both"


class SessionDeactivationReason(StrEnum):
    """BL-484 — 라이브 세션이 **왜** 죽었는지. `LiveSignalSession.deactivated_reason` 의 값 집합.

    ★이 클래스가 사유 문자열의 유일한 정본이다. 그전까지 사유는 Slack/Telegram alert 로만
    나가고 DB 에 남지 않았다 — 알림을 놓치면 화면 어디에도 "왜 멈췄나" 가 없었다.

    ★`tasks/live_signal.py` 의 호출부는 소유 경계 때문에 리터럴을 쓴다(그 파일은 다른 워커가
    쥐고 있어 import 를 추가할 수 없다). 대신
    `tests/tasks/test_deactivation_reason_wiring.py` 가 그 파일의 모든 `deactivate(...)` 호출을
    AST 로 훑어 **여기 없는 값이 새면 실패**시킨다. 새 사유를 추가하려면 여기에 먼저 등재해야 한다.

    ★컬럼 타입은 PG enum 이 아니라 `String(64)` 다 — `LiveSignalInterval` 이 밟은 자동
    enum cast(`UndefinedObjectError`) 함정을 피한다. 그래서 **읽을 때는 plain str 로 온다**
    (`.value`/`.name` 금지 — BL-453 과 동일 계약).

    ★BL-571 — 값 집합은 `ck_live_signal_sessions_deactivated_reason` CHECK 제약이
    원장에서 못박는다(아래 `_DEACTIVATION_REASON_CHECK`). **그래서 사유를 추가하려면
    이 enum + 마이그레이션 + FE 라벨 3곳을 함께 고쳐야 한다** — 컬럼 타입을 String 으로
    고른 시점의 "사유 추가에 DDL 불필요" 성질은 의도적으로 포기했다. 이유는
    `_DEACTIVATION_REASON_CHECK` 주석 참조. 빠뜨리면
    `tests/test_migrations.py::test_deactivation_reason_check_matches_the_enum` 이 잡는다.
    """

    # preflight (evaluate 진입 전 차단) — `live_signal.py` 의 `preflight_cat` 집합.
    coverage_unrunnable = "coverage_unrunnable"
    degraded_unconsented = "degraded_unconsented"
    equity_baseline_missing = "equity_baseline_missing"
    equity_exhausted = "equity_exhausted"
    # runtime (Pine 재생 중 발산)
    run_live_error = "run_live_error"
    runtime_divergence = "runtime_divergence"
    # 포지션 정합 실패
    gap_resync_position_mismatch = "gap_resync_position_mismatch"
    position_divergence = "position_divergence"
    # 사람이 Stop 을 눌렀다
    user_stopped = "user_stopped"


# BL-571 — 원장 쪽 방어. `deactivated_reason` 에 enum 밖 값이 들어오면 DB 가 거절한다.
#
# ★왜 (iii) repository 검증이나 (ii) 주기 스캔이 아니라 (i) CHECK 인가 —
# 실제로 원장을 오염시킨 3종(`soak_closed_by_operator` / `interim_window_stop` /
# `prefix_w1_window_done`)은 **코드가 만든 값이 아니다**. 운영자가 soak 중 psql 로 직접
# UPDATE 한 값이고, 화면은 그걸 원문 그대로 보여줬다. 기존 가드
# (`tests/tasks/test_deactivation_reason_wiring.py`)는 `src` 의 `deactivate(...)` 호출부를
# AST 로 훑는다 — 그 범위는 옳지만, psql·스크립트·수기 경로는 구조적으로 시야 밖이다.
# repository 검증도 같은 한계를 갖는다(ORM 을 통과하는 쓰기만 본다). 주기 스캔은 막지 못하고
# 사후에 알릴 뿐이다. **쓰는 주체가 누구든 막는 유일한 자리가 원장 자신이다.**
#
# ★대가 — 사유 추가에 마이그레이션이 필요해진다. 컬럼 타입은 그대로 `String(64)` 라
# 자동 enum cast 함정(`UndefinedObjectError`)은 여전히 없지만, 값 집합이 DDL 에 박히므로
# enum 만 고치고 마이그레이션을 빠뜨리면 **프로덕션에서 세션 종료가 IntegrityError 로 실패**한다
# (화면 라벨 오염보다 나쁜 고장이다). 그래서 이 표현식을 손으로 적지 않고 enum 에서 생성하고,
# 마이그레이션에 박힌 사본은 `tests/test_migrations.py` 의 드리프트 감시가 enum 과 대조한다.
#
# `IS NULL OR` 는 가독성용이다 — 세 값 논리상 `NULL IN (...)` 은 NULL 이라 CHECK 를
# 통과하므로 없어도 동작은 같다. NULL 은 "마이그레이션 이전에 죽은 세션" 으로 정당하다.
_DEACTIVATION_REASON_CHECK = "deactivated_reason IS NULL OR deactivated_reason IN ({})".format(
    ", ".join(f"'{reason}'" for reason in SessionDeactivationReason)
)


class ExchangeAccount(SQLModel, table=True):
    __tablename__ = "exchange_accounts"
    __table_args__ = (
        Index("ix_exchange_accounts_user", "user_id"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    exchange: ExchangeName = Field(nullable=False)
    mode: ExchangeMode = Field(nullable=False)
    api_key_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    api_secret_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    # Sprint 7d: OKX requires a passphrase on top of key+secret. NULL for exchanges
    # that don't use passphrase (Bybit/Binance).
    passphrase_encrypted: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )
    label: str | None = Field(default=None, max_length=120, nullable=True)
    # BL-501 — Bybit query-api로 확인한 거래소 계정 식별자/권한. NULL은 아직 미확인이다.
    exchange_uid: str | None = Field(
        default=None,
        sa_column=Column(String(64), nullable=True),
    )
    read_only: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_strategy", "strategy_id"),
        Index("ix_orders_account_state", "exchange_account_id", "state"),
        Index(
            "uq_orders_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    exchange_account_id: UUID = Field(
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    symbol: str = Field(max_length=32, nullable=False)
    side: OrderSide = Field(nullable=False)
    type: OrderType = Field(nullable=False)
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    price: Decimal | None = Field(default=None, sa_column=Column(Numeric(18, 8), nullable=True))
    state: OrderState = Field(index=True, nullable=False)
    webhook_payload: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    idempotency_key: str | None = Field(default=None, max_length=200, nullable=True)
    exchange_order_id: str | None = Field(default=None, max_length=120, nullable=True)
    filled_price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # autoplan Eng E7: CCXT partial fill (filled < quantity) 지원. MDD evaluator가 참조.
    filled_quantity: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    realized_pnl: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # MP-2 — realized_pnl 출처 마커. NULL = pine_v2 추정값, 값 있음 = 거래소 확정(closedPnl).
    realized_pnl_synced_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    # autoplan Eng E2: same-key + different-body 충돌 감지용 payload hash (SHA-256 bytes).
    idempotency_payload_hash: bytes | None = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    # Sprint 7a: Bybit Futures 레버리지/마진 모드. Spot 경로는 NULL.
    leverage: int | None = Field(default=None, nullable=True)
    margin_mode: str | None = Field(default=None, max_length=16, nullable=True)
    # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브.
    # ADD COLUMN(alembic 20260626_0001). 전부 default None/False = 기존 entry 회귀.
    # reduce_only: close 주문 over-fill 방지 (반대편 시장청산이 reduceOnly 없으면 over-fill/반전 위험).
    reduce_only: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    # trigger_price: standalone 트리거(조건부) 주문 트리거가 (SL/Trail trigger market).
    trigger_price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # trigger_by: 트리거 가격 기준 (Bybit MarkPrice/IndexPrice/LastPrice).
    trigger_by: str | None = Field(default=None, max_length=16, nullable=True)
    # take_profit / stop_loss: entry attach bracket TP/SL 트리거가.
    take_profit: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    stop_loss: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # Wave 2 (TP/SL placement) — ADD COLUMN(alembic 20260626_0002). 전부 default None 회귀.
    # trigger_direction: Bybit v5 triggerDirection(1=가격 RISE 시 트리거, 2=FALL 시).
    #   standalone 트리거 주문(SL/Trail) 방향. exit_order_mapping.trigger_direction_for 계산.
    trigger_direction: int | None = Field(default=None, nullable=True)
    # oco_group_id: OCO 형제 추적용 app-side 식별자(거래소 미주입). sibling-cancel 오케스트레이션이
    #   DB 조회용으로 사용(Wave 2 deferred). 같은 entry 의 TP/SL leg 가 동일 값 공유.
    oco_group_id: str | None = Field(default=None, max_length=64, nullable=True)
    # trailing_stop: Bybit native trailingStop(quote 거리). contract 전용 라이브 param.
    trailing_stop: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    # Sprint 23 BL-102 — dispatch 시점 (exchange, mode, has_leverage) snapshot.
    # _async_execute / _async_fetch_order_status 가 본 snapshot 우선 사용.
    # nullable: legacy row (Sprint 23 이전 생성) 는 NULL → 기존 fallback 동작.
    # schema: {"exchange": "bybit", "mode": "demo", "has_leverage": false}
    # codex G.0 P1 #4: invalid JSON 시 _parse_order_dispatch_snapshot 가 graceful fallback.
    dispatch_snapshot: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    submitted_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    # NOTE: terminal timestamp — repository.transition_to_{filled,rejected,cancelled}가
    # 모두 이 컬럼에 기록한다. "filled"라는 이름은 오래된 의미 잔재. 향후 analytics가
    # rejected/cancelled 시점을 따로 쓸 이유가 생기면 terminal_at으로 rename 고려.
    filled_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class KillSwitchEvent(SQLModel, table=True):
    __tablename__ = "kill_switch_events"
    __table_args__ = (
        CheckConstraint(
            "(trigger_type = 'cumulative_loss' AND strategy_id IS NOT NULL AND exchange_account_id IS NULL) "
            "OR (trigger_type IN ('daily_loss','api_error') "
            "    AND exchange_account_id IS NOT NULL AND strategy_id IS NULL)",
            name="ck_kill_switch_events_trigger_scope",
        ),
        Index(
            "ix_kill_switch_events_active_strategy",
            "strategy_id",
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index(
            "ix_kill_switch_events_active_account",
            "exchange_account_id",
            postgresql_where=text("resolved_at IS NULL"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trigger_type: KillSwitchTriggerType = Field(nullable=False)
    strategy_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    exchange_account_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    trigger_value: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    threshold: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    triggered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    resolved_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    resolution_note: str | None = Field(default=None, max_length=500, nullable=True)


class FundingRate(SQLModel, table=True):
    """거래소 funding rate 기록 — 선물 포지션 PnL 보정용.

    8시간마다 정산되는 Bybit/OKX USDT Perpetual funding rate를 저장.
    Alembic: 20260421_0001_add_funding_rates_table.py
    """
    __tablename__ = "funding_rates"
    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "funding_timestamp", name="uq_funding_rates_exchange_symbol_ts"),
        Index("ix_funding_rates_exchange_symbol", "exchange", "symbol"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    symbol: str = Field(max_length=32, nullable=False)
    exchange: ExchangeName = Field(nullable=False)
    funding_rate: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    funding_timestamp: datetime = Field(
        sa_column=Column(AwareDateTime(), nullable=False)
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )


class WebhookSecret(SQLModel, table=True):
    __tablename__ = "webhook_secrets"
    __table_args__ = (
        Index("ix_webhook_secrets_strategy_active", "strategy_id", "revoked_at"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    # /cso CSO-1: EncryptionService(MultiFernet)로 암호화 저장. 평문 TEXT 금지.
    # Sprint 6 spec §8 Open Item 1 공식 해소 — DB leak = webhook 위조 방지.
    secret_encrypted: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )


# ── Sprint 26: Live Signal Auto-Trading ────────────────────────────────────


class LiveSignalSession(SQLModel, table=True):
    """Sprint 26 — Pine strategy 의 자동 evaluate + broker 발주 session.

    한 사용자 ≤ 5건 active. (user_id, strategy_id, exchange_account_id, symbol)
    partial unique index — `is_active=true` 인 row 만 unique (deactivate 후 재INSERT 가능).

    bar_claim_token: try_claim_bar 의 advisory token (codex G.0 P2 #3).
    last_evaluated_bar_time: CAS 기반 race-safe 평가 (1분 Beat 가 같은 bar 두 번 평가 차단).
    """

    __tablename__ = "live_signal_sessions"
    __table_args__ = (
        # BL-571 — 값 집합을 원장이 직접 거절한다. 표현식 근거는 `_DEACTIVATION_REASON_CHECK`.
        CheckConstraint(
            _DEACTIVATION_REASON_CHECK,
            name="ck_live_signal_sessions_deactivated_reason",
        ),
        Index("ix_live_sessions_user_active", "user_id", "is_active"),
        Index(
            "ix_live_sessions_active_due",
            "is_active",
            "last_evaluated_bar_time",
            postgresql_where=text("is_active = true"),
        ),
        # codex G.0 P2 #2: partial unique index — is_active=true 인 row 만 unique
        Index(
            "uq_live_sessions_active_unique",
            "user_id",
            "strategy_id",
            "exchange_account_id",
            "symbol",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            "user_id",
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    strategy_id: UUID = Field(
        sa_column=Column(
            "strategy_id",
            ForeignKey("strategies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    exchange_account_id: UUID = Field(
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    symbol: str = Field(max_length=32, nullable=False)
    # Sprint 26 Phase D fix — Alembic 이 String(8) 로 컬럼 생성. SQLAlchemy 가 자동
    # PG enum cast (`$N::livesignalinterval`) 시도해 UndefinedObjectError 발생하므로
    # 명시적 String 컬럼 + Python-level StrEnum 으로 round-trip.
    # ★BL-453 — 새 세션이 재조회한 행은 plain str 로 온다(재캐스팅 없음).
    # `.value`/`.name` 금지, `==`/`!=`/`str()` 만 쓸 것.
    interval: LiveSignalInterval = Field(sa_column=Column("interval", String(8), nullable=False))
    is_active: bool = Field(default=True)
    last_evaluated_bar_time: datetime | None = Field(
        default=None,
        sa_column=Column(AwareDateTime(), nullable=True),
    )
    bar_claim_token: UUID | None = Field(default=None)
    # 활성 레거시 세션은 실제 시작 잔고를 알 수 없다. NULL은 진실의 부재이며 소비 측이 fail-closed한다.
    equity_baseline_usdt: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )
    deactivated_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    # BL-484 — 종료 사유. 값 집합은 `SessionDeactivationReason` 이 정본이다.
    # NULL 은 "마이그레이션 이전에 죽은 세션" = 사유 부재이며, 소비 측은 이를 감추지 않고
    # "사유 미기록" 으로 읽는다(0 이나 빈 문자열로 위장하지 않는다).
    deactivated_reason: str | None = Field(
        default=None, sa_column=Column(String(64), nullable=True)
    )


class LiveSignalState(SQLModel, table=True):
    """Sprint 26 — Live Signal session 의 캐시/UI state.

    Option B (warmup replay) 채택 — 매 evaluate 마다 run_historical 재실행이
    source-of-truth. 이 테이블은 (a) 마지막 strategy_state_report 캐시 (UI 표시용)
    + (b) 누적 통계 (total_closed_trades / total_realized_pnl). 1:1 with session.

    schema_version: 향후 schema migration 안전성 (codex G.0 P3 #2).
    """

    __tablename__ = "live_signal_states"
    __table_args__ = ({"schema": "trading"},)

    session_id: UUID = Field(
        sa_column=Column(
            "session_id",
            ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    schema_version: int = Field(default=1)
    last_strategy_state_report: dict[str, object] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    total_closed_trades: int = Field(default=0)
    total_realized_pnl: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(18, 8), nullable=False, server_default=text("0")),
    )
    # Sprint 28 Slice 3 (BL-140b) — cumulative realized PnL timeseries.
    # 형식: [{"timestamp_ms": 1700000000000, "cumulative_pnl": "0.123"}, ...]
    # ASC sorted by timestamp_ms. Decimal-first 합산 (Sprint 4 D8) 영구 규칙 적용.
    # nullable=True (legacy row 호환), server_default '[]' (신규 row).
    equity_curve: list[dict[str, object]] | None = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True, server_default=text("'[]'::jsonb")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class LiveSignalEvent(SQLModel, table=True):
    """Sprint 26 — Transactional outbox (codex G.0 P1 #3).

    eval task 가 같은 트랜잭션에서 events INSERT + state upsert + session.last_evaluated
    update + commit. dispatch_live_signal_event_task (별도 task) 가 status=pending event 를
    OrderService.execute. broker 발주 후 mark_dispatched / mark_failed.

    UNIQUE (session_id, bar_time, sequence_no, action, trade_id) — codex G.0 P2 #5
    sequence_no idempotency. 같은 evaluate 가 두 번 fire 해도 INSERT 1번만.

    partial pending index — list_pending 빠른 조회.
    """

    __tablename__ = "live_signal_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "bar_time",
            "sequence_no",
            "action",
            "trade_id",
            name="uq_live_signal_events_idempotency",
        ),
        Index("ix_live_signal_events_session_bar", "session_id", "bar_time"),
        Index(
            "ix_live_signal_events_pending",
            "status",
            postgresql_where=text("status = 'pending'"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(
        sa_column=Column(
            "session_id",
            ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    bar_time: datetime = Field(sa_column=Column(AwareDateTime(), nullable=False))
    sequence_no: int = Field(nullable=False)
    action: str = Field(max_length=16, nullable=False)  # "entry" | "close"
    direction: str = Field(max_length=8, nullable=False)  # "long" | "short"
    trade_id: str = Field(max_length=64, nullable=False)
    qty: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    comment: str = Field(default="", max_length=200)
    # MP-1 — close 이벤트의 청산 realized PnL (event-loop 계산). dispatch task 가
    # Order.realized_pnl 로 전파 → kill-switch 손실 평가기가 SUM 하여 작동. entry 는 None.
    realized_pnl: Decimal | None = Field(
        default=None, sa_column=Column("realized_pnl", Numeric(18, 8), nullable=True)
    )
    # Phase 3 — entry signal 의 exit 레벨 (event-loop fold). dispatch task 가
    # OrderRequest bracket(take_profit/stop_loss) + trailing follow-on 으로 전파.
    # ADD COLUMN(alembic 20260627_0001). entry 만 set, close/회귀 전략은 None.
    take_profit: Decimal | None = Field(
        default=None, sa_column=Column("take_profit", Numeric(18, 8), nullable=True)
    )
    stop_loss: Decimal | None = Field(
        default=None, sa_column=Column("stop_loss", Numeric(18, 8), nullable=True)
    )
    trailing_stop: Decimal | None = Field(
        default=None, sa_column=Column("trailing_stop", Numeric(18, 8), nullable=True)
    )
    # Sprint 26 Phase D fix — interval 과 동일 사유 (PG enum 미생성, String(16) 컬럼).
    # ★BL-453 — 재조회 시 plain str. `.value`/`.name` 금지, `==`/`!=`/`str()` 만.
    status: LiveSignalEventStatus = Field(
        default=LiveSignalEventStatus.pending,
        sa_column=Column("status", String(16), nullable=False, server_default="pending"),
    )
    order_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "order_id",
            ForeignKey("trading.orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    dispatched_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )


class AlertRule(SQLModel, table=True):
    """Live Signal 세션의 손실한도·워치독 알림 규칙."""

    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint(
            "(rule_type = 'loss_limit' AND threshold_percent IS NOT NULL) "
            "OR (rule_type = 'watchdog' AND threshold_percent IS NULL)",
            name="ck_alert_rules_type_threshold",
        ),
        Index("ix_alert_rules_session_active", "session_id", "is_active"),
        Index(
            "uq_alert_rules_active_type",
            "session_id",
            "rule_type",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(
        sa_column=Column(
            "session_id",
            ForeignKey("trading.live_signal_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    # LiveSignalInterval 과 같은 String + StrEnum 계약. PG enum 생성 금지.
    # ★BL-453 — 재조회 시 plain str. `.value`/`.name` 금지, `==`/`!=`/`str()` 만.
    rule_type: AlertRuleType = Field(sa_column=Column("rule_type", String(32), nullable=False))
    threshold_percent: Decimal | None = Field(
        default=None,
        sa_column=Column("threshold_percent", Numeric(18, 8), nullable=True),
    )
    # ★BL-453 — 재조회 시 plain str. `.value`/`.name` 금지, `==`/`!=`/`str()` 만.
    channel: AlertChannel = Field(
        sa_column=Column("channel", String(16), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("true")),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class ExitClassification(StrEnum):
    """거래소 청산 기록의 출처 분류. 값은 VARCHAR 로 저장한다(DB enum 미사용)."""

    ours = "ours"
    bracket_tp = "bracket_tp"
    bracket_sl = "bracket_sl"
    trailing = "trailing"
    liquidation = "liquidation"
    external_manual = "external_manual"
    unknown = "unknown"


class ExitAttribution(StrEnum):
    """이 청산 손익을 어느 전략에 귀속할 수 있는지의 확신 등급."""

    exact = "exact"
    inferred = "inferred"
    none = "none"


class ExchangeExit(SQLModel, table=True):
    __tablename__ = "exchange_exits"
    __table_args__ = (
        Index("uq_exchange_exits_row", "exchange_account_id", "row_hash", unique=True),
        Index("ix_exchange_exits_account_created", "exchange_account_id", "exchange_created_at"),
        Index("ix_exchange_exits_classification", "classification"),
        {"schema": "trading"},
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    exchange_account_id: UUID = Field(
        sa_column=Column(
            "exchange_account_id",
            ForeignKey("trading.exchange_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    exchange_order_id: str = Field(sa_column=Column(String(120), nullable=False))
    row_hash: str = Field(sa_column=Column(String(64), nullable=False))
    symbol: str = Field(sa_column=Column(String(32), nullable=False))
    # ccxt 는 closed-pnl 행의 side 를 뒤집으므로(Buy→short) 여기에는 거래소 원본 info.side 를 그대로 넣는다.
    side: str = Field(sa_column=Column(String(8), nullable=False))
    closed_pnl: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    closed_size: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    avg_entry_price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    avg_exit_price: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(18, 8), nullable=True)
    )
    exchange_created_at: datetime = Field(sa_column=Column(AwareDateTime(), nullable=False))
    exchange_updated_at: datetime | None = Field(
        default=None, sa_column=Column(AwareDateTime(), nullable=True)
    )
    # ★BL-453 — 재조회 시 plain str. `.value`/`.name` 금지, `==`/`!=`/`str()` 만.
    # dogfood 에서 실제로 `_alert_new_exchange_exits` 가 이 경로로 매 사이클 죽었다.
    classification: ExitClassification = Field(
        sa_column=Column("classification", String(24), nullable=False)
    )
    create_type: str | None = Field(default=None, sa_column=Column(String(32), nullable=True))
    stop_order_type: str | None = Field(
        default=None, sa_column=Column(String(32), nullable=True)
    )
    order_link_id: str | None = Field(default=None, sa_column=Column(String(120), nullable=True))
    matched_order_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "matched_order_id",
            ForeignKey("trading.orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    attributed_strategy_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "attributed_strategy_id",
            ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # ★BL-453 — 재조회 시 plain str. `.value`/`.name` 금지, `==`/`!=`/`str()` 만.
    attribution_confidence: ExitAttribution = Field(
        sa_column=Column("attribution_confidence", String(16), nullable=False)
    )
    # none_as_null=True 로 Python None 을 SQL NULL 로 보존한다. 기본 JSONB 는 JSONB 'null'을
    # 저장해 IS NULL 술어가 무력해지는 webhook_payload 함정을 반복하지 않는다.
    raw: dict[str, object] = Field(
        sa_column=Column(postgresql.JSONB(none_as_null=True), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(AwareDateTime(), nullable=False, server_default=text("NOW()")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            AwareDateTime(),
            nullable=False,
            server_default=text("NOW()"),
            onupdate=lambda: datetime.now(UTC),
        ),
    )

    @staticmethod
    def compute_row_hash(
        order_id: object | None,
        created_time: object | None,
        updated_time: object | None,
        closed_size: object | None,
        closed_pnl: object | None,
        avg_entry_price: object | None,
        avg_exit_price: object | None,
        cum_exit_value: object | None,
    ) -> str:
        """같은 창을 다시 조회해도 같은 행은 같은 해시를 얻어 upsert 가 멱등해진다.

        내용이 완전히 동일한 두 행은 하나로 합쳐지는데, 이는 구분 불가능한 행이므로 허용한다.

        ★호출자 계약 — 값은 반드시 **거래소 원본 문자열**을 그대로 넘긴다. 해시는 값이 아니라
        표현에 민감해서(`"0.10"` 과 `Decimal("0.1")` 은 서로 다른 digest) 파싱된 Decimal 을
        넘기면 같은 행이 매 주기 새 행으로 적재된다.
        `order_id` 는 비어 있으면 안 된다 — 전 필드가 비면 해시가 한 값으로 축퇴해
        서로 다른 행이 UNIQUE 에 흡수된다.
        """
        if order_id is None or str(order_id) == "":
            raise ValueError("row hash requires a non-empty exchange order id")
        values = (
            order_id,
            created_time,
            updated_time,
            closed_size,
            closed_pnl,
            avg_entry_price,
            avg_exit_price,
            cum_exit_value,
        )
        # 구분자는 거래소 값에 나타날 수 없는 제어문자를 쓴다. 인쇄 가능한 구분자는
        # 값 안에 섞이면 인접 필드 경계를 옮겨 서로 다른 행이 같은 해시를 얻는다.
        # ★결측은 None 과 "" 를 반드시 같게 정규화한다. Bybit 이 한 주기엔 빈 문자열을,
        # 다른 주기엔 키 자체를 생략하면 같은 행이 두 해시로 갈려 UNIQUE 를 통과하고,
        # aggregate_closed_pnl 이 두 번 합산해 realized_pnl 이 실제의 2배로 백필된다.
        payload = "\x1f".join(
            "\x00" if value is None or str(value) == "" else str(value) for value in values
        )
        return hashlib.sha256(payload.encode()).hexdigest()
