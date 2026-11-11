# Trilha didática de harnesses de computer use

## Contexto

Faço parte do time de desenvolvimento de uma empresa que constrói uma **plataforma de agentes** para atender a diferentes empresas clientes. Hoje a plataforma tem apenas agentes de chat. Mas a plataforma ofereça governança: controle de acessos a ferramentas, controle custos, etc.

Uma empresa cliente específica quer automatizar uma tarefa que exige cadastrar dados num sistema legado com interface gráfica: esse sistema tem uma API, mas ela cobre só parte dos dados, e o restante precisa ser preenchido pela GUI. Isso nos levou a estudar **agentes de computer use**, que operam um computador observando a tela e agindo com mouse e teclado.

Ao investigar o tema, descobri que um agente pode "ver" uma interface de três formas, da mais para a menos estruturada: pelo **DOM** (a árvore viva de objetos que o navegador monta a partir do HTML, usada por ferramentas como o Playwright); pela **árvore de acessibilidade** (a descrição de alto nível que o sistema operacional expõe para leitores de tela, com papel, nome, valor, estado e posição de cada elemento; no Windows ela é acessada pela **UIA – UI Automation**, e em Java Swing pelo **Java Access Bridge**); ou apenas por **pixels** (screenshots interpretados por um modelo de visão, que responde com coordenadas de clique, porém é mais lento, sujeito a erro e custoso).

Queremos atender à necessidade do cliente e, na sequência, melhorar a plataforma em geral, oferecendo clientes de computer use governados e seguros.

Para dominar a tecnologia antes de construir as soluções e para ensinar aos meus alunos no futuro (sou professor universitário de IA), quero criar um **repositório de projetos didáticos e minimalistas de harness de computer use**, em ordem crescente de complexidade de código. O propósito é exclusivamente educativo: entender, como *harness engineer*, cada peça que compõe um agente de computer use — das primitivas de ver e agir até permissões, avaliação e orquestração de sandboxes. Cada projeto deve ser pequeno, legível e focado em **uma ideia nova**, reaproveitando o que veio antes.

## Diretrizes gerais do repositório

- **Linguagem:** Python 3.14+. Criar ambiente uv e documentar as dependências para o conjunto de projetos como um todo.
- (Secundário, desejável) **Interface comum `Computer`** com métodos mínimos (onde for possível): `screenshot()`, `click(x, y)`, `double_click(x, y)`, `type(text)`, `key(combo)`, `scroll(dx, dy)`. Cada projeto usa ou troca a implementação dessa interface (local, container, Playwright, UIA, MCP).
- **Um diretório por projeto** (`p01_olho_e_mao/`, `p02_loop_minimo/`…), cada um com `README.md` explicando o que ensina, como rodar e o que observar.
- **Simplicidade:** código curto e comentado, sem abstrações desnecessárias, tratamento de erro só onde ensina algo. De fácil legibilidade por humanos (evitar código muito particularmente "Pythonic", onde houver alternativa mais simples).
- **Provedor de modelo plugável** onde fizer sentido (OpenAI por padrão; permitir trocar entre outros privados; de forma secundária, suportar modelos abertos como alternativa).
- **Versões de API e nomes de ferramentas/modelos:** conferir na documentação oficial no momento da implementação, pois mudam com frequência.

Estrutura sugerida:

```
computer-use-harnesses/
├── common/            # interface Computer, utilitários de imagem, logging
├── docker/            # imagem base Linux com Xvfb + noVNC (P3 em diante)
├── p01_olho_e_mao/
├── p02_loop_minimo/
├── ...
└── p18_pool_sandboxes/
```

## Projetos

### Nível 1 — Primitivas

#### P1. "Olho e mão" sem IA (~30 linhas)
Tira um screenshot, abre um editor de texto, clica e digita por coordenadas fixas.
**Ensina:** coordenadas, escala de tela/DPI, o que significa "ver" e "agir".
**Recursos técnicos:** `pyautogui`, `mss` (screenshot rápido), `Pillow`; no Linux, `xdotool` como alternativa.

#### P2. Loop mínimo de computer use (~100 linhas)
Loop `screenshot → modelo → ação → repete` usando a ferramenta de computer use do provedor, com limite de passos e condição de parada. Roda em VM descartável.
**Ensina:** o loop agêntico, o formato `tool_use`/`tool_result`, como o modelo decide parar.
**Recursos técnicos:** SDK `anthropic` com a ferramenta *computer use* (verificar versão/beta atual); alternativa: SDK `openai` com o modelo de computer use da OpenAI; `pyautogui` + `mss` para executar.

#### P3. Loop dentro de um container (~150 linhas + Dockerfile)
Container Linux com display virtual; o harness executa ações via `docker exec` e o desenvolvedor assiste pelo navegador.
**Ensina:** isolamento, display virtual, observação ao vivo.
**Recursos técnicos:** Docker, `Xvfb`, gerenciador de janelas leve (`xfwm4`/`fluxbox`), `xdotool`, `scrot`/`import` (ImageMagick), `x11vnc` + `noVNC`; SDK `docker` para Python. Referência: *computer-use-demo* da Anthropic (anthropic-quickstarts).

#### P4. Escala de coordenadas e resolução
Reduz o screenshot antes de enviar ao modelo e converte as coordenadas de volta. Compara taxa de acerto em 1024×768 e 1920×1080.
**Ensina:** resolução versus precisão versus custo de tokens.
**Recursos técnicos:** `Pillow` (resize), contagem de tokens/custo pela resposta da API.

### Nível 2 — Formas de perceber a tela

#### P5. Agente de navegador por DOM/acessibilidade
Envia ao LLM um snapshot textual da página (elementos com papel, nome e `ref`) em vez de imagem; o modelo responde ações como "preencher ref=12 com X".
**Ensina:** percepção estruturada; comparação de custo e acerto com o P2.
**Recursos técnicos:** `playwright` (Python) — snapshot de acessibilidade/ARIA da página, `get_by_role`, `get_by_label`; referências: Playwright MCP, `browser-use`, Stagehand.

#### P6. Agente Windows por UIA
Gera dump da árvore UIA da janela em texto e age pelo identificador do elemento. Ideal para treinar com o próprio sistema legado do cliente.
**Ensina:** árvore de acessibilidade em apps desktop e seus limites.
**Recursos técnicos:** `pywinauto` (backend `uia`) ou `uiautomation`; ferramenta de inspeção Accessibility Insights for Windows / `inspect.exe`. Variante Java Swing: Java Access Bridge (`jabswitch -enable`) com a biblioteca `JavaAccessBridge` do RPA Framework e o Access Bridge Explorer.

#### P7. Set-of-Mark
Desenha caixas numeradas sobre os elementos detectados e o modelo escolhe "clicar no 7" em vez de uma coordenada.
**Ensina:** grounding; separar "entender a tela" de "localizar o elemento".
**Recursos técnicos:** `Pillow` (desenho), OCR com `pytesseract` ou `easyocr`, opcionalmente a árvore UIA/DOM como fonte das caixas; versão avançada com **OmniParser** (Microsoft; repositório CC-BY-4.0, atenção às licenças dos pesos — alguns detectores antigos são AGPL).

#### P8. Harness híbrido
Usa a árvore (DOM/UIA) quando existe e cai para screenshot quando não existe ou a ação falha.
**Ensina:** estratégia de fallback, o padrão real de produção.
**Recursos técnicos:** combinação de P2, P5 e P6 atrás da interface `Computer`.

### Nível 3 — Robustez do loop

#### P9. Gestão de contexto
Mantém só os últimos N screenshots, resume o histórico antigo e mede custo por tarefa.
**Ensina:** por que tarefas longas estouram contexto e orçamento.
**Recursos técnicos:** contagem de tokens da API, prompt caching do provedor (quando disponível), sumarização com um modelo menor.

#### P10. Verificação e retentativa
Após cada ação, checa se a tela mudou como esperado; ao final, um passo verificador confirma o resultado.
**Ensina:** detecção de erro, idempotência, critérios de sucesso.
**Recursos técnicos:** diff de imagem com `imagehash` ou `scikit-image` (SSIM), releitura da árvore UIA/DOM, chamada de verificação ao LLM com saída estruturada (`pydantic`).

#### P11. Planejador + executor
Um modelo forte planeja os passos em texto; um modelo menor ou um modelo de grounding executa cada passo.
**Ensina:** divisão de papéis, custo versus capacidade.
**Recursos técnicos:** LLM de planejamento (ex.: Claude); grounding com **UI-TARS** (pesos abertos, ByteDance) servido via `vllm` ou similar, ou **OmniParser** + LLM; referência de arquitetura: **Agent S** (Simular).

### Nível 4 — Segurança e controle

#### P12. Permissões e aprovação humana
Camada entre modelo e driver que classifica ações (leitura, escrita, envio). Ações de escrita pausam e pedem aprovação; inclui allowlist de domínios/aplicativos e limites de passos e tempo.
**Ensina:** política como código, separada do agente.
**Recursos técnicos:** arquivo de política em YAML + `pydantic`; aprovação via terminal ou página simples com `fastapi`; no container, regras de rede (`iptables` ou proxy com allowlist).

#### P13. Cofre de credenciais
O modelo pede "preencher senha do sistema X" e o driver injeta o valor; a senha nunca aparece no prompt nem nos logs.
**Ensina:** manter segredos fora do contexto do modelo.
**Recursos técnicos:** `keyring` (local) ou HashiCorp Vault via `hvac`; ferramenta dedicada `fill_secret(secret_id, alvo)`; mascaramento nos logs.

#### P14. Laboratório de prompt injection
Página/app de teste com textos maliciosos visíveis na tela; mede o comportamento do agente com e sem as defesas do P12.
**Ensina:** a tela é dado não confiável; o valor do isolamento.
**Recursos técnicos:** páginas HTML estáticas servidas no container, cenários de ataque versionados, comparação de resultados com o P17.

### Nível 5 — Infraestrutura de plataforma

#### P15. Driver como servidor MCP
O "computador" vira um servidor MCP (`screenshot`, `click`, `type`, `get_tree`) usável por qualquer agente ou cliente MCP.
**Ensina:** desacoplar harness do ambiente.
**Recursos técnicos:** SDK oficial `mcp` para Python (FastMCP); referências: **Cua Driver** (MIT) e a API do **Bytebot** (Apache 2.0).

#### P16. Gravador e reprodutor de trajetórias
Grava cada passo (screenshot, ação, raciocínio) num formato simples, com visualizador HTML; trajetórias bem-sucedidas viram scripts reexecutáveis sem LLM.
**Ensina:** auditoria e a ideia de transformar trajetória em skill.
**Recursos técnicos:** JSONL + pasta de imagens; visualizador HTML estático; geração de script `playwright`/`pywinauto` a partir da trajetória (quando houver seletores estruturados); referência: **OpenAdapt** (MIT).

#### P17. Mini-benchmark
De 10 a 20 tarefas com verificadores automáticos, rodando todas as variantes de harness e comparando taxa de sucesso, número de passos e custo.
**Ensina:** avaliação objetiva entre abordagens.
**Recursos técnicos:** `pytest` ou runner próprio, verificadores em Python (estado de arquivo, registro via API, conteúdo de tela); referências: **OSWorld** (Apache 2.0), **Windows Agent Arena** (MIT), **Cua Bench**.

#### P18. Pool de sandboxes com fila
Várias sessões em paralelo, cada uma num container/VM efêmero criado a partir de um template, com fila de tarefas, timeouts, visualização ao vivo e "assumir controle".
**Ensina:** orquestração — o núcleo do computer use como recurso da plataforma.
**Recursos técnicos:** SDK `docker` (ou KVM/Hyper-V para Windows; `dockur/windows` para testes), fila com `asyncio` ou `rq`/Redis, `fastapi` para a API de tarefas, `noVNC` ou **Apache Guacamole** (Apache 2.0) para visualização; referências: **Bytebot**, **Cua** (sandboxes).

## Leitura de código de referência (após a trilha)

1. **computer-use-demo da Anthropic** (MIT) — próximo do P2/P3.
2. **Bytebot** (Apache 2.0) — próximo do P15/P18.
3. **Cua** (MIT; componentes de terceiros com licenças próprias) — driver, sandboxes e benchmark.
4. **Microsoft UFO²** (MIT) — próximo do P6/P8 no Windows.

## Ordem sugerida de implementação na nova sessão

1. `common/` com a interface `Computer` e o container base do P3 (ele serve de ambiente seguro para quase todos os projetos).
2. P1 a P4.
3. P17 cedo, numa versão pequena, para comparar os projetos seguintes.
4. P5 a P18, um por vez, cada um com README e tarefa de demonstração.
