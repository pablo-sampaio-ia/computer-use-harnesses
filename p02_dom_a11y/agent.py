"""P2: agente de navegador por DOM/acessibilidade (sem imagens).

Em vez de um screenshot, o modelo recebe uma lista de elementos interativos:
    [3] textbox "E-mail" value=""
    [7] button "Salvar cliente"
e responde com ferramentas: click(ref=7), fill(ref=3, text="..."). Sem coordenadas, sem visao.

    uv run python -m p02_dom_a11y.agent --headed "Abra http://localhost:8000 e cadastre ..."
    uv run python -m p02_dom_a11y.agent --cdp http://localhost:9223 "..."     # Chromium do container
"""
import argparse
import subprocess
import time

from playwright.sync_api import sync_playwright

from common.llm import LLM
from common.toolloop import run_tool_agent

# Monta a lista de elementos interativos VISIVEIS e marca cada um com data-ref="N".
# (O Playwright MCP faz algo parecido com a arvore de acessibilidade; aqui o JS e explicito para ensinar.)
SNAPSHOT_JS = """() => {
  document.querySelectorAll('[data-ref]').forEach(e => e.removeAttribute('data-ref'));
  const sel = 'a[href],button,input,select,textarea,[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[onclick]';
  const out = []; let n = 0;
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect(), st = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || st.visibility === 'hidden' || st.display === 'none') continue;
    n++; el.setAttribute('data-ref', n);
    const tag = el.tagName.toLowerCase();
    const inputRole = {checkbox:'checkbox', radio:'radio', submit:'button', button:'button'};
    const role = el.getAttribute('role') || (tag === 'a' ? 'link' : tag === 'select' ? 'combobox'
               : tag === 'input' ? (inputRole[el.type] || 'textbox') : tag);
    let name = el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].innerText)
             || el.placeholder || el.innerText || el.value || el.title || el.name || '';
    name = name.replace(/\\s+/g, ' ').trim().slice(0, 80);
    let extra = '';
    if (['input','textarea','select'].includes(tag) && !['submit','button'].includes(el.type)) extra += ` value="${(el.value||'').slice(0,60)}"`;
    if (el.checked) extra += ' checked';
    if (tag === 'select') extra += ' options=[' + [...el.options].map(o => o.text).join(' | ') + ']';
    out.push(`[${n}] ${role} "${name}"${extra}`);
  }
  return out;
}"""

SYSTEM = ("Voce opera um navegador por ferramentas. A cada passo recebe a URL, o titulo, o texto visivel "
          "e a lista de elementos interativos numerados. Use `ref` com o numero do elemento. "
          "Os numeros mudam quando a pagina muda. Quando terminar, chame `done`.")


def make_tools(page):
    def loc(ref):
        return page.locator(f'[data-ref="{ref}"]')

    def goto(url):
        page.goto(url)
        return "ok"

    def click(ref):
        loc(ref).click(timeout=5000)
        page.wait_for_load_state()
        return "ok"

    def fill(ref, text):
        loc(ref).fill(text, timeout=5000)
        return "ok"

    def select(ref, option):
        loc(ref).select_option(label=option, timeout=5000)
        return "ok"

    def press(key):
        page.keyboard.press(key)
        return "ok"

    def done(resumo=""):
        return "fim"

    obj = lambda props, req: {"type": "object", "properties": props, "required": req}
    ref = {"ref": {"type": "integer"}}
    return [
        ({"name": "goto", "description": "Abre uma URL", "parameters": obj({"url": {"type": "string"}}, ["url"])}, goto),
        ({"name": "click", "description": "Clica no elemento", "parameters": obj(ref, ["ref"])}, click),
        ({"name": "fill", "description": "Preenche um campo de texto",
          "parameters": obj({**ref, "text": {"type": "string"}}, ["ref", "text"])}, fill),
        ({"name": "select", "description": "Escolhe uma opcao de um select",
          "parameters": obj({**ref, "option": {"type": "string"}}, ["ref", "option"])}, select),
        ({"name": "press", "description": "Pressiona uma tecla (ex.: Enter)",
          "parameters": obj({"key": {"type": "string"}}, ["key"])}, press),
        ({"name": "done", "description": "Encerra a tarefa", "parameters": obj({"resumo": {"type": "string"}}, [])}, done),
    ]


def observe_factory(page):
    def observe():
        page.wait_for_load_state()
        elems = page.evaluate(SNAPSHOT_JS)
        text = page.inner_text("body")[:1500]
        return f"URL: {page.url}\nTITULO: {page.title()}\nTEXTO:\n{text}\nELEMENTOS:\n" + "\n".join(elems)
    return observe


def run_on_page(page, goal, llm=None, max_steps=25, verbose=True):
    return run_tool_agent(llm or LLM(), SYSTEM, goal, observe_factory(page), make_tools(page), max_steps, verbose)


def bench_agent(computer, goal):
    """Variante para o benchmark: inicia o Chromium DO CONTAINER com CDP e conecta de fora."""
    computer.sh("sh", "-c", "pgrep -x socat >/dev/null || (nohup socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222 "
                ">/dev/null 2>&1 &); nohup chromium --remote-debugging-port=9222 about:blank >/dev/null 2>&1 &")
    time.sleep(4)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9223")
        page = browser.contexts[0].pages[0]
        return run_on_page(page, goal, verbose=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--cdp", help="URL CDP de um Chromium ja aberto (ex.: http://localhost:9223)")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    with sync_playwright() as p:
        if args.cdp:
            browser = p.chromium.connect_over_cdp(args.cdp)
            page = browser.contexts[0].pages[0]
        else:
            browser = p.chromium.launch(headless=not args.headed)
            page = browser.new_page()
        run_on_page(page, args.goal)
