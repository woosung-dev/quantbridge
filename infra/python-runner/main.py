"""이 파일은 gVisor 컨테이너 안에서만 실행되는 사용자 코드 로더다."""

import contextlib
import json
import sys


def main():
    incoming = sys.stdin
    outgoing = sys.stdout
    # 사용자 print 는 프로토콜 스트림에 섞이지 않는다. /dev/null 은 디스크를 채우지 않는다.
    with open("/dev/null", "w") as discarded:
        try:
            first = json.loads(incoming.readline(1_048_576))
            if first.get("type") != "init" or first.get("protocol") != 1:
                raise ValueError("protocol mismatch")
            params = first["params"]
            namespace = {"__name__": "__quantbridge_strategy__"}
            with contextlib.redirect_stdout(discarded), contextlib.redirect_stderr(discarded):
                # 신뢰 경계는 Python 구문 제한이 아니라 컨테이너/gVisor 다.
                exec(compile(first["source"], "<strategy>", "exec"), namespace)
                callback = namespace["on_bar"]
                state = namespace["init"](params) if "init" in namespace else {}
            if not callable(callback) or not isinstance(state, dict):
                raise ValueError("init must return dict; on_bar must be callable")
            outgoing.write('{"ready":1}\n')
            outgoing.flush()
            history = []
            for raw in incoming:
                message = json.loads(raw)
                if message.get("type") != "bar":
                    raise ValueError("expected bar")
                history.append(message["bar"])
                context = {"bar": history[-1], "history": history, "position": message["position"], "params": params}
                with contextlib.redirect_stdout(discarded), contextlib.redirect_stderr(discarded):
                    intent = callback(context, state)
                encoded = json.dumps({"intent": intent}, allow_nan=False)
                if len(encoded.encode()) > 65535:
                    raise ValueError("output limit")
                outgoing.write(encoded + "\n")
                outgoing.flush()
        except BaseException as exc:
            outgoing.write(json.dumps({"error": type(exc).__name__ + ": " + str(exc)[:500]}) + "\n")
            outgoing.flush()
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
