"""Sprint 10 Phase C — real_broker pytest plugin.

--run-real-broker 플래그 로만 marker 수집 + Bybit Demo credentials env 검증.

기본 동작:
- pytest 실행 → real_broker marker 테스트 전부 skip
- pytest --run-real-broker → 모두 실행. credentials 없으면 fail with clear message.

Nightly CI (`nightly-real-broker.yml`) 이 `pytest --run-real-broker` 로 호출.

주의: 글로벌 conftest (`tests/conftest.py`) 에 `pytest_addoption` (--run-mutations) 과
`pytest_collection_modifyitems` 가 이미 있음. 본 파일은 다른 옵션/마커 만 다루므로
pytest hook 체인 상 충돌 없이 병렬 등록됨.
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """--run-real-broker 플래그 등록 (opt-in 방식, default=False)."""
    parser.addoption(
        "--run-real-broker",
        action="store_true",
        default=False,
        help="run tests marked 'real_broker' (requires Bybit Demo credentials)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """`--run-real-broker` 없으면 real_broker marker 아이템 skip.

    글로벌 conftest 의 mutation marker 제어 와 동일 패턴.
    hook 체인: pytest 가 두 conftest 의 구현을 순서대로 호출 (충돌 없음).
    """
    if config.getoption("--run-real-broker"):
        return
    skip_marker = pytest.mark.skip(
        reason="real_broker: requires --run-real-broker flag + Bybit Demo credentials"
    )
    for item in items:
        if "real_broker" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def bybit_demo_test_credentials() -> tuple[str, str]:
    """BYBIT_DEMO_API_KEY_TEST / BYBIT_DEMO_API_SECRET_TEST env 로드.

    --run-real-broker 실행 경로에서만 호출됨. env 미설정 시 pytest.fail
    (clear error message — CI 에서 Secrets 누락 즉시 파악 가능).

    Returns:
        (api_key, api_secret) 튜플. 비어있으면 pytest.fail 로 테스트 중단.
    """
    key = os.environ.get("BYBIT_DEMO_API_KEY_TEST", "").strip()
    secret = os.environ.get("BYBIT_DEMO_API_SECRET_TEST", "").strip()
    if not key or not secret:
        pytest.fail(
            "Phase C E2E requires BYBIT_DEMO_API_KEY_TEST + BYBIT_DEMO_API_SECRET_TEST "
            "env. Set via GitHub Secrets (nightly-real-broker.yml) or local .env.local."
        )
    return key, secret
