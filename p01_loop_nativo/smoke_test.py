"""Teste de fumaça SEM Docker: tela simulada com um botao. Gasta poucos tokens.

    uv run python -m p01_loop_nativo.smoke_test openai
"""
import sys

from common.fake_computer import FakeComputer
from common.loop import run_agent

provider = sys.argv[1] if len(sys.argv) > 1 else "openai"
pc = FakeComputer()
stats = run_agent(pc, "Clique no botao OK que aparece na tela e depois diga 'pronto'.",
                  provider=provider, max_steps=6, approve=lambda m: True, run_dir=f"runs/smoke-{provider}")
print("cliques:", pc.log)
print("botao acionado:", pc.pressed)
sys.exit(0 if pc.pressed else 1)
