"""O loop agentico: screenshot -> modelo -> acoes -> screenshot -> ...

Este arquivo e o coracao da trilha. Os projetos seguintes trocam o Computer,
o Provider ou acrescentam pecas ao redor deste loop.
"""
import json
import time
from pathlib import Path

from common.images import Scaler
from common.providers import Result, make_provider
from prompts import load_env_prompt

NOT_RUN = "Not executed: an earlier computer action in this turn failed."


def execute(computer, scaler, a):
    """Executa UMA acao normalizada na tela real."""
    k = a.kind
    if k in ("click", "double_click", "move", "scroll"):
        x, y = scaler.to_screen(a.x, a.y)
    if k == "click":
        computer.click(x, y, a.button)
    elif k == "double_click":
        computer.double_click(x, y)
    elif k == "move":
        computer.move(x, y)
    elif k == "drag":
        (x1, y1), (x2, y2) = scaler.to_screen(a.x, a.y), scaler.to_screen(a.x2, a.y2)
        computer.drag(x1, y1, x2, y2)
    elif k == "type":
        computer.type(a.text)
    elif k == "key":
        computer.key(a.text)
    elif k == "scroll":
        computer.scroll(x, y, a.dx, a.dy)
    elif k == "wait":
        time.sleep(min(a.seconds, 10))
    # "screenshot" nao faz nada: o screenshot e tirado depois de qualquer acao.


def ask_human(message):
    return input(f"\n[APROVACAO] {message}\nExecutar? [s/N] ").strip().lower() == "s"


def run_agent(computer, goal, provider="openai", model=None, max_steps=25, max_width=1280,
              approve=ask_human, run_dir=None, verbose=True, system_prompt=None):
    """Roda o agente ate o modelo parar de pedir acoes ou estourar `max_steps`.

    `system_prompt`: texto de instrucoes de sistema (opcional). Se None, usa o arquivo apontado pela variavel
    CU_SYSTEM_PROMPT_FILE, se existir; senao NAO ha system prompt (so o objetivo). Veja a pasta prompts/.
    Devolve dict com: done, steps, text, tokens_in, tokens_out, run_dir.
    """
    system_prompt = system_prompt or load_env_prompt()
    scaler = Scaler(computer.width, computer.height, max_width)
    prov = make_provider(provider, (scaler.model_w, scaler.model_h), model, system_prompt)
    run_dir = Path(run_dir or f"runs/{time.strftime('%Y%m%d-%H%M%S')}-{provider}")
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = open(run_dir / "trace.jsonl", "w", encoding="utf-8")

    def shot():
        return scaler.to_model_image(computer.screenshot())

    stats = dict(done=False, steps=0, text="", tokens_in=0, tokens_out=0, run_dir=str(run_dir))
    png = shot()
    turn = prov.start(goal, png)

    for step in range(1, max_steps + 1):
        stats["tokens_in"] += turn.tokens_in
        stats["tokens_out"] += turn.tokens_out
        if turn.text:
            stats["text"] = turn.text
        if not turn.actions:                       # o modelo parou: tarefa "concluida"
            stats["done"] = True
            break
        if turn.safety and not approve("; ".join(turn.safety)):
            stats["text"] = "interrompido: aprovacao humana negada"
            break
        if turn.safety and hasattr(prov, "safety_ack"):
            prov.safety_ack = True

        results, failed = [], False
        for a in turn.actions:
            if failed:
                results.append(Result(a, NOT_RUN))
                continue
            try:
                execute(computer, scaler, a)
                results.append(Result(a))
            except Exception as e:                 # ensina: erro volta ao modelo, nao derruba o loop
                failed = True
                results.append(Result(a, f"{type(e).__name__}: {e}"))
            if verbose:
                print(f"  [{step}] {a.kind} {a.text or (a.x, a.y)}" + (f"  ERRO {results[-1].error}" if results[-1].error else ""))
        time.sleep(0.5)                            # deixa a interface atualizar
        png = shot()
        (run_dir / f"step_{step:03d}.png").write_bytes(png)
        trace.write(json.dumps({"step": step, "text": turn.text,
                                "actions": [vars(r.action) | {"error": r.error} for r in results],
                                "tokens_in": turn.tokens_in, "tokens_out": turn.tokens_out},
                               ensure_ascii=False) + "\n")
        stats["steps"] = step
        turn = prov.reply(results, png)
    trace.close()
    if verbose:
        print(f"fim: done={stats['done']} passos={stats['steps']} tokens={stats['tokens_in']}/{stats['tokens_out']}")
    return stats
