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

## System prompt (opcional)
Por padrão **não há** system prompt: o modelo recebe só o objetivo, e a ferramenta de computer use define suas capacidades.
Para testar instruções de sistema, os prompts ficam em `prompts/` (fora do código) e valem para os 3 provedores
(`instructions` na OpenAI, `system` na Anthropic, `system_instruction` no Gemini; reenviados em toda chamada):
```bash
uv run python -m p01_loop_nativo.web_test openai --system computer_use_default     # ou --system-file meu.md
CU_SYSTEM_PROMPT_FILE=prompts/computer_use_default.md uv run python -m bench.run ...   # vale também p/ bench/pool
```
**Efeito medido (OpenAI, cadastrar 1 cliente):** sem prompt, 2 passos e ~5,4 mil tokens; com o prompt de exemplo ("confira
o resultado de cada ação"), 6 passos e ~34 mil tokens, pois o modelo passou a agir uma ação por vez, conferindo cada uma.
Mesmo resultado final, 6× o custo: instruções de sistema mudam muito o comportamento, então meça antes de adotar.

## Por que o `start` da OpenAI não envia o PNG
Na ferramenta `computer` da OpenAI a tela chega como *resultado* de uma chamada e o modelo sempre começa pedindo um
`screenshot`. Testado: enviar o PNG junto com o objetivo não eliminou esse passo e custou ~2,7 mil tokens a mais.
Anthropic e Gemini aceitam a imagem já no primeiro turno, e lá ela é enviada.
