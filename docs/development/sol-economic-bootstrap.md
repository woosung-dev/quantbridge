# 봉인 후 경제 ARM bootstrap

계산 계약은 [Sol 전략 연구](./sol-strategy-lab.md)의 동결 경제 실행을 따른다. 경제 workflow는 기존 semantic workflow와 별개다. 전체 의미 검증 1,350건과 C8의 실제 종료 0을 확인한 봉인 후보 `A/python`의 payload만 사용한다. 원 1,440건·기간·계산·첫 semantic pass 선정은 유지하며, payload와 semantic execute overlay의 URL/SHA를 의존성 설치 전에 확인한다.

`sol-research-economics.yml`은 동일 소유자·공개 저장소·동일 저장소 PR925·첫 attempt·`sol-research-economics-execute` label만 받는다. 무료 표준 `ubuntu-24.04-arm` 40개 논리 host를 요청하고 각 실행 host는 4process를 사용한다. 원 ordinal 1440과 사전 고정 shuffle 배치를 유지하고, 이미 소비한 job을 재시도하지 않는다. 실제 품질 봉인 전에 label을 붙이거나 실행하지 않는다.

bootstrap은 고정 base → freq1h revision → root의 semantic execute overlay → 경제 delta 순서로 인증한다. 기존 helper의 SHA를 먼저 확인하고 dependency/runtime/crypto/cleanup만 재사용한다. 경제 delta는 새 디렉터리의 source/inputs 사본에 25개 허용 파일만 추가한다. 기존 파일 덮어쓰기와 링크를 거절하며, base pending·manifest·입력 inventory·helper·3image를 대조한다. 원 semantic helper/workflow는 수정하지 않는다.

Release의 `epoch8-economic-remote-XX.claim.json`을 새로 예약한 뒤 worker를 시작한다. worker에는 복호화 키·GitHub token을 전달하지 않는다. 신규 세션의 실제 worker 종료를 수거하고, process group이 남으면 guest cleanup을 거절한다. 보호된 원 guest 이미지/runsc와 격리 정책은 기존 runtime 검사를 그대로 사용한다.

결과는 모든 원 cache·receipt·비공개 로그를 gzip한 뒤 `result-v8-economic-N` 문맥으로 AES-GCM 암호화한다. `epoch8-economic-N-RUNID.enc`만 게시하며 압축본·암호문 각각 2GiB Release 한도를 넘으면 파일을 삭제하거나 요약하지 않고 중단한다. 원 cache의 `metrics`에는 `drawdown_curve`·`buy_and_hold_curve` 전체 배열이 포함된다. 6개월 분봉은 각 배열이 262,080개 점이므로 scalar metadata만으로 저장 용량을 추정하지 않는다. cache와 receipt에 반복되는 전체 곡선도 보존 대상이다.

별도 root 수신기는 내려받은 asset metadata/암호문 SHA·size·run/shard를 대조하고 EOF/MAC 성공을 수거한 뒤에만 gzip tar를 읽는다. 성공한 worker·4lane·guest0·claim/plan/source binding만 새 비공개 host inbox에 단일 writer로 게시한다. 모든 cache와 비공개 wrapper/log는 `_bootstrap/`에 보존한다. 실패 pack은 진단 경로에 남고 계산 결과로 승격되지 않는다. 수신기는 경제 journal/report writer가 아니며 최종1440·family720+720·입력 해시 검증은 별도 원 root finalizer의 권한이다.

수신 후 저장 최적화는 완료 host만 대상으로 하며 원문 SHA와 경로를 유지한 투명 압축·동일 파일 hardlink를 사용할 수 있다. 원 암호문을 보존하고 gzip 전체 멤버가 인증된 파일 지도와 일치하는지 검증한 뒤 임시 복호화 archive만 정리한다. 이때 관측한 gzip SHA를 원 receiver가 기록하지 않은 plaintext SHA인 것처럼 표시하지 않는다. 중단된 다운로드와 실패 관측은 덮지 않고 별도 수거 epoch가 검증된 완료물만 채택한다. 계산·생성·실패 결과를 다시 실행하는 재개와 구분한다.

로컬 암호문 다운로드 cache를 비울 때는 해당 host의 수신·압축 실제 종료 0과 전체 원문 SHA, 현재 Release asset의 정확 ID·size·SHA256을 먼저 대조하고 증거를 동기 저장한다. 동일 암호문의 Release·tag·asset과 로컬 비공개 복호화 키는 이후 정리 대상에서 제외한다. 이는 현재 원격 사본의 관측이지 미래 보존을 보장하는 서비스 약속이 아니다. 새 수거 epoch가 로컬 cipher를 요구하면 원 asset을 같은 SHA로 복원하기 전에는 재채택할 수 없다. 원 cache·receipt·곡선은 로컬에 모두 유지한다.

root 집계가 전체 결과를 동시에 메모리에 올리지 못하면 원 계산 함수는 유지하고 receipt 경로·SHA 인덱스와 한 건씩 처리하는 저장 계층을 사용한다. report용 메모리 입력의 곡선 제외 전에 전체 metrics의 중복 충돌을 검사한다. 원 전체 results/journal은 원 JSON 바이트를 복원하는 lossless gzip과 압축·해제 SHA/길이로 보존하며, 부분 출력은 전체1440·720+720·source·cache·원 report 검증 후에만 게시한다. 저장 최적화를 새 수익률 계산이나 후보 재선정으로 사용하지 않는다.

합성 검사와 원 Mac/ARM Linux loader의 12개 입력 해시 동일성을 확인했다. 경제 payload의 plan SHA는 `2b4a8733076041a08562e6ba34d6fc32b59f84f09a0fbc7fd37ba4bfe5bb592f`, 암호문 SHA는 `6a69ba2645aa0d4b96c11a932d64991c4c6b916979b1639598ea6070d616f18d`다. 입력 준비·인증과 실제 경제 실행의 완료는 별개이며, 최종 판정은 원격 영수증과 root의 1,440건 finalize를 따른다.

경제 전용 배치는 seed20261022를 유지한40host×4=160논리lane이며 각 host36job/lane9job이다. 의미 평가의 local6+remote16과 품질 봉인 계약은 변경하지 않는다. 실제 동시수는 계정 한도(Free20/Pro40)에 따르고 초과 요청은 queue되며 유료 runner로 fallback하지 않는다. 슬롯 증가를 실측 가속이나 결과 동등성의 증명으로 보지 않는다.
