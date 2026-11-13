"""확정 원시 피드를 gVisor 전용 전송에 더한다. 호스트는 소스를 실행하지 않는다."""

from __future__ import annotations

from src.strategy.code_runtime.models import validate_code_intent
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.python_runtime.sandbox import DockerPythonTransport

from tools.research.mtf_v1.feeds import CausalFeeds


class MtfTransport(DockerPythonTransport):
    def __init__(self, image: str, feeds: CausalFeeds, timeout: float = 900):
        self.feeds = feeds
        self._ready = False
        super().__init__(image=image, timeout=timeout)

    def exchange(self, message: dict) -> dict:
        if not self._ready:
            if message.get("type") != "init" or message.get("protocol") != 1:
                raise ValueError("MTF init 계약 오류")
            validate_source_and_params(message["source"], message["params"])
            reply = super().exchange({**message, "mtf_contract": "same_btc_causal_raw_v1"})
            if reply != {"ready": 1}:
                raise ValueError("MTF ready 계약 오류")
            self._ready = True
            return reply
        if message.get("type") != "bar":
            raise ValueError("MTF bar 계약 오류")
        reply = super().exchange({**message, "market": self.feeds.for_bar(message["bar"])})
        if set(reply) != {"intent"}:
            raise ValueError("MTF 응답은 intent 하나여야 합니다")
        return {"intent": validate_code_intent(reply["intent"])}
