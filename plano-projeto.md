# Trilha didática de harnesses de computer use (v2)

> Revisão da v1 (guardada em `plano-projeto.v1.md`): 18 projetos → **10**. Estado: **P1–P10 implementados** (ver "Estado da implementação" no fim).

## Contexto

Faço parte do time de desenvolvimento de uma empresa que constrói uma **plataforma de agentes** para atender a diferentes empresas clientes. Hoje a plataforma tem apenas agentes de chat, mas oferece governança: controle de acesso a ferramentas, controle de custos etc.

Uma empresa cliente quer automatizar uma tarefa que exige cadastrar dados num sistema legado com interface gráfica: o sistema tem uma API, mas ela cobre só parte dos dados; o restante precisa ser preenchido pela GUI. Isso nos levou a estudar **agentes de computer use**, que operam um computador observando a tela e agindo com mouse e teclado.

Um agente pode "ver" uma interface de três formas, da mais para a menos estruturada: pelo **DOM** (árvore viva do navegador; Playwright/CDP); pela **árvore de acessibilidade** (papel, nome, valor, estado e posição de cada elemento; no Windows via **UIA**, em Java Swing via **Java Access Bridge**); ou só por **pixels** (screenshots interpretados por um modelo de visão que devolve coordenadas: mais lento, mais propenso a erro e mais caro).

Queremos atender o cliente e, em seguida, oferecer à plataforma clientes de computer use governados e seguros.

Para dominar a tecnologia e ensinar meus alunos (sou professor universitário de IA), quero um **repositório de projetos didáticos e minimalistas de harness de computer use**, em ordem crescente de complexidade. O propósito é exclusivamente educativo: entender cada peça de um agente de computer use, das primitivas à governança e à avaliação. Cada projeto é pequeno, legível e focado em **uma ideia nova**, reaproveitando o que veio antes.

## Critério de seleção da v2

O objetivo da trilha é comparar **formas diferentes de executar tarefas**. Por isso:

- Cada projeto restante muda **como o agente percebe ou age** (pixels nativos, DOM, código, UIA, grounding aberto, híbrido) ou **como o trabalho é organizado** (planejador/executor, skills gravadas, MCP, pool).
- Os cortes e fusões recaíram sobre projetos cujo desafio é mais **engenharia/segurança** do que **capacidade de executar tarefas**: P4 (escala) virou experimento do P1; P9–P11 (contexto, verificação, planejador) foram agrupados; P12–P14 (permissões, cofre, injection) viraram um projeto só; P17+P18 (benchmark e pool) idem.
- Saltos maiores: vários projetos testam várias coisas novas de uma vez, com o benchmark comum medindo o efeito de cada uma.

## Panorama tecnológico (conferir na documentação oficial na implementação)

Tendências observadas em nov/2026. Fontes secundárias divergem em nomes e versões de modelos, então **nenhum identificador abaixo é definitivo**.

- **Ferramentas nativas de computer use nos três grandes provedores**: Anthropic (ferramenta `computer` na Messages API, com versões datadas), OpenAI (ferramenta `computer` na Responses API; o antigo `computer-use-preview` foi descontinuado) e Google Gemini (ferramenta embutida, coordenadas normalizadas 0–999). Vocabulários de ação, convenções de coordenadas e formato de resultado diferem.
- **Dois modos de agir**: ações estruturadas (clique/tecla) ou **o modelo escrevendo código** (Playwright/PyAutoGUI) executado em sandbox.
- **Navegador**: o eixo mudou para **CDP direto** e **snapshots de acessibilidade com `ref`**: Playwright MCP / Playwright CLI (estado em disco como YAML), Stagehand v3 (sem Playwright, CDP nativo), Browser Use (harness sobre Chrome real via CDP), agent-browser (Vercel Labs).
- **Windows**: servidores MCP baseados em UIA (Windows-MCP, pywinauto-MCP, WinWright, e servidores híbridos UIA + CDP + OCR). Windows Agent Arena e UFO² como referência.
- **Modelos abertos**: UI-TARS (ByteDance), famílias de visão dos modelos abertos recentes (Qwen-VL e afins, GUI-Owl), OmniParser (Microsoft). Observação: modelos abertos pequenos caem muito de OSWorld para benchmarks mais novos (ex.: OpenComputer), ou seja, **o desempenho em benchmark antigo superestima a robustez**.
- **Avaliação**: OSWorld-Verified já está perto da saturação (líderes ~85%, humano ~72%). O sucessor **OSWorld 2.0** (tarefas longas) é bem mais duro, e há protocolos novos (OpenComputer etc.). Para o nosso mini-benchmark, usar **verificadores baseados em estado**, não em tela.

## Diretrizes gerais do repositório

- **Linguagem:** Python recente com **uv**; documentar dependências do conjunto. **Atenção:** pywinauto, `torch`/`onnx` (OmniParser/UI-TARS) e outras podem não ter rodas para o Python 3.14. Fixar versão por projeto (`.python-version`) e permitir 3.12/3.13 onde necessário.
- **Interface comum `Computer`** (secundário, onde couber): `screenshot()`, `click(x, y)`, `double_click(x, y)`, `type(text)`, `key(combo)`, `scroll(dx, dy)`. Cada projeto usa ou troca a implementação (container X11, Playwright/CDP, UIA, MCP).
- **Um diretório por projeto** (`p01_...`), cada um com `README.md` (o que ensina, como rodar, o que observar) e **uma tarefa de demonstração** que também é registrada no benchmark comum.
- **Simplicidade:** código curto e comentado, sem abstrações desnecessárias, erro tratado só onde ensina; evitar idiomas muito "Pythônicos" quando houver alternativa mais legível.
- **Provedor plugável:** adaptadores finos para Anthropic, OpenAI e Gemini (padrão: o de sua preferência no momento); modelos abertos via servidor compatível com a API OpenAI (`vllm`, Ollama etc.) como alternativa secundária.
- **Verificar** versões de API, nomes de ferramentas e modelos na documentação oficial na hora de implementar.
- **Segurança como padrão desde o P1**: tudo roda em sandbox descartável (container ou VM). Nunca no desktop pessoal.

## Estrutura sugerida

```
computer-use-harnesses/
├── common/            # interface Computer, imagem, logging, adaptadores de provedor, runner do mini-benchmark
├── docker/            # imagem Linux: Xvfb + WM leve + noVNC (+ Chromium) 
├── bench/             # tarefas e verificadores (cresce a cada projeto)
├── p01_loop_nativo/
├── ...
└── p10_bench_e_pool/
```

## Warm-up (não é projeto): `common/` e "olho e mão" sem IA

Um script de ~30 linhas (`pyautogui` + `mss` ou `xdotool` no container) que tira screenshot, abre um editor e digita por coordenadas fixas. Serve de aula zero (coordenadas, DPI, "ver" e "agir") e já materializa a interface `Computer` + a imagem Docker. Mais um **mini-benchmark v0** (3–5 tarefas com verificadores de estado), para que todo projeto seguinte seja medido desde o início.

## Projetos

### Nível 1 — Pixels e provedores

#### P1. Loop nativo multi-provedor em container *(funde P2, P3, P4 da v1)*
Loop `screenshot → modelo → ação → repete` com a ferramenta nativa de computer use de **três provedores** atrás de adaptadores finos, rodando no container com noVNC para assistir ao vivo. Limite de passos e condição de parada. Inclui o experimento de **resolução/escala** (1024×768 vs. 1920×1080, redução do screenshot e conversão de coordenadas, incluindo a convenção 0–999 do Gemini).
**Ensina:** o loop agêntico e o formato `tool_use`/`tool_result` (ou equivalente); como cada provedor difere; isolamento e display virtual; resolução × precisão × custo.
**Recursos:** SDKs `anthropic`, `openai`, `google-genai`; Docker + Xvfb + noVNC + `xdotool`; `Pillow`. Referência: *computer-use-demo* da Anthropic.

### Nível 2 — Formas diferentes de perceber e agir

#### P2. Navegador por DOM/acessibilidade *(P5)*
Snapshot textual da página (papel, nome, `ref`) no lugar de imagem; o modelo responde `click ref=12`, `fill ref=7 "X"`. Duas variantes de conexão: Playwright direto e **CDP puro** (conectando a um Chromium já aberto no container).
**Ensina:** percepção estruturada; custo e acerto versus P1; quando o DOM é "grande demais".
**Recursos:** `playwright` (snapshot ARIA), CDP; referências: Playwright MCP/CLI, Browser Use, Stagehand v3.

#### P3. Código como ação *(novo)*
O modelo não emite cliques: escreve um **script** (Playwright ou PyAutoGUI), o harness executa em sandbox e devolve stdout/erros/screenshot final. O modelo itera sobre falhas.
**Ensina:** CodeAct para GUI; menos passos e mais barato em tarefas repetitivas (ex.: preencher 50 linhas), mas mais difícil de auditar e limitar.
**Recursos:** modo de código dos provedores (quando existir) ou execução em sandbox própria; `playwright`/`pyautogui`.

#### P4. Agente Windows por UIA *(P6)*
Dump da árvore UIA da janela em texto; ações pelo identificador do elemento (`invoke`, `set_value`, `select`). Ideal para treinar no sistema legado do cliente. Variante: Java Swing via Java Access Bridge.
**Ensina:** árvore de acessibilidade em apps desktop, e seus limites (controles customizados, elementos sem nome).
**Recursos:** `pywinauto` (backend `uia`) ou `uiautomation`; Accessibility Insights / `inspect.exe`; Java Access Bridge. Referências: Windows-MCP, UFO², Windows Agent Arena. **Ambiente:** VM Windows descartável ou `dockur/windows`; não cabe no container Linux.

#### P5. Grounding visual e modelos abertos *(funde P7 e o grounding do P11)*
Para apps **sem árvore** (canvas, Citrix, Flutter, jogos): detectar/rotular elementos (Set-of-Mark com OmniParser ou OCR + caixas numeradas) **e** usar um **modelo de grounding aberto** (UI-TARS ou equivalente atual, servido via `vllm`/Ollama) que devolve coordenadas. Comparar: modelo grande só com pixels × SoM × grounding aberto.
**Ensina:** separar "entender a tela" de "localizar o elemento"; trade-off de custo/privacidade com modelos locais; alertar para a queda de desempenho fora do benchmark original.
**Recursos:** `Pillow`, `easyocr`/`pytesseract`, OmniParser (checar licenças dos pesos), UI-TARS/Qwen-VL via `vllm`. Requer GPU ou serviço hospedado.

### Nível 3 — Orquestrar e tornar confiável

#### P6. Híbrido + planejador/executor *(funde P8 e P11)*
Um **roteador** escolhe a percepção/ação por passo: DOM (P2) → UIA (P4) → pixels (P1/P5), com fallback quando falha ou o elemento não existe. Sobre isso, um **modelo forte planeja** em texto e um **modelo barato executa** cada passo.
**Ensina:** o padrão real de produção (fallback entre camadas) e a divisão de papéis custo × capacidade (referência: Agent S).
**Recursos:** os projetos anteriores atrás da interface `Computer`; saída estruturada com `pydantic`.

#### P7. Robustez: contexto, verificação e retentativa *(funde P9 e P10)*
Mantém só os N últimos screenshots, resume o histórico, usa prompt caching, mede custo por tarefa. Após cada ação verifica a mudança (diff de imagem/SSIM, releitura da árvore); ao final, um **verificador** com saída estruturada confirma o resultado.
**Ensina:** por que tarefas longas estouram contexto/orçamento; detecção de erro, idempotência, critérios de sucesso.
**Recursos:** contagem de tokens da API, caching do provedor, `scikit-image`/`imagehash`, `pydantic`.

#### P8. Trajetórias → skills reexecutáveis *(P16)*
Grava cada passo (screenshot, ação, raciocínio, seletor estruturado quando houver) em JSONL + visualizador HTML. Trajetórias bem-sucedidas são **compiladas em scripts sem LLM** (Playwright/pywinauto), com fallback ao agente se o script quebrar (*self-healing*).
**Ensina:** auditoria; transformar exploração cara em automação barata. Esse é o caminho natural para a tarefa do cliente (cadastros repetitivos).
**Recursos:** JSONL, HTML estático, geração de código a partir de seletores; referência: OpenAdapt.

### Nível 4 — Plataforma

#### P9. Gateway MCP governado *(funde P15, P12, P13 e o laboratório de P14)*
O "computador" vira um **servidor MCP** (`screenshot`, `click`, `type`, `get_tree`…), consumível por qualquer agente MCP (inclusive agentes de código de terceiros). Entre o agente e o driver fica uma **camada de política**: classificação de ações (leitura/escrita/envio), aprovação humana para escritas, allowlist de apps/domínios, limites de passo/tempo/custo, **cofre** (`fill_secret(id, alvo)`: segredo nunca vai ao prompt ou log) e log de auditoria. Inclui **páginas de teste com prompt injection** para medir com e sem defesas.
**Ensina:** desacoplar harness e ambiente; política como código separada do agente; a tela como dado não confiável.
**Recursos:** SDK oficial `mcp` (FastMCP), YAML + `pydantic`, `fastapi` para aprovação, `keyring`/Vault, regras de rede/proxy no container. Referências: Cua Driver, Bytebot.

#### P10. Benchmark e pool de sandboxes *(funde P17 e P18)*
Evolui o mini-benchmark do warm-up (~15–20 tarefas, verificadores por **estado**: arquivo, registro via API, banco), incluindo cenários de **injection** do P9 e ao menos uma tarefa Windows. Roda todas as variantes (P1–P9) em **sandboxes efêmeras paralelas**, com fila, timeouts, visualização ao vivo e "assumir controle". Relatório: sucesso, passos, custo, tempo.
**Ensina:** avaliação objetiva entre abordagens e orquestração, o núcleo do computer use como recurso de plataforma.
**Recursos:** SDK `docker`, `asyncio` ou `rq`/Redis, `fastapi`, noVNC; Hyper-V/`dockur/windows` para Windows. Referências: OSWorld, Windows Agent Arena, Cua Bench, Bytebot.

## Leitura de código de referência (após a trilha)

1. **computer-use-demo da Anthropic** (MIT): próximo do P1.
2. **Playwright MCP / Browser Use / Stagehand**: próximos do P2 e P3.
3. **Microsoft UFO²** e **Windows-MCP**: próximos do P4 e P6.
4. **Bytebot** (Apache 2.0) e **Cua** (MIT; componentes de terceiros com licenças próprias): próximos do P9 e P10.

## Ordem de implementação

1. `common/` + imagem Docker + warm-up + mini-benchmark v0.
2. P1 → P2 → P3 (o benchmark compara desde cedo).
3. P4 (exige ambiente Windows) e P5 (exige GPU/serviço): podem ser feitos em paralelo.
4. P6 → P7 → P8.
5. P9 → P10.

## Pontos em aberto para decidir antes de implementar

- **Provedor padrão** e orçamento de API para as comparações do P1/P10.
- **Ambiente Windows** para o P4 (VM local? `dockur/windows`? máquina dedicada?) e se haverá app legado fictício parecido com o do cliente.
- **GPU** para o P5 (local, nuvem ou API hospedada de modelo aberto).
- Se o P3 deve usar o modo de código nativo dos provedores ou só um executor próprio.
- Se vale manter P9 e P10 como projetos finais ou deixar um deles como "extensão" caso se queira ficar em 9.

## Estado da implementação (nov/2026)

Todos os 10 projetos têm código e README próprio. **Ambiente de teste:** Windows 11, sem Docker, chaves da OpenAI e do
Gemini (sem Anthropic). Tudo que roda em navegador foi testado de verdade (Playwright headless) com o modelo da OpenAI.

| Projeto | Estado | Observação |
|---|---|---|
| warm-up / `common/` / Docker / bench v0 | escrito; **Docker nunca executado** | sem Docker nesta máquina |
| P1 loop nativo | **OpenAI testado** (navegador isolado); Gemini: 1ª chamada ok, resposta travou em 503; **Anthropic não testado** | `FakeComputer`/`PlaywrightComputer` para teste sem Docker |
| P2 DOM | testado | 2 cadastros em 10 passos |
| P3 código como ação | testado | 3 cadastros em 3 passos |
| P4 UIA Windows | testado (WinForms local) | limite real: ComboBox sem `ExpandCollapse` |
| P5 grounding visual | `som` e `ground` testados com modelo geral | **modelo aberto (UI-TARS etc.) não testado** |
| P6 híbrido + planejador/executor | testado (executor `gpt-6.1-terra`) | UIA não integrado; ganho de custo não medido |
| P7 robustez | testado | `all` 121k × `last2` 37,6k tokens |
| P8 trajetórias → skills | testado | replay 0 token; cura ~3,2k |
| P9 gateway MCP | testado (mcp 2.x) | aprovação interativa `ask` não exercitada |
| P10 bench + pool | testado (backend local) | `DockerBackend` e noVNC não testados |

Desvios em relação ao plano: UIA fora do híbrido (P6); modelos abertos e Anthropic sem teste; pool com processos locais.
Testes offline: `uv run python -m unittest discover -s tests -t .`
