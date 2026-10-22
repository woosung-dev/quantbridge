# 봉인 후 경제 ARM bootstrap

계산 계약은 [Sol 전략 연구](./sol-strategy-lab.md)의 동결 경제 실행을 따른다. 경제 workflow는 기존 semantic workflow와 별개다. 전체 의미 검증 1,350건과 C8의 실제 종료 0을 확인한 봉인 후보 `A/python`의 payload만 사용한다. 원 1,440건·기간·계산·첫 semantic pass 선정은 유지하며, payload와 semantic execute overlay의 URL/SHA를 의존성 설치 전에 확인한다.

`sol-research-economics.yml`은 동일 소유자·공개 저장소·동일 저장소 PR925·첫 attempt·`sol-research-economics-execute` label만 받는다. 무료 표준 `ubuntu-24.04-arm` 40개 논리 host를 요청하고 각 실행 host는 4process를 사용한다. 원 ordinal 1440과 사전 고정 shuffle 배치를 유지하고, 이미 소비한 job을 재시도하지 않는다. 실제 품질 봉인 전에 label을 붙이거나 실행하지 않는다.

bootstrap은 고정 base → freq1h revision → root의 semantic execute overlay → 경제 delta 순서로 인증한다. 기존 helper의 SHA를 먼저 확인하고 dependency/runtime/crypto/cleanup만 재사용한다. 경제 delta는 새 디렉터리의 source/inputs 사본에 25개 허용 파일만 추가한다. 기존 파일 덮어쓰기와 링크를 거절하며, base pending·manifest·입력 inventory·helper·3image를 대조한다. 원 semantic helper/workflow는 수정하지 않는다.

Release의 `epoch8-economic-remote-XX.claim.json`을 새로 예약한 뒤 worker를 시작한다. worker에는 복호화 키·GitHub token을 전달하지 않는다. 신규 세션의 실제 worker 종료를 수거하고, process group이 남으면 guest cleanup을 거절한다. 보호된 원 guest 이미지/runsc와 격리 정책은 기존 runtime 검사를 그대로 사용한다.

결과는 모든 원 cache·receipt·비공개 로그를 gzip한 뒤 `result-v8-economic-N` 문맥으로 AES-GCM 암호화한다. `epoch8-economic-N-RUNID.enc`만 게시하며 압축본·암호문 각각 2GiB Release 한도를 넘으면 파일을 삭제하거나 요약하지 않고 중단한다. 현재 원 run_job cache는 binding·metrics·count·해시를 저장하고 equity/minute 배열 본문은 저장하지 않는다. 실제 payload 크기는 미관측이므로 분할 필요 여부는 확인 전이다.

별도 root 수신기는 내려받은 asset metadata/암호문 SHA·size·run/shard를 대조하고 EOF/MAC 성공을 수거한 뒤에만 gzip tar를 읽는다. 성공한 worker·4lane·guest0·claim/plan/source binding만 새 비공개 host inbox에 단일 writer로 게시한다. 모든 cache와 비공개 wrapper/log는 `_bootstrap/`에 보존한다. 실패 pack은 진단 경로에 남고 계산 결과로 승격되지 않는다. 수신기는 경제 journal/report writer가 아니며 최종1440·family720+720·입력 해시 검증은 별도 원 root finalizer의 권한이다.

합성 검사와 원 Mac/ARM Linux loader의 12개 입력 해시 동일성을 확인했다. 경제 payload의 plan SHA는 `2b4a8733076041a08562e6ba34d6fc32b59f84f09a0fbc7fd37ba4bfe5bb592f`, 암호문 SHA는 `6a69ba2645aa0d4b96c11a932d64991c4c6b916979b1639598ea6070d616f18d`다. 입력 준비·인증과 실제 경제 실행의 완료는 별개이며, 최종 판정은 원격 영수증과 root의 1,440건 finalize를 따른다.

경제 전용 배치는 seed20261022를 유지한40host×4=160논리lane이며 각 host36job/lane9job이다. 의미 평가의 local6+remote16과 품질 봉인 계약은 변경하지 않는다. 실제 동시수는 계정 한도(Free20/Pro40)에 따르고 초과 요청은 queue되며 유료 runner로 fallback하지 않는다. 슬롯 증가를 실측 가속이나 결과 동등성의 증명으로 보지 않는다.
