# P8 — Trajetórias → skills reexecutáveis (sem LLM) com autocura

**Ideia nova:** o agente resolve a tarefa **uma vez** (caro); a trajetória vira um **script parametrizado** que roda
**sem LLM** (barato, determinístico). Se a interface mudar e o script quebrar, o agente **cura**: termina a tarefa
pelo caminho caro (e a skill pode ser regravada).

```bash
M="uv run python -m p08_trajetorias_skills.skills"
$M record cadastro --url http://localhost:8000 "Cadastre o cliente Maria Souza, e-mail ..., tipo Empresa, clicando em Salvar cliente."
$M compile cadastro            # gera runs/skills/cadastro/skill.py
$M replay  cadastro --url http://localhost:8000 nome_completo="Ana Lima" e_mail=ana@exemplo.com telefone="11 90000-0001" tipo="Pessoa fisica"
$M replay  cadastro --url http://localhost:8000/v2 ...    # interface mudou (rótulos renomeados) -> cura com o agente
$M viewer  cadastro            # runs/skills/cadastro/viewer.html: auditoria visual da trajetória
```

## Medição (sistema legado de teste)
| Etapa | Tokens |
|---|---|
| gravação (1 vez, agente P2) | ~2,8 mil |
| replay com valores novos | **0** |
| replay na interface alterada (`/v2`) + cura | ~3,2 mil (cadastro correto) |

## O que observar
- A trajetória guarda **localizadores estáveis** (rótulo, papel, nome), não o `ref` efêmero do P2: é isso que torna o
  script reexecutável. Sem seletores estruturados (só pixels), a trajetória **não** vira script — limite real.
- Cada `fill` vira um **parâmetro** (nome vem do rótulo do campo).
- Detalhe aprendido: o rótulo de um `<select>` dentro de `<label>` traz o texto das opções; usamos só a 1ª linha. E a
  autocura **mascarou o bug** no primeiro teste: por isso o replay imprime a exceção que a causou.

## Riscos / limites
Skill gerada é código que roda sem supervisão: revise antes de promover. Heurística de parametrização simples (só campos
preenchidos). Não regrava automaticamente após a cura. Referência de ideia: OpenAdapt.
