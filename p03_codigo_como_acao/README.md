# P3 — Código como ação

**Ideia nova:** o modelo **escreve um script** (Playwright) em vez de emitir um clique por vez. Uma ferramenta:
`run_code(code)`; o harness devolve o `print` ou o erro, e o modelo corrige.

```bash
uv run python -m p03_codigo_como_acao.agent --headed "Abra http://localhost:8000 e cadastre ..."
```

## O que observar
- Cadastrar 3 clientes: **3 passos, ~1,5 mil tokens** (P2: 10 passos para 2 clientes). Um `for` faz o trabalho de 15 cliques.
- O código gerado é impresso no fim: já é uma **trajetória reexecutável** (base do P8).
- O modelo "inspeciona" com `print(...)` — ele decide quanto da página quer ver.

## Riscos (didáticos)
`exec()` **não é sandbox**. O navegador é descartável, mas o código roda no processo do harness. Menos auditável
que ações discretas: não dá para aprovar "um clique" — só o script inteiro. É o oposto do P9 (governança por ação).
