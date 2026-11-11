# Guia didático: como testar a trilha

Três camadas, da mais barata e segura para a mais cara. Comece sempre pela 1.

| Camada | Precisa de | Custa API? | Toca no seu desktop? |
|---|---|---|---|
| 1. Testes offline | só `uv` | não | não |
| 2. Navegador isolado (Playwright) | Chromium do Playwright + chave de API | sim, pouco | não (headless) |
| 3. Container Docker / app Windows | Docker; ou Windows | sim | só o formulário de teste (P4) |

## 0. Preparação (uma vez)
```bash
uv sync --extra browser --extra windows --extra vision --extra mcp
uv run playwright install chromium
```
Chaves **só por variável de ambiente** (nunca em arquivo, nunca impressas): `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`ANTHROPIC_API_KEY`. Modelos: `OPENAI_CU_MODEL`, `GEMINI_CU_MODEL`, `ANTHROPIC_CU_MODEL`, `LLM_MODEL`
(confira os nomes atuais nas docs dos provedores).

## 1. Testes offline (segundos, sem API)
```bash
uv run python -m unittest discover -s tests -t .
```
Cobrem: escala de coordenadas, nomes de teclas, tradução das ações de cada provedor, parser de grounding, detecção de
"a tela mudou". **Esperado:** `Ran 8 tests ... OK`. Se falhar, nada mais vale a pena testar.

## 2. Sistema legado de teste
Quase tudo é testado contra um "sistema legado" de brinquedo (formulário de cadastro). Suba-o num terminal:
```bash
export LEGACY_STATE=$PWD/runs/clientes.jsonl     # arquivo onde ele grava cada cadastro
uv run python docker/legacy_app.py               # http://localhost:8000
```
Páginas: `/` cadastro · `/v2` rótulos renomeados · `/canvas` botão desenhado em canvas · `/info` dado para ler ·
`/login` · `/injecao` (prompt injection). **A verificação é sempre pelo estado:** `cat runs/clientes.jsonl`.
Zere o arquivo entre testes (`: > runs/clientes.jsonl`).

## 3. Projeto por projeto

**P1 — loop nativo** (sem Docker, tela simulada; gasta poucos tokens):
```bash
uv run python -m p01_loop_nativo.smoke_test openai      # esperado: "botao acionado: True"
```
Contra um navegador real isolado, use o `PlaywrightComputer` (veja `common/pw_computer.py`). Com Docker: ver o README do P1.

**P2 / P3 — DOM e código:**
```bash
uv run python -m p02_dom_a11y.agent  "Abra http://localhost:8000 e cadastre Ana Lima, ana@exemplo.com, telefone 11 90000-0001, clicando em 'Salvar cliente'"
uv run python -m p03_codigo_como_acao.agent "...a mesma tarefa..."
```
**Esperado:** 1 linha nova em `runs/clientes.jsonl`. Compare passos e tokens impressos na última linha.

**P4 — Windows UIA** (abre **uma janela de formulário** no seu desktop; o agente só enxerga esse processo):
```bash
uv run python -m p04_windows_uia.agent --demo        # esperado: 2 registros impressos no final
```
**P5 — pixels sem ferramenta nativa:** `uv run python -m p05_grounding_visual.agent --mode som --url http://localhost:8000 "Cadastre ..."`
(`--mode ground` para o grounder).

**P6 — híbrido:** `... -m p06_hibrido.agent --url http://localhost:8000/canvas "Preencha nome e e-mail e clique no botao verde"`
(com `--plan` para planejador/executor; opcional `EXECUTOR_MODEL=<modelo mais barato>`).

**P7 — robustez:** `... -m p07_robustez.robust --policy last2 --retries 0 --evidence-file runs/clientes.jsonl --url http://localhost:8000 "Cadastre os clientes ..."`
Troque `--policy` entre `all`, `last2`, `summary` e compare `tokens_in`.

**P8 — skills:** `record` → `compile` → `replay` (sem LLM) → `replay` em `/v2` (cura). Comandos no README do P8.
**Esperado:** o replay na v1 imprime "skill executada SEM LLM: ok".

**P9 — segurança:** `PYTHONPATH=. uv run python -m p09_gateway_mcp.lab` (requer `LEGACY_STATE` igual ao do sistema legado).
**Esperado:** governança `off` → `DANO NO SISTEMA: True`; `on` → `False` e duas linhas `NEGADO`; "senha vazou? False".

**P10 — benchmark:** `PYTHONPATH=. uv run python -m p10_bench_e_pool.pool --parallel 4` → tabela em `runs/p10_report.md`
(~4 min, 30 jobs). Para um recorte: `--agents p02:dom p03:codigo --tasks w3_canvas`.

## 4. Container Docker (ainda **não** testado pelo autor)
```bash
uv run python docker/run.py build && uv run python docker/run.py up     # assista em http://localhost:6080/vnc.html
uv run python warmup/olho_e_mao.py --container cu-sandbox               # gera antes.png / depois.png
uv run python p01_loop_nativo/run.py --provider openai "Abra o Mousepad e escreva Ola"
uv run python -m bench.run --agents p01:openai                          # benchmark v0 dentro do container
```
Se algo falhar, suspeite primeiro de: `xdotool`/`import` ausentes, display `:1` fora do ar (`docker logs cu-sandbox`),
Chromium sem `--no-sandbox`. Relate o que quebrar: essa camada é a mais provável de precisar de ajuste.

## 5. Como diagnosticar
- **Nada acontece / agente "desiste":** veja os passos impressos; confira se o modelo **recebeu a imagem** (um bug já
  foi causado por isso: o texto estava ok e a imagem não chegava).
- **Repetiu a ação várias vezes:** o agente provavelmente não vê a confirmação na tela/texto. Cheque `runs/clientes.jsonl`
  por **duplicados**.
- **503 / alta demanda (Gemini):** transitório; tente de novo ou troque `GEMINI_CU_MODEL`.
- **Custos:** cada execução imprime `tokens=entrada/saída`. Imagens somam ~1 mil tokens cada, e se acumulam no histórico.
- **Segurança:** nunca aponte `LocalComputer` para seu desktop fora de uma VM; o P3 usa `exec()` (não é sandbox).
