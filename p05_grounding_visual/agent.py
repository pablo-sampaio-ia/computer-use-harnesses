"""P5: agente de pixels SEM a ferramenta nativa de computer use. Dois jeitos de "localizar":

  --mode som     Set-of-Mark: o OCR numera os elementos; o modelo diz "clique na caixa 7".
  --mode ground  Planejador diz O QUE ("clique no botao Salvar"); um GROUNDER devolve ONDE (x, y).
                 O grounder pode ser um modelo aberto local (UI-TARS etc.).

Roda sobre qualquer `Computer` (container, navegador Playwright...).
    uv run python -m p05_grounding_visual.agent --mode som --url http://localhost:8000 "Cadastre ..."
"""
import argparse
import time

from common.llm import LLM
from common.toolloop import run_tool_agent
from p05_grounding_visual.grounding import locate, make_grounder
from p05_grounding_visual.marks import detect_grid, detect_ocr, draw_marks

SYSTEM_SOM = ("Voce opera uma tela so por imagem. A imagem tem caixas vermelhas NUMERADAS sobre o texto detectado por OCR. "
              "Para clicar, use click_mark(mark=N) (clica no centro da caixa; dx/dy deslocam em pixels, util para clicar num "
              "campo vazio ao lado de seu rotulo). Depois de clicar num campo, use type_text. Numeros mudam a cada passo. "
              "Verifique o resultado na imagem seguinte e chame `done` ao terminar.")

SYSTEM_GROUND = ("Voce opera uma tela so por imagem. Para clicar, descreva o elemento em linguagem natural com "
                 "click_on(description=...): outro modelo achara as coordenadas. Depois de clicar num campo de texto, "
                 "use type_text. Verifique o resultado na imagem seguinte e chame `done` ao terminar.")


def make_tools(pc, mode, state, grounder=None):
    def click_mark(mark, dx=0, dy=0):
        x1, y1, x2, y2, _ = state["boxes"][mark - 1]
        pc.click((x1 + x2) // 2 + dx, (y1 + y2) // 2 + dy)
        return "ok"

    def click_on(description):
        x, y = locate(grounder, state["png"], description, pc.width, pc.height)
        pc.click(x, y)
        return f"cliquei em ({x},{y})"

    def type_text(text):
        pc.type(text)
        return "ok"

    def press_key(key):
        pc.key(key)
        return "ok"

    def scroll(dy):
        pc.scroll(pc.width // 2, pc.height // 2, 0, dy)
        return "ok"

    def done(resumo=""):
        return "fim"

    obj = lambda props, req: {"type": "object", "properties": props, "required": req}
    common = [
        ({"name": "type_text", "description": "Digita texto no elemento focado", "parameters": obj({"text": {"type": "string"}}, ["text"])}, type_text),
        ({"name": "press_key", "description": "Tecla/atalho no estilo xdotool (Return, Tab, ctrl+s)", "parameters": obj({"key": {"type": "string"}}, ["key"])}, press_key),
        ({"name": "scroll", "description": "Rola (positivo = para baixo)", "parameters": obj({"dy": {"type": "integer"}}, ["dy"])}, scroll),
        ({"name": "done", "description": "Encerra a tarefa", "parameters": obj({"resumo": {"type": "string"}}, [])}, done),
    ]
    if mode == "som":
        head = ({"name": "click_mark", "description": "Clica numa caixa numerada",
                 "parameters": obj({"mark": {"type": "integer"}, "dx": {"type": "integer"}, "dy": {"type": "integer"}}, ["mark"])}, click_mark)
    else:
        head = ({"name": "click_on", "description": "Clica no elemento descrito",
                 "parameters": obj({"description": {"type": "string"}}, ["description"])}, click_on)
    return [head] + common


def run_visual(pc, goal, mode="som", detector="ocr", llm=None, max_steps=20, verbose=True):
    state = {"boxes": [], "png": b""}
    grounder = make_grounder() if mode == "ground" else None

    def observe():
        time.sleep(0.5)
        png = pc.screenshot()
        state["png"] = png
        if mode == "som":
            boxes = detect_ocr(png) if detector == "ocr" else detect_grid(png)
            state["boxes"] = boxes
            marked, legend = draw_marks(png, boxes)
            return f"Caixas detectadas:\n{legend}", marked
        return f"Tela {pc.width}x{pc.height}.", png

    system = SYSTEM_SOM if mode == "som" else SYSTEM_GROUND
    stats = run_tool_agent(llm or LLM(), system, goal, observe, make_tools(pc, mode, state, grounder), max_steps, verbose)
    if grounder:
        stats["tokens_in"] += grounder.tokens_in
        stats["tokens_out"] += grounder.tokens_out
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--mode", choices=["som", "ground"], default="som")
    ap.add_argument("--detector", choices=["ocr", "grid"], default="ocr")
    ap.add_argument("--url", help="abre esta URL num Chromium headless (Playwright) e usa a pagina como tela")
    ap.add_argument("--container", help="usa o container Docker como tela")
    args = ap.parse_args()
    if args.container:
        from common.computer import ContainerComputer
        run_visual(ContainerComputer(args.container), args.goal, args.mode, args.detector)
    else:
        from playwright.sync_api import sync_playwright
        from common.pw_computer import PlaywrightComputer
        with sync_playwright() as p:
            page = p.chromium.launch().new_page()
            page.goto(args.url)
            run_visual(PlaywrightComputer(page, 1024, 768), args.goal, args.mode, args.detector)
