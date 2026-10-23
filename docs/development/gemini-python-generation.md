# Gemini 자연어 → 실행 Python preview

`/strategies/code`의 자연어 생성은 `code_v1` Python 초안을 만든다. 기존
`/strategies/generate`의 Pine 정본·읽기 전용 Python DTO와 다른 계약이다.
저장·버전·백테스트는 [기존 코드 전략 계약](code-strategy-storage.md)을 재사용한다.

## 검토와 저장

인증된 `POST /strategies/code/generate`는 자연어 `prompt`, `warmup_bars`, JSON `params`를
받아 Python 코드 스냅샷·가정·요청/응답 모델·관측 usage를 반환한다. 응답은 preview이며
DB 저장이나 전략 실행을 하지 않는다. 구문·함수 진입점 확인은 실행·의미 검증 통과가 아니다.

사용자는 원문과 가정을 검토하고 적용을 눌러 편집기에 옮긴다. 버전 저장과 백테스트 요청은
각각 별도 행동이다. 미저장 변경이 있으면 백테스트를 제출하지 않는다. 생성·적용·저장으로
Demo를 시작하지 않는다. 계정 또는 선택 전략이 바뀐 뒤 도착한 오래된 생성 응답은 버린다.

적용된 source·language·params·warmup이 유지될 때 생성 출처를 보존한다. 사용자가 코드를
바꾸면 수동 편집 출처와 부모 버전을 기록한다. 이 provenance는 출처 설명이며 모델 생성이나
의미 일치를 인증하는 서명이 아니다. 실제 응답 모델이나 usage가 없으면 미관측으로 표시한다.

## Provider와 비밀 경계

기존 `complete_json`과 Gemini Developer API를 사용한다. 설정에 Gemini가 허용돼 있어야 하며
새 경로는 다른 provider로 fallback하지 않는다. 모델은 `GEMINI_MODEL` 설정을 따른다.
비교 실험의 순위가 모델 설정을 자동으로 바꾸지 않는다. 빈 provider 설정은 계속 호출을 막는다.
SDK의 전체 시도 수는 1이며 생성 실패를 숨은 재시도로 바꾸지 않는다.

실험 키는 사용자가 승인한 프로젝트의 Free 증거와 동일한 gitignore 비밀 파일에서만 읽는다.
파일0600·상위 폴더0700을 확인하고 dotenv·`SecretStr`를 사용한다. 키를 명령행·프롬프트·
로그·예외·Git·보고서에 넣지 않는다. 키가 포함될 수 있는 SDK 원문 예외와 traceback 대신
안전한 오류 분류와 HTTP 상태만 남긴다. 미보고 token usage를 0 사용으로 해석하지 않는다.

생성 코드의 실행은 기존 gVisor·network none·read-only·nonroot 실행기뿐이다. 생성 provider의
키·네트워크 권한·호스트 파일은 실행기에 전달하지 않는다. SDK의 유한 I/O timeout은 호스트
전체 wall time의 정확한 상한 또는 브라우저 취소 즉시 provider 종료를 보증하지 않는다.

## 주문 계약

코드는 완료 봉에서 `hold|long|short|close` 의도만 반환한다. 공통 원장이 다음 봉 시가 진입과
수량·손절·익절·추적을 소유한다. 신호 완료 봉과 그 이전 완료 봉의 극값을 사용한다.
실제 진입가를 E, 두 봉 최저가를 L, 최고가를 H라 하면 long의 초기 R은 `1.1×(E−L)`,
short는 `1.1×(H−E)`다. 10%는 가격 자체가 아닌 위험 거리의 buffer다.

손실 방향1R에 SL, 이익 방향1.5R에서 최초 수량50%를 한 번 청산하고, 2R부터 비용 전
본절과 2R 거리 trailing을 적용한다. long/short는 대칭이며 비양수 R은 진입을 거부한다.
백테스트는 반대 신호에서 잔량 청산 뒤 반전한다. Demo는 flat·보호 취소를 확인한 다음
평가에서 새 같은 방향 의도가 있어야 재진입하므로 과거 반대 의도를 지연 실행하지 않는다.

## 검증 범위

가짜 provider 자동테스트는 preview 무저장·비활성 호출0회·Gemini 전용 호출·안전한 오류·
미보고 metadata·검토 적용·불변 버전 저장·미저장 실행 차단을 검증한다. CI Playwright는
실제 인증·전용 DB의 코드 저장과 생성 응답/백테스트 요청 대체 범위를 구분한다.
브라우저의 제출 성공은 실제 Python 계산 완료의 증거가 아니다.

실제 생성물의 공개 실행과 독립 의미 검증은 연구 전용 VM의 기존 gVisor runner에서 직접
수행한다. 워크트리와 다른 소스를 mount한 공유 Celery worker를 실행 증거로 사용하지 않는다.
작업 브랜치 head에 연결된 CI의 backend·frontend·여정 검증이 최종 품질 게이트다.
