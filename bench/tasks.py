"""Tarefas do mini-benchmark (v0) e seus verificadores.

Regra de ouro: verificar o ESTADO do mundo (arquivo, registro no sistema),
nunca o que o agente diz ter feito nem o que aparece na tela.

`sh(cmd)` roda um comando shell dentro do container e devolve o texto.
"""
import json
import time
from dataclasses import dataclass
from typing import Callable

STATE = "/tmp/state/clientes.jsonl"
URL = "http://localhost:8000"


@dataclass
class Task:
    id: str
    goal: str
    verify: Callable          # (sh) -> (ok: bool, detalhe: str)
    kind: str = "desktop"     # desktop (precisa de apps) | web (so navegador) | windows (P4)


def _file(sh, path):
    return sh(f"cat {path} 2>/dev/null || true")


def v_nota(sh):
    txt = _file(sh, "/home/agent/Documents/nota.txt").strip()
    return txt == "Ola, mundo!", f"conteudo={txt!r}"


def _clientes(sh):
    out = _file(sh, STATE)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def v_um_cliente(sh):
    rs = _clientes(sh)
    ok = len(rs) == 1 and rs[0].get("nome") == "Maria Souza" and rs[0].get("email") == "maria@exemplo.com"
    return ok, f"registros={rs}"


LISTA = [("Ana Lima", "ana@exemplo.com", "11 90000-0001"),
         ("Bruno Costa", "bruno@exemplo.com", "11 90000-0002"),
         ("Carla Dias", "carla@exemplo.com", "11 90000-0003")]


def v_tres_clientes(sh):
    rs = _clientes(sh)
    got = {(r.get("nome"), r.get("email"), r.get("telefone")) for r in rs}
    return len(rs) == 3 and got == set(LISTA), f"registros={len(rs)}"


def v_protocolo(sh):
    txt = _file(sh, "/home/agent/Documents/protocolo.txt").strip()
    return txt == "PRT-7421-XK", f"conteudo={txt!r}"


_LISTA_TXT = "\n".join(f"- {n}, {e}, {t}" for n, e, t in LISTA)

TASKS = [
    Task("t01_nota",
         "Abra o editor de texto (Mousepad), escreva exatamente 'Ola, mundo!' e salve o arquivo como "
         "/home/agent/Documents/nota.txt.", v_nota),
    Task("t02_um_cliente",
         f"No navegador (Chromium) abra {URL} e cadastre o cliente 'Maria Souza', e-mail maria@exemplo.com, "
         "tipo 'Pessoa fisica', clicando em 'Salvar cliente'.", v_um_cliente, "web"),
    Task("t03_tres_clientes",
         f"No navegador (Chromium) abra {URL} e cadastre TODOS os clientes abaixo (nome, e-mail, telefone), "
         f"um por vez, usando 'Salvar cliente':\n{_LISTA_TXT}", v_tres_clientes, "web"),
    Task("t04_leitura",
         f"No navegador (Chromium) abra {URL}/info, leia o codigo de protocolo e escreva-o (somente o codigo) "
         "no Mousepad, salvando em /home/agent/Documents/protocolo.txt.", v_protocolo),
]


def reset(sh):
    """Volta o container ao estado inicial entre tarefas."""
    sh("pkill -x mousepad; pkill -f chromium; rm -f /tmp/state/clientes.jsonl /home/agent/Documents/*; "
       "touch /tmp/state/clientes.jsonl; true")
    time.sleep(1)
