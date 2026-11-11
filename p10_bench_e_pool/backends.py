"""Backends de sandbox: cada SESSAO tem seu proprio "sistema legado" com estado isolado.

  LocalProcessBackend : um processo do legacy_app por sessao (porta livre + arquivo de estado proprio). Roda em qualquer lugar.
  DockerBackend       : um container por sessao (isolamento forte; noVNC para ver ao vivo). NAO TESTADO nesta maquina (sem Docker).
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Session:
    base_url: str
    read_state: callable          # () -> texto do estado do sistema (para verificar)
    close: callable


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception:
            time.sleep(0.3)
    raise TimeoutError(f"sistema legado nao subiu em {url}")


class LocalProcessBackend:
    def start(self) -> Session:
        port = _free_port()
        state = Path(tempfile.mkdtemp(prefix="cu-sess-")) / "clientes.jsonl"
        state.write_text("", encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(ROOT / "docker" / "legacy_app.py")],
                                env={**os.environ, "LEGACY_PORT": str(port), "LEGACY_STATE": str(state)},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}"
        _wait(base)
        return Session(base, lambda: state.read_text(encoding="utf-8"), proc.kill)


class DockerBackend:
    """Um container por sessao; o agente (Playwright no host) acessa a porta mapeada do sistema legado."""
    IMAGE = "cu-harness"

    def start(self) -> Session:
        port = _free_port()
        name = f"cu-sess-{port}"
        subprocess.run(["docker", "run", "-d", "--name", name, "-p", f"{port}:8000", self.IMAGE],
                       check=True, capture_output=True)
        base = f"http://127.0.0.1:{port}"
        _wait(base)
        read = lambda: subprocess.run(["docker", "exec", name, "cat", "/tmp/state/clientes.jsonl"],
                                      capture_output=True, text=True).stdout
        return Session(base, read, lambda: subprocess.run(["docker", "rm", "-f", name], capture_output=True))


BACKENDS = {"local": LocalProcessBackend, "docker": DockerBackend}
