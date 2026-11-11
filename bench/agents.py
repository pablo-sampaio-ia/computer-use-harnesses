"""Registro das variantes de agente comparadas pelo benchmark.

Cada projeto acrescenta uma entrada:  nome -> (funcao, tipos de tarefa que suporta)
Um agente e uma funcao  (computer, goal) -> dict(done, steps, tokens_in, tokens_out, ...)
Agentes de DOM (P2) so conseguem tarefas "web"; agentes de pixels fazem "desktop" e "web".
"""
from common.loop import run_agent

ALL = {"desktop", "web"}


def _native(provider):
    def agent(computer, goal):
        return run_agent(computer, goal, provider=provider, max_steps=30,
                         approve=lambda msg: True,   # benchmark roda sem humano
                         verbose=False)
    return agent


AGENTS = {
    "p01:openai": (_native("openai"), ALL),
    "p01:gemini": (_native("gemini"), ALL),
    "p01:anthropic": (_native("anthropic"), ALL),
}

# Cada projeto registra a si mesmo aqui (import tardio evita dependencias pesadas desnecessarias).
try:
    from p02_dom_a11y.agent import bench_agent as _p02
    AGENTS["p02:dom"] = (_p02, {"web"})
except ImportError:
    pass

try:
    from p03_codigo_como_acao.agent import bench_agent as _p03
    AGENTS["p03:codigo"] = (_p03, {"web"})
except ImportError:
    pass
