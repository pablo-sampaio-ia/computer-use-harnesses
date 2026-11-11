"""Loop para agentes baseados em TEXTO (sem imagem): observa -> LLM escolhe ferramenta -> executa.

Diferente do loop de pixels: a "tela" chega como texto (DOM, arvore UIA...). Para controlar custo,
so a observacao MAIS RECENTE vai ao modelo; as anteriores sao descartadas (as acoes ficam no historico).
"""
import json


def run_tool_agent(llm, system, goal, observe, tools, max_steps=25, verbose=True):
    """tools: lista de (schema_json, funcao). `done` e uma ferramenta comum que encerra o loop.

    Devolve dict(done, steps, text, tokens_in, tokens_out).
    """
    schemas = [s for s, _ in tools]
    funcs = {s["name"]: f for s, f in tools}
    history = [{"role": "system", "content": system}, {"role": "user", "content": f"TAREFA: {goal}"}]
    stats = dict(done=False, steps=0, text="")

    for step in range(1, max_steps + 1):
        obs = observe()                           # texto, ou (texto, png) quando o agente tambem ve a tela
        text, images = obs if isinstance(obs, tuple) else (obs, None)
        cur = {"role": "user", "content": f"ESTADO ATUAL DA TELA:\n{text}"}
        if images:
            cur["images"] = images if isinstance(images, list) else [images]
        msg = llm.chat(history + [cur], schemas)
        history.append(msg.as_message())
        stats["steps"] = step
        if not msg.tool_calls:                    # o modelo respondeu em texto: encerrou
            stats["done"], stats["text"] = True, msg.content or ""
            break
        finished = False
        for call in msg.tool_calls:
            name, args = call["name"], json.loads(call["arguments"] or "{}")
            try:
                out = funcs[name](**args)
            except Exception as e:                # erro volta ao modelo
                out = f"ERRO: {type(e).__name__}: {e}"
            if verbose:
                print(f"  [{step}] {name}({args}) -> {str(out)[:80]}")
            history.append({"role": "tool", "tool_call_id": call["id"], "content": str(out)})
            if name == "done":
                finished, stats["text"] = True, args.get("resumo", "")
        if finished:
            stats["done"] = True
            break
    stats["tokens_in"], stats["tokens_out"] = llm.tokens_in, llm.tokens_out
    if verbose:
        print(f"fim: done={stats['done']} passos={stats['steps']} tokens={stats['tokens_in']}/{stats['tokens_out']}")
    return stats
