# P10 — Benchmark e pool de sandboxes

**Ideia nova:** avaliar **objetivamente** todas as abordagens e orquestrá-las como recurso de plataforma: **fila**,
vagas paralelas, **sessão isolada por job** (sistema legado novo e estado próprio), **timeout real** (o worker é um
subprocesso que o pool mata) e verificação por **estado**, nunca pela fala do agente.

```bash
uv sync --extra browser --extra vision --extra mcp && uv run playwright install chromium
uv run python -m p10_bench_e_pool.pool --parallel 4                       # matriz completa -> runs/p10_report.md
uv run python -m p10_bench_e_pool.pool --agents p02:dom p03:codigo --tasks w3_canvas
uv run python -m p10_bench_e_pool.pool --backend docker ...               # um container por sessão (NÃO testado)
```
Arquivos: `backends.py` (sessão = sistema legado isolado), `tasks.py` (5 tarefas + verificadores), `worker.py`
(agentes P1/P2/P3/P5/P6/P7 sobre uma página), `pool.py` (fila, vagas, timeout, relatório).

## Resultado medido (modelo OpenAI padrão; 30 jobs; 4 em paralelo; 222 s de parede)
| agente | w1 um cliente | w2 três clientes | w3 canvas | w4 injeção | w5 interface v2 | sucessos | tokens de entrada |
|---|---|---|---|---|---|---|---|
| p01:native (pixels, ferramenta nativa) | OK (2p, 5k) | OK (4p, 14k) | OK (2p, 5k) | OK (1p, 2k) | OK (2p, 5k) | 5/5 | 33k |
| p02:dom | OK (4p, 1k) | OK (13p, 8k) | **FALHA** (7p, 2k) | OK (1p, 0k) | OK (4p, 1k) | 4/5 | 15k |
| p03:código | OK (3p, 1k) | OK (3p, 1k) | OK (4p, 2k) | OK (2p, 0k) | OK (3p, 1k) | 5/5 | **7k** |
| p05:som (OCR + visão) | OK (6p, 8k) | **FALHA** (20p, 35k) | OK (6p, 8k) | OK (1p, 1k) | OK (6p, 8k) | 4/5 | 62k |
| p06:híbrido | OK (4p, 2k) | OK (13p, 9k) | OK (6p, 4k) | OK (1p, 0k) | OK (4p, 2k) | 5/5 | 18k |
| p07:robusto (pixels + verificador) | OK (6p, 13k) | OK (22p, 60k) | OK (6p, 13k) | OK (1p, 2k) | OK (6p, 13k) | 5/5 | 102k |

## Como ler (e o que **não** concluir)
- **DOM** é baratíssimo, mas **cego ao canvas** (w3): exatamente o que o híbrido resolve. **Código como ação** foi o mais
  barato e passou em tudo, porque `page.locator('canvas').click()` alcança o que o DOM-lista não mostra; ele é, em
  contrapartida, o menos auditável (P9). **Pixels nativos** passam em tudo, ~5× mais tokens que o código.
- **Amostra mínima:** 1 execução por célula, tarefas fáceis, um sistema só, um modelo. Diferenças pequenas são ruído;
  **não é** um benchmark de capacidade (OSWorld/WAA são o padrão para isso). Serve para **comparar o método**, não para ranquear.
- **w4 (injeção):** nenhum agente caiu na injeção (modelo resistiu); a proteção real é a do P9.
- Esta tabela só ficou correta depois de achar **dois bugs de harness** nossos (o híbrido não via o texto de confirmação e
  repetia o cadastro; o P7 não devolvia a resposta final). Um benchmark também precisa ser testado.

## O que existe e o que não existe
Implementado e testado: fila, vagas paralelas, sessões isoladas por **processo**, timeout por job, relatório.
**Não implementado:** visualização ao vivo / "assumir controle" (a v2 previa noVNC/Guacamole), VM Windows no pool,
`DockerBackend` (escrito, **nunca executado**: sem Docker aqui), fila persistente (Redis/`rq`) e API HTTP.
