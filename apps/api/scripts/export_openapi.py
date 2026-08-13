#!/usr/bin/env python
"""FastAPI OpenAPI 스키마를 결정적으로 덤프한다 (BL-717 계약축 PoC).

- 출력: 레포 루트 `contracts/openapi/openapi.json` (키 정렬 + indent 2 + 개행 고정
  — 같은 코드에서 두 번 실행하면 byte-identical 이어야 한다).
- 실행: pytest 와 동일하게 `.env.local` 통째 소싱이 전제다 (Settings 의
  `trading_encryption_keys` 가 기본값 없는 필수 필드).
    cd apps/api && set -a; . ./.env.local; set +a; uv run python scripts/export_openapi.py
- `--check`: 파일을 쓰지 않고 커밋된 스키마와 비교, 다르면 exit 1 (CI drift 게이트용).
- production 은 `openapi_url=None` 으로 라우트 노출만 막을 뿐 `app.openapi()` 생성은
  막지 않지만, 계약의 기준 환경은 development 로 고정한다 (아래 APP_ENV 강제).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 계약 기준 환경 고정 — 호스트의 APP_ENV 가 무엇이든 export 는 development 의미론으로 뜬다.
# (ADR-029 교훈: 환경 파생값이 산출물에 섞이면 drift 판정이 비결정이 된다.)
os.environ["APP_ENV"] = "development"

REPO_ROOT = BACKEND_ROOT.parents[1]
OUTPUT = REPO_ROOT / "contracts" / "openapi" / "openapi.json"


def _dump() -> str:
    from src.main import create_app

    schema = create_app().openapi()
    return json.dumps(schema, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    # 깊이 파생 경로 자기검증 — ADR-029 「parents[N] 사각」 재발 방지.
    if not (REPO_ROOT / "apps" / "api").is_dir():
        print(f"레포 루트 파생 실패: {REPO_ROOT}", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="쓰지 않고 커밋된 스키마와 비교만 한다 (다르면 exit 1)",
    )
    args = parser.parse_args()

    rendered = _dump()

    if args.check:
        if not OUTPUT.exists():
            print(f"drift: {OUTPUT} 이 없다 — export 를 먼저 커밋해라", file=sys.stderr)
            return 1
        committed = OUTPUT.read_text(encoding="utf-8")
        if committed != rendered:
            print(
                "drift: 코드의 OpenAPI 와 contracts/openapi/openapi.json 이 다르다.\n"
                "  재생성: cd apps/api && set -a; . ./.env.local; set +a; "
                "uv run python scripts/export_openapi.py",
                file=sys.stderr,
            )
            return 1
        print(f"drift 없음: {OUTPUT} ({len(rendered)} chars)")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"작성: {OUTPUT} ({len(rendered)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
