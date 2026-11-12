"""System prompts editaveis, FORA do codigo. Cada prompt e um arquivo .md nesta pasta.

Uso:
  - linha de comando:  --system computer_use_default     (nome sem .md)   ou   --system-file caminho/qualquer.md
  - variavel de ambiente (vale para bench/pool tambem):  CU_SYSTEM_PROMPT_FILE=prompts/computer_use_default.md
  - em codigo:  run_agent(..., system_prompt=prompts.load("computer_use_default"))

Por padrao NAO ha system prompt no loop nativo (so o objetivo): os resultados medidos nos READMEs foram sem ele.
"""
import os
from pathlib import Path

HERE = Path(__file__).parent


def load(name_or_path: str) -> str:
    """Aceita o nome de um arquivo desta pasta (sem .md) ou um caminho."""
    p = Path(name_or_path)
    if not p.exists():
        p = HERE / f"{name_or_path}.md"
    return p.read_text(encoding="utf-8").strip()


def load_env_prompt():
    """Texto do arquivo em CU_SYSTEM_PROMPT_FILE, ou None."""
    f = os.getenv("CU_SYSTEM_PROMPT_FILE")
    return load(f) if f else None
