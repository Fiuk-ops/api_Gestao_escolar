# Status da interface

## Bloqueio identificado

O módulo `src/school_system/web.py` chama `render_template(...)` em 29 telas,
mas o repositório original não continha os diretórios `templates/` nem
`static/`. Isso não é consequência da organização: esses arquivos não existem
nem no commit anterior disponível no repositório.

As telas de login, cadastro e painel inicial foram recriadas para eliminar o
erro interno no acesso inicial. Para as 26 telas restantes, a aplicação agora
exibe uma página de preparação com status `503`, em vez de retornar erro `500`.

## Caminhos esperados

As páginas restantes devem ser recuperadas ou implementadas sob `templates/`,
incluindo:

```text
login.html
cadastro.html
dashboard_v2.html
turmas/listar.html
alunos/listar.html
pedagogico/dashboard.html
comercial/dashboard.html
frequencia/registrar.html
notas/registrar.html
relatorios/index.html
admin/dashboard.html
```

O código também está preparado para usar `static/` na raiz do projeto.

## Próxima ação

Se existir uma cópia local, um backup ou outro repositório com `templates/` e
`static/`, esses diretórios podem ser incorporados diretamente. Caso não
existam, a melhor sequência é criar primeiro `base.html`, login, dashboard e
as páginas de alunos/turmas, validando cada fluxo antes de seguir para os
módulos administrativo, financeiro e relatórios.
