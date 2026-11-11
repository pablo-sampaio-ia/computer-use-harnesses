"""LLM de texto com chamada de ferramentas.

Usado pelos agentes que NAO usam a ferramenta nativa de computer use (P2, P3, P4, P6...).
Duas "linguas" por baixo, uma interface so:
  - OpenAI  -> Responses API (alguns modelos novos nao aceitam ferramentas em Chat Completions)
  - Gemini / modelos abertos (vllm, Ollama) -> Chat Completions compativel com OpenAI

Mensagens neutras:
  {"role": "system"|"user", "content": str, "images": [png bytes] (opcional, so user)}
  {"role": "assistant", "content": str, "tool_calls": [{"id", "name", "arguments"(json str)}]}
  {"role": "tool", "tool_call_id": str, "content": str}

Variaveis: LLM_PROVIDER=openai|gemini|local  LLM_MODEL=...  LLM_BASE_URL=...
"""
import os
import base64
from dataclasses import dataclass, field

from openai import OpenAI

DEFAULTS = {
    "openai": (None, "OPENAI_API_KEY", "gpt-6.1-sol", "responses"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "gemini-3.8-flash", "chat"),
    "local": ("http://localhost:8001/v1", None, "local-model", "chat"),
}


# Custo de imagem depende do "detail": low (barato, ilegivel p/ texto pequeno) < high < original.
IMAGE_DETAIL = os.getenv("LLM_IMAGE_DETAIL", "high")


def _data_url(png):
    return "data:image/png;base64," + base64.b64encode(png).decode()


@dataclass
class Reply:
    content: str = ""
    tool_calls: list = field(default_factory=list)   # [{"id", "name", "arguments"}]

    def as_message(self):
        return {"role": "assistant", "content": self.content, "tool_calls": self.tool_calls}


class LLM:
    def __init__(self, provider=None, model=None):
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        base, key_env, default_model, self.api = DEFAULTS[provider]
        self.client = OpenAI(base_url=os.getenv("LLM_BASE_URL", base),
                             api_key=(os.getenv(key_env) if key_env else "none"))
        self.model = model or os.getenv("LLM_MODEL", default_model)
        self.tokens_in = self.tokens_out = 0

    def chat(self, messages, tools=None) -> Reply:
        return (self._responses if self.api == "responses" else self._chat)(messages, tools or [])

    # ---- Responses API
    def _responses(self, messages, tools):
        items = []
        for m in messages:
            if m["role"] == "tool":
                items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": m["content"]})
            elif m["role"] == "assistant":
                if m["content"]:
                    items.append({"role": "assistant", "content": m["content"]})
                for c in m.get("tool_calls", []):
                    items.append({"type": "function_call", "call_id": c["id"], "name": c["name"],
                                  "arguments": c["arguments"]})
            elif m.get("images"):
                parts = [{"type": "input_text", "text": m["content"]}] + [
                    {"type": "input_image", "image_url": _data_url(i), "detail": IMAGE_DETAIL} for i in m["images"]]
                items.append({"role": m["role"], "content": parts})
            else:
                items.append({"role": m["role"], "content": m["content"]})
        kw = dict(model=self.model, input=items)
        if tools:
            kw["tools"] = [{"type": "function", **t} for t in tools]
        r = self.client.responses.create(**kw)
        self.tokens_in += r.usage.input_tokens
        self.tokens_out += r.usage.output_tokens
        reply = Reply(content=r.output_text or "")
        for o in r.output:
            if o.type == "function_call":
                reply.tool_calls.append({"id": o.call_id, "name": o.name, "arguments": o.arguments})
        return reply

    # ---- Chat Completions
    def _chat(self, messages, tools):
        msgs = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                msgs.append({"role": "assistant", "content": m["content"] or None, "tool_calls": [
                    {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in m["tool_calls"]]})
            elif m.get("images"):
                parts = [{"type": "text", "text": m["content"]}] + [
                    {"type": "image_url", "image_url": {"url": _data_url(i), "detail": IMAGE_DETAIL}} for i in m["images"]]
                msgs.append({"role": m["role"], "content": parts})
            else:
                msgs.append(m)
        kw = dict(model=self.model, messages=msgs)
        if tools:
            kw["tools"] = [{"type": "function", "function": t} for t in tools]
        r = self.client.chat.completions.create(**kw)
        if r.usage:
            self.tokens_in += r.usage.prompt_tokens
            self.tokens_out += r.usage.completion_tokens
        msg = r.choices[0].message
        return Reply(content=msg.content or "", tool_calls=[
            {"id": c.id, "name": c.function.name, "arguments": c.function.arguments} for c in (msg.tool_calls or [])])
