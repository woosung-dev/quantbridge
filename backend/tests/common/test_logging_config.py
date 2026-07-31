"""BL-561 — `extra=` 필드가 실제로 렌더되는지.

★이 파일의 판정 기준은 "값이 함께 찍히는가" 다. 이벤트 이름만 남는 것이 원래 결함이었다.
soak 2026-07-30 의 실측 라인이 이랬다::

    [2026-07-30 16:03:35,101: WARNING/ForkPoolWorker-1] live_signal_position_divergence

★표적 변이 — `build_logging_config()` 의 formatter 를 stdlib `logging.Formatter` 로
되돌리면 `test_wired_config_renders_divergence_pair` 부터 무너진다.
"""

from __future__ import annotations

import ast
import io
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

import src as src_module
from src.common import logging_config
from src.common.logging_config import (
    KeyValueFormatter,
    build_logging_config,
    configure_logging,
    normalize_level,
)


def _format(msg: str, extra: dict[str, object], *, exc_info: object = None) -> str:
    """`extra=` 를 실은 LogRecord 1건을 실제 포매터에 통과시킨다."""
    formatter = KeyValueFormatter("%(levelname)s %(message)s")
    record = logging.LogRecord(
        name="src.tasks.live_signal",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,  # type: ignore[arg-type]
    )
    record.__dict__.update(extra)
    return formatter.format(record)


# --- 1. 값과 함께 렌더된다 (BL-560 이 못 얻었던 크기 쌍) ------------------------------


def test_renders_engine_and_exchange_position_with_values():
    out = _format(
        "live_signal_position_divergence",
        {
            "session_id": "0d1f",
            "category": "same_side",
            "engine_position": "1.5",
            "exchange_position": "-1.5",
        },
    )
    assert "live_signal_position_divergence" in out
    assert "engine_position=1.5" in out
    assert "exchange_position=-1.5" in out
    assert "category=same_side" in out


# --- 2. 동적 키셋 (`extra={..., **divergence}`) ---------------------------------------


def test_renders_runtime_varying_key_set():
    """`tasks/live_signal.py` 의 `extra={"session_id": ..., **divergence}` 재현.

    키를 하드코딩한 포매터라면 여기서 죽거나 조용히 버린다.
    """
    divergence_a = {"reason": "breach_exceeds_cap", "had_resting": True, "cap": Decimal("0.02")}
    divergence_b = {"reason": "trigger_already_breached", "trade_id": 41, "spot_ref": None}

    out_a = _format("live_conditional_reconcile_divergence", {"session_id": "s", **divergence_a})
    out_b = _format("live_conditional_reconcile_divergence", {"session_id": "s", **divergence_b})

    assert "reason=breach_exceeds_cap" in out_a
    assert "had_resting=true" in out_a
    assert "cap=0.02" in out_a
    # 다른 호출은 완전히 다른 키셋이다.
    assert "trade_id=41" in out_b
    assert "spot_ref=null" in out_b
    assert "had_resting" not in out_b


# --- 3. 예약 속성과 충돌해도 죽지 않는다 ----------------------------------------------


def test_reserved_attributes_are_not_emitted_as_extras():
    """표준 LogRecord 속성은 ` key=value` 로 새어 나오지 않는다."""
    out = _format("evt", {})
    assert out == "WARNING evt"
    for reserved in ("levelname=", "asctime=", "processName=", "lineno=", "msg=", "args="):
        assert reserved not in out


def test_reserved_key_in_extra_raises_from_stdlib_not_from_us():
    """★실제 `logger.warning(..., extra=...)` 경로로 **진짜 동작**을 단언한다.

    앞선 판본은 `record.__dict__` 를 직접 오염시켜 `Logger.makeRecord` 를 우회했다.
    그래서 "예약 키가 와도 안 죽는다" 고 주장하면서 실제로는 확인하지 않았다 — 거짓 그린.

    실제 동작은 **죽는다**: stdlib `makeRecord` 가 우리 포매터에 닿기 전에 KeyError 를
    던진다. 우리가 고를 수 있는 동작이 아니라 stdlib 계약이다. 우회 가드를 넣지 않기로
    한 근거는 `test_only_dynamic_extra_site_cannot_produce_reserved_keys` 가 지킨다.
    """
    logger = logging.getLogger("tests.bl561.reserved")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    try:
        with pytest.raises(KeyError, match="Attempt to overwrite 'message' in LogRecord"):
            logger.warning("evt", extra={"message": "collision"})
        # 예약 키가 아니면 같은 경로가 멀쩡히 지나간다 (KeyError 가 키 무관 상시 발생이 아님).
        logger.warning("evt", extra={"real": 1})
    finally:
        logger.handlers = []


def test_only_dynamic_extra_site_cannot_produce_reserved_keys():
    """`extra={..., **divergence}` (`tasks/live_signal.py:1039`) 가 예약 키를 만들 수 있는가.

    ★`backend/src` 전체에서 `extra=` 에 dict 를 unpack 하는 곳은 이 **한 자리뿐**이고,
    그 dict 는 `conditional_entry_planner.plan_reconcile` 이 만든다. 거기서 append 되는
    dict 는 전부 **리터럴 키**라 키 집합이 닫혀 있다 — 그래서 sanitize 가드를 넣지 않았다.

    이 테스트가 그 닫힘을 고정한다. 계획기가 `name` / `module` 같은 키를 새로 추가하면
    여기서 실패한다 (그때 비로소 가드가 필요해진다).
    """
    planner = Path(src_module.__file__).parent / "trading/services/conditional_entry_planner.py"
    tree = ast.parse(planner.read_text(encoding="utf-8"))

    keys: set[str] = set()
    dynamic: list[str] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "divergences"
        ):
            continue
        for arg in node.args:
            if not isinstance(arg, ast.Dict):
                dynamic.append(f"non-literal dict: {type(arg).__name__}")
                continue
            for key in arg.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)
                else:
                    # `{**other}` 는 key 가 None 이다 — 키 집합이 열린다.
                    dynamic.append(ast.dump(key) if key is not None else "**unpack")

    assert keys, "divergence dict 리터럴을 하나도 못 찾았다 — 계획기 구조가 바뀌었다"
    assert not dynamic, f"divergence 키 집합이 더 이상 닫혀 있지 않다: {dynamic}"
    collisions = keys & logging_config._RESERVED_ATTRS
    assert not collisions, f"divergence 키가 LogRecord 예약 속성과 충돌한다: {sorted(collisions)}"


def test_unsafe_key_characters_are_sanitised():
    out = _format("evt", {"has space": 1, "eq=key": 2})
    assert "has_space=1" in out
    assert "eq_key=2" in out


# --- 4. 값 렌더는 어떤 입력에도 예외를 던지지 않는다 ------------------------------------


class _Exploding:
    def __str__(self) -> str:
        raise RuntimeError("boom")


def test_value_rendering_is_total():
    """★로깅이 예외를 던지면 그게 더 큰 사고다."""
    recursive: dict[str, object] = {"self": None}
    recursive["self"] = recursive

    out = _format(
        "evt",
        {
            "none": None,
            "dec": Decimal("0.000001"),
            "ts": datetime(2026, 7, 30, 16, 3, 35, tzinfo=UTC),
            "spaced": "reduce-only order has same side",
            "empty": "",
            "recursive": recursive,
            "boom": _Exploding(),
            "flag": False,
        },
    )
    assert "none=null" in out
    assert "dec=0.000001" in out
    assert "ts=2026-07-30T16:03:35+00:00" in out
    # 공백이 섞인 값은 따옴표로 묶여 파싱 가능해야 한다.
    assert 'spaced="reduce-only order has same side"' in out
    assert 'empty=""' in out
    assert "boom=<unrenderable>" in out
    assert "flag=false" in out
    assert "recursive=" in out


def test_extras_come_before_traceback():
    """extras 가 traceback 꼬리에 매달리면 읽을 수 없다."""
    try:
        raise ValueError("nope")
    except ValueError as exc:
        exc_info = (type(exc), exc, exc.__traceback__)

    out = _format("evt", {"session_id": "abc"}, exc_info=exc_info)
    assert "session_id=abc" in out
    assert out.index("session_id=abc") < out.index("Traceback")


# --- 5. 실제 배선 (표적 변이 지점) -----------------------------------------------------


def test_wired_config_renders_divergence_pair():
    """`build_logging_config()` 가 실제로 우리 포매터를 물리는가.

    ★표적 변이: formatter 를 stdlib `logging.Formatter` 로 되돌리면 이 단언이 실패한다.
    dictConfig 는 전역을 건드리므로 여기선 같은 설정 dict 에서 포매터만 꺼내 격리 검증한다
    (pytest caplog 핸들러를 떼어내지 않기 위함).
    """
    spec = build_logging_config("INFO")["formatters"]["keyvalue"]
    formatter = spec["()"](fmt=spec["format"])

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    logger = logging.getLogger("tests.bl561.wiring")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    try:
        logger.warning(
            "live_signal_position_divergence",
            extra={"engine_position": "1", "exchange_position": "-1"},
        )
    finally:
        logger.handlers = []

    rendered = stream.getvalue()
    assert "live_signal_position_divergence" in rendered
    assert "engine_position=1" in rendered
    assert "exchange_position=-1" in rendered
    # 원래 결함 = 이벤트 이름만 남는 것. 그 상태와 구분된다.
    assert rendered.strip() != "live_signal_position_divergence"


@pytest.fixture
def _restore_root_logging() -> Iterator[None]:
    """root 핸들러/레벨 + `_configured` 스냅샷 후 복원.

    caplog 를 쓰는 다른 테스트를 오염시키지 않는다. `_configured` 까지 되돌려야
    아래 `test_main_module_import_configures_logging` 이 실행 순서에 독립적이다.
    """
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_configured = logging_config._configured
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
        logging_config._configured = saved_configured


def test_configure_logging_installs_formatter_on_root(_restore_root_logging: None):
    """★표적 변이: `configure_logging()` 배선을 걷어내면 실패한다."""
    configure_logging(level="INFO", force=True)
    root = logging.getLogger()
    assert any(isinstance(h.formatter, KeyValueFormatter) for h in root.handlers)
    assert root.level == logging.INFO


def test_root_config_does_not_touch_propagation():
    """개별 로거 `propagate` 를 끊으면 caplog 이 조용히 빈 목록을 준다.

    `backend/tests/trading/test_reconcile_fetcher.py:115` 가 겪었던 flaky 의 재발 방지.
    """
    config = build_logging_config("INFO")
    assert "loggers" not in config
    assert config["disable_existing_loggers"] is False
    assert config["root"]["handlers"] == ["console"]


def test_main_module_import_configures_logging():
    """★표적 변이: `src/main.py` 의 `configure_logging()` 호출을 지우면 실패한다.

    uvicorn 은 `src.main:app` 을 import 하는 것으로 로깅을 세운다 — 이 테스트가 그
    production import 경로를 그대로 탄다(호출 자체를 재현하는 게 아니라 실제로 돈다).
    """
    import src.main  # noqa: F401  (import 부수효과로 root 가 설정된다)

    assert logging_config.is_configured(), "src.main import 가 로깅을 세우지 않았다"


def test_celery_setup_logging_signal_installs_formatter(_restore_root_logging: None):
    """★celery worker 기동과 **같은 경로**로 시그널을 발화시켜 결과를 단언한다.

    앞선 판본은 receiver 가 하나라도 있는지만 봤다 — callback 을 no-op 으로 바꿔도
    통과하는 거짓 그린이었다. 여기서는 celery 가 `Logging.setup_logging_subsystem`
    에서 보내는 것과 같은 인자로 직접 `send()` 하고, root 에 우리 포매터가 실제로
    설치됐는지 본다.

    ★표적 변이 2종이 모두 여기서 잡힌다 — `@setup_logging.connect` 제거(=receiver 0)
    와 `_configure_worker_logging` 을 `pass` 로 비우기(=포매터 미설치).
    """
    from celery.signals import setup_logging

    import src.tasks.celery_app  # noqa: F401  (import 부수효과로 시그널이 연결된다)

    root = logging.getLogger()
    root.handlers = []
    # 이미 설정된 프로세스에선 `configure_logging()` 이 조기 반환한다 — worker 기동
    # 시점(미설정)을 재현하려면 되돌려야 한다. 픽스처가 원상 복구한다.
    logging_config._configured = False

    receivers = setup_logging.send(
        sender=None, loglevel=logging.INFO, logfile=None, format=None, colorize=None
    )

    assert receivers, "celery setup_logging 에 receiver 가 없다 → root hijack 부활"
    assert any(isinstance(h.formatter, KeyValueFormatter) for h in root.handlers), (
        "시그널은 붙었는데 callback 이 포매터를 세우지 않았다"
    )


# --- 6. 레벨 ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("debug", "DEBUG"), (" warning ", "WARNING"), ("", "INFO"), (None, "INFO"), ("nope", "INFO")],
)
def test_normalize_level(raw: str | None, expected: str):
    assert normalize_level(raw) == expected
