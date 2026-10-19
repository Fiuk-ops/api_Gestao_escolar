"""
SISTEMA GESTÃO ESCOLAR v2.0 - COMPLETO
Integra Pedagógico, Comercial, Anexos, Auditoria
"""

from flask import Flask, render_template, request, session, redirect, flash, jsonify
import sqlite3
from datetime import datetime, date, timedelta
import json
import os
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound
from .auth import Autenticacao
from .config import Config, STATIC_DIR, TEMPLATES_DIR, database_path, ensure_runtime_directories
from .database import criar_banco_dados
from .database_extensions import criar_banco_dados_v2

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/static',
)
app.config.from_object(Config)

ensure_runtime_directories()


# ============================================================================
# API DA BIBLIOTECA
# ============================================================================

# Catálogo inicial do desafio. Em uma próxima etapa, estes dados podem ser
# migrados para uma tabela no banco de dados sem alterar as URLs da API.
LIVROS_DISPONIVEIS = [
    {'id': 1, 'titulo': 'O Pequeno Príncipe', 'autor': 'Antoine de Saint-Exupéry'},
    {'id': 2, 'titulo': 'Capitães da Areia', 'autor': 'Jorge Amado'},
    {'id': 3, 'titulo': 'Quarto de Despejo', 'autor': 'Carolina Maria de Jesus'},
]


@app.route('/biblioteca', methods=['GET'])
def pagina_biblioteca():
    """Exibe a página inicial da biblioteca com uma mensagem de boas-vindas."""
    return render_template('biblioteca.html')


@app.route('/api/biblioteca', methods=['GET'])
def boas_vindas_biblioteca():
    """Apresenta a API da biblioteca escolar."""
    return jsonify({
        'mensagem': 'Seja bem-vindo à API da Biblioteca Escolar!',
        'rotas': {
            'livros': '/api/biblioteca/livros',
            'consulta_por_id': '/api/biblioteca/livros/<livro_id>',
            'planejar_cadastro': '/api/biblioteca/livros',
        },
    })


@app.route('/api/biblioteca/livros', methods=['GET'])
def listar_livros_biblioteca():
    """Lista todos os títulos disponíveis no catálogo."""
    return jsonify({'livros': LIVROS_DISPONIVEIS, 'total': len(LIVROS_DISPONIVEIS)})


@app.route('/api/biblioteca/livros/<int:livro_id>', methods=['GET'])
def consultar_livro_biblioteca(livro_id):
    """Consulta um livro pelo seu identificador."""
    livro = next((item for item in LIVROS_DISPONIVEIS if item['id'] == livro_id), None)
    if livro is None:
        return jsonify({'erro': 'Livro não encontrado.', 'livro_id': livro_id}), 404
    return jsonify({'livro': livro})


@app.route('/api/biblioteca/livros', methods=['POST'])
def planejar_cadastro_livro():
    """Recebe os dados necessários para planejar o cadastro de um livro."""
    dados = request.get_json(silent=True) or {}
    titulo = (dados.get('titulo') or '').strip()
    autor = (dados.get('autor') or '').strip()

    if not titulo or not autor:
        return jsonify({
            'erro': 'Informe os campos "titulo" e "autor" para planejar o cadastro.'
        }), 400

    proximo_id = max((livro['id'] for livro in LIVROS_DISPONIVEIS), default=0) + 1
    return jsonify({
        'mensagem': 'Cadastro de livro planejado com sucesso.',
        'livro_planejado': {'id': proximo_id, 'titulo': titulo, 'autor': autor},
        'observacao': 'Esta rota ainda não grava dados no catálogo.',
    }), 202


@app.errorhandler(TemplateNotFound)
def template_not_found(error):
    """Evita erro 500 enquanto telas legadas ainda estão sendo recuperadas."""
    app.logger.warning("Template ausente: %s", error.name)
    return render_template('interface_indisponivel.html', template_name=error.name), 503

def get_db():
    conexao = sqlite3.connect(database_path())
    conexao.row_factory = sqlite3.Row
    return conexao

def executar_query(query, params=(), fetch_one=False):
    try:
        conexao = get_db()
        cursor = conexao.cursor()
        cursor.execute(query, params)
        resultado = cursor.fetchone() if fetch_one else cursor.fetchall()
        conexao.close()
        return resultado
    except Exception as e:
        print(f"Erro na query: {e}")
        return None

def executar_update(query, params=()):
    try:
        conexao = get_db()
        cursor = conexao.cursor()
        cursor.execute(query, params)
        conexao.commit()
        conexao.close()
        return True
    except Exception as e:
        print(f"Erro ao executar: {e}")
        return False

def pode_acessar(*tipos_permitidos):
    tipo = session.get('tipo_usuario')
    return tipo in tipos_permitidos

def login_requerido():
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Acesso negado. Faça login primeiro!', 'error')
                return redirect('/login')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def registrar_audit(usuario_id, usuario_tipo, acao, tabela, id_registro, valores_novos):
    executar_update('''
    INSERT INTO audit_log (usuario_id, usuario_tipo, acao, tabela_afetada, id_registro, valores_novos)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (usuario_id, usuario_tipo, acao, tabela, id_registro, json.dumps(valores_novos)))


def ensure_bootstrap_admin():
    """Cria o primeiro acesso somente quando o banco ainda não tem usuários."""
    conexao = get_db()
    cursor = conexao.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        if cursor.fetchone()[0] > 0:
            return False

        email = os.environ.get('INITIAL_ADMIN_EMAIL', 'admin@escola.com').strip().lower()
        senha = os.environ.get('INITIAL_ADMIN_PASSWORD', 'Mudar@123')
        cpf = os.environ.get('INITIAL_ADMIN_CPF', '00000000000')

        cursor.execute('SELECT id FROM funcionarios WHERE email = ?', (email,))
        funcionario = cursor.fetchone()
        if funcionario:
            funcionario_id = funcionario['id']
        else:
            cursor.execute('''
            INSERT INTO funcionarios (nome, email, cpf, senha, cargo, ativo)
            VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                'Administrador do Sistema',
                email,
                cpf,
                Autenticacao.hash_senha(senha),
                'Administrador',
            ))
            funcionario_id = cursor.lastrowid

        cursor.execute('''
        INSERT INTO usuarios (email, senha, tipo_usuario, tabela_referencia, id_referencia, ativo)
        VALUES (?, ?, 'admin', 'funcionarios', ?, 1)
        ''', (email, Autenticacao.hash_senha(senha), funcionario_id))
        conexao.commit()
        app.logger.warning('Administrador inicial criado: %s', email)
        return True
    finally:
        conexao.close()

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        usuario = Autenticacao.autenticar(email, senha)
        
        if usuario:
            session['usuario_id'] = usuario['id_referencia']
            session['email'] = usuario['email']
            session['tipo_usuario'] = usuario['tipo_usuario']
            session['tabela_referencia'] = usuario['tabela_referencia']
            session['exibir_boas_vindas'] = True
            registrar_audit(usuario['id_referencia'], usuario['tipo_usuario'], 'LOGIN', 'usuarios', usuario['id_referencia'], {})
            flash('Login realizado!', 'success')
            return redirect('/dashboard')
        else:
            flash('Email ou senha incorretos!', 'error')
    
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')
        telefone = request.form.get('telefone')
        data_nascimento = request.form.get('data_nascimento')
        
        try:
            conexao = get_db()
            cursor = conexao.cursor()
            
            cursor.execute('''
            INSERT INTO alunos (nome, email, cpf, senha, matricula, data_nascimento, telefone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, email, cpf, Autenticacao.hash_senha(senha), 
                  f"ALN{int(datetime.now().timestamp())}", data_nascimento, telefone))
            
            aluno_id = cursor.lastrowid
            
            cursor.execute('''
            INSERT INTO usuarios (email, senha, tipo_usuario, tabela_referencia, id_referencia)
            VALUES (?, ?, ?, ?, ?)
            ''', (email, Autenticacao.hash_senha(senha), 'aluno', 'alunos', aluno_id))
            
            conexao.commit()
            conexao.close()
            
            flash('Cadastro realizado! Faça login.', 'success')
            return redirect('/login')
        except Exception as e:
            flash(f'Erro: {str(e)}', 'error')
    
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'LOGOUT', 'usuarios', session.get('usuario_id'), {})
    session.clear()
    flash('Desconectado!', 'info')
    return redirect('/login')

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

# ============================================================================
# DASHBOARD v2 - NOVO COM GRÁFICOS
# ============================================================================

@app.route('/dashboard')
@login_requerido()
def dashboard():
    tipo_usuario = session.get('tipo_usuario')
    usuario_id = session.get('usuario_id')
    
    # Estatísticas gerais
    total_alunos = executar_query('SELECT COUNT(*) FROM alunos WHERE ativo = 1', fetch_one=True)[0] or 0
    total_professores = executar_query('SELECT COUNT(*) FROM professores WHERE ativo = 1', fetch_one=True)[0] or 0
    total_turmas = executar_query('SELECT COUNT(*) FROM turmas WHERE ativa = 1', fetch_one=True)[0] or 0
    total_cursos = executar_query('SELECT COUNT(*) FROM cursos WHERE ativo = 1', fetch_one=True)[0] or 0
    
    # Dados para gráficos
    alunos_por_status = executar_query('''
    SELECT COALESCE(status, 'Não informado') as status, COUNT(*) as total 
    FROM status_aluno GROUP BY status
    ''') or []
    
    receita_mes = executar_query('''
    SELECT SUM(valor_pago) FROM financeiro WHERE strftime('%Y-%m', data_vencimento) = strftime('%Y-%m', 'now')
    ''', fetch_one=True)[0] or 0
    
    matriculas_mes = executar_query('''
    SELECT COUNT(*) FROM matriculas WHERE strftime('%Y-%m', data_matricula) = strftime('%Y-%m', 'now')
    ''', fetch_one=True)[0] or 0
    
    dados = {
        'tipo_usuario': tipo_usuario,
        'usuario_id': usuario_id,
        'total_alunos': total_alunos,
        'total_professores': total_professores,
        'total_turmas': total_turmas,
        'total_cursos': total_cursos,
        'receita_mes': float(receita_mes) if receita_mes else 0,
        'matriculas_mes': matriculas_mes,
        'alunos_por_status': [dict(s) for s in alunos_por_status] if alunos_por_status else []
    }
    dados['exibir_boas_vindas'] = session.pop('exibir_boas_vindas', False)
    
    # Dados por tipo de usuário
    if tipo_usuario == 'aluno':
        aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (usuario_id,), fetch_one=True)
        turmas = executar_query('''
        SELECT t.*, p.nome as professor_nome, c.nome as curso_nome
        FROM turmas t
        JOIN matriculas m ON t.id = m.turma_id
        JOIN professores p ON t.professor_id = p.id
        JOIN cursos c ON t.curso_id = c.id
        WHERE m.aluno_id = ?
        ''', (usuario_id,))
        dados.update({
            'aluno': dict(aluno) if aluno else {},
            'turmas': [dict(t) for t in turmas] if turmas else []
        })
    
    elif tipo_usuario == 'professor':
        turmas = executar_query('''
        SELECT t.*, c.nome as curso_nome, COUNT(m.id) as total_alunos
        FROM turmas t
        JOIN cursos c ON t.curso_id = c.id
        LEFT JOIN matriculas m ON t.id = m.turma_id
        WHERE t.professor_id = ?
        GROUP BY t.id
        ''', (usuario_id,))
        dados['turmas'] = [dict(t) for t in turmas] if turmas else []
    
    return render_template('dashboard_v2.html', **dados)

# ============================================================================
# TURMAS
# ============================================================================

@app.route('/turmas')
@login_requerido()
def listar_turmas():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    turmas = executar_query('''
    SELECT t.*, c.nome as curso_nome, p.nome as professor_nome, COUNT(m.id) as total_alunos
    FROM turmas t
    JOIN cursos c ON t.curso_id = c.id
    JOIN professores p ON t.professor_id = p.id
    LEFT JOIN matriculas m ON t.id = m.turma_id
    GROUP BY t.id ORDER BY t.data_inicio DESC
    ''')
    
    return render_template('turmas/listar.html', turmas=[dict(t) for t in turmas] if turmas else [])

@app.route('/turma/nova', methods=['GET', 'POST'])
@login_requerido()
def nova_turma():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        if executar_update('''
        INSERT INTO turmas (codigo, nome, curso_id, professor_id, data_inicio, data_fim, horario, sala, capacidade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request.form.get('codigo'), request.form.get('nome'), request.form.get('curso_id'),
              request.form.get('professor_id'), request.form.get('data_inicio'), request.form.get('data_fim'),
              request.form.get('horario'), request.form.get('sala'), request.form.get('capacidade'))):
            flash('Turma criada!', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_TURMA', 'turmas', 1, {})
            return redirect('/turmas')
        flash('Erro!', 'error')
    
    cursos = executar_query('SELECT * FROM cursos WHERE ativo = 1')
    professores = executar_query('SELECT * FROM professores WHERE ativo = 1')
    return render_template('turmas/nova.html', 
                         cursos=[dict(c) for c in cursos] if cursos else [],
                         professores=[dict(p) for p in professores] if professores else [])


@app.route('/turma/<int:turma_id>/alunos', methods=['GET', 'POST'])
@login_requerido()
def gerenciar_alunos_turma(turma_id):
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    turma = executar_query('''
    SELECT t.*, c.nome AS curso_nome, p.nome AS professor_nome
    FROM turmas t
    JOIN cursos c ON c.id = t.curso_id
    JOIN professores p ON p.id = t.professor_id
    WHERE t.id = ?
    ''', (turma_id,), fetch_one=True)
    if not turma:
        flash('Turma não encontrada!', 'error')
        return redirect('/turmas')

    if request.method == 'POST':
        try:
            aluno_id = int(request.form.get('aluno_id', ''))
        except (TypeError, ValueError):
            flash('Selecione um aluno válido.', 'error')
        else:
            aluno = executar_query('SELECT id FROM alunos WHERE id = ? AND ativo = 1', (aluno_id,), fetch_one=True)
            total = executar_query("SELECT COUNT(*) FROM matriculas WHERE turma_id = ? AND status = 'ativa'", (turma_id,), fetch_one=True)[0]
            if not aluno:
                flash('Aluno não encontrado.', 'error')
            elif turma['capacidade'] and total >= turma['capacidade']:
                flash('A turma já atingiu a capacidade máxima.', 'error')
            else:
                try:
                    conexao = get_db()
                    conexao.execute('''
                    INSERT INTO matriculas (aluno_id, turma_id, data_matricula, status)
                    VALUES (?, ?, ?, 'ativa')
                    ''', (aluno_id, turma_id, date.today()))
                    conexao.commit()
                    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'MATRICULAR_ALUNO', 'matriculas', aluno_id, {'turma_id': turma_id})
                    flash('Aluno adicionado à turma!', 'success')
                    return redirect(f'/turma/{turma_id}/alunos')
                except sqlite3.IntegrityError:
                    if 'conexao' in locals():
                        conexao.rollback()
                    flash('Este aluno já está na turma.', 'error')
                finally:
                    if 'conexao' in locals():
                        conexao.close()

    matriculados = executar_query('''
    SELECT a.id, a.nome, a.email, a.matricula, m.data_matricula
    FROM matriculas m
    JOIN alunos a ON a.id = m.aluno_id
    WHERE m.turma_id = ? AND m.status = 'ativa'
    ORDER BY a.nome
    ''', (turma_id,))
    disponiveis = executar_query('''
    SELECT a.id, a.nome, a.matricula
    FROM alunos a
    WHERE a.ativo = 1
      AND NOT EXISTS (SELECT 1 FROM matriculas m WHERE m.aluno_id = a.id AND m.turma_id = ? AND m.status = 'ativa')
    ORDER BY a.nome
    ''', (turma_id,))

    return render_template(
        'turmas/alunos.html',
        turma=dict(turma),
        matriculados=[dict(a) for a in matriculados] if matriculados else [],
        disponiveis=[dict(a) for a in disponiveis] if disponiveis else [],
    )

# ============================================================================
# CURSOS
# ============================================================================

@app.route('/cursos')
@login_requerido()
def listar_cursos_principais():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    cursos = executar_query('''
    SELECT c.*, COUNT(DISTINCT m.id) AS total_modulos, COUNT(DISTINCT t.id) AS total_turmas
    FROM cursos c
    LEFT JOIN modulos m ON m.curso_id = c.id
    LEFT JOIN turmas t ON t.curso_id = c.id AND t.ativa = 1
    WHERE c.ativo = 1
    GROUP BY c.id
    ORDER BY c.nome
    ''')
    return render_template('cursos/listar.html', cursos=[dict(c) for c in cursos] if cursos else [])


@app.route('/curso/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_curso_principal():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        descricao = (request.form.get('descricao') or '').strip()
        disciplinas_texto = request.form.get('disciplinas') or ''
        try:
            duracao = int(request.form.get('duracao_meses')) if request.form.get('duracao_meses') else None
            valor = float(request.form.get('valor')) if request.form.get('valor') else None
            if duracao is not None and duracao < 1:
                raise ValueError
            if valor is not None and valor < 0:
                raise ValueError
        except ValueError:
            flash('Duração e valor devem ser números válidos.', 'error')
            return render_template('cursos/novo.html')

        if not nome:
            flash('Informe o nome do curso.', 'error')
            return render_template('cursos/novo.html')

        disciplinas = []
        for item in disciplinas_texto.replace(';', '\n').replace(',', '\n').splitlines():
            disciplina = item.strip()
            if disciplina and disciplina not in disciplinas:
                disciplinas.append(disciplina)

        conexao = None
        try:
            conexao = get_db()
            cursor = conexao.cursor()
            cursor.execute('''
            INSERT INTO cursos (nome, descricao, duracao_meses, valor, ativo)
            VALUES (?, ?, ?, ?, 1)
            ''', (nome, descricao, duracao, valor))
            curso_id = cursor.lastrowid
            for ordem, disciplina in enumerate(disciplinas, start=1):
                cursor.execute('INSERT INTO modulos (curso_id, nome, ordem) VALUES (?, ?, ?)', (curso_id, disciplina, ordem))
            conexao.commit()
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_CURSO', 'cursos', curso_id, {'disciplinas': len(disciplinas)})
            flash('Curso criado com sucesso!', 'success')
            return redirect('/cursos')
        except sqlite3.IntegrityError:
            if conexao:
                conexao.rollback()
            flash('Já existe um curso com este nome.', 'error')
        except Exception:
            if conexao:
                conexao.rollback()
            app.logger.exception('Erro ao cadastrar curso')
            flash('Não foi possível cadastrar o curso. Tente novamente.', 'error')
        finally:
            if conexao:
                conexao.close()

    return render_template('cursos/novo.html')

# ============================================================================
# PROFESSORES
# ============================================================================

@app.route('/professores')
@login_requerido()
def listar_professores():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    professores = executar_query('''
    SELECT p.*, COUNT(t.id) AS total_turmas
    FROM professores p
    LEFT JOIN turmas t ON t.professor_id = p.id AND t.ativa = 1
    WHERE p.ativo = 1
    GROUP BY p.id
    ORDER BY p.nome
    ''')
    return render_template('professores/listar.html', professores=[dict(p) for p in professores] if professores else [])


@app.route('/professor/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_professor():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        cpf = (request.form.get('cpf') or '').strip()
        senha = request.form.get('senha') or ''
        formacao = (request.form.get('formacao') or '').strip()
        especialidade = (request.form.get('especialidade') or '').strip()

        if not all((nome, email, cpf, senha)):
            flash('Preencha nome, e-mail, CPF e senha.', 'error')
            return render_template('professores/novo.html')

        conexao = None
        try:
            conexao = get_db()
            cursor = conexao.cursor()
            senha_hash = Autenticacao.hash_senha(senha)
            matricula = f"PRF{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            cursor.execute('''
            INSERT INTO professores (nome, email, cpf, senha, matricula, formacao, especialidade, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (nome, email, cpf, senha_hash, matricula, formacao, especialidade))
            professor_id = cursor.lastrowid
            cursor.execute('''
            INSERT INTO usuarios (email, senha, tipo_usuario, tabela_referencia, id_referencia, ativo)
            VALUES (?, ?, 'professor', 'professores', ?, 1)
            ''', (email, senha_hash, professor_id))
            conexao.commit()
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_PROFESSOR', 'professores', professor_id, {})
            flash('Professor cadastrado com sucesso!', 'success')
            return redirect('/professores')
        except sqlite3.IntegrityError:
            if conexao:
                conexao.rollback()
            flash('Já existe um professor com este e-mail ou CPF.', 'error')
        except Exception:
            if conexao:
                conexao.rollback()
            app.logger.exception('Erro ao cadastrar professor')
            flash('Não foi possível cadastrar o professor. Tente novamente.', 'error')
        finally:
            if conexao:
                conexao.close()

    return render_template('professores/novo.html')

# ============================================================================
# SALAS
# ============================================================================

@app.route('/salas')
@login_requerido()
def listar_salas():
    """Mantém links antigos funcionando após a unificação com Turmas."""
    return redirect('/turmas')


@app.route('/sala/nova', methods=['GET', 'POST'])
@login_requerido()
def nova_sala():
    return redirect('/turma/nova')

# ============================================================================
# ALUNOS
# ============================================================================

@app.route('/alunos')
@login_requerido()
def listar_alunos():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    alunos = executar_query('SELECT * FROM alunos WHERE ativo = 1 ORDER BY nome')
    return render_template('alunos/listar.html', alunos=[dict(a) for a in alunos] if alunos else [])

@app.route('/aluno/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_aluno():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        cpf = (request.form.get('cpf') or '').strip()
        senha = request.form.get('senha') or ''
        telefone = (request.form.get('telefone') or '').strip()
        data_nascimento = request.form.get('data_nascimento') or None

        if not all((nome, email, cpf, senha)):
            flash('Preencha nome, e-mail, CPF e senha.', 'error')
            return render_template('alunos/novo.html')

        conexao = None
        try:
            conexao = get_db()
            cursor = conexao.cursor()
            senha_hash = Autenticacao.hash_senha(senha)
            
            cursor.execute('''
            INSERT INTO alunos (nome, email, cpf, senha, matricula, data_nascimento, telefone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, email, cpf, senha_hash,
                  f"ALN{datetime.now().strftime('%Y%m%d%H%M%S%f')}", data_nascimento,
                  telefone))
            
            aluno_id = cursor.lastrowid
            
            cursor.execute('''
            INSERT INTO usuarios (email, senha, tipo_usuario, tabela_referencia, id_referencia)
            VALUES (?, ?, ?, ?, ?)
            ''', (email, senha_hash,
                  'aluno', 'alunos', aluno_id))
            
            # Criar status inicial
            cursor.execute('''
            INSERT INTO status_aluno (aluno_id, status, data_atualizacao)
            VALUES (?, ?, ?)
            ''', (aluno_id, 'Não Iniciou', date.today()))
            
            conexao.commit()
            flash('Aluno criado!', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_ALUNO', 'alunos', aluno_id, {})
            return redirect('/alunos')
        except sqlite3.IntegrityError:
            if conexao:
                conexao.rollback()
            flash('Já existe um aluno cadastrado com este e-mail ou CPF.', 'error')
        except Exception:
            if conexao:
                conexao.rollback()
            app.logger.exception('Erro ao cadastrar aluno')
            flash('Não foi possível cadastrar o aluno. Tente novamente.', 'error')
        finally:
            if conexao:
                conexao.close()
    
    return render_template('alunos/novo.html')

@app.route('/aluno/<int:aluno_id>')
@login_requerido()
def detalhe_aluno(aluno_id):
    aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (aluno_id,), fetch_one=True)
    if not aluno:
        flash('Aluno não encontrado!', 'error')
        return redirect('/alunos')
    
    turmas = executar_query('''
    SELECT t.*, c.nome as curso_nome, p.nome as professor_nome
    FROM turmas t
    JOIN matriculas m ON t.id = m.turma_id
    JOIN cursos c ON t.curso_id = c.id
    JOIN professores p ON t.professor_id = p.id
    WHERE m.aluno_id = ?
    ''', (aluno_id,))
    
    notas = executar_query('''
    SELECT n.*, m.nome as modulo_nome
    FROM notas n
    JOIN matriculas mat ON n.matricula_id = mat.id
    JOIN modulos m ON n.modulo_id = m.id
    WHERE mat.aluno_id = ?
    ''', (aluno_id,))
    
    frequencia = executar_query('''
    SELECT COUNT(*) as total, SUM(CASE WHEN presente = 1 THEN 1 ELSE 0 END) as presentes
    FROM frequencias f
    JOIN matriculas m ON f.matricula_id = m.id
    WHERE m.aluno_id = ?
    ''', (aluno_id,), fetch_one=True)
    
    status = executar_query('''
    SELECT * FROM status_aluno WHERE aluno_id = ? ORDER BY data_criacao DESC LIMIT 1
    ''', (aluno_id,), fetch_one=True)
    
    relatorios = executar_query('''
    SELECT * FROM relatorios_aluno WHERE aluno_id = ? ORDER BY data_criacao DESC
    ''', (aluno_id,))
    
    return render_template('alunos/detalhe.html',
                         aluno=dict(aluno),
                         turmas=[dict(t) for t in turmas] if turmas else [],
                         notas=[dict(n) for n in notas] if notas else [],
                         frequencia=dict(frequencia) if frequencia else {},
                         status=dict(status) if status else {},
                         relatorios=[dict(r) for r in relatorios] if relatorios else [])

@app.route('/aluno/<int:aluno_id>/deletar')
@login_requerido()
def deletar_aluno(aluno_id):
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (aluno_id,), fetch_one=True)
    if not aluno:
        flash('Aluno nÃ£o encontrado!', 'error')
        return redirect('/alunos')

    sucesso = executar_update('UPDATE alunos SET ativo = 0 WHERE id = ?', (aluno_id,))
    executar_update('UPDATE usuarios SET ativo = 0 WHERE tabela_referencia = ? AND id_referencia = ?', ('alunos', aluno_id))

    if sucesso:
        registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'DESATIVAR_ALUNO', 'alunos', aluno_id, {})
        flash('Aluno desativado com sucesso!', 'success')
    else:
        flash('Erro ao desativar aluno!', 'error')

    return redirect('/alunos')

# ============================================================================
# PEDAGOGICO - NOVO
# ============================================================================

@app.route('/pedagogico')
@login_requerido()
def pedagogico():
    if not pode_acessar('admin', 'professor', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    turmas = executar_query('''
    SELECT t.*, p.nome as professor_nome, c.nome as curso_nome, COUNT(m.id) as total_alunos
    FROM turmas t
    JOIN professores p ON t.professor_id = p.id
    JOIN cursos c ON t.curso_id = c.id
    LEFT JOIN matriculas m ON t.id = m.turma_id
    GROUP BY t.id
    ORDER BY t.data_inicio DESC
    ''')
    
    return render_template('pedagogico/dashboard.html',
                         turmas=[dict(t) for t in turmas] if turmas else [])

@app.route('/pedagogico/aluno/<int:aluno_id>')
@login_requerido()
def pedagogico_aluno_detalhes(aluno_id):
    aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (aluno_id,), fetch_one=True)
    if not aluno:
        flash('Aluno não encontrado!', 'error')
        return redirect('/pedagogico')
    
    status = executar_query('''
    SELECT * FROM status_aluno WHERE aluno_id = ? ORDER BY data_criacao DESC LIMIT 1
    ''', (aluno_id,), fetch_one=True)
    
    turmas = executar_query('''
    SELECT t.*, c.nome as curso_nome, p.nome as professor_nome
    FROM turmas t
    JOIN matriculas m ON t.id = m.turma_id
    JOIN cursos c ON t.curso_id = c.id
    JOIN professores p ON t.professor_id = p.id
    WHERE m.aluno_id = ?
    ''', (aluno_id,))
    
    notas = executar_query('''
    SELECT n.*, m.nome as modulo_nome, t.nome as turma_nome
    FROM notas n
    JOIN matriculas mat ON n.matricula_id = mat.id
    JOIN modulos m ON n.modulo_id = m.id
    JOIN turmas t ON mat.turma_id = t.id
    WHERE mat.aluno_id = ?
    ORDER BY t.nome
    ''', (aluno_id,))
    
    frequencia = executar_query('''
    SELECT COUNT(*) as total, SUM(CASE WHEN presente = 1 THEN 1 ELSE 0 END) as presentes
    FROM frequencias f
    JOIN matriculas m ON f.matricula_id = m.id
    WHERE m.aluno_id = ?
    ''', (aluno_id,), fetch_one=True)
    
    relatorios = executar_query('''
    SELECT * FROM relatorios_aluno WHERE aluno_id = ? ORDER BY data_criacao DESC
    ''', (aluno_id,))
    
    return render_template('pedagogico/aluno_detalhes.html',
                         aluno=dict(aluno),
                         status=dict(status) if status else {},
                         turmas=[dict(t) for t in turmas] if turmas else [],
                         notas=[dict(n) for n in notas] if notas else [],
                         frequencia=dict(frequencia) if frequencia else {},
                         relatorios=[dict(r) for r in relatorios] if relatorios else [])

@app.route('/pedagogico/aluno/<int:aluno_id>/relatorio/novo', methods=['POST'])
@login_requerido()
def novo_relatorio_aluno(aluno_id):
    if not pode_acessar('admin', 'professor', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/pedagogico')
    
    titulo = request.form.get('titulo')
    conteudo = request.form.get('conteudo')
    
    executar_update('''
    INSERT INTO relatorios_aluno (aluno_id, tipo, titulo, conteudo, criado_por)
    VALUES (?, ?, ?, ?, ?)
    ''', (aluno_id, 'pedagogico', titulo, conteudo, session.get('usuario_id')))
    
    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_RELATORIO', 'relatorios_aluno', aluno_id, {'titulo': titulo})
    flash('Relatório criado!', 'success')
    return redirect(f'/pedagogico/aluno/{aluno_id}')

@app.route('/pedagogico/aluno/<int:aluno_id>/status/novo', methods=['POST'])
@login_requerido()
def novo_status_aluno(aluno_id):
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/pedagogico')
    
    status = request.form.get('status')
    motivo = request.form.get('motivo')
    
    executar_update('''
    INSERT INTO status_aluno (aluno_id, status, motivo, data_atualizacao)
    VALUES (?, ?, ?, ?)
    ''', (aluno_id, status, motivo, date.today()))
    
    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'ALTERAR_STATUS', 'status_aluno', aluno_id, {'status': status})
    flash(f'Status alterado para: {status}', 'success')
    return redirect(f'/pedagogico/aluno/{aluno_id}')

# ============================================================================
# COMERCIAL - NOVO
# ============================================================================

@app.route('/comercial')
@login_requerido()
def comercial():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    matriculas_mes = executar_query('''
    SELECT COUNT(*) FROM matriculas WHERE strftime('%Y-%m', data_matricula) = strftime('%Y-%m', 'now')
    ''', fetch_one=True)[0] or 0
    
    receita_mes = executar_query('''
    SELECT SUM(valor_pago) FROM financeiro WHERE strftime('%Y-%m', data_vencimento) = strftime('%Y-%m', 'now')
    ''', fetch_one=True)[0] or 0
    
    pendente = executar_query('''
    SELECT SUM(valor_total - valor_pago) FROM financeiro WHERE status = 'pendente'
    ''', fetch_one=True)[0] or 0
    
    return render_template('comercial/dashboard.html',
                         matriculas_mes=matriculas_mes,
                         receita_mes=float(receita_mes) if receita_mes else 0,
                         pendente=float(pendente) if pendente else 0)

@app.route('/comercial/matricula/nova', methods=['GET', 'POST'])
@login_requerido()
def nova_matricula_comercial():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id')
        turma_id = request.form.get('turma_id')
        valor_total = float(request.form.get('valor_total'))
        parcelas = int(request.form.get('parcelas'))
        
        # Criar matrícula
        executar_update('''
        INSERT INTO matriculas (aluno_id, turma_id, data_matricula, status)
        VALUES (?, ?, ?, ?)
        ''', (aluno_id, turma_id, date.today(), 'ativa'))
        
        matricula_id = executar_query('SELECT last_insert_rowid()', fetch_one=True)[0]
        
        # Criar financeiro
        executar_update('''
        INSERT INTO financeiro (matricula_id, valor_total, data_vencimento, status, parcelas, descricao)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (matricula_id, valor_total, date.today() + timedelta(days=30), 'pendente', parcelas, 'Matrícula'))
        
        # Criar parcelas
        valor_parcela = valor_total / parcelas
        for i in range(parcelas):
            data_vencimento = date.today() + timedelta(days=30 * (i + 1))
            executar_update('''
            INSERT INTO parcelas (financeiro_id, numero_parcela, valor_parcela, data_vencimento, status)
            VALUES (?, ?, ?, ?, ?)
            ''', (matricula_id, i + 1, valor_parcela, data_vencimento, 'pendente'))
        
        registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'NOVA_MATRICULA', 'matriculas', matricula_id, {})
        flash('Matrícula criada!', 'success')
        return redirect('/comercial/matriculas')
    
    alunos = executar_query('SELECT id, nome FROM alunos WHERE ativo = 1 ORDER BY nome')
    turmas = executar_query('SELECT id, nome FROM turmas WHERE ativa = 1 ORDER BY nome')
    cursos = executar_query('SELECT id, nome, valor FROM cursos WHERE ativo = 1')
    
    return render_template('comercial/matricula_nova.html',
                         alunos=[dict(a) for a in alunos] if alunos else [],
                         turmas=[dict(t) for t in turmas] if turmas else [],
                         cursos=[dict(c) for c in cursos] if cursos else [])

@app.route('/comercial/matriculas')
@login_requerido()
def listar_matriculas_comercial():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    matriculas = executar_query('''
    SELECT m.*, a.nome as aluno_nome, t.nome as turma_nome
    FROM matriculas m
    JOIN alunos a ON m.aluno_id = a.id
    JOIN turmas t ON m.turma_id = t.id
    ORDER BY m.data_matricula DESC
    ''')
    
    return render_template('comercial/matriculas.html',
                         matriculas=[dict(m) for m in matriculas] if matriculas else [])

@app.route('/comercial/financeiro')
@login_requerido()
def comercial_financeiro():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    financeiros = executar_query('''
    SELECT f.*, a.nome as aluno_nome, t.nome as turma_nome
    FROM financeiro f
    JOIN matriculas m ON f.matricula_id = m.id
    JOIN alunos a ON m.aluno_id = a.id
    JOIN turmas t ON m.turma_id = t.id
    ORDER BY f.data_vencimento
    ''')
    
    return render_template('comercial/financeiro.html',
                         financeiros=[dict(f) for f in financeiros] if financeiros else [])

@app.route('/comercial/parcelas/<int:financeiro_id>')
@login_requerido()
def ver_parcelas(financeiro_id):
    financeiro = executar_query('SELECT * FROM financeiro WHERE id = ?', (financeiro_id,), fetch_one=True)
    if not financeiro:
        flash('Não encontrado!', 'error')
        return redirect('/comercial/financeiro')
    
    parcelas = executar_query('''
    SELECT * FROM parcelas WHERE financeiro_id = ? ORDER BY numero_parcela
    ''', (financeiro_id,))
    
    return render_template('comercial/parcelas.html',
                         financeiro=dict(financeiro),
                         parcelas=[dict(p) for p in parcelas] if parcelas else [])

@app.route('/comercial/parcela/<int:parcela_id>/pagar', methods=['POST'])
@login_requerido()
def pagar_parcela(parcela_id):
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/comercial/financeiro')
    
    metodo = request.form.get('metodo_pagamento', 'dinheiro')
    
    executar_update('''
    UPDATE parcelas SET status = 'pago', data_pagamento = ?, metodo_pagamento = ? WHERE id = ?
    ''', (date.today(), metodo, parcela_id))
    
    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'PAGAR_PARCELA', 'parcelas', parcela_id, {})
    flash('Pagamento registrado!', 'success')
    return redirect(request.referrer)

# ============================================================================
# ANEXOS
# ============================================================================

@app.route('/aluno/<int:aluno_id>/anexos')
@login_requerido()
def anexos_aluno(aluno_id):
    aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (aluno_id,), fetch_one=True)
    if not aluno:
        flash('Aluno não encontrado!', 'error')
        return redirect('/alunos')
    
    anexos = executar_query('''
    SELECT * FROM anexos WHERE aluno_id = ? ORDER BY data_upload DESC
    ''', (aluno_id,))
    
    return render_template('alunos/anexos.html',
                         aluno=dict(aluno),
                         anexos=[dict(a) for a in anexos] if anexos else [])

@app.route('/aluno/<int:aluno_id>/anexo/novo', methods=['POST'])
@login_requerido()
def novo_anexo(aluno_id):
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect(f'/aluno/{aluno_id}/anexos')
    
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado!', 'error')
        return redirect(f'/aluno/{aluno_id}/anexos')
    
    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado!', 'error')
        return redirect(f'/aluno/{aluno_id}/anexos')
    
    nome_seguro = secure_filename(arquivo.filename)
    if not nome_seguro:
        flash('Nome de arquivo invÃ¡lido!', 'error')
        return redirect(f'/aluno/{aluno_id}/anexos')
    
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho_arquivo = arquivo.stream.tell()
    arquivo.stream.seek(0)
    
    nome_arquivo = f"{aluno_id}_{datetime.now().timestamp()}_{nome_seguro}"
    caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
    arquivo.save(caminho_arquivo)
    
    tipo = request.form.get('tipo', 'documento')
    titulo = request.form.get('titulo', arquivo.filename)
    
    executar_update('''
    INSERT INTO anexos (aluno_id, tipo, titulo, arquivo, arquivo_nome, arquivo_tamanho, arquivo_tipo)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (aluno_id, tipo, titulo, caminho_arquivo, nome_seguro, tamanho_arquivo, arquivo.content_type))
    
    registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'UPLOAD_ANEXO', 'anexos', aluno_id, {'tipo': tipo})
    flash('Anexo enviado!', 'success')
    return redirect(f'/aluno/{aluno_id}/anexos')

# ============================================================================
# FREQUÊNCIA E NOTAS
# ============================================================================

@app.route('/notas')
@login_requerido()
def listar_turmas_notas():
    if not pode_acessar('admin', 'funcionario', 'professor'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')

    if session.get('tipo_usuario') == 'professor':
        turmas = executar_query('''
        SELECT t.*, c.nome AS curso_nome, COUNT(m.id) AS total_alunos
        FROM turmas t
        JOIN cursos c ON c.id = t.curso_id
        LEFT JOIN matriculas m ON m.turma_id = t.id AND m.status = 'ativa'
        WHERE t.professor_id = ? AND t.ativa = 1
        GROUP BY t.id
        ORDER BY t.nome
        ''', (session.get('usuario_id'),))
    else:
        turmas = executar_query('''
        SELECT t.*, c.nome AS curso_nome, p.nome AS professor_nome, COUNT(m.id) AS total_alunos
        FROM turmas t
        JOIN cursos c ON c.id = t.curso_id
        JOIN professores p ON p.id = t.professor_id
        LEFT JOIN matriculas m ON m.turma_id = t.id AND m.status = 'ativa'
        WHERE t.ativa = 1
        GROUP BY t.id
        ORDER BY t.nome
        ''')

    return render_template('notas/index.html', turmas=[dict(t) for t in turmas] if turmas else [])

@app.route('/turma/<int:turma_id>/frequencia', methods=['GET', 'POST'])
@login_requerido()
def frequencia_turma(turma_id):
    if not pode_acessar('admin', 'funcionario', 'professor'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    turma = executar_query('SELECT * FROM turmas WHERE id = ?', (turma_id,), fetch_one=True)
    if not turma:
        flash('Turma não encontrada!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        data_aula = request.form.get('data_aula')
        matriculas = executar_query('''
        SELECT m.id FROM matriculas m WHERE m.turma_id = ?
        ''', (turma_id,))
        
        for matricula in matriculas:
            presente = request.form.get(f'presente_{matricula["id"]}')
            executar_update('''
            INSERT INTO frequencias (matricula_id, data_aula, presente)
            VALUES (?, ?, ?)
            ''', (matricula['id'], data_aula, 1 if presente else 0))
        
        registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'REGISTRAR_FREQUENCIA', 'frequencias', turma_id, {})
        flash('Frequência registrada!', 'success')
        return redirect(f'/turma/{turma_id}/frequencia')
    
    alunos = executar_query('''
    SELECT m.id, a.id as aluno_id, a.nome
    FROM matriculas m
    JOIN alunos a ON m.aluno_id = a.id
    WHERE m.turma_id = ?
    ''', (turma_id,))
    
    return render_template('frequencia/registrar.html',
                         turma=dict(turma),
                         alunos=[dict(a) for a in alunos] if alunos else [])

@app.route('/turma/<int:turma_id>/notas', methods=['GET', 'POST'])
@login_requerido()
def notas_turma(turma_id):
    if not pode_acessar('admin', 'funcionario', 'professor'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    turma = executar_query('SELECT * FROM turmas WHERE id = ?', (turma_id,), fetch_one=True)
    if not turma:
        flash('Turma não encontrada!', 'error')
        return redirect('/dashboard')

    if session.get('tipo_usuario') == 'professor' and turma['professor_id'] != session.get('usuario_id'):
        flash('Você só pode lançar notas nas suas próprias turmas.', 'error')
        return redirect('/notas')
    
    if request.method == 'POST':
        try:
            matricula_id = int(request.form.get('matricula_id', ''))
            modulo_id = int(request.form.get('modulo_id', ''))
            primeira_nota = float(request.form.get('primeira_nota', ''))
            segunda_nota = float(request.form.get('segunda_nota', ''))
            terceira_nota = float(request.form.get('terceira_nota', ''))
            if any(nota < 0 or nota > 10 for nota in (primeira_nota, segunda_nota, terceira_nota)):
                raise ValueError
        except (TypeError, ValueError):
            flash('Informe três notas entre 0 e 10.', 'error')
        else:
            matricula = executar_query('SELECT id FROM matriculas WHERE id = ? AND turma_id = ?', (matricula_id, turma_id), fetch_one=True)
            modulo = executar_query('SELECT id FROM modulos WHERE id = ? AND curso_id = ?', (modulo_id, turma['curso_id']), fetch_one=True)
            if not matricula or not modulo:
                flash('Aluno ou matéria inválidos para esta turma.', 'error')
            else:
                media = round((primeira_nota + segunda_nota + terceira_nota) / 3, 2)
                nota_existente = executar_query('SELECT id FROM notas WHERE matricula_id = ? AND modulo_id = ?', (matricula_id, modulo_id), fetch_one=True)
                if nota_existente:
                    executar_update('''
                    UPDATE notas SET primeira_nota = ?, segunda_nota = ?, terceira_nota = ?, media_final = ?
                    WHERE id = ?
                    ''', (primeira_nota, segunda_nota, terceira_nota, media, nota_existente['id']))
                else:
                    executar_update('''
                    INSERT INTO notas (matricula_id, modulo_id, primeira_nota, segunda_nota, terceira_nota, media_final)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (matricula_id, modulo_id, primeira_nota, segunda_nota, terceira_nota, media))

                registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'REGISTRAR_NOTAS', 'notas', matricula_id, {'media_final': media})
                flash('Notas registradas com média final calculada!', 'success')
                return redirect(f'/turma/{turma_id}/notas')
    
    modulos = executar_query('''
    SELECT * FROM modulos WHERE curso_id = (SELECT curso_id FROM turmas WHERE id = ?)
    ''', (turma_id,))
    
    alunos = executar_query('''
    SELECT m.id as matricula_id, a.id as aluno_id, a.nome
    FROM matriculas m
    JOIN alunos a ON m.aluno_id = a.id
    WHERE m.turma_id = ?
    ''', (turma_id,))

    notas_lancadas = executar_query('''
    SELECT n.*, a.nome AS aluno_nome, mo.nome AS modulo_nome
    FROM notas n
    JOIN matriculas mat ON mat.id = n.matricula_id
    JOIN alunos a ON a.id = mat.aluno_id
    JOIN modulos mo ON mo.id = n.modulo_id
    WHERE mat.turma_id = ?
    ORDER BY a.nome, mo.ordem, mo.nome
    ''', (turma_id,))
    
    return render_template('notas/registrar.html',
                         turma=dict(turma),
                         modulos=[dict(m) for m in modulos] if modulos else [],
                         alunos=[dict(a) for a in alunos] if alunos else [],
                         notas_lancadas=[dict(n) for n in notas_lancadas] if notas_lancadas else [])

# ============================================================================
# RELATÓRIOS
# ============================================================================

@app.route('/relatorios')
@login_requerido()
def relatorios():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    return render_template('relatorios/index.html')

@app.route('/relatorio/turmas')
@login_requerido()
def relatorio_turmas():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    turmas = executar_query('''
    SELECT t.*, c.nome as curso_nome, p.nome as professor_nome, COUNT(m.id) as total_alunos
    FROM turmas t
    JOIN cursos c ON t.curso_id = c.id
    JOIN professores p ON t.professor_id = p.id
    LEFT JOIN matriculas m ON t.id = m.turma_id
    GROUP BY t.id
    ''')
    
    return render_template('relatorios/turmas.html',
                         turmas=[dict(t) for t in turmas] if turmas else [])

@app.route('/relatorio/frequencia')
@login_requerido()
def relatorio_frequencia():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    dados = executar_query('''
    SELECT a.nome, t.nome as turma, COUNT(*) as total_aulas,
           SUM(CASE WHEN f.presente = 1 THEN 1 ELSE 0 END) as presentes,
           ROUND(SUM(CASE WHEN f.presente = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as percentual
    FROM frequencias f
    JOIN matriculas m ON f.matricula_id = m.id
    JOIN alunos a ON m.aluno_id = a.id
    JOIN turmas t ON m.turma_id = t.id
    GROUP BY m.aluno_id, m.turma_id
    ORDER BY a.nome
    ''')
    
    return render_template('relatorios/frequencia.html',
                         dados=[dict(d) for d in dados] if dados else [])

@app.route('/relatorio/desempenho')
@login_requerido()
def relatorio_desempenho():
    if not pode_acessar('admin', 'funcionario'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    dados = executar_query('''
    SELECT a.nome, t.nome as turma, m.nome as modulo,
           n.primeira_nota, n.segunda_nota, n.terceira_nota, n.media_final
    FROM notas n
    JOIN matriculas mat ON n.matricula_id = mat.id
    JOIN alunos a ON mat.aluno_id = a.id
    JOIN turmas t ON mat.turma_id = t.id
    JOIN modulos m ON n.modulo_id = m.id
    ORDER BY a.nome, m.nome
    ''')
    
    return render_template('relatorios/desempenho.html',
                         dados=[dict(d) for d in dados] if dados else [])

@app.route('/relatorios/historico/<int:aluno_id>')
@login_requerido()
def historico_aluno(aluno_id):
    aluno = executar_query('SELECT * FROM alunos WHERE id = ?', (aluno_id,), fetch_one=True)
    if not aluno:
        flash('Aluno não encontrado!', 'error')
        return redirect('/alunos')
    
    relatorios = executar_query('''
    SELECT * FROM relatorios_aluno WHERE aluno_id = ? ORDER BY data_criacao DESC
    ''', (aluno_id,))
    
    log = executar_query('''
    SELECT * FROM audit_log WHERE id_registro = ? ORDER BY data_acao DESC
    ''', (aluno_id,))
    
    return render_template('relatorios/historico.html',
                         aluno=dict(aluno),
                         relatorios=[dict(r) for r in relatorios] if relatorios else [],
                         log=[dict(l) for l in log] if log else [])

# ============================================================================
# ADMIN
# ============================================================================

@app.route('/admin')
@login_requerido()
def admin_dashboard():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    total_alunos = executar_query('SELECT COUNT(*) FROM alunos WHERE ativo = 1', fetch_one=True)[0] or 0
    total_professores = executar_query('SELECT COUNT(*) FROM professores WHERE ativo = 1', fetch_one=True)[0] or 0
    total_funcionarios = executar_query('SELECT COUNT(*) FROM funcionarios WHERE ativo = 1', fetch_one=True)[0] or 0
    total_turmas = executar_query('SELECT COUNT(*) FROM turmas WHERE ativa = 1', fetch_one=True)[0] or 0
    total_cursos = executar_query('SELECT COUNT(*) FROM cursos WHERE ativo = 1', fetch_one=True)[0] or 0
    receita = executar_query('SELECT SUM(valor_pago) FROM financeiro', fetch_one=True)[0] or 0
    
    return render_template('admin/dashboard.html',
                         total_alunos=total_alunos,
                         total_professores=total_professores,
                         total_funcionarios=total_funcionarios,
                         total_turmas=total_turmas,
                         total_cursos=total_cursos,
                         receita_total=float(receita) if receita else 0)

@app.route('/admin/funcionarios')
@login_requerido()
def listar_funcionarios():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    funcionarios = executar_query('''
    SELECT f.*, s.nome as setor_nome
    FROM funcionarios f
    LEFT JOIN setores s ON f.setor_id = s.id
    ORDER BY f.nome
    ''')
    
    return render_template('admin/funcionarios/listar.html', 
                         funcionarios=[dict(f) for f in funcionarios] if funcionarios else [])

@app.route('/admin/funcionario/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_funcionario():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        try:
            conexao = get_db()
            cursor = conexao.cursor()
            
            senha_temp = Autenticacao.gerar_senha_temporaria()
            
            cursor.execute('''
            INSERT INTO funcionarios (nome, email, cpf, senha, cargo, setor_id, salario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (request.form.get('nome'), request.form.get('email'), request.form.get('cpf'),
                  Autenticacao.hash_senha(senha_temp), request.form.get('cargo'),
                  request.form.get('setor_id'), request.form.get('salario')))
            
            func_id = cursor.lastrowid
            
            cursor.execute('''
            INSERT INTO usuarios (email, senha, tipo_usuario, tabela_referencia, id_referencia)
            VALUES (?, ?, ?, ?, ?)
            ''', (request.form.get('email'), Autenticacao.hash_senha(senha_temp), 'funcionario', 'funcionarios', func_id))
            
            conexao.commit()
            conexao.close()
            
            flash(f'Funcionario criado! Senha: {senha_temp}', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_FUNCIONARIO', 'funcionarios', func_id, {})
            return redirect('/admin/funcionarios')
        except Exception as e:
            flash(f'Erro: {str(e)}', 'error')
    
    setores = executar_query('SELECT * FROM setores')
    return render_template('admin/funcionarios/novo.html', 
                         setores=[dict(s) for s in setores] if setores else [])

@app.route('/admin/cursos')
@login_requerido()
def listar_cursos():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    cursos = executar_query('''
    SELECT c.*, COUNT(DISTINCT t.id) as total_turmas
    FROM cursos c
    LEFT JOIN turmas t ON c.id = t.curso_id
    GROUP BY c.id ORDER BY c.nome
    ''')
    
    return render_template('admin/cursos/listar.html', 
                         cursos=[dict(c) for c in cursos] if cursos else [])

@app.route('/admin/curso/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_curso():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        if executar_update('''
        INSERT INTO cursos (nome, descricao, duracao_meses, valor)
        VALUES (?, ?, ?, ?)
        ''', (request.form.get('nome'), request.form.get('descricao'),
              request.form.get('duracao_meses'), request.form.get('valor'))):
            flash('Curso criado!', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_CURSO', 'cursos', 1, {})
            return redirect('/admin/cursos')
        flash('Erro!', 'error')
    
    return render_template('admin/cursos/novo.html')

@app.route('/admin/modulos')
@login_requerido()
def listar_modulos():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    modulos = executar_query('''
    SELECT m.*, c.nome as curso_nome
    FROM modulos m
    JOIN cursos c ON m.curso_id = c.id
    ORDER BY c.nome, m.ordem
    ''')
    
    return render_template('admin/modulos/listar.html', 
                         modulos=[dict(m) for m in modulos] if modulos else [])

@app.route('/admin/modulo/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_modulo():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        if executar_update('''
        INSERT INTO modulos (curso_id, nome, descricao, carga_horaria, ordem)
        VALUES (?, ?, ?, ?, ?)
        ''', (request.form.get('curso_id'), request.form.get('nome'),
              request.form.get('descricao'), request.form.get('carga_horaria'),
              request.form.get('ordem'))):
            flash('Modulo criado!', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_MODULO', 'modulos', 1, {})
            return redirect('/admin/modulos')
        flash('Erro!', 'error')
    
    cursos = executar_query('SELECT * FROM cursos WHERE ativo = 1 ORDER BY nome')
    return render_template('admin/modulos/novo.html', 
                         cursos=[dict(c) for c in cursos] if cursos else [])

@app.route('/admin/setores')
@login_requerido()
def listar_setores():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    setores = executar_query('''
    SELECT s.*, COUNT(f.id) as total_funcionarios
    FROM setores s
    LEFT JOIN funcionarios f ON s.id = f.setor_id
    GROUP BY s.id ORDER BY s.nome
    ''')
    
    return render_template('admin/setores/listar.html', 
                         setores=[dict(s) for s in setores] if setores else [])

@app.route('/admin/setor/novo', methods=['GET', 'POST'])
@login_requerido()
def novo_setor():
    if not pode_acessar('admin'):
        flash('Acesso negado!', 'error')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        if executar_update('''
        INSERT INTO setores (nome, descricao)
        VALUES (?, ?)
        ''', (request.form.get('nome'), request.form.get('descricao'))):
            flash('Setor criado!', 'success')
            registrar_audit(session.get('usuario_id'), session.get('tipo_usuario'), 'CRIAR_SETOR', 'setores', 1, {})
            return redirect('/admin/setores')
        flash('Erro!', 'error')
    
    return render_template('admin/setores/novo.html')

def initialize_database():
    """Inicializa os dois grupos de tabelas usados pela aplicação."""
    criar_banco_dados()
    criar_banco_dados_v2()
    ensure_bootstrap_admin()


def run_server():
    initialize_database()
    
    print("\n" + "="*70)
    print("Sistema de Gestão Escolar v2.0")
    print("="*70)
    print("\nAcesse: http://localhost:5000")
    print("Admin: admin@escola.com / Mudar@123")
    print("\n" + "="*70 + "\n")
    
    app.run(debug=False, host=app.config['HOST'], port=app.config['PORT'], threaded=True)
