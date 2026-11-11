# computer-use-harnesses

Trilha didática de harnesses de computer use. Plano: [plano-projeto.md](plano-projeto.md).

```bash
uv sync                      # dependências base (Python 3.13)
uv run python docker/run.py build && uv run python docker/run.py up
```

Extras opcionais por projeto: `uv sync --extra browser` (P2/P3), `--extra windows` (P4),
`--extra vision` (P5), `--extra robust` (P7), `--extra mcp` (P9), `--extra pool` (P10).

| Pasta | Ideia |
|---|---|
| `warmup/` | olho e mão sem IA |
| `common/` | interface `Computer`, loop, adaptadores de provedor |
| `bench/` | mini-benchmark (verifica o **estado**, não a tela) |
| `p01_loop_nativo/` | loop com a ferramenta nativa (Anthropic, OpenAI, Gemini) |
| `p02_dom_a11y/` | navegador por DOM/acessibilidade |
| `p03_codigo_como_acao/` | o modelo escreve código em vez de cliques |
| `p04_windows_uia/` | Windows por UI Automation |
| `p05_grounding_visual/` | Set-of-Mark e modelos abertos |
| `p06_hibrido/` | roteador de percepção + planejador/executor |
| `p07_robustez/` | contexto, verificação, retentativa |
| `p08_trajetorias_skills/` | gravar → compilar em script |
| `p09_gateway_mcp/` | MCP governado |
| `p10_bench_e_pool/` | benchmark em sandboxes paralelas |

**Segurança:** nunca use `LocalComputer` fora de uma VM descartável.
