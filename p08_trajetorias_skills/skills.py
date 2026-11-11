"""P8: trajetoria -> skill reexecutavel (sem LLM), com auto-correcao.

  record : o agente do P2 resolve a tarefa UMA vez (caro); cada passo e gravado com um LOCALIZADOR ESTAVEL
           (rotulo/papel/nome), nao com o `ref` efemero. Sai: runs/skills/<nome>/trajectory.jsonl + passo_N.png
  compile: a trajetoria vira uma funcao Python/Playwright PARAMETRIZADA (cada `fill` vira parametro)
  replay : roda a skill com novos valores, sem LLM (barato). Se um passo quebrar, o agente "cura": termina a tarefa
           pelo caminho caro e a skill pode ser regravada.
  viewer : pagina HTML estatica para auditar a trajetoria.

    uv run python -m p08_trajetorias_skills.skills record cadastro --url http://localhost:8000 "Cadastre ..."
    uv run python -m p08_trajetorias_skills.skills compile cadastro
    uv run python -m p08_trajetorias_skills.skills replay cadastro --url http://localhost:8000 nome_completo="Ana Lima" ...
"""
import argparse
import html
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from common.llm import LLM
from common.toolloop import run_tool_agent
from p02_dom_a11y.agent import SYSTEM, make_tools, observe_factory

ROOT = Path("runs/skills")

DESCRIBE_JS = """el => ({tag: el.tagName.toLowerCase(), type: el.type || '', id: el.id || '', name: el.name || '',
  label: (el.labels && el.labels[0]) ? el.labels[0].innerText.trim() : '', aria: el.getAttribute('aria-label') || '',
  placeholder: el.placeholder || '', text: (el.innerText || el.value || '').trim().slice(0, 60)})"""


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower().strip()).strip("_") or "campo"


def locator_code(d):
    """Descritor do elemento -> expressao Playwright, do mais ao menos estavel."""
    q = json.dumps
    d = {**d, "label": d["label"].split("\n")[0].strip()}      # <select> dentro de <label> traz o texto das opcoes
    if d["label"]:
        return f'page.get_by_label({q(d["label"], ensure_ascii=False)})', d["label"]
    if d["aria"]:
        return f'page.get_by_label({q(d["aria"], ensure_ascii=False)})', d["aria"]
    if d["tag"] == "button" or d["type"] in ("submit", "button"):
        return f'page.get_by_role("button", name={q(d["text"], ensure_ascii=False)})', d["text"]
    if d["tag"] == "a":
        return f'page.get_by_role("link", name={q(d["text"], ensure_ascii=False)})', d["text"]
    if d["placeholder"]:
        return f'page.get_by_placeholder({q(d["placeholder"], ensure_ascii=False)})', d["placeholder"]
    if d["name"]:
        return f'page.locator({q("[name=" + d["name"] + "]")})', d["name"]
    return f'page.locator({q("#" + d["id"])})', d["id"]


# ----------------------------------------------------------------------------- record
def record(name, url, goal, max_steps=25):
    out = ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    traj = []
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(url)
        tools = []
        for schema, fn in make_tools(page):
            def wrapped(*a, _fn=fn, _n=schema["name"], **k):
                ev = {"action": _n, **k}
                if "ref" in k:                                   # captura o localizador ANTES de agir
                    ev["element"] = page.locator(f'[data-ref="{k["ref"]}"]').evaluate(DESCRIBE_JS)
                res = _fn(*a, **k)
                ev["screenshot"] = f"passo_{len(traj) + 1}.png"
                page.screenshot(path=str(out / ev["screenshot"]))
                traj.append(ev)
                return res
            tools.append((schema, wrapped))
        stats = run_tool_agent(LLM(), SYSTEM, goal, observe_factory(page), tools, max_steps)
    (out / "trajectory.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in traj), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({"goal": goal, "url": url, "tokens": stats["tokens_in"]}, ensure_ascii=False))
    print(f"gravados {len(traj)} passos em {out}  (tokens da gravacao: {stats['tokens_in']})")


# ----------------------------------------------------------------------------- compile
def compile_skill(name):
    out = ROOT / name
    traj = [json.loads(l) for l in (out / "trajectory.jsonl").read_text(encoding="utf-8").splitlines()]
    params, body = {}, ["    page.goto(url)"]                  # toda skill comeca abrindo a URL
    for ev in traj:
        a = ev["action"]
        if a == "goto":
            continue
        elif a in ("fill", "select"):
            code, label = locator_code(ev["element"])
            pname = slug(label)
            params[pname] = ev.get("text", ev.get("option"))
            method = "fill" if a == "fill" else "select_option"
            arg = pname if a == "fill" else f"label={pname}"
            body.append(f"    {code}.{method}({arg})")
        elif a == "click":
            body.append(f"    {locator_code(ev['element'])[0]}.click()")
            body.append("    page.wait_for_load_state()")
        elif a == "press":
            body.append(f'    page.keyboard.press({json.dumps(ev["key"])})')
    sig = ", ".join([f'url="{json.loads((out / "meta.json").read_text())["url"]}"'] + [f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in params.items()])
    code = f'# Skill "{name}" gerada automaticamente da trajetoria gravada (sem LLM).\ndef run(page, {sig}):\n' + "\n".join(body) + "\n"
    (out / "skill.py").write_text(code, encoding="utf-8")
    print(code)


# ----------------------------------------------------------------------------- replay (+ cura)
def replay(name, url, values, heal=True):
    out = ROOT / name
    ns = {}
    exec((out / "skill.py").read_text(encoding="utf-8"), ns)
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.set_default_timeout(5000)           # falhar rapido: um seletor quebrado nao deve travar 30 s
        try:
            ns["run"](page, url=url, **values)
            print("skill executada SEM LLM: ok")
            return {"healed": False, "tokens": 0}
        except Exception as e:
            print(f"skill quebrou ({type(e).__name__}: {str(e).splitlines()[0][:120]}); "
                  f"{'curando com o agente...' if heal else 'abortando'}")
            if not heal:
                raise
            meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            page.goto(url)
            goal = (f"{meta['goal']}\n\nUSE ESTES VALORES (campos): {json.dumps(values, ensure_ascii=False)}. "
                    "A interface mudou em relacao ao que voce ja viu; descubra os rotulos novos.")
            s = run_tool_agent(LLM(), SYSTEM, goal, observe_factory(page), make_tools(page), 25)
            return {"healed": True, "tokens": s["tokens_in"]}


# ----------------------------------------------------------------------------- viewer
def viewer(name):
    out = ROOT / name
    rows = []
    for n, l in enumerate((out / "trajectory.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        ev = json.loads(l)
        desc = {k: v for k, v in ev.items() if k not in ("screenshot", "element", "action")}
        rows.append(f"<tr><td>{n}</td><td><b>{html.escape(ev['action'])}</b><br>{html.escape(json.dumps(desc, ensure_ascii=False))}"
                    f"<br><small>{html.escape(json.dumps(ev.get('element', ''), ensure_ascii=False))}</small></td>"
                    f"<td><img src='{ev['screenshot']}' width=360></td></tr>")
    (out / "viewer.html").write_text("<html><meta charset=utf-8><body style='font-family:sans-serif'>"
        f"<h2>Trajetoria: {html.escape(name)}</h2><table border=1 cellpadding=6>" + "".join(rows) + "</table></body></html>", encoding="utf-8")
    print(f"abra {out / 'viewer.html'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["record", "compile", "replay", "viewer"])
    ap.add_argument("name")
    ap.add_argument("goal_or_values", nargs="*", help="record: a tarefa; replay: param=valor ...")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--no-heal", action="store_true")
    a = ap.parse_args()
    if a.cmd == "record":
        record(a.name, a.url, " ".join(a.goal_or_values))
    elif a.cmd == "compile":
        compile_skill(a.name)
    elif a.cmd == "replay":
        replay(a.name, a.url, dict(kv.split("=", 1) for kv in a.goal_or_values), not a.no_heal)
    else:
        viewer(a.name)
