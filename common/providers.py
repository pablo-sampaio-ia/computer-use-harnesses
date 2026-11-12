"""Adaptadores finos para a ferramenta nativa de computer use de cada provedor.

Todos expoem a mesma interface:
    turn = provider.start(goal, png)          # primeira chamada
    turn = provider.reply(results, png)       # depois de executar as acoes
e devolvem `Turn(actions, text, ...)` com acoes NORMALIZADAS (classe Action).
Coordenadas das acoes estao no espaco da imagem que o modelo viu (ver Scaler).

ATENCAO: nomes de modelos/ferramentas mudam rapido. Confira nas docs oficiais:
  Anthropic: platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool
  OpenAI:    developers.openai.com/api/docs/guides/tools-computer-use
  Gemini:    aistudio.google.com/docs/computer-use
"""
import base64
import json
import os
from dataclasses import dataclass, field

from common.keys import to_xdotool


@dataclass
class Action:
    kind: str                 # screenshot click double_click move drag type key scroll wait
    x: int = 0
    y: int = 0
    x2: int = 0               # destino do drag
    y2: int = 0
    text: str = ""            # type / key
    dx: int = 0               # scroll em cliques de roda
    dy: int = 0
    button: str = "left"
    seconds: float = 1.0
    call_id: str = ""         # id da chamada no provedor
    name: str = ""            # nome original da acao (para devolver o resultado)


@dataclass
class Result:
    action: Action
    error: str = ""           # vazio = ok


@dataclass
class Turn:
    actions: list = field(default_factory=list)
    text: str = ""            # texto do modelo (resposta final quando nao ha acoes)
    tokens_in: int = 0
    tokens_out: int = 0
    safety: list = field(default_factory=list)   # mensagens que exigem aprovacao humana


def b64(png: bytes) -> str:
    return base64.b64encode(png).decode()


def as_dict(obj):
    """Objetos do SDK (pydantic) ou dicts -> dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(vars(obj))


def px_to_clicks(px, per_click=100):
    """Pixels de rolagem -> cliques de roda (pelo menos 1)."""
    return 0 if not px else (1 if abs(px) < per_click else round(px / per_click))


# --------------------------------------------------------------------------- OpenAI
class OpenAIProvider:
    """Responses API + ferramenta {"type": "computer"}. Acoes vem em lote (`actions`)."""

    def __init__(self, model=None, system=None):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_CU_MODEL", "gpt-6.1-sol")
        self.tools = [{"type": "computer"}]
        # `instructions` NAO e herdado via previous_response_id: precisa ir em TODA chamada.
        self.sys = {"instructions": system} if system else {}
        self.prev_id = None
        self.call_id = None
        self.pending_checks = []

    def _parse(self, resp):
        turn = Turn(text=getattr(resp, "output_text", "") or "")
        usage = getattr(resp, "usage", None)
        if usage:
            turn.tokens_in, turn.tokens_out = usage.input_tokens, usage.output_tokens
        self.prev_id = resp.id
        calls = [i for i in resp.output if i.type == "computer_call"]
        if calls:
            call = calls[0]
            self.call_id = call.call_id
            self.pending_checks = [as_dict(c) for c in (getattr(call, "pending_safety_checks", None) or [])]
            turn.safety = [c.get("message", str(c)) for c in self.pending_checks]
            for a in call.actions:
                turn.actions.append(self._action(as_dict(a), call.call_id))
        return turn

    @staticmethod
    def _action(a, call_id):
        t = a["type"]
        base = dict(call_id=call_id, name=t)
        if t == "keypress":
            return Action("key", text=to_xdotool(a["keys"]), **base)
        if t == "scroll":
            return Action("scroll", x=a.get("x", 0), y=a.get("y", 0),
                          dx=px_to_clicks(a.get("scroll_x", 0)), dy=px_to_clicks(a.get("scroll_y", 0)), **base)
        if t == "drag":
            p = a["path"]  # lista de pontos {x, y}
            return Action("drag", x=p[0]["x"], y=p[0]["y"], x2=p[-1]["x"], y2=p[-1]["y"], **base)
        if t == "wait":
            return Action("wait", seconds=2, **base)
        if t in ("click", "double_click", "move"):
            return Action(t, x=a.get("x", 0), y=a.get("y", 0), button=a.get("button", "left"), **base)
        if t == "type":
            return Action("type", text=a["text"], **base)
        return Action("screenshot", **base)

    def start(self, goal, png):
        # `png` NAO e usado de proposito. Na ferramenta `computer` da OpenAI, a tela chega como RESULTADO de uma chamada
        # (computer_call_output), e o modelo sempre comeca pedindo um `screenshot`. Testado: mandar o PNG junto com o
        # objetivo nao eliminou esse passo e ainda custou ~2,7 mil tokens a mais (8,2k contra 5,4k). Gemini e Anthropic
        # aceitam a imagem no 1o turno, entao la ela vai.
        return self._parse(self.client.responses.create(model=self.model, tools=self.tools, input=goal, **self.sys))

    def reply(self, results, png):
        item = {
            "type": "computer_call_output",
            "call_id": self.call_id,
            "output": {"type": "computer_screenshot",
                       "image_url": f"data:image/png;base64,{b64(png)}", "detail": "original"},
        }
        if self.pending_checks:
            item["acknowledged_safety_checks"] = self.pending_checks
        return self._parse(self.client.responses.create(
            model=self.model, tools=self.tools, previous_response_id=self.prev_id, input=[item], **self.sys))


# --------------------------------------------------------------------------- Gemini
class GeminiProvider:
    """Interactions API + ferramenta computer_use. Coordenadas normalizadas 0-999."""

    def __init__(self, model=None, image_size=(1280, 800), environment="desktop", system=None):
        from google import genai
        self.client = genai.Client()
        # A doc nao diz se `system_instruction` e herdado via previous_interaction_id: reenviamos sempre.
        self.sys = {"system_instruction": system} if system else {}
        self.model = model or os.getenv("GEMINI_CU_MODEL", "gemini-3.8-flash")
        self.tools = [{"type": "computer_use", "environment": environment}]
        self.w, self.h = image_size
        self.prev_id = None
        self.safety_ack = False

    def _px(self, x, y):
        return round(x / 1000 * self.w), round(y / 1000 * self.h)

    def _parse(self, it):
        turn = Turn()
        self.prev_id = it.id
        u = getattr(it, "usage", None)
        if u:
            turn.tokens_in = getattr(u, "total_input_tokens", 0) or 0
            turn.tokens_out = getattr(u, "total_output_tokens", 0) or 0
        for s in it.steps:
            if s.type == "model_output":
                turn.text += " ".join(b.text for b in s.content if b.type == "text")
            elif s.type == "function_call":
                a = as_dict(s.arguments) if not isinstance(s.arguments, str) else json.loads(s.arguments)
                sd = a.get("safety_decision")
                if sd and sd.get("decision") == "require_confirmation":
                    turn.safety.append(sd.get("explanation", "confirmar acao"))
                turn.actions.append(self._action(s.name, a, s.id))
        return turn

    def _action(self, name, a, call_id):
        base = dict(call_id=call_id, name=name)
        if name in ("click", "double_click", "right_click", "middle_click", "move"):
            x, y = self._px(a["x"], a["y"])
            kind = {"right_click": "click", "middle_click": "click"}.get(name, name)
            button = {"right_click": "right", "middle_click": "middle"}.get(name, "left")
            return Action(kind, x=x, y=y, button=button, **base)
        if name == "drag_and_drop":
            x, y = self._px(a["start_x"], a["start_y"])
            x2, y2 = self._px(a["end_x"], a["end_y"])
            return Action("drag", x=x, y=y, x2=x2, y2=y2, **base)
        if name == "type":
            # press_enter opcional: apendemos "\n" que o xdotool digita como Enter.
            return Action("type", text=a["text"] + ("\n" if a.get("press_enter") else ""), **base)
        if name in ("press_key",):
            return Action("key", text=to_xdotool(a["key"]), **base)
        if name == "hotkey":
            return Action("key", text=to_xdotool(a["keys"]), **base)
        if name == "scroll":
            x, y = self._px(a.get("x", 500), a.get("y", 500))
            n = px_to_clicks(a.get("magnitude_in_pixels", 300))
            d = a.get("direction", "down")
            return Action("scroll", x=x, y=y, dy=n if d == "down" else -n if d == "up" else 0,
                          dx=n if d == "right" else -n if d == "left" else 0, **base)
        if name == "wait":
            return Action("wait", seconds=a.get("seconds", 1), **base)
        return Action("screenshot", **base)   # take_screenshot e acoes nao suportadas

    def start(self, goal, png):
        it = self.client.interactions.create(
            model=self.model, tools=self.tools,
            input=[{"type": "text", "text": goal},
                   {"type": "image", "data": b64(png), "mime_type": "image/png"}], **self.sys)
        return self._parse(it)

    def reply(self, results, png):
        items = []
        for r in results:
            info = {"error": r.error} if r.error else {}
            if self.safety_ack:
                info["safety_acknowledgement"] = True
            items.append({
                "type": "function_result", "name": r.action.name, "call_id": r.action.call_id,
                "result": [{"type": "text", "text": json.dumps(info)},
                           {"type": "image", "data": b64(png), "mime_type": "image/png"}],
            })
        it = self.client.interactions.create(
            model=self.model, tools=self.tools, previous_interaction_id=self.prev_id, input=items, **self.sys)
        return self._parse(it)


# --------------------------------------------------------------------------- Anthropic
class AnthropicProvider:
    """Messages API + {"type": "computer_toolset_20260801"}. Cada acao e um tool_use."""

    NOT_RUN = "Not executed: an earlier computer action in this turn failed."

    def __init__(self, model=None, system=None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("ANTHROPIC_CU_MODEL", "claude-sonnet-5-5")
        self.tools = [{"type": "computer_toolset_20260801"}]
        self.sys = {"system": system} if system else {}      # aqui a API e sem estado: reenviamos sempre mesmo
        self.messages = []

    def _call(self):
        resp = self.client.messages.create(model=self.model, max_tokens=4096,
                                           tools=self.tools, messages=self.messages, **self.sys)
        self.messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
        turn = Turn(tokens_in=resp.usage.input_tokens, tokens_out=resp.usage.output_tokens)
        for b in resp.content:
            if b.type == "text":
                turn.text += b.text
            elif b.type == "tool_use":
                turn.actions.append(self._action(b.name, b.input, b.id))
        return turn

    @staticmethod
    def _action(name, i, call_id):
        base = dict(call_id=call_id, name=name)
        c = i.get("coordinate") or [0, 0]
        if name in ("left_click", "right_click", "middle_click"):
            return Action("click", x=c[0], y=c[1], button=name.split("_")[0], **base)
        if name == "double_click":
            return Action("double_click", x=c[0], y=c[1], **base)
        if name == "mouse_move":
            return Action("move", x=c[0], y=c[1], **base)
        if name == "left_click_drag":
            s = i["start_coordinate"]
            return Action("drag", x=s[0], y=s[1], x2=c[0], y2=c[1], **base)
        if name == "type":
            return Action("type", text=i["text"], **base)
        if name == "key":
            return Action("key", text=to_xdotool(i["text"]), **base)
        if name == "scroll":
            n, d = i.get("scroll_amount", 3), i.get("scroll_direction", "down")
            return Action("scroll", x=c[0], y=c[1], dy=n if d == "down" else -n if d == "up" else 0,
                          dx=n if d == "right" else -n if d == "left" else 0, **base)
        if name == "wait":
            return Action("wait", seconds=i.get("duration", 1), **base)
        return Action("screenshot", **base)   # screenshot, zoom, cursor_position...

    def start(self, goal, png):
        self.messages = [{"role": "user", "content": [
            {"type": "text", "text": goal},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(png)}}]}]
        return self._call()

    def reply(self, results, png):
        content = []
        last = len(results) - 1
        for n, r in enumerate(results):
            block = {"type": "tool_result", "tool_use_id": r.action.call_id, "toolset_name": "computer"}
            if r.error:
                block.update(is_error=True, content=r.error)
            elif n == last or r.action.kind == "screenshot":
                block["content"] = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(png)}}]
            else:
                block["content"] = "OK"
            content.append(block)
        self.messages.append({"role": "user", "content": content})
        return self._call()


def make_provider(name, image_size, model=None, system=None):
    """`image_size` so importa ao Gemini (coordenadas 0-999 -> pixels). `system`: instrucoes de sistema (opcional)."""
    if name == "openai":
        return OpenAIProvider(model, system)
    if name == "gemini":
        return GeminiProvider(model, image_size, system=system)
    if name == "anthropic":
        return AnthropicProvider(model, system)
    raise ValueError(f"provedor desconhecido: {name}")
