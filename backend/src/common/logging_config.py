"""구조화 로그 렌더 — `extra=` 필드를 ` key=value` 로 살려낸다 (BL-561).

배경. `backend/src` 에는 로깅 설정이 **아예 없었다**. 그래서 두 프로세스가 서로 다르게
깨져 있었다:

- **celery worker** — `worker_hijack_root_logger` 기본 True → celery 포매터가 root 를
  잡는다. 그 포맷 문자열에 `extra` 자리가 없어 **전량 소실**. 메시지 이름만 남았다.
- **uvicorn/API** — uvicorn 기본 LOGGING_CONFIG 는 `uvicorn*` 만 설정하고 **root 에는
  핸들러를 두지 않는다** → `src.*` 는 `logging.lastResort`(WARNING, `%(message)s`)로
  떨어진다. **INFO 는 아예 사라지고** WARNING 도 이벤트 이름만 남는다. worker 보다 나쁘다.

실측 로그 라인(soak 2026-07-30)이 이랬다::

    [2026-07-30 16:03:35,101: WARNING/ForkPoolWorker-1] live_signal_position_divergence

값이 하나도 없어 BL-560 의 수용 기준("엔진/거래소 포지션 쌍을 함께 남긴다")이 **구조적으로
충족 불가**였다. 같은 계열의 두 번째 발생이다(BL-553 이 `trade_ids` 를 확인 신호에서 뺀 이유).

`extra=` 호출 사이트 135개는 이미 전부 구조화 로그 모양(메시지 = 이벤트 이름, `%s` 보간
없음)이라 **포매터만 고치면 그대로 살아난다.** 호출 사이트는 건드리지 않는다.

설계 제약(사용자 결정):

- **신규 의존성 금지** — structlog / python-json-logger 를 쓰지 않는다. stdlib 전용.
- **출력은 JSON 이 아니라 `key=value`** — 지금 용도는 사람이 `docker logs` 로 읽는 것이다.
"""

from __future__ import annotations

import json
import logging
import logging.config
import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

# celery 기본 포맷과 눈에 익은 모양을 유지한다 — 운영자가 `docker logs` 로 읽던 형태다.
# `%(processName)s` 가 prefork 워커에서 `ForkPoolWorker-1` 을 그대로 준다.
LOG_FORMAT = "[%(asctime)s: %(levelname)s/%(processName)s] %(name)s %(message)s"

_VALID_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# key 로 쓸 수 없는 문자. `**divergence` 처럼 임의 dict 가 흘러들어오므로
# 공백/`=` 가 섞인 키가 파싱을 깨뜨리지 않게 치환한다.
_KEY_UNSAFE = re.compile(r"[^A-Za-z0-9_.\-]")
# 값에 이게 있으면 따옴표로 감싼다.
_VALUE_NEEDS_QUOTE = re.compile(r'[\s"=]')


def _reserved_attrs() -> frozenset[str]:
    """`LogRecord` 표준 속성 집합 — ★하드코딩하지 않고 런타임에 파생한다.

    Python 마이너 버전마다 표준 속성이 늘어난다(3.12 의 `taskName`). 목록을 손으로
    적으면 버전이 오를 때 조용히 표준 속성이 `extra` 인 척 섞여 나온다.
    `format()` 이 나중에 채우는 `message` / `asctime` 만 따로 더한다.
    """
    probe = logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    )
    return frozenset(vars(probe)) | {"message", "asctime"}


_RESERVED_ATTRS = _reserved_attrs()


def _render_value(value: object) -> str:
    """값 1개를 로그 안전 문자열로. ★어떤 입력에도 예외를 던지지 않는다."""
    try:
        if value is None:
            return "null"
        # bool 은 int 의 subclass 라 반드시 먼저 본다.
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int | float | Decimal):
            return str(value)
        if isinstance(value, datetime | date | time):
            return value.isoformat()
        # 재귀 dict 는 CPython repr 이 `{...}` 로 잘라 주므로 str() 로 안전하다.
        text = value if isinstance(value, str) else str(value)
    except Exception:
        # __str__ 이 터지는 객체. 로깅이 예외를 던지면 그게 더 큰 사고다.
        return "<unrenderable>"
    if text == "" or _VALUE_NEEDS_QUOTE.search(text):
        try:
            return json.dumps(text, ensure_ascii=False)
        except Exception:
            return '"<unrenderable>"'
    return text


def _render_extras(record: logging.LogRecord) -> str:
    """표준 속성을 제외한 나머지 전부를 ` key=value` 로 이어 붙인다.

    ★키를 하드코딩하지 않는다 — `tasks/live_signal.py:1039` 의
    `extra={"session_id": ..., **divergence}` 처럼 **키 집합이 런타임에 달라지는**
    호출 사이트가 있다(`conditional_entry_planner.py` 의 여러 dict 가 흘러든다).

    ★**예약 키가 `extra=` 로 오면 죽는다 — 여기가 아니라 그 앞에서.** stdlib
    `Logger.makeRecord` 가 `KeyError: Attempt to overwrite 'message' in LogRecord` 를
    던진다. 우리가 고를 수 있는 동작이 아니라 stdlib 계약이라 **우회 가드를 두지 않았다.**
    근거: `extra=` 에 dict 를 unpack 하는 곳은 `live_signal.py:1039` **한 자리뿐**이고
    그 dict 의 키는 계획기의 리터럴 16종으로 닫혀 있어 예약 속성과 겹치지 않는다.
    그 닫힘은 `tests/common/test_logging_config.py` 의
    `test_only_dynamic_extra_site_cannot_produce_reserved_keys` 가 고정한다 —
    계획기가 `name` 같은 키를 새로 추가하면 그 테스트가 실패한다.
    """
    try:
        items = [
            (key, value)
            for key, value in record.__dict__.items()
            if key not in _RESERVED_ATTRS and not key.startswith("_")
        ]
    except Exception:
        return ""
    if not items:
        return ""
    # 삽입 순서를 유지한다 — 호출 사이트가 적은 순서(session_id 먼저)가 곧 읽는 순서다.
    return "".join(f" {_KEY_UNSAFE.sub('_', str(k)) or '_'}={_render_value(v)}" for k, v in items)


class KeyValueFormatter(logging.Formatter):
    """`extra=` 로 넘어온 필드를 메시지 뒤에 ` key=value` 로 붙이는 포매터 (BL-561)."""

    def formatMessage(self, record: logging.LogRecord) -> str:
        """★`format()` 이 아니라 `formatMessage()` 를 덮는다.

        `format()` 은 이 결과 **뒤에** exc_info / stack_info 를 붙인다. 그래서 여기서
        붙여야 extras 가 traceback **앞**에 온다. `format()` 을 덮으면 필드가 traceback
        꼬리에 매달려 읽을 수 없게 된다.
        """
        base = super().formatMessage(record)
        try:
            extras = _render_extras(record)
        except Exception:
            return base
        return f"{base}{extras}" if extras else base


def normalize_level(level: str | None) -> str:
    """레벨 문자열 정규화. 모르는 값이면 INFO 로 떨어뜨린다(기동을 막지 않는다)."""
    candidate = (level or "").strip().upper()
    return candidate if candidate in _VALID_LEVELS else "INFO"


def build_logging_config(level: str = "INFO") -> dict[str, Any]:
    """celery worker / uvicorn 이 **같이 쓰는** dictConfig 딕셔너리."""
    return {
        "version": 1,
        # ★False 의무 — uvicorn 이 먼저 세운 `uvicorn.*` 로거를 죽이지 않는다.
        "disable_existing_loggers": False,
        "formatters": {
            "keyvalue": {
                "()": KeyValueFormatter,
                "format": LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "keyvalue",
                "stream": "ext://sys.stdout",
            },
        },
        # ★root 에만 붙이고 개별 로거의 `propagate` 는 건드리지 않는다.
        # propagate 를 끊으면 pytest caplog 이 조용히 빈 목록을 준다
        # (`backend/tests/trading/test_reconcile_fetcher.py:115` 의 flaky 이력).
        "root": {"handlers": ["console"], "level": normalize_level(level)},
    }


_configured = False


def is_configured() -> bool:
    """`configure_logging()` 이 이 프로세스에서 한 번이라도 돌았는가."""
    return _configured


def configure_logging(level: str | None = None, *, force: bool = False) -> None:
    """root 에 `KeyValueFormatter` 핸들러를 세운다. 프로세스당 1회.

    ★재실행 방지가 안전장치다 — `dictConfig` 는 root 의 **기존 핸들러를 제거**한다.
    테스트 실행 중에 다시 돌면 pytest 가 붙여 둔 caplog 핸들러를 떼어내 버린다.
    설정 자체를 테스트할 때만 `force=True`.
    """
    global _configured
    if _configured and not force:
        return
    resolved = level or ""
    if not resolved:
        # import 순환을 피하려고 지연 import (core.config 가 common 을 참조할 수 있다).
        from src.core.config import settings

        resolved = str(settings.log_level)
    logging.config.dictConfig(build_logging_config(resolved))
    _configured = True
