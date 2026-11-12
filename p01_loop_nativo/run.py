"""P1: loop nativo de computer use, multi-provedor, no container.

    uv run python p01_loop_nativo/run.py --provider openai "Abra o Mousepad e escreva Ola"
    uv run python p01_loop_nativo/run.py --provider gemini --max-width 1024 "..."
    uv run python p01_loop_nativo/run.py --sweep "<tarefa>"     # experimento de resolucao

O loop em si esta em common/loop.py (~80 linhas). Aqui so ha a linha de comando.
"""
import argparse

from common.computer import ContainerComputer
import prompts
from common.loop import run_agent

ap = argparse.ArgumentParser()
ap.add_argument("goal")
ap.add_argument("--provider", default="openai", choices=["openai", "gemini", "anthropic"])
ap.add_argument("--model")
ap.add_argument("--container", default="cu-sandbox")
ap.add_argument("--max-steps", type=int, default=25)
ap.add_argument("--max-width", type=int, default=1280, help="largura que o modelo ve (escala)")
ap.add_argument("--sweep", action="store_true", help="repete a tarefa em varias resolucoes")
ap.add_argument("--system", help="nome de um prompt em prompts/ (ex.: computer_use_default); padrao: sem system prompt")
ap.add_argument("--system-file", help="caminho de um .md com o system prompt")
args = ap.parse_args()
system = prompts.load(args.system_file or args.system) if (args.system or args.system_file) else None

pc = ContainerComputer(args.container)
widths = [640, 1024, 1280] if args.sweep else [args.max_width]
for w in widths:
    print(f"=== largura enviada ao modelo: {w}px ===")
    s = run_agent(pc, args.goal, args.provider, args.model, args.max_steps, w, system_prompt=system)
    print(f"largura={w} done={s['done']} passos={s['steps']} tokens_in={s['tokens_in']} tokens_out={s['tokens_out']}")
