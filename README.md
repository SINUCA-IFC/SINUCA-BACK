# SINUCA — Backend

API do Simulado Interdisciplinar das Nações Unidas do Campus Araquari. Usa Django, Django REST Framework, ORM, allauth, JWT, PostgreSQL/SQLite, Cloudinary, WhiteNoise e Web Push com VAPID.

- [Passagem de bastão](https://github.com/SINUCA-IFC/SINUCA-Documentacao-PI/blob/main/docs/PASSAGEM-DE-BASTAO.md).
- [Documentação central do projeto](https://github.com/SINUCA-IFC/SINUCA-Documentacao-PI).
- [Contrato de autenticação](docs/django-allauth.md).
- [Operação de notificações](docs/NOTIFICACOES.md).

## Situação funcional

Há usuários, países/delegações, turmas, categorias, tarefas, cronogramas, links, postagens, mensagens/leitura por usuário, uploads e inscrições push. O cadastro público cria alunos, exige confirmação de e-mail e aguarda atribuição de país pela organização. Papéis e privilégios são controlados no servidor.

O papel `evaluator` existe, mas **lançamento de notas, médias e painel de avaliação ainda não existem**. A retirada de participante também precisa ser concluída: o frontend chama `remover-delegacao`, ação ausente no backend atual. Consulte o documento de passagem de bastão para pendências e requisitos futuros.

## Preparar o ambiente local

`runtime.txt` indica Python 3.13; `pyproject.toml` declara `>=3.10`. Esta revisão foi testada com Python 3.14.9. Padronizar uma versão entre a equipe e o servidor antes de mudar as dependências.

No curso, usamos somente PDM, com ambientes virtuais desativados. Com Python e PDM instalados, executar `deactivate` caso exista um ambiente virtual ativo no terminal e preparar o projeto:

```sh
git clone https://github.com/SINUCA-IFC/SINUCA-BACK.git
cd SINUCA-BACK
pdm config --local python.use_venv false
pdm install
```

Executar os comandos locais com `pdm run`, usando as dependências gerenciadas pelo PDM.

No Linux, a identificação de conteúdo dos arquivos pode exigir `libmagic1` instalado pelo sistema. `requirements.txt` é gerado pelo PDM; não atualizar suas versões isoladamente de `pyproject.toml` e `pdm.lock`.

Criar `.env` local, sem conexão com produção:

```dotenv
MODE=DEVELOPMENT
DEBUG=True
SECRET_KEY=preencha-com-uma-chave-local-aleatoria
DATABASE_URL=sqlite:///db.sqlite3
FRONTEND_URL=http://localhost:5173
FRONTEND_ALLOWED_ORIGINS=
AUTH_CROSS_SITE_COOKIES=False
AUTH_COOKIE_SECURE=False
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Gerar a chave com `pdm run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. O e-mail de console mostra o código no terminal e não envia mensagens. Não versionar `.env`. O arquivo `.env.example` descreve configuração de deploy, não uma base SQLite local pronta.

As opções de cookies acima são necessárias para HTTP local: o modo cross-site exige cookies seguros/HTTPS. Para testar Google localmente, configurar também cliente OAuth/callback e seguir o contrato de autenticação.

```sh
pdm run migrate
pdm run createsuperuser
pdm run dev
```

O superusuário usa e-mail como login. Criar países, turmas, categorias e contas controladas em `http://127.0.0.1:8000/admin/`. O `role` organizador e as flags `is_staff`/`is_superuser` não são equivalentes. Não há carga completa homologada do evento; o script antigo incompatível foi retirado.

No frontend, usar `VITE_API_BASE_URL=http://localhost:8000` em `.env.local`, mantendo o Axios em `/api`. O proxy do Vite encaminha as chamadas; não é necessário editar o Axios para trocar de ambiente.

## Código e contratos

```text
app/                       settings, URLs, paginação e configurações de teste
core/
  models/                  entidades e relações
  serializers/             validação e representação
  views/                   endpoints, permissões e escopo
  permissions.py           regras por perfil/objeto
  services/                eventos e transporte de notificações
  management/commands/     comando de tarefas atrasadas
  migrations/              histórico do schema
  tests/ e test_*.py       regressões
uploader/                  arquivos próprios, limites, validação e uploads
```

Manter a estrutura ensinada no tutorial DRF. Não reimplementar cadastro fora do allauth nem substituir viewsets simples por uma hierarquia própria. Não apagar migrações de bancos existentes.

| Endpoint | Uso |
| --- | --- |
| `/api/token/`, `/api/token/refresh/`, `/api/token/verify/` | JWT. |
| `/api/registro/`, `/api/registro/confirmar-email/`, `/api/registro/reenviar-codigo/` | Cadastro e código real de e-mail. |
| `/api/auth/csrf/`, `/api/auth/google/`, `/api/token/session/`, `/api/auth/logout/` | Sessão Google e troca por JWT. |
| `/api/usuarios/me/`, `/api/usuarios/pendentes/`, `/api/usuarios/{id}/aprovar/` | Perfil e atribuição de país. |
| `/api/paises/`, `/api/turmas/`, `/api/categorias/` | Cadastros. |
| `/api/postagens/`, `/api/tarefas/`, `/api/cronogramas/`, `/api/docs/` | Conteúdo e atividades com permissões próprias. |
| `/api/mensagens/` e ações `conversas`, `lidas`, `nao-lidas` | Chat e leitura por usuário/delegação. |
| `/api/media/images/`, `/api/media/documents/` | Upload autenticado. |
| `/api/vapid-public-key/`, `/api/push-subscriptions/` | Web Push. |
| `/api/schema/`, `/api/doc/`, `/api/redoc/` | OpenAPI, Swagger e ReDoc. |

A barra final importa. Listas retornam `results`, `page`, `page_size` e `total_pages`; padrão de dez itens. JWT usa `Authorization: Bearer <access>`. `docs` representa links compartilhados; upload de PDF é infraestrutura distinta e ainda não está conectado ao formulário de documentos da delegação.

## Testar sem usar o banco real

```sh
pdm run python manage.py test --settings=app.settings_test --noinput
pdm run python manage.py check --settings=app.settings_test
pdm run python manage.py makemigrations --check --dry-run --settings=app.settings_test
```

Essa configuração ignora `.env`, usa SQLite em memória, e-mail de teste e armazenamento temporário. A suíte atual tem 185 testes. O aviso de VAPID vazia é esperado nesse modo. Testes locais não comprovam PostgreSQL, entrega SMTP/push, Google ou configuração publicada.

OpenAPI ainda tem pendências de introspecção, especialmente endpoints push e serializers com relações. Conferir as mensagens de `spectacular --validate`; exit code 0 sozinho não significa schema sem problemas.

## Comandos de manutenção com PDM

Executar conforme necessário; criar migrações somente após alterar os modelos e revisar os arquivos gerados antes de aplicá-los:

```sh
pdm run makemigrations
pdm run migrate
pdm run diagram
```

Para adicionar ou remover dependências, usar `pdm add` ou `pdm remove` e revisar `pyproject.toml`, `pdm.lock` e a exportação `requirements.txt`.

`dev` inicia o servidor. `makemigrations` cria migrações, `migrate` aplica as existentes e `diagram` gera diagrama com django-extensions/Graphviz. São comandos independentes: iniciar o servidor não reescreve `.env` e aplicar migrações não cria schema nem imagem implicitamente. Usar `pdm run python manage.py test --settings=app.settings_test --noinput` para testes isolados.

`pdm run check` executa o Ruff configurado. `pdm run format` inclui correção automática; revisar o diff antes de manter uma reformatação ampla.

## Produção e operação

A API publicada é `https://sinuca-backend.class.fabricadesoftware.ifc.edu.br`. Configurar no painel do servidor, sem versionar valores secretos:

- `MODE=DEPLOY`, `DEBUG=False`, `SECRET_KEY` própria e PostgreSQL em `DATABASE_URL`.
- `CLOUDINARY_URL` para mídia; estáticos servidos por WhiteNoise.
- SMTP, remetente autorizado e senha de aplicativo para confirmação real de e-mail.
- Google client ID/secret e callback `https://<backend>/accounts/google/login/callback/`.
- `FRONTEND_URL=https://sinuca-ifc-mocha.vercel.app`; origens extras somente quando necessárias em `FRONTEND_ALLOWED_ORIGINS`.
- `AUTH_COOKIE_SECURE=True` e, na topologia entre sites distintos, `AUTH_CROSS_SITE_COOKIES=True`. CORS/CSRF continuam obrigatórios; bloqueio de cookies de terceiros pode impedir o Google.
- Par VAPID e `VAPID_SUBJECT` para push. Chave privada fica no servidor.

A configuração ainda possui fallback de chave e hosts amplos: revisar antes de uso real. `TRUST_PROXY_HTTPS` só deve ser ativado se o proxy sobrescrever corretamente o header. Mais detalhes no contrato de autenticação.

O processo web é `gunicorn app.wsgi --log-file -`. `build.sh` instala dependências, coleta estáticos e aplica migrações; o `Procfile` também prevê migrações na fase release. Confirmar qual fase o provedor usa, fazer backup e testar restauração antes de mudanças em produção.

Agendar externamente `python manage.py notify_overdue_tasks`. O comando não instala cron automaticamente. Conferir entrega em navegadores/aparelhos inscritos, sem confundir resposta do provedor com exibição da notificação.

Após publicar, validar com contas de teste e API real: cadastro, código/reenvio, login/Google, aprovação, tarefas, recursos, chat e push. Registrar commits, migrações e resultados. Nenhum deploy foi realizado pela simplificação descrita na passagem de bastão.
