# SINUCA — Back-end

API do **Simulado Interdisciplinar das Nações Unidas do Campus Araquari (SINUCA)**, projeto do Instituto Federal Catarinense.

O sistema apoia a organização do evento e a comunicação com os participantes, centralizando delegações, tarefas, cronogramas, notícias e materiais de apoio.

A interface web está no [SINUCA-FRONT](https://github.com/SINUCA-IFC/SINUCA-FRONT).

## Funcionalidades

- Autenticação JWT com login por e-mail.
- Cadastro público de alunos.
- Aprovação com atribuição de delegação pela organização.
- Perfis de aluno, avaliador e organizador.
- Gestão de países, turmas, categorias e postagens.
- Tarefas com responsáveis e prazos.
- Cronogramas e materiais de apoio.
- Mensagens entre a organização e as delegações.
- Upload de imagens e documentos.
- Notificações Web Push.
- Administração pelo Django Admin.
- Documentação OpenAPI com Swagger UI e ReDoc.

O perfil de avaliador existe no modelo de usuário, mas um módulo de atribuição de notas às delegações não está implementado nesta versão. A disponibilidade dos recursos na interface depende da versão do front-end.

## Tecnologias

| Tecnologia | Finalidade |
| --- | --- |
| Python / Django | Aplicação e modelos |
| Django REST Framework | API REST |
| Simple JWT | Autenticação |
| drf-spectacular | Documentação OpenAPI |
| SQLite / PostgreSQL | Banco de dados |
| Cloudinary | Armazenamento de mídia em produção |
| WhiteNoise | Arquivos estáticos |
| pywebpush | Notificações |
| Gunicorn | Servidor WSGI |
| PDM | Dependências e tarefas |

As dependências estão definidas em `pyproject.toml`, `pdm.lock` e `requirements.txt`. O `requirements.txt` é gerado pelo PDM.

## Pré-requisitos

- Git.
- Python 3.13, conforme `runtime.txt`.
- pip e suporte a ambientes virtuais, ou PDM.
- Biblioteca `libmagic` no Linux para identificação de arquivos.

O `pyproject.toml` declara Python >= 3.10; a compatibilidade efetiva também depende das versões travadas das dependências.

Em Debian/Ubuntu, quando necessário:

```bash
sudo apt-get install libmagic1
```

O banco padrão é SQLite. PostgreSQL pode ser configurado por `DATABASE_URL`.

## Instalação

```bash
git clone https://github.com/SINUCA-IFC/SINUCA-BACK.git
cd SINUCA-BACK
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Linux / macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuração

A aplicação carrega o arquivo `.env` da raiz com `python-dotenv`. Edite os valores para o ambiente local:

```dotenv
MODE=DEVELOPMENT
DEBUG=True
SECRET_KEY=substitua-por-uma-chave-local-aleatoria
DATABASE_URL=sqlite:///db.sqlite3
```

Gere uma chave com:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| Variável | Finalidade |
| --- | --- |
| `MODE` | `DEVELOPMENT` seleciona armazenamento local de mídia |
| `DEBUG` | Ativa depuração; padrão: `False` |
| `SECRET_KEY` | Chave do Django |
| `DATABASE_URL` | Conexão com o banco |
| `CLOUDINARY_URL` | Configuração de mídia fora do modo de desenvolvimento |
| `VAPID_PUBLIC_KEY` | Chave pública Web Push |
| `VAPID_PRIVATE_KEY` | Chave privada VAPID ou caminho absoluto do PEM |
| `VAPID_SUBJECT` | Contato do serviço push, como `mailto:contato@seu-dominio.com` |

Mantenha senhas e chaves privadas fora de commits.

### Mídia em desenvolvimento

Em `app/settings.py`, o ramo `MODE == 'DEVELOPMENT'` define atualmente:

```python
MEDIA_URL = 'https://127.0.0.1:800/media/'
```

Para servir uploads com o servidor local na porta 8000, ajuste para:

```python
MEDIA_URL = 'http://127.0.0.1:8000/media/'
```

Essa URL está definida no código e não é corrigida apenas pela criação do `.env`.

## Banco de dados e execução

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

A autenticação do superusuário utiliza e-mail.

| Endereço | Finalidade |
| --- | --- |
| http://127.0.0.1:8000/admin/ | Administração |
| http://127.0.0.1:8000/api/ | Raiz da API |
| http://127.0.0.1:8000/api/doc/ | Swagger UI |
| http://127.0.0.1:8000/api/redoc/ | ReDoc |
| http://127.0.0.1:8000/api/schema/ | Esquema OpenAPI |

Cadastre países, turmas e demais dados iniciais pelo Admin.

Para integrar o front-end local, configure o Axios para utilizar `http://127.0.0.1:8000/api`.

## Autenticação

Solicite os tokens utilizando uma conta existente:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@example.com","password":"sua-senha"}'
```

A resposta contém `access` e `refresh`.

Nas requisições autenticadas, envie:

```http
Authorization: Bearer <access>
```

### Aprovação de alunos

O cadastro público cria um aluno sem país, com aprovação pendente.

Organizadores e superusuários podem consultar:

```http
GET /api/usuarios/pendentes/
```

Para atribuir uma delegação:

```http
POST /api/usuarios/{id}/aprovar/
Content-Type: application/json

{"country": 1}
```

A aprovação atribui a delegação. Alunos sem delegação possuem restrições de escrita.

## Endpoints principais

| Caminho | Recurso |
| --- | --- |
| `/api/token/` | Obtenção de tokens |
| `/api/token/refresh/` | Renovação do token |
| `/api/token/verify/` | Verificação do token |
| `/api/registro/` | Cadastro de aluno |
| `/api/usuarios/` | Usuários |
| `/api/usuarios/me/` | Usuário autenticado |
| `/api/usuarios/pendentes/` | Alunos aguardando delegação |
| `/api/usuarios/{id}/aprovar/` | Atribuição de delegação |
| `/api/paises/` | Países |
| `/api/turmas/` | Turmas |
| `/api/categorias/` | Categorias |
| `/api/postagens/` | Postagens |
| `/api/tarefas/` | Tarefas |
| `/api/cronogramas/` | Cronogramas |
| `/api/docs/` | Links e materiais |
| `/api/mensagens/` | Mensagens |
| `/api/media/images/` | Upload de imagens |
| `/api/media/documents/` | Upload de documentos |
| `/api/vapid-public-key/` | Chave pública VAPID |
| `/api/push-subscriptions/` | Inscrições Web Push |

Consulte o Swagger para métodos, campos, ações e permissões. As listagens utilizam paginação com tamanho padrão de 10 itens.

## Notificações Web Push

Configure o par de chaves VAPID no ambiente do back-end. A chave privada deve permanecer somente no servidor.

Os eventos incluem:

- Criação de postagens.
- Atribuição de tarefas.
- Novas mensagens.
- Tarefas atrasadas.

A verificação de atrasos depende da execução periódica de:

```bash
python manage.py notify_overdue_tasks
```

O comando não configura um agendador automaticamente.

Consulte [docs/NOTIFICACOES.md](docs/NOTIFICACOES.md) para geração de chaves, configuração, agendamento e testes. O recebimento também exige um cliente com suporte a push e autorização do usuário.

## Verificações

Com o ambiente configurado:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

A suíte contém testes de permissões, aprovação, mensagens, tarefas, paginação, uploads e notificações.

### Alternativa com PDM

```bash
pdm install
pdm run python manage.py migrate
pdm run python manage.py runserver 127.0.0.1:8000
pdm run test
pdm run check
```

`pdm run check` executa o Ruff.

O script `pdm run migrate` também gera migrações e um diagrama por meio de hooks. Utilize `pdm run python manage.py migrate` para apenas aplicar as migrações existentes.

## Estrutura

```text
app/                     Configurações e URLs
core/
  management/commands/   Comandos administrativos
  migrations/            Migrações do domínio
  models/                Modelos
  serializers/           Serialização e validação
  services/              Serviços de notificações
  tests/                 Testes automatizados
  views/                 Endpoints
uploader/                Uploads e validação de arquivos
docs/                    Documentação complementar
scripts/                 Utilitários
manage.py                Comandos Django
pyproject.toml           Dependências e tarefas PDM
requirements.txt         Dependências exportadas
Procfile                 Processos web e release
build.sh                 Instalação, estáticos e migrações
```

## Publicação

O `Procfile` utiliza Gunicorn para servir `app.wsgi` e define uma etapa de release para aplicar migrações.

O `build.sh` instala dependências, coleta arquivos estáticos e aplica migrações.

Configure no ambiente de destino:

- `SECRET_KEY` própria.
- `DEBUG=False`.
- `DATABASE_URL`.
- `MODE` diferente de `DEVELOPMENT`.
- `CLOUDINARY_URL` para o armazenamento padrão de produção.
- Chaves VAPID, se forem utilizadas notificações.
- HTTPS.

As configurações de hosts e CORS estão em `app/settings.py` e atualmente são permissivas. Ajuste-as aos domínios da implantação.

## Referências

- [Front-end](https://github.com/SINUCA-IFC/SINUCA-FRONT)
- [Organização SINUCA-IFC](https://github.com/SINUCA-IFC)
- [Documento do projeto](https://docs.google.com/document/d/17GRwIq2vJa5Fo7NMv2ppM04NwbgOPGmEZtuLE4Cn_as/edit)

## Licença

O `pyproject.toml` declara licença MIT.
