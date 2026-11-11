# P7 — Robustez: contexto, verificação e retentativa

**Ideias novas:** (1) política de contexto; (2) detectar "a tela não mudou"; (3) verificador final **com evidência de
estado** e retentativa **idempotente**.

```bash
uv run python -m p07_robustez.robust --policy last2 --retries 0 --evidence-file runs/clientes.jsonl \
   --url http://localhost:8000 "Cadastre os clientes Ana Lima (...) e Bruno Costa (...)"
```
Agente só de pixels com histórico controlado por nós (provedor sem estado). Políticas: `all`, `last2`, `summary`.

## Medição (2 clientes, mesma tarefa, 15 passos, ambos corretos)
| Política | Tokens de entrada |
|---|---|
| `all` (todas as telas) | ~121 mil |
| `last2` (2 últimas telas) | ~37,6 mil |
| `summary` (last2 + resumo a cada 4 passos) | ~42 mil |

Cada screenshot antigo mantido custa ~1 mil tokens **em toda chamada seguinte**: o custo cresce quadraticamente.
Em tarefas curtas o resumo não compensa; em tarefas longas, sim (não medido aqui).

## Lição aprendida (medida, não planejada)
Na primeira versão o verificador via **só a tela final**. Numa tarefa com 2 itens ele reprovava ("só vejo o Bruno") e a
retentativa **duplicou cadastros** (4–5 registros em vez de 2). Correções no código:
1. o verificador recebe **evidência de estado** de fonte confiável (`evidence()`: aqui, o arquivo do sistema legado);
2. a retentativa recebe o estado atual e a ordem de **não repetir** o que já consta (**idempotência**).

## Limites
Detecção de mudança por diferença média de pixels (limiar fixo): relógios/animações dão falso positivo. Para mais
robustez: SSIM (`scikit-image`) ou hash perceptual (`imagehash`) — extra `robust`.
