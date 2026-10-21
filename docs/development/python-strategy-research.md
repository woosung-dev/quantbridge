# 오프라인 전략 연구와 Python 서비스 미도입 경계

결정 정본은 [ADR-045](../adr/045-python-strategy-research.md)다. 사용자 Python의 웹 편집·저장·서버
백테스트·자동매매는 제공하지 않는다. Python View는 계속 읽기 전용이며 Pine 실행 경로를 사용한다.

## 보존 범위

- `tools/research/`: 후보 정의·데이터·오프라인 비교·근거 내보내기. 명령은 해당 [README](../../tools/research/README.md).
- `src/backtest/engine/{python_adapter,swing_risk_adapter}.py`와 `strategy/python_runtime/`의 로컬 transport·
  프로토콜·serialization·SDK·스윙 청산 계산: 오프라인 연구 CLI에서만 사용한다.
- `infra/python-runner/`의 로컬 gVisor 이미지와 빌드 도구: API gateway나 서버 서비스로 배포하지 않는다.
- `python_strategy/models.py`·`20261021_0001`: 기존 연구 원장 3테이블의 스키마와 적용 이력 보존 전용이다.

앱 API 라우터·Celery include/beat·원격 runner client/gateway·실행기 환경 변수·웹 실험실은 없다.
DB 스키마를 자동 삭제하거나 기존 Pine 전략·백테스트·거래 계정을 바꾸지 않는다.

## 청산과 검증 경계

직전 완료 두 봉의 스윙 극값과 10% 여유로 초기 SL을 계산하고 1.5R에서 50% 반익절,
2R에서 진입가에 도달하는 간격으로 트레일링을 시작하는 계산은 유지한다. 이 계산의 존재는
모든 Pine 코호트의 V2 성과 검증이나 거래소 부분 체결·취소·재시작 보호가 완료됐다는 뜻이 아니다.
Pine 검증의 정본은 [신호 교차 검증](./pine-signal-validation.md)이다.

단일 백테스트 완료·원본 재현·비용 반영 성과·미사용 기간 통과를 구분한다. 과거에 이미 탐색한 기간을
독립 holdout으로 부르지 않는다. 오프라인 결과를 웹·서버 실행 활성화 승인으로 사용하지 않는다.

종전 웹/API 실행 계약 원문은 `git show 66061cd2:docs/development/python-strategy-research.md`에 있다.
