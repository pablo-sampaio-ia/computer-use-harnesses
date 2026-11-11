"""P6: agente HIBRIDO (DOM + pixels sob demanda) e PLANEJADOR/EXECUTOR.

1) Hibrido: por padrao o modelo recebe so o DOM textual (barato, preciso). A imagem so e anexada quando
   (a) a ultima acao falhou, (b) a lista de elementos veio vazia, ou (c) o modelo chamou `look()`.
   Tem ferramentas estruturadas (click/fill por ref) E de pixels (click_xy). Se o elemento nao existe no
   DOM (ex.: botao desenhado num <canvas>), o modelo "cai" para pixels.
2) Planejador/executor: um modelo forte quebra a tarefa em passos curtos; um modelo mais barato executa
   cada passo com o agente hibrido. Se um passo falha, o planejador replaneja UMA vez.

    uv run python -m p06_hibrido.agent --url http://localhost:8000/canvas "Cadastre ... e confirme"
    uv run python -m p06_hibrido.agent --plan --url ...        # com planejador/executor
Modelos: PLANNER_MODEL / EXECUTOR_MODEL (ou LLM_MODEL). Veja os nomes atuais na doc do provedor.
"""
import argparse
import json
import os

from playwright.sync_api import sync_playwright

from common.llm import LLM
from common.pw_computer import PlaywrightComputer
from common.toolloop import run_tool_agent
from p02_dom_a11y.agent import SNAPSHOT_JS, make_tools as dom_tools

SYSTEM = ("Voce opera um navegador. Normalmente recebe so a lista de elementos do DOM (use `ref`). Se o elemento que "
          "voce precisa NAO aparece na lista (ex.: botao desenhado em canvas), chame `look()` para ver a tela e use "
          "click_xy(x, y) com coordenadas da imagem. Depois de agir, verifique o resultado. Termine com `done`.")


class HybridAgent:
    def __init__(self, page, llm=None):
        self.page, self.pc = page, PlaywrightComputer(page, 1024, 768)
        self.llm = llm or LLM()
        self.want_image = False          # liga quando precisamos de pixels
        self.last_error = False
        self.pixel_steps = self.dom_steps = 0

    def tools(self):
        base = dom_tools(self.page)
        wrapped = []
        for schema, fn in base:             # embrulha as ferramentas de DOM para detectar falhas
            def guarded(*a, _fn=fn, **k):
                try:
                    self.dom_steps += 1
                    return _fn(*a, **k)
                except Exception:
                    self.last_error = True
                    raise
            wrapped.append((schema, guarded))

        def look():
            self.want_image = True
            return "ok: vou anexar a tela"

        def click_xy(x, y):
            self.pixel_steps += 1
            self.pc.click(x, y)
            return "ok"

        def type_text(text):
            self.pixel_steps += 1
            self.pc.type(text)
            return "ok"

        o = lambda p, r: {"type": "object", "properties": p, "required": r}
        extra = [
            ({"name": "look", "description": "Anexa um screenshot ao proximo estado", "parameters": o({}, [])}, look),
            ({"name": "click_xy", "description": "Clica em coordenadas da imagem (pixels)",
              "parameters": o({"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"])}, click_xy),
            ({"name": "type_text", "description": "Digita no elemento focado (apos click_xy)",
              "parameters": o({"text": {"type": "string"}}, ["text"])}, type_text),
        ]
        return wrapped + extra

    def observe(self):
        self.page.wait_for_load_state()
        elems = self.page.evaluate(SNAPSHOT_JS)
        # O TEXTO visivel e essencial: e nele que aparecem confirmacoes ("Cliente salvo") — sem ele o agente repete a acao.
        body = self.page.inner_text("body")[:1200]
        text = f"URL: {self.page.url}\nTEXTO:\n{body}\nELEMENTOS:\n" + ("\n".join(elems) or "(nenhum)")
        need_image = self.want_image or self.last_error or not elems
        self.want_image = self.last_error = False
        if need_image:
            return text + "\n[imagem anexada]", self.pc.screenshot()
        return text

    def run(self, goal, max_steps=20, verbose=True):
        s = run_tool_agent(self.llm, SYSTEM, goal, self.observe, self.tools(), max_steps, verbose)
        s.update(dom_steps=self.dom_steps, pixel_steps=self.pixel_steps)
        return s


# ------------------------------------------------------------------ planejador / executor
def plan(planner, goal, context=""):
    r = planner.chat([
        {"role": "system", "content": "Voce e um planejador. Quebre a tarefa em 2 a 6 passos curtos e verificaveis para "
         "um agente que opera um navegador. Responda APENAS com um array JSON de strings."},
        {"role": "user", "content": goal + (f"\n\nContexto de falha anterior: {context}" if context else "")}])
    txt = r.content[r.content.index("["): r.content.rindex("]") + 1]
    return json.loads(txt)


def run_plan(page, goal, verbose=True):
    planner = LLM(model=os.getenv("PLANNER_MODEL"))
    executor_llm = LLM(model=os.getenv("EXECUTOR_MODEL"))
    steps = plan(planner, goal)
    replanned = False
    i = 0
    while i < len(steps):
        if verbose:
            print(f"PASSO {i + 1}/{len(steps)}: {steps[i]}")
        s = HybridAgent(page, executor_llm).run(steps[i], max_steps=10, verbose=verbose)
        if s["done"]:
            i += 1
        elif not replanned:                          # replaneja uma vez, a partir do estado atual
            replanned = True
            steps = steps[:i] + plan(planner, goal, f"falhou no passo: {steps[i]}")
        else:
            break
    return dict(done=i >= len(steps), steps=i, planner_tokens=(planner.tokens_in, planner.tokens_out),
                executor_tokens=(executor_llm.tokens_in, executor_llm.tokens_out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--url", required=True)
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args()
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(args.url)
        print(run_plan(page, args.goal) if args.plan else HybridAgent(page).run(args.goal))
