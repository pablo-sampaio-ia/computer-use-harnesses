# P2 — Navegador por DOM/acessibilidade

**Ideia nova:** trocar a imagem por uma **lista textual de elementos** (papel, nome, valor) com número (`ref`).
O modelo responde `click(ref=5)` / `fill(ref=2, text=...)`. Sem coordenadas e sem visão.

```bash
uv sync --extra browser && uv run playwright install chromium
uv run python -m p02_dom_a11y.agent --headed "Abra http://localhost:8000 e cadastre ..."
# "sistema legado" de teste local: uv run python docker/legacy_app.py   (porta 8000)
# contra o Chromium do container: --cdp http://localhost:9223 (ver bench_agent)
```

## O que observar
- `SNAPSHOT_JS` em `agent.py`: é a "árvore" que o modelo enxerga (nome acessível = aria-label, `<label>`, placeholder…).
  Playwright MCP/CLI fazem isso com a árvore de acessibilidade real; aqui o JS é explícito para ensinar.
- `common/toolloop.py`: só a observação **mais recente** vai ao modelo (custo constante por passo).
- Contraste com o P1: sem coordenadas, sem erro de clique, bem mais barato — mas **só funciona onde há DOM**.

## Resultado medido (cadastrar 2 clientes, modelo OpenAI, máquina local)
10 passos, ~5,5 mil tokens de entrada, 2 registros corretos no sistema legado.

## Limites
Páginas enormes estouram o snapshot; elementos em `canvas`/iframes cross-origin ficam invisíveis; `ref` muda a cada página.
