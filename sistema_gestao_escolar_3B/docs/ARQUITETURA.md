# Arquitetura do projeto

## Código em execução

| Local | Responsabilidade |
| --- | --- |
| `app.py` | Ponto de entrada compatível: inicia o servidor. |
| `src/school_system/web.py` | Aplicação Flask, rotas e inicialização do schema. |
| `src/school_system/auth.py` | Hash e verificação de senha, autenticação. |
| `src/school_system/database.py` | Schema base do SQLite. |
| `src/school_system/database_extensions.py` | Tabelas complementares. |
| `src/school_system/config.py` | Configuração, banco, uploads e caminhos locais. |
| `scripts/` | População de demonstração, criação de admin e teste manual. |

## Convenções adotadas

- Código de produção fica em `src/school_system`.
- Dados locais ficam em `data/` e nunca devem entrar no Git.
- Apenas `app.py` é usado para iniciar o servidor.
- Versões antigas, rascunhos e duplicações foram preservados em `legacy/` para
  consulta, mas não devem ser importados pela aplicação.
- Documentos que descreviam etapas antigas foram preservados em `docs/legacy/`.
  O `README.md` e os arquivos diretamente em `docs/` são a referência atual.

## Próxima refatoração recomendada

`web.py` ainda reúne 39 rotas e parte do acesso a dados. Depois que as telas
forem recuperadas, a próxima etapa deve dividir as rotas por domínio:

```text
routes/
  auth.py
  alunos.py
  pedagogico.py
  comercial.py
  administrativo.py
services/
  matriculas.py
  financeiro.py
repositories/
  alunos.py
  turmas.py
```

Essa divisão deve ser feita junto de testes por rota, para preservar o
comportamento do sistema durante a migração.

