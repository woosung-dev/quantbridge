ARG PYTHON_BASE
FROM ${PYTHON_BASE}

RUN pip install --no-cache-dir numpy==2.2.6 pandas==2.3.3 \
    && groupadd --gid 10001 strategy \
    && useradd --uid 10001 --gid 10001 --no-create-home strategy
WORKDIR /runner
COPY infra/python-runner/main.py /runner/main.py
COPY apps/api/src/strategy/python_runtime/sdk.py /tmp/quantbridge_sdk.py
RUN python -c "import shutil, sysconfig; shutil.move('/tmp/quantbridge_sdk.py', sysconfig.get_path('purelib') + '/quantbridge_sdk.py')"
USER 10001:10001
ENTRYPOINT ["python", "-I", "-u", "/runner/main.py"]
