"""P1 contra um NAVEGADOR REAL isolado (Chromium headless do Playwright), sem Docker e sem tocar no seu desktop.

O agente ve a pagina como pixels e age com mouse/teclado, igual ao loop do container; so que a "tela" e a pagina.
Requer o sistema legado no ar (ver GUIA_DE_TESTES.md, secao 2) e `uv run playwright install chromium`.

    uv run python -m p01_loop_nativo.web_test openai
    uv run python -m p01_loop_nativo.web_test gemini --url http://localhost:8000/v2
"""
import argparse

from playwright.sync_api import sync_playwright

import prompts
from common.loop import run_agent
from common.pw_computer import PlaywrightComputer

ap = argparse.ArgumentParser()
ap.add_argument("provider", choices=["openai", "gemini", "anthropic"])
ap.add_argument("--url", default="http://localhost:8000")
ap.add_argument("--goal", default="Cadastre o cliente 'Maria Souza', e-mail maria@exemplo.com, "
                                  "clicando em 'Salvar cliente'.")
ap.add_argument("--system", help="nome de um prompt em prompts/ (ex.: computer_use_default); padrao: sem system prompt")
ap.add_argument("--system-file", help="caminho de um .md com o system prompt")
args = ap.parse_args()
system = prompts.load(args.system_file or args.system) if (args.system or args.system_file) else None

with sync_playwright() as p:
    page = p.chromium.launch().new_page()          # headless: nenhuma janela aparece
    page.goto(args.url)                            # a "tela" nao tem barra de endereco: abra a URL antes
    pc = PlaywrightComputer(page, 1024, 768)
    # approve=...: sem humano para aprovar pedidos de seguranca do provedor (e um sistema de teste)
    run_agent(pc, args.goal, provider=args.provider, max_steps=20, approve=lambda m: True,
              system_prompt=system)
print("Confira o estado: cat runs/clientes.jsonl   |  prints de cada passo em runs/<data>-<provedor>/")
