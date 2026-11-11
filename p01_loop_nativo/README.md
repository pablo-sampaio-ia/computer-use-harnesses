# P1 — Loop nativo multi-provedor em container

**Ideia nova:** o loop agêntico `screenshot → modelo → ações → screenshot`, usando a ferramenta
*nativa* de computer use de três provedores, dentro de um container descartável.

## Como rodar
```bash
uv sync
uv run python docker/run.py build     # uma vez
uv run python docker/run.py up        # sobe e imprime a URL do noVNC (assista!)
uv run python p01_loop_nativo/run.py --provider openai "Abra o Mousepad e escreva Ola"
```
Chaves: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`. Modelos por variável de ambiente
(`OPENAI_CU_MODEL`, `GEMINI_CU_MODEL`, `ANTHROPIC_CU_MODEL`) — confira os nomes atuais nas docs.

## O que observar
- `common/loop.py`: o loop inteiro. O modelo "para" quando não pede mais ações.
- `common/providers.py`: três vocabulários diferentes viram uma só `Action`:
  - **Anthropic**: cada ação é um `tool_use` (`left_click`, `key`…), coordenadas em pixels da imagem enviada.
  - **OpenAI**: um `computer_call` com **lote** de `actions`; você devolve **um** screenshot por chamada.
  - **Gemini**: `function_call` com coordenadas **normalizadas 0–999** e `intent`.
- Erros de ação voltam ao modelo como resultado (não derrubam o loop); ações pendentes de um lote
  que falhou recebem "Not executed".
- `runs/<data>/`: um PNG por passo + `trace.jsonl`.

## Experimento de resolução
`--sweep` repete a tarefa com 640, 1024 e 1280 px de largura. Compare passos, acertos e **tokens de entrada**.
Telas menores são mais baratas, mas elementos pequenos ficam ilegíveis.

## Status
Escrito e verificado com tela simulada (sem Docker nesta máquina). Rodar no container e com a Anthropic
(sem chave aqui) ainda **não foi testado**.
