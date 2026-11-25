# NAVI Engineering Core v0.1.0

Fundação de engenharia local-first, orientada a evidências. [English](README.md).

## Instalação (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\navi.exe doctor
```

A CLI detecta perfis, cria manifestos sem sobrescrever, valida cinco contratos e prepara gates de engenharia. O modo padrão de verify é planejamento; --execute executa código confiável do projeto, não é sandbox. Os perfis planejados são rejeitados até implementação.

A CI inclui Linux e Windows, teste de instalação, contratos, CMake/CTest, Node e um teste do workflow reutilizável no próprio Core. Consulte as execuções reais antes de considerar uma revisão homologada.

[Integração GitHub](docs/GITHUB.md) · [Roadmap](docs/ROADMAP.md) · [Decisões](docs/DECISIONS.md).

Nenhuma configuração privada é distribuída. Licença MIT.

## Agent Bridge (prévia)

`navi agents` planeja ou cria instruções de repositório sem sobrescrever arquivos existentes. `navi skills` lista metadados de candidatos, sem executar skills. Consulte [o guia](docs/AGENT_BRIDGE.md).

## Independência de provedores

O Core não depende de nenhum assistente de IA. Escolha um único host: Codex, Claude Code, Gemini CLI ou GitHub Copilot. Papéis lógicos podem ser executados sequencialmente no mesmo host. Sem troca automática de provedor. Consulte [a arquitetura](docs/PROVIDER_INDEPENDENCE.md).

Para novos projetos, `navi init --root . --profile documentation --host gemini` registra o host preferido. Use `--host none` para projetos sem IA. A preferência é opcional e não instala nenhum agente.
