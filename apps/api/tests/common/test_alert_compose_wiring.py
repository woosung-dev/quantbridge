"""[BL-838] compose alert env 대칭 테스트(Docker/DB 의존 없음).

★**이 파일이 재는 것** — 「alert 를 내는 컨테이너가 alert 채널 env 를 받는가」.
2026-08-30 아키텍처 감사 시점에 그것을 재는 것이 **아무것도 없었고**, 그래서
`backend-worker`(기본 큐 전담 — `-Q` 가 없다)만 `SLACK_WEBHOOK_URL` 을 못 받은 채
`orphan_scanner`·kill switch·stuck order 의 critical alert 이 **전부 무음 소실**했다.
`common/alert.py` 는 webhook 이 없으면 예외도 로그 경고도 아니라 `return False` 라
배포에서 아무 흔적이 남지 않는다.

★**서비스 목록을 하드코딩하지 않는 이유** — [BL-843] 이 잡은 결함이 정확히 그것이다
(「목록형 스코프는 파일이 사라져도 조용히 통과한다」). 대상 집합은 compose 자신에서
`command` 로 파생시키고, **파생 집합이 비면 즉시 실패**시킨다 — 빈 입력이 「전건 통과」로
새는 것이 이 레포가 반복해서 밟은 함정이다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).parents[4]
_COMPOSE = _ROOT / "infra" / "compose" / "docker-compose.yml"

# alert 채널 env 3종. `common/alert.py`(Slack) · `common/telegram_alert.py`(Telegram) 가
# `core/config.py` 를 통해 읽는다. 셋 다 `[선택]`이라 compose 는 `${VAR:-}` 로 넘긴다.
_ALERT_ENV_KEYS = ("SLACK_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

# ★파생 로직이 rename·오타로 깨지면 아래 단언이 잡는다. 이 튜플은 스코프가 아니라
#   **파생 결과의 기대값**이다(스코프였다면 [BL-843] 과 같은 결함이 된다).
_EXPECTED_CELERY_SERVICES = frozenset(
    {
        "backend-worker",
        "backend-ws-stream",
        "backend-optimizer-heavy",
        "backend-beat",
    }
)


def _load_compose(path: Path) -> dict[str, Any]:
    yaml.SafeLoader.add_constructor(
        "!override", lambda loader, node: loader.construct_sequence(node)
    )
    return yaml.load(path.read_text(), Loader=yaml.SafeLoader)


def _celery_services(compose: dict[str, Any]) -> dict[str, Any]:
    """`command` 가 celery 를 부르는 서비스만 돌려준다.

    ★`command` 는 base 에서 문자열, isolated override 에서 리스트다 — `str()` 로 평탄화해
    둘 다 같은 판정을 받게 한다.
    """
    services: dict[str, Any] = compose["services"]
    return {name: svc for name, svc in services.items() if "celery" in str(svc.get("command", ""))}


def test_celery_service_derivation_is_not_empty_and_matches_expected() -> None:
    """파생 집합이 비면 이 파일의 다른 단언이 전부 항진명제가 된다.

    ★양성 대조 — 빈 입력이 「일치」로 새는 것을 여기서 막는다.
    """
    derived = _celery_services(_load_compose(_COMPOSE))

    assert derived, "celery 서비스 파생이 0건이다 — 빈 집합 위의 초록은 무증거다"
    assert set(derived) == _EXPECTED_CELERY_SERVICES, (
        f"파생된 celery 서비스가 기대와 다르다: {sorted(derived)} "
        f"vs {sorted(_EXPECTED_CELERY_SERVICES)}"
    )


def test_every_celery_service_receives_all_alert_channel_env() -> None:
    """[BL-838] alert 채널 env 는 celery 서비스 전건 대칭이어야 한다.

    ★`backend-beat` 는 순수 스케줄러라 지금은 task 를 실행하지 않지만 함께 잰다 —
    비대칭을 허용하는 순간 「이 서비스는 안 내니까」가 다음 무음 소실의 근거가 된다.
    """
    derived = _celery_services(_load_compose(_COMPOSE))
    missing: dict[str, list[str]] = {}

    for name, svc in derived.items():
        environment: dict[str, Any] = svc.get("environment", {})
        absent = [key for key in _ALERT_ENV_KEYS if key not in environment]
        if absent:
            missing[name] = absent

    assert not missing, f"alert env 누락 — 이 서비스의 경보는 무음 소실한다: {missing}"


def test_alert_env_is_optional_passthrough_not_required() -> None:
    """세 값은 `[선택]`이므로 `${VAR:-}` 여야 한다.

    `${VAR:?required}` 로 올리면 키 없는 로컬 개발 스택이 아예 안 뜬다
    (`TRADING_ENCRYPTION_KEYS` 가 그 형태를 쓰는 것과 대비된다).
    """
    derived = _celery_services(_load_compose(_COMPOSE))
    wrong: dict[str, dict[str, str]] = {}

    for name, svc in derived.items():
        environment: dict[str, Any] = svc.get("environment", {})
        bad = {
            key: str(environment[key])
            for key in _ALERT_ENV_KEYS
            if key in environment and str(environment[key]) != "${" + key + ":-}"
        }
        if bad:
            wrong[name] = bad

    assert not wrong, f"alert env 는 `${{VAR:-}}` 통과여야 한다: {wrong}"
