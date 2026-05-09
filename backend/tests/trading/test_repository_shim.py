# BL-204 repository.py 6-class god file 분할 후 shim re-export 하위호환 검증

from __future__ import annotations


def test_legacy_path_imports_all_six_classes() -> None:
    """기존 path (src.trading.repository) 에서 6 class 모두 import 가능."""
    from src.trading.repository import (
        ExchangeAccountRepository,
        KillSwitchEventRepository,
        LiveSignalEventRepository,
        LiveSignalSessionRepository,
        OrderRepository,
        WebhookSecretRepository,
    )

    # 각 class 가 실제 class 객체인지 확인 (shim 이 올바른 객체를 re-export)
    assert isinstance(ExchangeAccountRepository, type)
    assert isinstance(OrderRepository, type)
    assert isinstance(KillSwitchEventRepository, type)
    assert isinstance(WebhookSecretRepository, type)
    assert isinstance(LiveSignalSessionRepository, type)
    assert isinstance(LiveSignalEventRepository, type)


def test_new_package_path_imports_all_six_classes() -> None:
    """신규 path (src.trading.repositories) 에서 6 class 모두 import 가능."""
    from src.trading.repositories import (
        ExchangeAccountRepository,
        KillSwitchEventRepository,
        LiveSignalEventRepository,
        LiveSignalSessionRepository,
        OrderRepository,
        WebhookSecretRepository,
    )

    assert isinstance(ExchangeAccountRepository, type)
    assert isinstance(OrderRepository, type)
    assert isinstance(KillSwitchEventRepository, type)
    assert isinstance(WebhookSecretRepository, type)
    assert isinstance(LiveSignalSessionRepository, type)
    assert isinstance(LiveSignalEventRepository, type)


def test_individual_module_paths_import_correct_class() -> None:
    """신규 path 의 individual file 에서 각 class 직접 import 가능."""
    from src.trading.repositories.exchange_account_repository import (
        ExchangeAccountRepository,
    )
    from src.trading.repositories.kill_switch_event_repository import (
        KillSwitchEventRepository,
    )
    from src.trading.repositories.live_signal_event_repository import (
        LiveSignalEventRepository,
    )
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.repositories.webhook_secret_repository import (
        WebhookSecretRepository,
    )

    assert isinstance(ExchangeAccountRepository, type)
    assert isinstance(OrderRepository, type)
    assert isinstance(KillSwitchEventRepository, type)
    assert isinstance(WebhookSecretRepository, type)
    assert isinstance(LiveSignalSessionRepository, type)
    assert isinstance(LiveSignalEventRepository, type)


def test_legacy_and_new_path_are_same_object() -> None:
    """shim 이 alias re-export — 양쪽 path 가 동일 class object 반환 (object identity).

    BL-200 SSOT pattern (Sprint 47) — `is` identity 검증.
    """
    from src.trading.repositories import OrderRepository as NewOrderRepo
    from src.trading.repository import OrderRepository as LegacyOrderRepo

    assert LegacyOrderRepo is NewOrderRepo

    from src.trading.repositories import (
        ExchangeAccountRepository as NewExchangeAccountRepo,
    )
    from src.trading.repository import (
        ExchangeAccountRepository as LegacyExchangeAccountRepo,
    )

    assert LegacyExchangeAccountRepo is NewExchangeAccountRepo


def test_individual_module_and_package_are_same_object() -> None:
    """package shim 과 individual file 이 같은 class object 를 가리킴."""
    from src.trading.repositories import OrderRepository as PackageOrderRepo
    from src.trading.repositories.order_repository import (
        OrderRepository as ModuleOrderRepo,
    )

    assert PackageOrderRepo is ModuleOrderRepo
