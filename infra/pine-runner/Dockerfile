ARG PYTHON_BASE
FROM ${PYTHON_BASE}
ARG PINE_REQUIREMENTS
RUN pip install --no-cache-dir ${PINE_REQUIREMENTS} \
    && groupadd --gid 10001 strategy \
    && useradd --uid 10001 --gid 10001 --no-create-home strategy
WORKDIR /runner
# 환경 파일·연구 결과는 복사하지 않는다. Pine 해석기 원본은 앱의 SSOT 그대로다.
COPY apps/api/src /runner/src
USER 10001:10001
ENTRYPOINT ["python", "-I", "-u", "/runner/src/strategy/code_runtime/pine_worker.py"]
