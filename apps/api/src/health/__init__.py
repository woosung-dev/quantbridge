"""Sprint 30 ε B3 — Health probe 모듈.

Cloud Run / docker compose healthcheck 가 호출하는 ``GET /healthz`` 가 본 모듈
의 router 에서 정의됨. Postgres / Redis / Celery 3-dep ping. dep 실패 시 503.

기존 ``GET /health`` (main.py) 는 backward-compat 위해 유지 — env 만 반환하는
단순 liveness 용. ``/healthz`` 는 readiness 용 (full dep check).

Note: ``router`` 객체 직접 import 는 ``from src.health.router import router`` 로 하세요.
패키지 ``__init__`` 가 router 를 re-export 하면 ``src.health.router`` 가 module
로 dotted-path lookup 시 APIRouter 객체로 가려져 monkeypatch 가 깨집니다 (Sprint 30 ε B3 회고).
"""
