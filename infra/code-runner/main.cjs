"use strict";

// 생성 코드는 이 파일과 함께 gVisor 내부에서만 컴파일·실행한다.
const fs = require("node:fs");
const readline = require("node:readline");
const { execFileSync } = require("node:child_process");
const path = require("node:path");

function emit(value) {
  const encoded = JSON.stringify(value);
  if (!encoded || Buffer.byteLength(encoded) > 65535) throw new Error("output limit");
  fs.writeSync(1, encoded + "\n");
}

function load(source) {
  const dir = fs.mkdtempSync("/tmp/qb-code-");
  fs.writeFileSync(path.join(dir, "strategy.ts"), source);
  fs.copyFileSync("/runner/sdk.d.ts", path.join(dir, "sdk.d.ts"));
  try {
    execFileSync(process.execPath, [
      "/opt/typescript/lib/tsc.js", "--strict", "--noEmitOnError",
      "--target", "ES2022", "--module", "commonjs", "--lib", "ES2022",
      "--types", "./sdk.d.ts", "--outDir", "./out", "strategy.ts",
    ], { cwd: dir, timeout: 60000, maxBuffer: 1048576, stdio: ["ignore", "pipe", "pipe"] });
  } catch (error) {
    const diagnostics = error.stdout ? error.stdout.toString() : error.message;
    throw new Error("TypeScript compile: " + diagnostics.slice(0, 1500));
  }
  // console가 JSONL과 섞이지 않는다. 직접 fd 출력은 호스트 출력 한도가 막는다.
  for (const method of ["log", "info", "warn", "error", "debug"]) console[method] = () => {};
  const strategy = require(path.join(dir, "out/strategy.js"));
  if (typeof strategy.onBar !== "function") throw new Error("onBar must be exported");
  return strategy;
}

async function main() {
  let strategy;
  let state;
  let params;
  const history = [];
  for await (const raw of readline.createInterface({ input: process.stdin, crlfDelay: Infinity })) {
    const message = JSON.parse(raw);
    if (!strategy) {
      if (message.type !== "init" || message.protocol !== 1) throw new Error("protocol mismatch");
      params = message.params;
      strategy = load(message.source);
      state = strategy.init ? strategy.init(params) : {};
      if (!state || typeof state !== "object" || Array.isArray(state) || typeof state.then === "function") {
        throw new Error("init must return a state object");
      }
      emit({ ready: 1 });
      continue;
    }
    if (message.type !== "bar") throw new Error("expected bar");
    history.push(message.bar);
    const intent = strategy.onBar({ bar: history.at(-1), history, position: message.position, params }, state);
    if (!intent || Object.keys(intent).length !== 1 ||
        !["hold", "long", "short", "close"].includes(intent.action)) {
      throw new Error("intent must contain only a valid action");
    }
    emit({ intent });
  }
}

main().catch((error) => {
  try { emit({ error: String(error).slice(0, 1800) }); } finally { process.exit(1); }
});
