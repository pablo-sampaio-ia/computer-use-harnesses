# P4 — Agente Windows por UI Automation (UIA)

**Ideia nova:** apps desktop também têm "DOM": a **árvore de acessibilidade** do Windows. O agente recebe
os controles em texto (`[e8] ComboBox "Tipo" id=cmbTipo value="Pessoa fisica"`) e age por **padrões UIA**
(`invoke`, `set_edit_text`…), sem mouse real e sem coordenadas.

```bash
uv sync --extra windows
uv run python -m p04_windows_uia.agent --demo          # abre um formulario WinForms "legado" e cadastra 2 clientes
uv run python -m p04_windows_uia.agent --pid 1234 --dump   # so imprime a arvore de um app qualquer
```
- `legacy_form.ps1`: o "sistema legado" (WinForms), grava cada cadastro em JSONL para verificação por estado.
  O launcher usa `-ExecutionPolicy Bypass` **só nesse processo** (máquinas com scripts desabilitados recusam o .ps1).
- **Segurança:** o agente fica preso a **um PID**; não enxerga nem toca nas outras janelas.
- Ferramenta de inspeção para explorar outros apps: Accessibility Insights for Windows / `inspect.exe`.
  Variante Java Swing: Java Access Bridge (`jabswitch -enable`) — mesma ideia, outra fonte da árvore (não implementada).

## O que observar
- `UiaSession.dump`: filtra tipos relevantes e numera os controles; o modelo nunca vê pixels.
- **Limite real, medido:** o `ComboBox` do WinForms não expõe `ExpandCollapsePattern`, então `select` falhou e o
  modelo precisou improvisar com teclado (22 passos; 2 registros corretos). Apps com controles customizados
  podem ficar quase opacos. É exatamente por isso que o **P6** usa fallback para pixels.
- Resultado: 2 clientes cadastrados corretamente (tipo "Empresa" incluído), ~19 mil tokens de entrada.

## Status
Testado nesta máquina (Windows 11) com WinForms. Não testado: Java Access Bridge e apps do cliente.
