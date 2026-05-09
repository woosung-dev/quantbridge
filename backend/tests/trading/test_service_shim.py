# BL-203 service.py 5 service + 2 Protocol 분할 후 shim re-export 하위호환 검증

from __future__ import annotations


def test_legacy_path_imports_5_services_and_2_protocols() -> None:
    """기존 path (src.trading.service) 에서 5 service + 2 Protocol 모두 import 가능."""
    from src.trading.service import (
        ExchangeAccountService,
        LiveSignalSessionService,
        OrderDispatcher,
        OrderService,
        StrategySessionsPort,
        WebhookSecretService,
    )

    # 각 class 가 실제 class object 인지 확인 (shim 이 올바른 객체를 re-export)
    assert isinstance(ExchangeAccountService, type)
    assert isinstance(WebhookSecretService, type)
    assert isinstance(OrderService, type)
    assert isinstance(LiveSignalSessionService, type)
    # Protocol 도 type instance (typing.Protocol 은 metaclass _ProtocolMeta)
    assert isinstance(OrderDispatcher, type)
    assert isinstance(StrategySessionsPort, type)


def test_new_package_path_imports_5_services_and_2_protocols() -> None:
    """신규 path (src.trading.services) 에서 5 service + 2 Protocol 모두 import 가능."""
    from src.trading.services import (
        ExchangeAccountService,
        LiveSignalSessionService,
        OrderDispatcher,
        OrderService,
        StrategySessionsPort,
        WebhookSecretService,
    )

    assert isinstance(ExchangeAccountService, type)
    assert isinstance(WebhookSecretService, type)
    assert isinstance(OrderService, type)
    assert isinstance(LiveSignalSessionService, type)
    assert isinstance(OrderDispatcher, type)
    assert isinstance(StrategySessionsPort, type)


def test_individual_module_paths_import_correct_class() -> None:
    """신규 path 의 individual file 에서 각 class / Protocol 직접 import 가능."""
    from src.trading.services.account_service import ExchangeAccountService
    from src.trading.services.live_session_service import LiveSignalSessionService
    from src.trading.services.order_service import OrderService
    from src.trading.services.protocols import OrderDispatcher, StrategySessionsPort
    from src.trading.services.webhook_secret_service import WebhookSecretService

    assert isinstance(ExchangeAccountService, type)
    assert isinstance(WebhookSecretService, type)
    assert isinstance(OrderService, type)
    assert isinstance(LiveSignalSessionService, type)
    assert isinstance(OrderDispatcher, type)
    assert isinstance(StrategySessionsPort, type)


def test_legacy_and_new_path_are_same_object() -> None:
    """shim 이 alias re-export — 양쪽 path 가 동일 class object 반환 (object identity).

    BL-200 SSOT pattern (Sprint 47) — `is` identity 검증.
    """
    from src.trading.service import OrderService as LegacyOrderService
    from src.trading.services import OrderService as NewOrderService

    assert LegacyOrderService is NewOrderService

    from src.trading.service import (
        ExchangeAccountService as LegacyExchangeAccountService,
    )
    from src.trading.services import (
        ExchangeAccountService as NewExchangeAccountService,
    )

    assert LegacyExchangeAccountService is NewExchangeAccountService

    from src.trading.service import OrderDispatcher as LegacyOrderDispatcher
    from src.trading.services import OrderDispatcher as NewOrderDispatcher

    assert LegacyOrderDispatcher is NewOrderDispatcher

    from src.trading.service import StrategySessionsPort as LegacyStrategySessionsPort
    from src.trading.services import StrategySessionsPort as NewStrategySessionsPort

    assert LegacyStrategySessionsPort is NewStrategySessionsPort


def test_no_module_level_state_in_live_session_service() -> None:
    """codex Fix #4 — `services/live_session_service.py` 의 module-level Celery prefork-unsafe state 0.

    BL-084 §11.2 audit gate — module-level `_engine`, `_provider`, `_redis_lock`,
    `_async_lock`, `create_async_engine()` 캐시 등이 fork 후 stale 가능. 모든 무거운
    객체는 함수 내부 lazy init 으로 강제.
    """
    from src.trading.services import live_session_service

    forbidden_attrs = {
        "_engine",
        "_provider",
        "_redis_lock",
        "_async_lock",
        "_session_maker",
        "_db_engine",
        "engine",  # bare engine module attribute (cls 안 self._engine 은 OK)
    }
    actual = set(vars(live_session_service).keys())
    leaked = forbidden_attrs & actual
    assert not leaked, (
        f"live_session_service module-level state 누설 — Celery prefork-unsafe. "
        f"발견: {leaked}. 함수 내부 lazy init 으로 이동 필요."
    )
