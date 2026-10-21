"""격리 transport 계약. unittest 직접 실행도 가능하며 DB·Celery를 사용하지 않는다."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import unittest
from typing import Any
from unittest.mock import Mock, patch

from src.strategy.code_runtime.models import CodeLanguage, CodeRuntimeError
from src.strategy.code_runtime.sandbox import DockerCodeTransport, create_transport
from src.strategy.python_runtime.protocol import PythonRunnerTimeout, PythonRuntimeError
from src.strategy.python_runtime.sandbox import DockerPythonTransport, sandbox_command


def bar(index: int = 0) -> dict[str, Any]:
    return {
        "type": "bar",
        "bar": {
            "index": index,
            "timestamp": f"2026-01-01T0{index}:00:00+00:00",
            **dict.fromkeys(("open", "high", "low", "close", "volume"), "100"),
        },
        "position": {"size": "0", "direction": "flat", "average_price": None},
    }


class SandboxContractTests(unittest.TestCase):
    def fake_transport(self) -> DockerCodeTransport:
        transport = object.__new__(DockerCodeTransport)
        transport.language = CodeLanguage.python
        transport._ready = False
        transport.close = Mock()  # type: ignore[method-assign]
        return transport

    def test_init_then_action_only_and_no_reinitialization(self) -> None:
        transport = self.fake_transport()
        with patch.object(
            DockerPythonTransport,
            "exchange",
            side_effect=[{"ready": 1}, {"intent": {"action": "close"}}],
        ):
            self.assertEqual(
                transport.exchange({"type": "init", "protocol": 1, "source": "code", "params": {}}),
                {"ready": 1},
            )
            self.assertEqual(transport.exchange(bar()), {"intent": {"action": "close"}})
            with self.assertRaises(CodeRuntimeError):
                transport.exchange({"type": "init"})
        transport.close.assert_called_once()  # type: ignore[attr-defined]

    def test_numeric_exit_and_malformed_reply_close_transport(self) -> None:
        for reply in (
            {"intent": {"action": "long", "stop_loss": "90"}},
            {"intent": {"action": "buy"}},
            {"intent": {"action": "hold"}, "pnl": "100"},
        ):
            with self.subTest(reply=reply):
                transport = self.fake_transport()
                transport._ready = True
                with (
                    patch.object(DockerPythonTransport, "exchange", return_value=reply),
                    self.assertRaises(CodeRuntimeError),
                ):
                    transport.exchange(bar())
                transport.close.assert_called_once()  # type: ignore[attr-defined]

    def test_invalid_language_or_deadline_never_starts_docker(self) -> None:
        with patch.object(DockerPythonTransport, "__init__") as start:
            for language in ("pine", "javascript", "unknown"):
                with self.subTest(language=language), self.assertRaises(CodeRuntimeError):
                    create_transport(language)
            for timeout in (0, -1, float("nan"), float("inf")):
                with self.subTest(timeout=timeout), self.assertRaises(CodeRuntimeError):
                    create_transport("python", timeout=timeout)
            start.assert_not_called()

    def test_commands_never_mount_host_or_use_plain_runc(self) -> None:
        command = sandbox_command("sha256:" + "a" * 64, "qb-python-probe")
        for option in (
            "--runtime=runsc",
            "--network=none",
            "--read-only",
            "--user=10001:10001",
            "--cpus=1",
            "--memory=1g",
            "--pids-limit=64",
            "--cap-drop=ALL",
        ):
            self.assertIn(option, command)
        self.assertFalse(
            any(item.startswith(("--volume", "--mount", "--env-file")) for item in command)
        )
        self.assertNotIn("--privileged", command)


class RealGvisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        docker = shutil.which("docker")
        if docker is None:
            raise unittest.SkipTest("Docker CLI가 없습니다")
        try:
            result = subprocess.run(
                [docker, "info", "--format", "{{json .Runtimes}}"],
                capture_output=True,
                timeout=10,
                check=True,
            )
            if "runsc" not in json.loads(result.stdout):
                raise unittest.SkipTest("runsc runtime이 없습니다")
            for image in ("quantbridge-python-runner:local", "quantbridge-typescript-runner:local"):
                subprocess.run(
                    [docker, "image", "inspect", image], capture_output=True, timeout=10, check=True
                )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise unittest.SkipTest("연구용 gVisor 이미지가 없습니다") from exc

    def start(self, language: str, source: str) -> DockerCodeTransport:
        transport = create_transport(language, timeout=30)
        self.addCleanup(transport.close)
        self.assertEqual(
            transport.exchange(
                {
                    "type": "init",
                    "protocol": 1,
                    "language": language,
                    "source": source,
                    "params": {},
                }
            ),
            {"ready": 1},
        )
        return transport

    def test_both_languages_execute_history_state_and_close_intent(self) -> None:
        sources = {
            "python": "def on_bar(ctx,state):\n state['n']=state.get('n',0)+1\n return {'action':'close' if len(ctx['history'])==state['n']==2 else 'hold'}",
            "typescript": "export function onBar(ctx: Context,state: Record<string,unknown>): Intent {state.n=Number(state.n??0)+1;return {action:ctx.history.length===state.n&&state.n===2?'close':'hold'};}",
        }
        for language, source in sources.items():
            with self.subTest(language=language):
                transport = self.start(language, source)
                self.assertEqual(transport.exchange(bar()), {"intent": {"action": "hold"}})
                self.assertEqual(transport.exchange(bar(1)), {"intent": {"action": "close"}})

    def test_python_cannot_access_host_files_network_or_app_secrets(self) -> None:
        source = """import os,socket
def on_bar(ctx,state):
 assert not os.path.exists('/Users/woosung')
 assert not os.environ.get('TRADING_ENCRYPTION_KEYS')
 try: open('/runner/probe','w').write('escape')
 except OSError: pass
 else: raise ValueError('root filesystem writable')
 try: connection=socket.create_connection(('1.1.1.1',80),timeout=0.3)
 except OSError: pass
 else: connection.close(); raise ValueError('external network reachable')
 return {'action':'hold'}
"""
        self.assertEqual(
            self.start("python", source).exchange(bar()), {"intent": {"action": "hold"}}
        )

    def test_typescript_cannot_access_host_files_network_or_app_secrets(self) -> None:
        source = """declare function require(name:string): any;
declare const process: {execPath:string;env:Record<string,string|undefined>};
export function onBar(ctx:Context,state:Record<string,unknown>):Intent {
 const fs=require('node:fs');
 if(fs.existsSync('/Users/woosung')||process.env.TRADING_ENCRYPTION_KEYS) throw Error('host access');
 let blocked=false;
 try {fs.writeFileSync('/runner/probe','escape');} catch {blocked=true;}
 if(!blocked) throw Error('root filesystem writable');
 require('node:child_process').execFileSync(process.execPath,['-e',
  "const net=require('node:net');const s=net.connect(80,'1.1.1.1');s.on('error',()=>process.exit(0));s.setTimeout(300,()=>process.exit(0));s.on('connect',()=>process.exit(2));"
 ],{timeout:2000,stdio:'ignore'});
 return {action:'hold'};
}
"""
        self.assertEqual(
            self.start("typescript", source).exchange(bar()), {"intent": {"action": "hold"}}
        )

    def test_strict_compile_error_is_not_executed(self) -> None:
        with self.assertRaisesRegex(PythonRuntimeError, "TypeScript compile"):
            self.start(
                "typescript",
                "const n:number='invalid'; export function onBar(){return {action:'hold'};}",
            )

    def test_invalid_intent_and_output_flood_fail_closed(self) -> None:
        sources = {
            "python": "def on_bar(ctx,state): return {'action':'long','stop_loss':'90'}",
            "typescript": "export function onBar(ctx:Context,state:Record<string,unknown>) {return {action:'long',stop_loss:'90'};}",
        }
        for language, source in sources.items():
            with self.subTest(language=language):
                transport = self.start(language, source)
                with self.assertRaises(PythonRuntimeError):
                    transport.exchange(bar())
                self.assertIsNone(transport._process)
        source = (
            "import os\ndef on_bar(ctx,state):\n os.write(1,b'x'*70000)\n return {'action':'hold'}"
        )
        transport = self.start("python", source)
        with self.assertRaisesRegex(PythonRuntimeError, "출력 한도"):
            transport.exchange(bar())
        self.assertIsNone(transport._process)

    def test_infinite_loops_timeout_and_containers_are_removed(self) -> None:
        sources = {
            "python": "def on_bar(ctx,state):\n while True: pass",
            "typescript": "export function onBar(ctx:Context,state:Record<string,unknown>):Intent {while(true){};}",
        }
        for language, source in sources.items():
            with self.subTest(language=language):
                transport = self.start(language, source)
                transport.deadline = time.monotonic() + 0.3
                with self.assertRaises(PythonRunnerTimeout):
                    transport.exchange(bar())
                self.assertIsNone(transport._process)
                result = subprocess.run(
                    ["docker", "container", "inspect", transport.name],
                    capture_output=True,
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
