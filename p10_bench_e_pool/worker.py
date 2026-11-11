"""Worker: roda UM agente numa tarefa dentro de UMA sessao e imprime o resultado como JSON na ultima linha.

Roda como SUBPROCESSO (o pool o mata no timeout): isolamento de falhas e timeouts reais.
    python -m p10_bench_e_pool.worker <agente> <tarefa> <base_url> <arquivo_estado>
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from common.pw_computer import PlaywrightComputer
from p10_bench_e_pool.tasks import BY_ID


def run(agent, page, goal, state_path):
    pc = PlaywrightComputer(page, 1024, 768)
    if agent == "p01:native":
        from common.loop import run_agent
        return run_agent(pc, goal, provider="openai", max_steps=25, approve=lambda m: True, verbose=False,
                         run_dir=f"runs/p10/{Path(state_path).parent.name}")
    if agent == "p02:dom":
        from p02_dom_a11y.agent import run_on_page
        return run_on_page(page, goal, verbose=False)
    if agent == "p03:codigo":
        from p03_codigo_como_acao.agent import run_on_page
        return run_on_page(page, goal, verbose=False)
    if agent == "p05:som":
        from p05_grounding_visual.agent import run_visual
        return run_visual(pc, goal, "som", verbose=False)
    if agent == "p06:hibrido":
        from p06_hibrido.agent import HybridAgent
        return HybridAgent(page).run(goal, verbose=False)
    if agent == "p07:robusto":
        from p07_robustez.robust import RobustAgent
        r = RobustAgent(pc, policy="last2", evidence=lambda: Path(state_path).read_text(encoding="utf-8")).run(goal, 0, verbose=False)
        return dict(done=r["success"], steps=r["steps"], text=r["text"], tokens_in=r["tokens_in"], tokens_out=r["tokens_out"])
    raise ValueError(agent)


if __name__ == "__main__":
    agent, task_id, base, state_path = sys.argv[1:5]
    task = BY_ID[task_id]
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(base + task.path)
        try:
            s = run(agent, page, task.goal, state_path)
            out = dict(done=bool(s.get("done")), steps=s.get("steps", 0), tokens_in=s.get("tokens_in", 0),
                       tokens_out=s.get("tokens_out", 0), answer=s.get("text", "") or "")
        except Exception as e:
            out = dict(done=False, steps=0, tokens_in=0, tokens_out=0, answer="", error=f"{type(e).__name__}: {e}"[:200])
    print("RESULT " + json.dumps(out, ensure_ascii=False))
