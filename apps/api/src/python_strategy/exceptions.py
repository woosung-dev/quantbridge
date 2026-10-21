from src.common.exceptions import AppException


class PythonRunnerUnavailable(AppException):
    status_code = 503
    code = "PYTHON_RUNNER_UNAVAILABLE"
    detail = "격리 Python 실행기가 준비되지 않았습니다."


class PythonRunConflict(AppException):
    status_code = 409
    detail = "이미 완료되었거나 실행 중인 작업이 있습니다."


class PythonVersionConflict(PythonRunConflict):
    code = "python_strategy_version_conflict"
    detail = "다른 창에서 전략이 수정되었습니다. 최신 버전을 확인하세요."
