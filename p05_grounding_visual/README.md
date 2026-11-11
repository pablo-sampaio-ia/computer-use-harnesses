# P5 — Grounding visual e modelos abertos

**Ideia nova:** para telas **sem árvore** (canvas, Citrix, apps customizados) é preciso *localizar* elementos
por pixels, **sem a ferramenta nativa de computer use**. Dois jeitos:

| Modo | Quem decide o quê |
|---|---|
| `som` (Set-of-Mark) | OCR numera os elementos; o modelo diz "clique na caixa 7" (`click_mark`, com `dx/dy` para campos vazios ao lado do rótulo) |
| `ground` | o planejador diz **o quê** ("campo E-mail"); um **grounder** devolve **onde** (x, y) |

```bash
uv sync --extra vision --extra browser && uv run playwright install chromium
uv run python -m p05_grounding_visual.agent --mode som    --url http://localhost:8000 "Cadastre ..."
uv run python -m p05_grounding_visual.agent --mode ground --url http://localhost:8000 "Cadastre ..."
# no container: --container cu-sandbox
```

## Grounder aberto (UI-TARS, Qwen-VL, GUI-Owl…)
Sirva o modelo com `vllm`/Ollama numa API compatível com OpenAI e aponte:
```bash
GROUND_PROVIDER=local GROUND_BASE_URL=http://localhost:8001/v1 GROUND_MODEL=<nome> uv run python -m p05_grounding_visual.agent --mode ground ...
```
`grounding.parse_point` aceita JSON e `(x,y)`; **UI-TARS usa coordenadas relativas à imagem redimensionada** — ajuste o
parser conforme a doc do modelo. OmniParser (detector de ícones) entraria como alternativa ao `detect_ocr` em `marks.py`.

## Resultado medido (cadastrar 1 cliente, página web, modelo geral da OpenAI como visão/grounder)
- `som`: 6 passos, ~8,6 mil tokens. `ground`: 6 passos, ~7,6 mil tokens. Ambos corretos.

## O que observar / limites
- OCR só acha **texto**: um campo vazio não tem caixa — por isso o `dx/dy`. OmniParser resolve parte disso.
- Bug didático encontrado no desenvolvimento: sem a imagem chegar ao modelo, o `som` ainda funcionou só pela *legenda*
  do OCR. Moral: **teste se o modelo realmente recebeu a imagem**.
- **Não testado aqui:** modelo aberto real (sem GPU/servidor nesta máquina) e o container Docker.
