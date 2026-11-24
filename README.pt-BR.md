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
