# Sistema de Gestão Escolar

Aplicação Flask para cursos, professores, turmas, alunos, matrículas e notas.

## API da Biblioteca Escolar

As rotas abaixo retornam JSON e não exigem login:

| Método | Rota | Uso |
| --- | --- | --- |
| `GET` | `/api/biblioteca` | Exibe a mensagem inicial e os caminhos disponíveis. |
| `GET` | `/api/biblioteca/livros` | Lista os títulos disponíveis no catálogo. |
| `GET` | `/api/biblioteca/livros/<livro_id>` | Consulta um livro pelo identificador, por exemplo `/api/biblioteca/livros/1`. |
| `POST` | `/api/biblioteca/livros` | Planeja o cadastro de um livro, recebendo JSON com `titulo` e `autor`. Ainda não grava no catálogo. |

A página `/biblioteca` abre um alerta de boas-vindas no navegador e possui um link para a lista de livros.

Exemplo de planejamento de cadastro:

```json
{
  "titulo": "A Bolsa Amarela",
  "autor": "Lygia Bojunga"
}
```

## Iniciar o servidor

### Windows

1. Extraia o projeto.
2. Dê duplo clique em `INICIAR_SERVIDOR.bat`.
3. Abra `http://localhost:5000`.

### Terminal

```bash
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

No macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Para parar, pressione `Ctrl+C` na janela do servidor.

## Primeiro acesso

Em um banco novo, o administrador é criado automaticamente:

| E-mail | Senha |
| --- | --- |
| `admin@escola.com` | `Mudar@123` |

Antes de publicar, defina `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` e
`SECRET_KEY` no ambiente.

## Ordem de uso

1. Crie o **Curso** e informe as matérias.
2. Cadastre os **Professores**.
3. Cadastre os **Alunos**.
4. Crie as **Turmas**, escolhendo curso e professor.
5. Em **Turmas**, use **Gerenciar alunos** para fazer as matrículas.
6. Em **Notas**, lance três notas; a média é calculada automaticamente.

## Dados locais

- Banco: `data/escola.db`.
- Uploads: `data/uploads`.
- Esses arquivos não devem ser enviados ao GitHub.

## Testes

```bash
python -m unittest discover tests -v
```

## Docker

Copie `.env.example` para `.env`, defina `SECRET_KEY` e execute:

```bash
docker compose up --build
```

## Subir para o GitHub

O projeto inclui `.gitignore`, `requirements.txt`, `.env.example`, Docker e
teste automático em `.github/workflows/tests.yml`.

```bash
git init
git add .
git commit -m "Sistema de gestão escolar"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

Não envie `.env`, `data/`, bancos `.db`, uploads ou senhas.
