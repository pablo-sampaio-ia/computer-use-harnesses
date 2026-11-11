# P6 — Híbrido (DOM + pixels sob demanda) e planejador/executor

**Ideias novas:** (1) **fallback entre camadas de percepção**; (2) **divisão de papéis** modelo forte × modelo barato.

```bash
uv run python -m p06_hibrido.agent --url http://localhost:8000/canvas "Preencha nome ... clique no botao verde 'Confirmar cadastro'"
uv run python -m p06_hibrido.agent --plan --url http://localhost:8000/canvas "..."      # com planejador/executor
# modelos: PLANNER_MODEL e EXECUTOR_MODEL (padrão: LLM_MODEL)
```
A página `/canvas` do sistema legado de teste (`docker/legacy_app.py`) tem o botão **desenhado em `<canvas>`**:
invisível ao DOM. É o caso real em que a camada estruturada não basta.

## Como o híbrido decide (`HybridAgent.observe`)
Por padrão o modelo vê **só texto** (DOM). A imagem é anexada quando: a ação anterior falhou, a lista de elementos veio
vazia, ou o modelo chamou `look()`. Resultado medido: campos preenchidos por `ref` (3 passos de DOM) e só o botão por
pixels (`look` + `click_xy`): ~4,6 mil tokens no total, 1 cadastro correto.

## Planejador/executor (`run_plan`)
O planejador devolve 2–6 passos em JSON; o executor roda cada um com o agente híbrido; um passo que falha gera **um**
replanejamento. Testado também com `EXECUTOR_MODEL=gpt-6.1-terra` (planejador no modelo padrão): 1 cadastro correto. O mecanismo foi validado, mas **o ganho de
custo (forte planeja, barato executa) não foi medido**. Defina `PLANNER_MODEL`/`EXECUTOR_MODEL` e compare no P10.

## Desvio do plano
A v2 previa DOM → UIA → pixels. Aqui foi implementado **DOM → pixels** (testável sem desktop). A superfície UIA do
P4 entra do mesmo jeito (observação em texto + ferramentas `click/set_text`), mas a integração **não foi feita**.
