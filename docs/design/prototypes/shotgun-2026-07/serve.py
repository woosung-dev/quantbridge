# 프로토타입 뷰어 전용 정적 서버 — 브라우저 캐시를 끄고 항상 최신 파일을 준다
"""
사용법.
  python3 serve.py           # http://localhost:4173/viewer.html
  python3 serve.py 4174      # 포트 지정

python3 -m http.server 는 Cache-Control 을 보내지 않아 브라우저가 옛 viewer.html 과
screen-*.html 을 그대로 재사용한다. 프로토타입을 고쳐 놓고 "안 바뀌었는데" 로 시간을
태우는 사고가 반복되므로, 이 서버는 모든 응답에 no-store 를 붙인다.
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 — 상위 시그니처 유지
        pass  # 조용히


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    handler = partial(NoCacheHandler, directory=str(HERE))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"뷰어  http://localhost:{port}/viewer.html   (캐시 없음)")
        print("종료  Ctrl+C")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n종료했습니다.")


if __name__ == "__main__":
    main()
