"""Roda variantes de agente sobre as tarefas e imprime uma tabela.

    uv run python -m bench.run --agents p01:openai p01:gemini --tasks t01_nota t02_um_cliente
Requer o container no ar (uv run python docker/run.py up).
"""
import argparse
import json
import time

from bench.agents import AGENTS
from bench.tasks import TASKS, reset
from common.computer import ContainerComputer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", default=list(AGENTS))
    ap.add_argument("--tasks", nargs="*", help="ids; padrao: todas as tarefas linux")
    ap.add_argument("--container", default="cu-sandbox")
    ap.add_argument("--out", default="bench_results.jsonl")
    args = ap.parse_args()

    computer = ContainerComputer(args.container)
    sh = lambda cmd: computer.sh("sh", "-c", cmd).decode()
    tasks = [t for t in TASKS if t.kind in ("desktop", "web") and (not args.tasks or t.id in args.tasks)]

    rows = []
    for name in args.agents:
        for t in [t for t in tasks if t.kind in AGENTS[name][1]]:
            reset(sh)
            t0 = time.time()
            try:
                stats = AGENTS[name][0](computer, t.goal)
            except Exception as e:
                stats = dict(done=False, steps=0, tokens_in=0, tokens_out=0, text=f"EXC {e}")
            ok, detail = t.verify(sh)
            row = dict(agent=name, task=t.id, success=ok, steps=stats["steps"], tokens_in=stats["tokens_in"],
                       tokens_out=stats["tokens_out"], seconds=round(time.time() - t0), detail=detail)
            rows.append(row)
            print(f"{name:16} {t.id:18} {'OK ' if ok else 'FALHA'} passos={row['steps']:3} "
                  f"tok={row['tokens_in']}/{row['tokens_out']} {row['seconds']}s")
    with open(args.out, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
