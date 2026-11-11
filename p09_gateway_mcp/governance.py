"""Camada de governanca: politica, aprovacao humana, cofre de credenciais e auditoria.

Fica ENTRE o agente (qualquer cliente MCP) e o driver (navegador). O agente nunca a contorna.
"""
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel


class Policy(BaseModel):
    allowed_hosts: list[str] = ["localhost"]
    max_actions: int = 40
    max_seconds: int = 600
    send_patterns: list[str] = []
    deny_patterns: list[str] = []
    approval: str = "ask"

    @classmethod
    def load(cls, path):
        return cls(**yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def host_allowed(self, url):
        host = urlparse(url).hostname or ""
        return host in self.allowed_hosts or url.startswith(("about:", "data:"))

    def classify_click(self, name):
        if any(re.search(p, name, re.I) for p in self.deny_patterns):
            return "deny"
        if any(re.search(p, name, re.I) for p in self.send_patterns):
            return "send"
        return "write"


# --------------------------------------------------------------------------- cofre
class Vault:
    """Segredos ficam FORA do contexto do modelo. Fonte: variavel CU_SECRET_<ID> ou keyring (servico 'cu-harness')."""

    def get(self, secret_id):
        v = os.getenv(f"CU_SECRET_{secret_id.upper()}")
        if v is None:
            try:
                import keyring
                v = keyring.get_password("cu-harness", secret_id)
            except Exception:
                v = None
        if v is None:
            raise KeyError(f"segredo '{secret_id}' nao existe")
        return v

    def all_values(self):
        vals = [v for k, v in os.environ.items() if k.startswith("CU_SECRET_") and v]
        return vals

    def scrub(self, text):
        """Remove qualquer segredo conhecido de um texto (saida de ferramenta, log...)."""
        for v in self.all_values():
            text = text.replace(v, "***")
        return text


# --------------------------------------------------------------------------- auditoria
class Audit:
    def __init__(self, path, vault):
        self.path, self.vault = Path(path), vault
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, **ev):
        line = self.vault.scrub(json.dumps({"ts": round(time.time(), 2), **ev}, ensure_ascii=False))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# --------------------------------------------------------------------------- aprovacao humana
class Approver:
    """`ask`: abre uma paginazinha em http://localhost:8765 listando pedidos; o humano clica Aprovar/Negar."""

    def __init__(self, mode, port=8765):
        self.mode, self.pending, self.lock = mode, {}, threading.Lock()
        if mode == "ask":
            self._serve(port)

    def _serve(self, port):
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/decide/"):
                    _, _, rid, verdict = self.path.split("/")
                    with outer.lock:
                        if rid in outer.pending:
                            outer.pending[rid]["ok"] = verdict == "ok"
                            outer.pending[rid]["event"].set()
                    self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
                with outer.lock:
                    items = "".join(f"<li>{p['text']} <a href='/decide/{rid}/ok'>[Aprovar]</a> <a href='/decide/{rid}/no'>[Negar]</a></li>"
                                    for rid, p in outer.pending.items() if not p["event"].is_set())
                body = f"<meta http-equiv=refresh content=2><h2>Aprovacoes pendentes</h2><ul>{items or '<li>nenhuma</li>'}</ul>".encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(body)

            def log_message(self, *a):
                pass

        threading.Thread(target=HTTPServer(("127.0.0.1", port), H).serve_forever, daemon=True).start()

    def request(self, text, timeout=120):
        if self.mode == "auto_approve":
            return True
        if self.mode == "auto_deny":
            return False
        rid = str(len(self.pending) + 1)
        ev = threading.Event()
        with self.lock:
            self.pending[rid] = {"text": text, "event": ev, "ok": False}
        ev.wait(timeout)                         # sem resposta = NEGA
        return self.pending[rid]["ok"]
