"""동일 BTC 확정 시간봉 입력을 받는 별도 연구 gVisor 진입점."""

import contextlib
import json
import sys


def main():
    incoming, outgoing = sys.stdin, sys.stdout
    index = -1
    with open("/dev/null", "w") as discarded:
        try:
            first = json.loads(incoming.readline(1_048_576))
            if (first.get("type") != "init" or first.get("protocol") != 1
                    or first.get("mtf_contract") != "same_btc_causal_raw_v1"):
                raise ValueError("MTF protocol mismatch")
            params = first["params"]
            namespace = {"__name__": "__quantbridge_strategy__"}
            with contextlib.redirect_stdout(discarded), contextlib.redirect_stderr(discarded):
                exec(compile(first["source"], "<strategy>", "exec"), namespace)
                callback = namespace["on_bar"]
                state = namespace["init"](params) if "init" in namespace else {}
            if not callable(callback) or not isinstance(state, dict):
                raise ValueError("init must return dict; on_bar must be callable")
            outgoing.write('{"ready":1}\n')
            outgoing.flush()
            history = []
            for index, raw in enumerate(incoming):
                message = json.loads(raw)
                if message.get("type") != "bar":
                    raise ValueError("expected bar")
                market = message["market"]
                if market.get("contract") != "same_btc_causal_raw_v1":
                    raise ValueError("market contract mismatch")
                history.append(message["bar"])
                context = {"bar": history[-1], "history": history,
                           "position": message["position"], "params": params, "market": market}
                with contextlib.redirect_stdout(discarded), contextlib.redirect_stderr(discarded):
                    intent = callback(context, state)
                encoded = json.dumps({"intent": intent}, allow_nan=False)
                if len(encoded.encode()) > 65535:
                    raise ValueError("output limit")
                outgoing.write(encoded + "\n")
                outgoing.flush()
        except BaseException as exc:
            outgoing.write(json.dumps({"error": f"bar_index={index} {type(exc).__name__}: {str(exc)[:400]}"}) + "\n")
            outgoing.flush()
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
