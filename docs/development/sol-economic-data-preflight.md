# 경제 CSV parser 전용 사전 검증

원 Mac/Linux 수치 생성 차이와 별개로 원 CSV parser의 결과가 달라지는지 경제 실행 전에 검사한다. 원13data파일과 원 loader의12cell parent/funding/execution 해시만 읽으며 선정·점수·ROI·신호·run_job·native는 읽거나 호출하지 않는다. 기존 source63/post7·workflow·semantic/경제 실행은 바꾸지 않는다.

전용 sol-economic-data-preflight.yml은 owner/public/same-repo PR925/첫 attempt/`sol-economic-data-preflight` label에 한해 무료 ubuntu-24.04-arm1대를 쓴다. root가 Mac12cell 기준을 exit0으로 생성하고 payload11,512,290바이트를 인증·게시했다. DATA_URL은 economic-data-preflight-v8.enc, SHA는0c5942f94b7d8a814d4510f37542ccb187e8b0af92769c961c3dd4750d9bcdc7로 고정했다. 원격 비교는 PENDING이다. 원 d5 base의 source/hostrequirements/pending만 재사용하고 Docker/runsc/image 설치·실행은 하지 않는다. 기존 경제/semantic helper와 분리된 새 파일만 추가한다.

root가 사용한 payload 생성·인증 명령의 형태는 다음과 같다.

```bash
python -B tools/research/sol_economic_data_preflight.py build \
  --directory ABS_NEW_PRIVATE_DATA_PAYLOAD --snapshot ABS_ORIGINAL_SNAPSHOT_JSON \
  --probe ABS_ARM_RUNNERS/tools/research/sol_economic_data_probe.py

python -B ABS_REVIEWED_CRYPTO encrypt \
  --input ABS_NEW_PRIVATE_DATA_PAYLOAD/data-preflight.tar.gz \
  --output ABS_NEW_PRIVATE_DATA_PAYLOAD/data-preflight.enc \
  --key-env SOL_RESEARCH_EPOCH7_KEY --context economic-data-preflight-input-v8
```

payload는 snapshot+10CSV+2source manifests+probe14개만 포함한다. 원 CSV·manifest SHA와 probe SHA를 확인하고 링크/extra/path escape/변경된 probe를 거절한다. 원 source는 기존 인증된 base에서 재사용한다. dependency step은 base가 기록한 정확 Python/numpy/pandas 버전을 설치하고 probe도 이를 대조한다. 복호화 키와 GitHub token은 probe child에 전달하지 않는다.

Mac 기준 결과도 같은 probe로 생성했다. 앱 `.env*`가 없는 **인증된 base/source**를 source-root로 사용하고, 빈 CWD·PATH만 가진 환경에서 원 numerical package 버전이 설치된 Python을 사용한다. probe는 버전/63+7원문/원snapshot SHA를 검증한다. 기준 생성 명령의 형태는 다음과 같다.

```bash
env -i PATH="$PATH" ABS_EXACT_PYTHON -B ABS_ARM_RUNNERS/tools/research/sol_economic_data_probe.py \
  --source-root ABS_AUTHENTICATED_BASE/source --pending ABS_AUTHENTICATED_BASE/inputs/pending.json \
  --snapshot ABS_ORIGINAL_SNAPSHOT_JSON --output ABS_NEW_PRIVATE_LOCAL_REFERENCE_JSON
```

probe는 원 sol_economic_data.load_snapshot/load_economic_cell을12번 호출한다. cells/frame_hash 두 함수만 SHA가 고정된 sol_economics.py의 원 AST에서 추출하고 경제 module 전체를 import하지 않는다. src·model·score·선정 module import와 socket/process 실행을 차단한다. historical1d도 parser 자체 검사용으로 읽지만 원 경제 정책에서는 계속 N_A다. 이 검사가 경제 분모/기간/NA/수식을 바꾸지 않는다.

원격 결과 asset은 `epoch8-economic-data-preflight-RUNID.enc`이며 문맥은 `economic-data-preflight-result-v8-RUNID`다. 모든 hash·actual wait/exit·private log/failure를 gzip/AES-GCM으로 보존한다. root는 asset metadata·암호문 SHA를 보존하고 실제 runid 문맥으로 인증 복호화한 뒤 비교한다. 공개 artifact/cache에 평문을 올리지 않는다.

```bash
python -B ABS_REVIEWED_CRYPTO decrypt --input ABS_REMOTE_RESULT_ENC \
  --output ABS_NEW_PRIVATE_RESULT_TAR_GZ --key-env SOL_RESEARCH_EPOCH7_KEY \
  --context economic-data-preflight-result-v8-ACTUAL_RUNID

python -B tools/research/sol_economic_data_preflight.py compare \
  --directory ABS_PRIVATE_COMPARISON_CONTEXT --local-result ABS_LOCAL_REFERENCE_JSON \
  --remote-result ABS_AUTHENTICATED_REMOTE_DATA_HASHES_JSON --output ABS_NEW_COMPARISON_PROOF_JSON
```

실제 원격 종료0/wait 및 인증 성공을 먼저 root가 확인한다. compare는 Mac/ARM Linux12개 cell 전체·원source/probe/snapshot·Python/package·해시가 정확히 같을 때만 새 proof를 쓴다. 하나라도 다르면 경제 dispatch를 시작하지 않고 원 CSV/parser 계약 차이로 보고한다. 성공도 경제 완료·ROI 검증이 아니다. 현재 증거는 synthetic10tests/ruff와 root의 Mac12cell 기준 생성 exit0이며 원격 비교는 PENDING이다.
