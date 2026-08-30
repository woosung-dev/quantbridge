"""WebSocket Celery task의 종료·lease 런타임 분기를 외부 I/O 없이 고정한다."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest


def _install_exchange_account_repository(
    monkeypatch: pytest.MonkeyPatch,
    *,
    account: object | None = None,
    accounts: list[object] | None = None,
) -> None:
    """task 조립이 repository 경계를 통해 계정을 읽는 계약용 fake."""
    repository_module = import_module("src.trading.repositories.exchange_account_repository")

    class _ExchangeAccountRepository:
        def __init__(self, _session: object) -> None:
            pass

        async def get_by_id(self, _account_id: UUID) -> object | None:
            return account

        async def list_by_exchange(self, _exchange: object) -> list[object]:
            return accounts or []

        async def list_by_exchange_uid(self, _exchange_uid: str) -> list[object]:
            return []

    monkeypatch.setattr(repository_module, "ExchangeAccountRepository", _ExchangeAccountRepository)


@pytest.mark.parametrize(
    ("task_name", "coroutine_name", "expected"),
    [
        ("run_bybit_private_stream", "_run_async", {"status": "private"}),
        ("run_bybit_public_ticker_stream", "_run_public_ticker_async", {"status": "public"}),
        ("reconcile_ws_streams", "_reconcile_async", {"status": "reconciled"}),
    ],
)
def test_stream_task_wrappers_delegate_one_coroutine_to_persistent_worker_loop(
    monkeypatch: pytest.MonkeyPatch,
    task_name: str,
    coroutine_name: str,
    expected: dict[str, str],
) -> None:
    """sync Celery wrapper는 asyncio.run이 아니라 영속 worker loop에 단 한 번 위임한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    worker_loop_module = import_module("src.tasks._worker_loop")
    async_entry = AsyncMock()
    received: list[object] = []

    def run_in_worker_loop(coroutine: object) -> dict[str, str]:
        received.append(coroutine)
        coroutine.close()  # type: ignore[union-attr]
        return expected

    monkeypatch.setattr(websocket_module, coroutine_name, async_entry)
    monkeypatch.setattr(worker_loop_module, "run_in_worker_loop", run_in_worker_loop)

    if task_name == "run_bybit_private_stream":
        result = getattr(websocket_module, task_name).run("account-1")
        async_entry.assert_called_once_with("account-1")
    else:
        result = getattr(websocket_module, task_name).run()
        async_entry.assert_called_once_with()

    assert result is expected
    assert len(received) == 1
    assert asyncio.iscoroutine(received[0])


class _Lease:
    """외부 Redis 없이 async lease 진입·해제와 lost_event 전달을 기록한다."""

    def __init__(self) -> None:
        self.lost_event = asyncio.Event()
        self.entered = 0
        self.exited = 0

    async def __aenter__(self) -> _Lease:
        self.entered += 1
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.exited += 1


@pytest.mark.asyncio
async def test_private_stream_enters_lease_and_passes_heartbeat_loss_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """private task는 circuit 통과 뒤 lease 안에서 같은 lost_event로 stream을 실행한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    circuit_breaker_module = import_module("src.tasks._ws_circuit_breaker")
    lease_module = import_module("src.tasks._ws_lease")
    lease = _Lease()
    stream_main = AsyncMock(return_value={"status": "completed", "account_id": "account-1"})
    acquire_ws_lease = AsyncMock(return_value=lease)

    monkeypatch.setattr(circuit_breaker_module, "is_circuit_open", AsyncMock(return_value=False))
    monkeypatch.setattr(lease_module, "acquire_ws_lease", acquire_ws_lease)
    monkeypatch.setattr(websocket_module, "_stream_main", stream_main)

    result = await websocket_module._run_async("account-1")

    assert result == {"status": "completed", "account_id": "account-1"}
    acquire_ws_lease.assert_awaited_once_with("account-1")
    stream_main.assert_awaited_once_with("account-1", lease_lost_event=lease.lost_event)
    assert lease.entered == 1
    assert lease.exited == 1


@pytest.mark.asyncio
async def test_public_ticker_enters_dedicated_lease_and_passes_loss_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """public ticker task는 전용 lease 안에서 heartbeat loss event를 stream에 전달한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    lease_module = import_module("src.tasks._ws_lease")
    lease = _Lease()
    stream_main = AsyncMock(return_value={"status": "completed"})
    acquire_ws_lease = AsyncMock(return_value=lease)

    monkeypatch.setattr(lease_module, "acquire_ws_lease", acquire_ws_lease)
    monkeypatch.setattr(websocket_module, "_public_ticker_stream_main", stream_main)

    result = await websocket_module._run_public_ticker_async()

    assert result == {"status": "completed"}
    acquire_ws_lease.assert_awaited_once_with(websocket_module._PUBLIC_TICKER_LEASE_ID)
    stream_main.assert_awaited_once_with(lease_lost_event=lease.lost_event)
    assert lease.entered == 1
    assert lease.exited == 1


@pytest.mark.asyncio
async def test_public_ticker_stream_completes_after_shutdown_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 종료 신호는 ticker stream 연결을 닫고 stop registry·engine을 함께 정리한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    public_stream_module = import_module("src.trading.websocket.bybit_public_stream")
    engine = MagicMock()
    engine.dispose = AsyncMock()

    class _StoppingPublicStream:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> _StoppingPublicStream:
            self.kwargs["stop_event"].set()
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    public_stream_factory = MagicMock(side_effect=_StoppingPublicStream)
    monkeypatch.setattr(websocket_module, "create_worker_engine_and_sm", lambda: (engine, object()))
    monkeypatch.setattr(
        websocket_module,
        "_list_active_ticker_symbols",
        AsyncMock(return_value={"BTCUSDT", "ETHUSDT"}),
    )
    monkeypatch.setattr(public_stream_module, "BybitPublicTickerStream", public_stream_factory)

    result = await websocket_module._public_ticker_stream_main()

    assert result == {"status": "completed"}
    assert public_stream_factory.call_args.kwargs["symbols"] == {"BTCUSDT", "ETHUSDT"}
    engine.dispose.assert_awaited_once_with()
    with websocket_module._STOP_EVENTS_LOCK:
        assert websocket_module._PUBLIC_TICKER_LEASE_ID not in websocket_module._STOP_EVENTS


@pytest.mark.asyncio
async def test_private_stream_builds_handlers_and_returns_reconnect_count_on_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bybit 계정 stream은 복호화·handler 조립 뒤 shutdown signal로 정상 종료한다."""
    from src.trading.models import ExchangeMode, ExchangeName

    websocket_module = import_module("src.tasks.websocket_task")
    encryption_module = import_module("src.trading.encryption")
    redis_module = import_module("src.common.redis_client")
    trading_websocket_module = import_module("src.trading.websocket")
    reconcile_fetcher_module = import_module("src.trading.websocket.reconcile_fetcher")
    account_id = str(uuid4())
    account_uuid = UUID(account_id)
    user_id = uuid4()
    account = SimpleNamespace(
        exchange=ExchangeName.bybit,
        api_key_encrypted=b"encrypted-key",
        api_secret_encrypted=b"encrypted-secret",
        mode=ExchangeMode.demo,
        user_id=user_id,
    )
    session = MagicMock()
    engine = MagicMock()
    engine.dispose = AsyncMock()
    settings = SimpleNamespace(trading_encryption_keys=["test-key"])
    crypto = MagicMock()
    crypto.decrypt.side_effect = ["api-key", "api-secret"]

    @asynccontextmanager
    async def session_context():
        yield session

    class _SessionMaker:
        def __call__(self):
            return session_context()

    class _StoppingPrivateStream:
        reconnect_count = 4
        # BL-837 — 페이크도 실물 인터페이스를 모델해야 한다. 정상 종료는 crash 가 아니다.
        supervisor_error = None

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> _StoppingPrivateStream:
            self.kwargs["stop_event"].set()
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    state_handler = MagicMock(return_value=object())
    position_handler = MagicMock(return_value=object())
    topic_router = MagicMock(return_value=object())
    reconcile_fetcher = MagicMock(return_value=object())
    reconciler = MagicMock(return_value=object())
    private_stream_factory = MagicMock(side_effect=_StoppingPrivateStream)
    redis_pool = object()

    monkeypatch.setattr(websocket_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        websocket_module, "create_worker_engine_and_sm", lambda: (engine, _SessionMaker())
    )
    monkeypatch.setattr(encryption_module, "EncryptionService", MagicMock(return_value=crypto))
    monkeypatch.setattr(redis_module, "get_redis_lock_pool", lambda: redis_pool)
    monkeypatch.setattr(trading_websocket_module, "StateHandler", state_handler)
    monkeypatch.setattr(trading_websocket_module, "PositionFanoutHandler", position_handler)
    monkeypatch.setattr(trading_websocket_module, "PrivateTopicRouter", topic_router)
    monkeypatch.setattr(trading_websocket_module, "Reconciler", reconciler)
    monkeypatch.setattr(trading_websocket_module, "BybitPrivateStream", private_stream_factory)
    monkeypatch.setattr(reconcile_fetcher_module, "BybitReconcileFetcher", reconcile_fetcher)
    _install_exchange_account_repository(monkeypatch, account=account)

    result = await websocket_module._stream_main(account_id)

    assert result == {"status": "completed", "account_id": account_id, "reconnect_count": 4}
    assert crypto.decrypt.call_args_list[0].args == (b"encrypted-key",)
    assert crypto.decrypt.call_args_list[1].args == (b"encrypted-secret",)
    state_handler.assert_called_once()
    assert callable(state_handler.call_args.args[0])
    position_handler.assert_called_once_with(ANY, redis_pool, str(user_id), account_uuid)
    topic_router.assert_called_once()
    reconciler.assert_called_once()
    assert callable(reconciler.call_args.args[0])
    reconcile_fetcher.assert_called_once_with(account=account, crypto=crypto)
    private_stream_kwargs = private_stream_factory.call_args.kwargs
    assert private_stream_kwargs["endpoint"] == websocket_module._BYBIT_DEMO_WS_ENDPOINT
    assert private_stream_kwargs["api_key"] == "api-key"
    assert private_stream_kwargs["api_secret"] == "api-secret"
    assert private_stream_kwargs["account_id"] == account_uuid
    assert private_stream_kwargs["topics"] == ("order", "position")
    engine.dispose.assert_awaited_once_with()
    with websocket_module._STOP_EVENTS_LOCK:
        assert account_id not in websocket_module._STOP_EVENTS


@pytest.mark.asyncio
async def test_reconcile_enqueues_only_inactive_private_and_public_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reconcile은 active lease는 건너뛰고 비활성 Bybit 계정·public ticker만 재등록한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    lease_module = import_module("src.tasks._ws_lease")
    repository_module = import_module("src.trading.repositories.live_signal_session_repository")
    from src.trading.models import ExchangeMode, ExchangeName

    first_account = SimpleNamespace(id=uuid4(), exchange=ExchangeName.bybit, mode=ExchangeMode.demo)
    second_account = SimpleNamespace(
        id=uuid4(), exchange=ExchangeName.bybit, mode=ExchangeMode.demo
    )
    legacy_live_account = SimpleNamespace(
        id=uuid4(), exchange=ExchangeName.bybit, mode=ExchangeMode.live
    )
    session = MagicMock()
    engine = MagicMock()
    engine.dispose = AsyncMock()

    @asynccontextmanager
    async def session_context():
        yield session

    class _SessionMaker:
        def __call__(self):
            return session_context()

    class _LiveSessionRepository:
        def __init__(self, received_session: object) -> None:
            assert received_session is session

        async def list_distinct_active_symbols(self) -> list[str]:
            return ["BTCUSDT"]

    is_lease_active = AsyncMock(side_effect=[True, False, False])
    private_delay = MagicMock()
    public_delay = MagicMock()
    monkeypatch.setattr(
        websocket_module, "create_worker_engine_and_sm", lambda: (engine, _SessionMaker())
    )
    monkeypatch.setattr(repository_module, "LiveSignalSessionRepository", _LiveSessionRepository)
    _install_exchange_account_repository(
        monkeypatch, accounts=[first_account, second_account, legacy_live_account]
    )
    monkeypatch.setattr(lease_module, "is_lease_active", is_lease_active)
    monkeypatch.setattr(websocket_module.run_bybit_private_stream, "delay", private_delay)
    monkeypatch.setattr(websocket_module.run_bybit_public_ticker_stream, "delay", public_delay)

    reconciled = await websocket_module._reconcile_async()

    first_id = str(first_account.id)
    second_id = str(second_account.id)
    assert reconciled == {
        "enqueued": [second_id],
        "skipped_active": [first_id],
        "total": 2,
        "public_ticker": "enqueued",
    }
    assert [args.args[0] for args in is_lease_active.await_args_list] == [
        first_id,
        second_id,
        websocket_module._PUBLIC_TICKER_LEASE_ID,
    ]
    private_delay.assert_called_once_with(second_id)
    assert str(legacy_live_account.id) not in reconciled["enqueued"]
    public_delay.assert_called_once_with()
    engine.dispose.assert_awaited_once_with()


def test_signal_all_stop_events_ignores_one_failed_loop() -> None:
    """한 stream loop의 cross-thread signal 실패는 다른 종료 훅을 중단하지 않는다."""
    websocket_module = import_module("src.tasks.websocket_task")
    failed_loop = MagicMock()
    failed_loop.call_soon_threadsafe.side_effect = RuntimeError("loop closed")
    event = asyncio.Event()

    with websocket_module._STOP_EVENTS_LOCK:
        websocket_module._STOP_EVENTS["failed-account"] = (failed_loop, event)
    try:
        assert websocket_module.signal_all_stop_events() == 0
        assert event.is_set() is False
    finally:
        with websocket_module._STOP_EVENTS_LOCK:
            websocket_module._STOP_EVENTS.pop("failed-account", None)


@pytest.mark.asyncio
async def test_public_ticker_first_connect_timeout_records_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """공개 ticker의 최초 연결 timeout은 circuit breaker 입력으로 변환한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    circuit_breaker_module = import_module("src.tasks._ws_circuit_breaker")
    public_stream_module = import_module("src.trading.websocket.bybit_public_stream")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    record_network_failure = AsyncMock(return_value=True)

    class _FirstConnectTimeoutStream:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _FirstConnectTimeoutStream:
            raise TimeoutError("first connection timed out")

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(websocket_module, "create_worker_engine_and_sm", lambda: (engine, object()))
    monkeypatch.setattr(
        websocket_module,
        "_list_active_ticker_symbols",
        AsyncMock(return_value={"BTCUSDT"}),
    )
    monkeypatch.setattr(circuit_breaker_module, "record_network_failure", record_network_failure)
    monkeypatch.setattr(public_stream_module, "BybitPublicTickerStream", _FirstConnectTimeoutStream)

    result = await websocket_module._public_ticker_stream_main()

    assert result == {"status": "first_connect_timeout", "circuit_opened": True}
    record_network_failure.assert_awaited_once_with(websocket_module._PUBLIC_TICKER_LEASE_ID)
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_lease_heartbeat_marks_lost_when_extend_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """heartbeat extend 실패는 split-brain 방지를 위해 lost_event를 set하고 끝낸다."""
    lease_module = import_module("src.tasks._ws_lease")
    lock = MagicMock()
    lock.extend = AsyncMock(return_value=False)
    lost_event = asyncio.Event()
    lease = lease_module.WsLease(lock, "account-1", ttl_ms=3, lost_event=lost_event)

    monkeypatch.setattr(lease_module.asyncio, "sleep", AsyncMock())

    await lease._heartbeat_loop()

    lock.extend.assert_awaited_once_with(3)
    assert lost_event.is_set()


@pytest.mark.asyncio
async def test_private_stream_circuit_open_skips_lease_and_records_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """열린 auth circuit은 lease·stream 진입 없이 metric과 info log만 남기고 종료한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    circuit_breaker_module = import_module("src.tasks._ws_circuit_breaker")
    metrics_module = import_module("src.common.metrics")
    logger = MagicMock()
    counter = MagicMock()
    stream_main = AsyncMock()

    monkeypatch.setattr(circuit_breaker_module, "is_circuit_open", AsyncMock(return_value=True))
    monkeypatch.setattr(metrics_module, "qb_ws_auth_circuit_total", counter)
    monkeypatch.setattr(websocket_module, "_stream_main", stream_main)
    monkeypatch.setattr(websocket_module, "logger", logger)

    result = await websocket_module._run_async("account-1")

    assert result == {"status": "circuit_open", "account_id": "account-1"}
    counter.labels.assert_called_once_with(outcome="skipped")
    counter.labels.return_value.inc.assert_called_once_with()
    stream_main.assert_not_awaited()
    logger.info.assert_called_once_with("ws_stream_circuit_open_skip account=%s", "account-1")


@pytest.mark.asyncio
async def test_public_ticker_duplicate_lease_records_metric_and_skips_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """public ticker lease 경쟁은 duplicate metric·log를 남기고 stream을 만들지 않는다."""
    websocket_module = import_module("src.tasks.websocket_task")
    lease_module = import_module("src.tasks._ws_lease")
    logger = MagicMock()
    counter = MagicMock()
    stream_main = AsyncMock()

    monkeypatch.setattr(lease_module, "acquire_ws_lease", AsyncMock(return_value=None))
    monkeypatch.setattr(websocket_module, "qb_ws_duplicate_enqueue_total", counter)
    monkeypatch.setattr(websocket_module, "_public_ticker_stream_main", stream_main)
    monkeypatch.setattr(websocket_module, "logger", logger)

    result = await websocket_module._run_public_ticker_async()

    assert result == {"status": "duplicate"}
    counter.inc.assert_called_once_with()
    stream_main.assert_not_awaited()
    logger.info.assert_called_once_with("ws_public_ticker_duplicate_skip")


@pytest.mark.asyncio
async def test_public_ticker_returns_no_symbols_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """활성 심볼 0건이면 연결·stop registry 등록 없이 engine을 정리한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    engine = MagicMock()
    engine.dispose = AsyncMock()

    monkeypatch.setattr(websocket_module, "create_worker_engine_and_sm", lambda: (engine, object()))
    monkeypatch.setattr(
        websocket_module, "_list_active_ticker_symbols", AsyncMock(return_value=set())
    )

    result = await websocket_module._public_ticker_stream_main()

    assert result == {"status": "no_symbols"}
    engine.dispose.assert_awaited_once_with()
    with websocket_module._STOP_EVENTS_LOCK:
        assert websocket_module._PUBLIC_TICKER_LEASE_ID not in websocket_module._STOP_EVENTS


@pytest.mark.asyncio
async def test_public_ticker_lease_loss_logs_and_closes_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """heartbeat lease 손실은 warning을 남기고 public ticker 연결·engine을 정리한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    public_stream_module = import_module("src.trading.websocket.bybit_public_stream")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    logger = MagicMock()
    lost_event = asyncio.Event()
    lost_event.set()

    class _PublicStream:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _PublicStream:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def update_symbols(self, _symbols: set[str]) -> None:
            raise AssertionError("lease loss must terminate before symbol refresh")

    monkeypatch.setattr(websocket_module, "create_worker_engine_and_sm", lambda: (engine, object()))
    monkeypatch.setattr(
        websocket_module,
        "_list_active_ticker_symbols",
        AsyncMock(return_value={"BTCUSDT"}),
    )
    monkeypatch.setattr(public_stream_module, "BybitPublicTickerStream", _PublicStream)
    monkeypatch.setattr(websocket_module, "logger", logger)

    result = await websocket_module._public_ticker_stream_main(lease_lost_event=lost_event)

    assert result == {"status": "lease_lost"}
    logger.warning.assert_called_once_with("ws_public_ticker_lease_lost_terminating")
    engine.dispose.assert_awaited_once_with()
    with websocket_module._STOP_EVENTS_LOCK:
        assert websocket_module._PUBLIC_TICKER_LEASE_ID not in websocket_module._STOP_EVENTS


@pytest.mark.asyncio
async def test_private_stream_missing_account_logs_error_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """삭제된 계정의 private stream 요청은 error log 뒤 engine을 정리하고 연결하지 않는다."""
    websocket_module = import_module("src.tasks.websocket_task")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    session = MagicMock()
    logger = MagicMock()

    @asynccontextmanager
    async def session_context():
        yield session

    class _SessionMaker:
        def __call__(self):
            return session_context()

    account_id = str(uuid4())
    monkeypatch.setattr(
        websocket_module,
        "create_worker_engine_and_sm",
        lambda: (engine, _SessionMaker()),
    )
    monkeypatch.setattr(websocket_module, "logger", logger)
    _install_exchange_account_repository(monkeypatch, account=None)

    result = await websocket_module._stream_main(account_id)

    assert result == {"status": "error", "reason": "account_not_found"}
    logger.error.assert_called_once_with("ws_stream_account_not_found account=%s", account_id)
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_private_stream_rejects_legacy_live_before_decrypt_or_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """보존된 live 계정은 private WS 자격증명 복호화·endpoint 선택 전에 차단한다."""
    from src.trading.exceptions import BybitDemoOnlyError
    from src.trading.models import ExchangeMode, ExchangeName

    websocket_module = import_module("src.tasks.websocket_task")
    encryption_module = import_module("src.trading.encryption")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    account_id = str(uuid4())
    account = SimpleNamespace(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.live,
        api_key_encrypted=b"encrypted-key",
        api_secret_encrypted=b"encrypted-secret",
    )

    @asynccontextmanager
    async def session_context():
        yield MagicMock()

    class _SessionMaker:
        def __call__(self):
            return session_context()

    crypto_cls = MagicMock()
    stream_factory = MagicMock()
    monkeypatch.setattr(
        websocket_module,
        "create_worker_engine_and_sm",
        lambda: (engine, _SessionMaker()),
    )
    monkeypatch.setattr(encryption_module, "EncryptionService", crypto_cls)
    monkeypatch.setattr("src.trading.websocket.BybitPrivateStream", stream_factory)
    _install_exchange_account_repository(monkeypatch, account=account)

    with pytest.raises(BybitDemoOnlyError):
        await websocket_module._stream_main(account_id)

    crypto_cls.assert_not_called()
    stream_factory.assert_not_called()
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_reconcile_zero_accounts_and_symbols_skips_all_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계정·활성 심볼이 모두 0건이면 lease 조회와 Celery enqueue 없이 종료한다."""
    websocket_module = import_module("src.tasks.websocket_task")
    repository_module = import_module("src.trading.repositories.live_signal_session_repository")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    session = MagicMock()
    private_delay = MagicMock()
    public_delay = MagicMock()

    @asynccontextmanager
    async def session_context():
        yield session

    class _SessionMaker:
        def __call__(self):
            return session_context()

    class _LiveSessionRepository:
        def __init__(self, received_session: object) -> None:
            assert received_session is session

        async def list_distinct_active_symbols(self) -> list[str]:
            return []

    monkeypatch.setattr(
        websocket_module,
        "create_worker_engine_and_sm",
        lambda: (engine, _SessionMaker()),
    )
    monkeypatch.setattr(repository_module, "LiveSignalSessionRepository", _LiveSessionRepository)
    _install_exchange_account_repository(monkeypatch, accounts=[])
    monkeypatch.setattr(websocket_module.run_bybit_private_stream, "delay", private_delay)
    monkeypatch.setattr(websocket_module.run_bybit_public_ticker_stream, "delay", public_delay)

    result = await websocket_module._reconcile_async()

    assert result == {
        "enqueued": [],
        "skipped_active": [],
        "total": 0,
        "public_ticker": "not_needed",
    }
    private_delay.assert_not_called()
    public_delay.assert_not_called()
    engine.dispose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_lease_heartbeat_exception_sets_lost_event_and_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis extend 예외는 heartbeat를 조용히 죽이지 않고 lost_event·warning으로 전환한다."""
    lease_module = import_module("src.tasks._ws_lease")
    lock = MagicMock()
    error = ConnectionError("redis disconnected")
    lock.extend = AsyncMock(side_effect=error)
    lost_event = asyncio.Event()
    logger = MagicMock()
    lease = lease_module.WsLease(lock, "account-1", ttl_ms=3, lost_event=lost_event)

    monkeypatch.setattr(lease_module.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(lease_module, "logger", logger)

    await lease._heartbeat_loop()

    lock.extend.assert_awaited_once_with(3)
    assert lost_event.is_set()
    logger.warning.assert_called_once_with(
        "ws_lease_extend_exception account=%s err=%r — lost_event set",
        "account-1",
        error,
    )


@pytest.mark.asyncio
async def test_private_stream_supervisor_crash_alerts_and_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[BL-837] supervisor 가 죽어서 깨어난 종료를 「정상 완료」로 보고하지 않는다.

    ★수리 전에는 이 경로 자체가 **도달 불가능**이었다 — supervisor 가 죽어도 `stop_event`
    를 아무도 set 하지 않아 `_stream_main` 이 영원히 대기했고, 그 사이 `async with lease:`
    가 lease 를 계속 갱신해 다른 워커의 인수까지 막았다.
    ★경보를 여기(task 층)에서 내는 이유 — `BybitAuthError` 선례와 같은 자리다. 스트림
    클래스는 `Settings` 를 안 쥐고 알림 책임도 안 진다.
    """
    from src.trading.models import ExchangeMode, ExchangeName

    websocket_module = import_module("src.tasks.websocket_task")
    encryption_module = import_module("src.trading.encryption")
    redis_module = import_module("src.common.redis_client")
    trading_websocket_module = import_module("src.trading.websocket")
    reconcile_fetcher_module = import_module("src.trading.websocket.reconcile_fetcher")

    account_id = str(uuid4())
    account = SimpleNamespace(
        exchange=ExchangeName.bybit,
        api_key_encrypted=b"encrypted-key",
        api_secret_encrypted=b"encrypted-secret",
        mode=ExchangeMode.demo,
        user_id=uuid4(),
    )
    engine = MagicMock()
    engine.dispose = AsyncMock()
    crypto = MagicMock()
    crypto.decrypt.side_effect = ["api-key", "api-secret"]
    boom = RuntimeError("bybit returned 403 on reconnect")

    @asynccontextmanager
    async def session_context():
        yield MagicMock()

    class _SessionMaker:
        def __call__(self):
            return session_context()

    class _CrashingPrivateStream:
        reconnect_count = 7
        # done-callback 이 하는 일과 같다 — 예외를 들고 stop_event 를 놓는다.
        supervisor_error = boom

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        async def __aenter__(self) -> _CrashingPrivateStream:
            self.kwargs["stop_event"].set()
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

    alert = AsyncMock(return_value=True)
    monkeypatch.setattr(websocket_module, "send_critical_alert", alert)
    monkeypatch.setattr(
        websocket_module, "get_settings", lambda: SimpleNamespace(trading_encryption_keys=["k"])
    )
    monkeypatch.setattr(
        websocket_module, "create_worker_engine_and_sm", lambda: (engine, _SessionMaker())
    )
    monkeypatch.setattr(encryption_module, "EncryptionService", MagicMock(return_value=crypto))
    monkeypatch.setattr(redis_module, "get_redis_lock_pool", lambda: object())
    monkeypatch.setattr(trading_websocket_module, "StateHandler", MagicMock())
    monkeypatch.setattr(trading_websocket_module, "PositionFanoutHandler", MagicMock())
    monkeypatch.setattr(trading_websocket_module, "PrivateTopicRouter", MagicMock())
    monkeypatch.setattr(trading_websocket_module, "Reconciler", MagicMock())
    monkeypatch.setattr(
        trading_websocket_module,
        "BybitPrivateStream",
        MagicMock(side_effect=_CrashingPrivateStream),
    )
    monkeypatch.setattr(reconcile_fetcher_module, "BybitReconcileFetcher", MagicMock())
    _install_exchange_account_repository(monkeypatch, account=account)

    result = await websocket_module._stream_main(account_id)

    assert result == {
        "status": "supervisor_failed",
        "account_id": account_id,
        "reconnect_count": 7,
    }
    alert.assert_awaited_once()
    assert "Supervisor" in alert.await_args.args[1]
    assert alert.await_args.args[3]["error"] == repr(boom)
    engine.dispose.assert_awaited_once_with()
