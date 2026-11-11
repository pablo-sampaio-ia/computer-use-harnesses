"""Grounding: dada uma imagem e uma descricao ("o botao Salvar"), devolver a coordenada.

Separa "decidir O QUE fazer" (planejador) de "saber ONDE clicar" (grounder). O grounder pode ser:
  - o mesmo modelo de visao de uso geral (padrao), ou
  - um modelo ABERTO especializado (UI-TARS, Qwen-VL, GUI-Owl...) servido por vllm/Ollama numa API
    compativel com OpenAI: GROUND_PROVIDER=local GROUND_BASE_URL=http://localhost:8001/v1 GROUND_MODEL=...
"""
import json
import os
import re

from common.llm import LLM

PROMPT = ("Esta e uma captura de tela de {w}x{h} pixels. Localize: \"{desc}\". "
          "Responda APENAS com JSON {{\"x\": <int>, \"y\": <int>}} com o centro do elemento, em pixels desta imagem.")


def make_grounder():
    provider = os.getenv("GROUND_PROVIDER", os.getenv("LLM_PROVIDER", "openai"))
    if os.getenv("GROUND_BASE_URL"):
        os.environ["LLM_BASE_URL"] = os.environ["GROUND_BASE_URL"]
    return LLM(provider, os.getenv("GROUND_MODEL"))


def parse_point(text, w, h):
    """Aceita JSON {"x":..,"y":..} ou o formato de modelos abertos: (x,y) / <|box_start|>(x,y)<|box_end|>.

    ATENCAO: UI-TARS usa coordenadas relativas a imagem redimensionada/normalizada (ver doc do modelo);
    ajuste aqui se o seu modelo nao responder em pixels da imagem enviada.
    """
    m = re.search(r'"x"\s*:\s*(\d+).*?"y"\s*:\s*(\d+)', text, re.S)
    if not m:
        m = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if not m:
        raise ValueError(f"nao achei coordenadas em: {text[:80]!r}")
    return min(int(m.group(1)), w - 1), min(int(m.group(2)), h - 1)


def locate(grounder, png, desc, w, h):
    reply = grounder.chat([{"role": "user", "content": PROMPT.format(w=w, h=h, desc=desc), "images": [png]}])
    return parse_point(reply.content, w, h)
