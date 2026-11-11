"""P7: robustez do loop de pixels — contexto, verificacao e retentativa.

Agente so de pixels (visao + ferramentas click_xy/type_text/press_key/scroll/done) com HISTORICO CONTROLADO POR NOS
(provedor sem estado). Tres pecas novas:
  1) Politica de contexto: `all` (ingenua), `last2` (so os 2 ultimos screenshots), `summary` (last2 + resumo do passado).
  2) Deteccao de "a tela nao mudou" apos cada acao (diferenca de imagem) -> o modelo e avisado.
  3) Verificador final com saida ESTRUTURADA (pydantic); se reprovar, um novo ciclo recebe o motivo.

    uv run python -m p07_robustez.robust --policy last2 --url http://localhost:8000 "Cadastre ..."
"""
import argparse
import io
import json
import time

from PIL import Image, ImageChops
from pydantic import BaseModel

from common.llm import LLM
from common.pw_computer import PlaywrightComputer

SYSTEM = ("Voce opera uma tela so por imagem (coordenadas em pixels da imagem). Use as ferramentas. Depois de cada acao "
          "voce recebe a tela nova e, se a tela nao mudou, um aviso. Termine com `done` somente quando o resultado estiver "
          "visivel e correto na tela.")


class Verdict(BaseModel):
    success: bool
    reason: str


def screen_changed(a: bytes, b: bytes, thr=0.5) -> bool:
    """True se a diferenca media (cinza, 96x72) passa de `thr` niveis. Sem dependencias extras
    (para algo mais robusto: SSIM com scikit-image ou hash perceptual com imagehash)."""
    f = lambda x: Image.open(io.BytesIO(x)).convert("L").resize((96, 72))
    diff = ImageChops.difference(f(a), f(b))
    return sum(diff.getdata()) / (96 * 72) > thr


def verify(llm, goal, png, evidence="") -> Verdict:
    """So a tela final raramente prova uma tarefa com varios itens: passe EVIDENCIA de estado quando houver."""
    r = llm.chat([{"role": "user", "images": [png], "content":
                   f"Tarefa pedida: {goal}\nEvidencia de estado do sistema (fonte confiavel):\n{evidence or '(nenhuma)'}\n"
                   "A tela final esta na imagem. A tarefa foi CUMPRIDA? "
                   'Responda so com JSON {"success": bool, "reason": str}.'}])
    return Verdict.model_validate_json(r.content[r.content.index("{"): r.content.rindex("}") + 1])


class RobustAgent:
    def __init__(self, pc, llm=None, policy="last2", max_steps=25, evidence=lambda: ""):
        self.evidence = evidence          # funcao -> texto com o ESTADO real (ex.: registros salvos)
        self.pc, self.llm, self.policy, self.max_steps = pc, llm or LLM(), policy, max_steps
        self.keep = {"all": 10**9, "last2": 2, "summary": 2}[policy]
        self.summarizer, self.last_text = LLM(), ""
        self.tools = self._tools()

    def _tools(self):
        o = lambda p, r: {"type": "object", "properties": p, "required": r}
        i = {"type": "integer"}
        return [
            {"name": "click_xy", "description": "Clica em (x, y)", "parameters": o({"x": i, "y": i}, ["x", "y"])},
            {"name": "type_text", "description": "Digita texto", "parameters": o({"text": {"type": "string"}}, ["text"])},
            {"name": "press_key", "description": "Tecla (Return, Tab, ctrl+s)", "parameters": o({"key": {"type": "string"}}, ["key"])},
            {"name": "scroll", "description": "Rola (positivo=baixo)", "parameters": o({"dy": i}, ["dy"])},
            {"name": "done", "description": "Encerra", "parameters": o({"resumo": {"type": "string"}}, [])},
        ]

    def _act(self, name, a):
        pc = self.pc
        if name == "click_xy":
            pc.click(a["x"], a["y"])
        elif name == "type_text":
            pc.type(a["text"])
        elif name == "press_key":
            pc.key(a["key"])
        elif name == "scroll":
            pc.scroll(pc.width // 2, pc.height // 2, 0, a["dy"])

    def _trim(self, history):
        """Politica de contexto: mantem imagens so nas ultimas `keep` observacoes."""
        idx = [n for n, m in enumerate(history) if m.get("images")]
        old = set(idx[:-self.keep]) if len(idx) > self.keep else set()
        out = []
        for n, m in enumerate(history):
            if n in old:
                m = {k: v for k, v in m.items() if k != "images"} | {"content": m["content"] + " [screenshot antigo omitido]"}
            out.append(m)
        return out

    def run_once(self, goal, extra="", verbose=True):
        history = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"TAREFA: {goal}\n{extra}"}]
        prev, steps, summary = None, 0, ""
        for steps in range(1, self.max_steps + 1):
            png = self.pc.screenshot()
            note = "" if prev is None or screen_changed(prev, png) else "AVISO: a tela NAO mudou desde a acao anterior."
            prev = png
            history.append({"role": "user", "content": f"Tela atual. {note} {summary}", "images": [png]})
            reply = self.llm.chat(self._trim(history), self.tools)
            history.append(reply.as_message())
            if not reply.tool_calls:
                break
            done = False
            for c in reply.tool_calls:
                args = json.loads(c["arguments"] or "{}")
                try:
                    self._act(c["name"], args)
                    out = "ok"
                except Exception as e:
                    out = f"ERRO: {e}"
                if verbose:
                    print(f"  [{steps}] {c['name']}({args}) {note}")
                history.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                if c["name"] == "done":
                    done, self.last_text = True, args.get("resumo", "")
            if done:
                break
            time.sleep(0.4)
            if self.policy == "summary" and steps % 4 == 0:          # resume o passado remoto
                acts = [t for m in history if m["role"] == "assistant" for t in m.get("tool_calls", [])]
                summary = "Resumo do que ja foi feito: " + self.summarizer.chat([{"role": "user", "content":
                    "Resuma em 2 frases o progresso, dadas estas acoes: " + json.dumps(acts, ensure_ascii=False)[:3000]}]).content
        return steps, self.pc.screenshot()

    def run(self, goal, max_retries=1, verbose=True):
        """Executa; verifica; se reprovar, tenta de novo com o motivo (ate `max_retries`)."""
        extra = ""
        for attempt in range(max_retries + 1):
            steps, png = self.run_once(goal, extra, verbose)
            v = verify(self.llm, goal, png, self.evidence())
            if verbose:
                print(f"verificador: success={v.success} ({v.reason})")
            if v.success:
                break
            # IDEMPOTENCIA: sem isto a retentativa duplica o que ja foi feito.
            extra = (f"A tentativa anterior foi reprovada: {v.reason}.\nEstado atual do sistema:\n{self.evidence()}\n"
                     "Faca SOMENTE o que falta; NAO repita itens que ja constam no estado.")
        return dict(success=v.success, reason=v.reason, attempts=attempt + 1, steps=steps, text=self.last_text,
                    tokens_in=self.llm.tokens_in + self.summarizer.tokens_in, tokens_out=self.llm.tokens_out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--url", required=True)
    ap.add_argument("--policy", choices=["all", "last2", "summary"], default="last2")
    ap.add_argument("--evidence-file", help="arquivo com o estado real do sistema (ex.: runs/clientes.jsonl)")
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        page = p.chromium.launch().new_page()
        page.goto(args.url)
        ev = (lambda: open(args.evidence_file, encoding="utf-8").read()) if args.evidence_file else (lambda: "")
        print(RobustAgent(PlaywrightComputer(page, 1024, 768), policy=args.policy, evidence=ev).run(args.goal, args.retries))
