"""Python 서비스 철거가 Pine API·작업과 기존 원장 보존을 침범하지 않는다."""

from fastapi.testclient import TestClient

from src.main import create_app
from src.tasks.celery_app import celery_app


def test_python_submission_is_unavailable_and_pine_api_remains() -> None:
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/api/v1/strategies" in paths
    assert not any("python-strategies" in path for path in paths)
    client = TestClient(app)
    response = client.post(
        "/api/v1/python-strategies", json={"name": "retired", "source": "print('ff')"}
    )
    assert response.status_code == 404


def test_no_python_tasks_are_registered_or_scheduled() -> None:
    assert "src.tasks.python_strategy" not in celery_app.conf.include
    assert not any(
        entry["task"].startswith("python_strategy.")
        for entry in celery_app.conf.beat_schedule.values()
    )
