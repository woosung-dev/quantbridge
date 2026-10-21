ARG NODE_BASE
FROM ${NODE_BASE}
ARG TYPESCRIPT_VERSION
RUN npm install --global --prefix /opt/typescript-install "typescript@${TYPESCRIPT_VERSION}" \
    && mv /opt/typescript-install/lib/node_modules/typescript /opt/typescript \
    && groupadd --gid 10001 strategy \
    && useradd --uid 10001 --gid 10001 --no-create-home strategy
WORKDIR /runner
COPY infra/code-runner/main.cjs infra/code-runner/sdk.d.ts /runner/
USER 10001:10001
ENTRYPOINT ["node", "/runner/main.cjs"]
