"""gVisor 컨테이너의 기존 Pine 해석기 JSONL worker."""

from __future__ import annotations

import base64
import contextlib
import json
import os
import sys
from typing import Any


def main() -> None:
    # 앱 설정 검증용 일회성 더미다. 호스트 키·DB·거래소 자격 증명은 전달하지 않는다.
    os.environ["TRADING_ENCRYPTION_KEYS"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
    sys.path.insert(0, "/runner")
    import pandas as pd

    from src.core.config import settings
    from src.strategy.code_runtime.pine import _PineInterpreterTransport

    # 호스트의 AST pickle·환경 파일을 읽지 않는다. 이 worker는 읽기 전용 컨테이너의 고정 cwd에서 시작한다.
    settings.pine_ast_cache_dir = ""
    engine = None
    output = sys.stdout
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response: dict[str, Any]
            if message.get("type") == "load" and engine is None:
                frame = pd.DataFrame(message["bars"])
                timestamps = frame.pop("timestamp")
                if "timeframe" in message:
                    if any(pd.Timestamp(value).tzinfo is None for value in timestamps):
                        raise ValueError("명시 timeframe의 timestamp는 timezone-aware여야 합니다")
                    frame.attrs["timeframe"] = message["timeframe"]
                frame.index = pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True))
                engine = _PineInterpreterTransport(frame)
                response = {"loaded": True}
                if "timeframe" in message:
                    response["timeframe"] = frame.attrs["timeframe"]
            elif engine is None:
                raise ValueError("Pine worker 데이터가 초기화되지 않았습니다")
            else:
                with contextlib.redirect_stdout(sys.stderr):
                    response = engine.exchange(message)
            output.write(json.dumps(response, allow_nan=False) + "\n")
            output.flush()
        except Exception as exc:
            output.write(json.dumps({"error": f"{type(exc).__name__}: {exc}"[:1000]}) + "\n")
            output.flush()
            break


if __name__ == "__main__":
    main()
