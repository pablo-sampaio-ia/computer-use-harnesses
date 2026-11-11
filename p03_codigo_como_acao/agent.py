"""P3: codigo como acao. O modelo nao clica: ele ESCREVE um script Playwright.

Uma unica ferramenta: run_code(code). O codigo roda com `page` (Playwright) ja aberto e `print`.
O harness devolve o que o script imprimiu, ou o erro. O modelo itera sobre as falhas.

Vantagem: um passo pode preencher 50 linhas com um `for`. Custo: muito mais dificil de auditar/limitar.

!! exec() NAO e um sandbox. Aqui so o NAVEGADOR e descartavel (container). Em producao, rode o codigo
!! gerado num processo/container isolado (ver P9 e P10). Nao aponte isto para sistemas reais.

    uv run python -m p03_codigo_como_acao.agent --headed "Abra http://localhost:8000 e cadastre ..."
"""
import argparse
import contextlib
import io
import time
import traceback

from playwright.sync_api import sync_playwright

from common.llm import LLM
from common.toolloop import run_tool_agent

SYSTEM = ("Voce controla um navegador escrevendo codigo Python com a API SINCRONA do Playwright. "
          "Ao chamar `run_code`, o codigo roda com a variavel `page` (pagina ja aberta) e voce NAO precisa importar nada. "
          "Voce nao ve a tela: use print() para inspecionar (ex.: print(page.inner_text('body')[:1000]), "
          "print(page.locator('input').count())). Prefira page.get_by_label / get_by_role / get_by_text. "
          "Seja eficiente: use loops para tarefas repetitivas. Depois de agir, VERIFIQUE com print antes de chamar `done`.")


def make_tools(page, log):
    def run_code(code):
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(code, {"page": page, "time": time, "print": print})
            res = out.getvalue()[:3000] or "(sem saida)"
        except Exception:
            res = (out.getvalue()[:1500] + "\nERRO:\n" + traceback.format_exc(limit=2)[-1500:])
        log.append(code)
        return res

    def done(resumo=""):
        return "fim"

    return [
        ({"name": "run_code", "description": "Executa codigo Python/Playwright; `page` ja existe. Devolve o que foi impresso.",
          "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}, run_code),
        ({"name": "done", "description": "Encerra a tarefa",
          "parameters": {"type": "object", "properties": {"resumo": {"type": "string"}}, "required": []}}, done),
    ]


def run_on_page(page, goal, llm=None, max_steps=15, verbose=True):
    log = []
    observe = lambda: f"URL: {page.url}\nTITULO: {page.title()}"      # sem DOM, sem imagem
    stats = run_tool_agent(llm or LLM(), SYSTEM, goal, observe, make_tools(page, log), max_steps, verbose)
    stats["code"] = log          # os scripts gerados sao uma trajetoria reexecutavel (ver P8)
    return stats


def bench_agent(computer, goal):
    computer.sh("sh", "-c", "pgrep -x socat >/dev/null || (nohup socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222 "
                ">/dev/null 2>&1 &); nohup chromium --remote-debugging-port=9222 about:blank >/dev/null 2>&1 &")
    time.sleep(4)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9223")
        return run_on_page(browser.contexts[0].pages[0], goal, verbose=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--cdp")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    with sync_playwright() as p:
        if args.cdp:
            page = p.chromium.connect_over_cdp(args.cdp).contexts[0].pages[0]
        else:
            page = p.chromium.launch(headless=not args.headed).new_page()
        s = run_on_page(page, args.goal)
        print("\n--- codigo gerado ---\n" + "\n#----\n".join(s["code"]))
