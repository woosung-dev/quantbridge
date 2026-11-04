ARG PYTHON_BASE
FROM ${PYTHON_BASE}

# 2026-11-04 — numpy·pandas 버전은 build.sh 가 `apps/api/uv.lock` 에서 읽어 넘긴다(pine-runner 와 같은 방식).
#   종전 하드코딩 `numpy==2.2.6` 은 cp314 휠이 없어 python 3.14 베이스에서 빌드가 깨졌다.
ARG RUNNER_REQUIREMENTS
RUN pip install --no-cache-dir ${RUNNER_REQUIREMENTS} \
    && groupadd --gid 10001 strategy \
    && useradd --uid 10001 --gid 10001 --no-create-home strategy
WORKDIR /runner
COPY infra/python-runner/main.py /runner/main.py
COPY apps/api/src/strategy/python_runtime/sdk.py /tmp/quantbridge_sdk.py
RUN python -c "import shutil, sysconfig; shutil.move('/tmp/quantbridge_sdk.py', sysconfig.get_path('purelib') + '/quantbridge_sdk.py')"
USER 10001:10001
ENTRYPOINT ["python", "-I", "-u", "/runner/main.py"]
