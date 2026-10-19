# Sistema de Gestao Escolar

Projeto Flask com SQLite para gestao escolar, incluindo alunos, turmas, notas, frequencia, financeiro, relatorios e area administrativa.

## Como subir para o GitHub

1. Crie um repositorio vazio no GitHub.
2. Envie todos os arquivos desta pasta para o repositorio.
3. Nao envie arquivos locais como `escola.db`, `uploads/`, `__pycache__/` ou `.env`; eles ja estao protegidos pelo `.gitignore`.

## Rodar com Docker

```bash
docker-compose up --build
```

Acesse:

```text
http://localhost:5000
```

## Rodar sem Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python database.py
python database_v2.py
python populate_db.py
python app.py
```

No Linux/macOS, ative o ambiente com:

```bash
source .venv/bin/activate
```

## Credenciais de teste

```text
Admin: admin@escola.com / Mudar@123
Comercial: comercial@escola.com / Comercial@123
Financeiro: financeiro@escola.com / Financeiro@123
Pedagogico: pedagogico@escola.com / Pedagogico@123
Professor: ana@escola.com / Prof@123
Aluno: joao@escola.com / Aluno@123
```

## Variaveis de ambiente

Copie `.env.example` para `.env` e troque a chave:

```bash
SECRET_KEY=uma-chave-forte-aqui
```

## Observacao

O banco SQLite e criado localmente pelos scripts `database.py`, `database_v2.py` e `populate_db.py`. Por isso, o arquivo `escola.db` nao deve ser versionado.

