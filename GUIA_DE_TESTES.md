# Guia didático: como testar a trilha

Três camadas, da mais barata e segura para a mais cara. Comece sempre pela 1.

| Camada | Precisa de | Custa API? | Executa no seu desktop? |
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

## 3. Warm-up: "olho e mão" sem IA

`warmup/olho_e_mao.py` é a aula zero: **sem modelo e sem API**. Ele tira um screenshot (ver), clica no centro da tela e
digita um texto (agir), tudo por coordenadas fixas. A lição é o que **quebra**: mude a resolução ou o DPI e o clique
cai no lugar errado, e é por isso que o computer use precisa de um modelo que *enxerga* onde clicar.

**Ele só roda com Docker?** Não, mas só há uma forma segura, que é com Docker. Os dois modos:

| Modo | Comando | Precisa de | Segurança |
|---|---|---|---|
| Container (recomendado) | `uv run python warmup/olho_e_mao.py --container cu-sandbox` | Docker + imagem construída (seção 5) | isolado |
| Local | `uv sync --extra local` e `... olho_e_mao.py --local` | só Python | **age no desktop onde roda**: clica no meio da tela e digita. Só numa **VM descartável** |

Sem Docker e sem VM, **pule o warm-up** por enquanto: os testes da seção 4 (P1 `smoke_test` e `web_test`) mostram a
mesma ideia de ver/agir por coordenadas sem tocar no seu desktop.

No modo container o script abre o Mousepad dentro do container, espera 3 s, tira `antes.png`, clica no centro
(para dar foco), digita `Ola do olho e mao!` e tira `depois.png`, ambos na pasta onde você rodou (o git os ignora).
**Esperado:** o texto aparece no `depois.png` (e ao vivo em http://localhost:6080/vnc.html). Se o texto não aparece, o
foco não foi para a janela: compare com `antes.png`. É exatamente o tipo de fragilidade que o resto da trilha resolve.
O benchmark v0 (`bench/`) faz parte do warm-up conceitualmente, mas também roda no container (seção 5).

## 4. Projeto por projeto

**P1 — loop nativo.** Há dois testes sem Docker, do mais simples ao mais realista:

1. *Tela simulada* (uma imagem desenhada com um botão; gasta poucos tokens). Prova que a **API do provedor** e o loop
   funcionam, sem navegador nenhum:
   ```bash
   uv run python -m p01_loop_nativo.smoke_test openai      # esperado: "botao acionado: True"
   ```
2. *Navegador real isolado.* O `PlaywrightComputer` (`common/pw_computer.py`) é um `Computer` cuja "tela" é uma página
   no Chromium **headless** do Playwright: o modelo vê **pixels** (screenshot) e responde com cliques e teclas, como
   no container, mas nada aparece no seu desktop. Com o sistema legado no ar (seção 2):
   ```bash
   uv run python -m p01_loop_nativo.web_test openai
   cat runs/clientes.jsonl          # esperado: 1 registro "Maria Souza"
   ```
   O que observar: os passos impressos (`click (x, y)`, `type ...`), os tokens no fim e os PNGs de cada passo em
   `runs/<data>-<provedor>/`. Limites: a "tela" é só a página (sem barra de endereço, por isso o script abre a URL
   antes) e só enxerga web, então não abre Mousepad nem apps de desktop; isso exige o container.

   Com Docker (aplicativos de desktop reais): seção 5 e README do P1.

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

## 5. Container Docker (ainda **não** testado pelo autor)
```bash
uv run python docker/run.py build && uv run python docker/run.py up     # assista em http://localhost:6080/vnc.html
uv run python warmup/olho_e_mao.py --container cu-sandbox               # gera antes.png / depois.png
uv run python p01_loop_nativo/run.py --provider openai "Abra o Mousepad e escreva Ola"
uv run python -m bench.run --agents p01:openai                          # benchmark v0 dentro do container
```
Se algo falhar, suspeite primeiro de: `xdotool`/`import` ausentes, display `:1` fora do ar (`docker logs cu-sandbox`),
Chromium sem `--no-sandbox`. Relate o que quebrar: essa camada é a mais provável de precisar de ajuste.

## 6. Como diagnosticar
- **Nada acontece / agente "desiste":** veja os passos impressos; confira se o modelo **recebeu a imagem** (um bug já
  foi causado por isso: o texto estava ok e a imagem não chegava).
- **Repetiu a ação várias vezes:** o agente provavelmente não vê a confirmação na tela/texto. Cheque `runs/clientes.jsonl`
  por **duplicados**.
- **503 / alta demanda (Gemini):** transitório; tente de novo ou troque `GEMINI_CU_MODEL`.
- **Custos:** cada execução imprime `tokens=entrada/saída`. Imagens somam ~1 mil tokens cada, e se acumulam no histórico.
- **Segurança:** nunca aponte `LocalComputer` para seu desktop fora de uma VM; o P3 usa `exec()` (não é sandbox).
