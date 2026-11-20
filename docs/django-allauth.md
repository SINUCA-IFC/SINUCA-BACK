# Contrato de autenticação para o frontend

Backend: `http://localhost:8000`. Frontend: `http://localhost:5173`.
O fluxo da API continua com JWT/Bearer, access válido por 3 horas e refresh por
1 dia. O allauth gerencia cadastro, confirmação e Google.

## Configuração

```powershell
pdm sync
pdm run python manage.py migrate
pdm run python manage.py runserver localhost:8000
```

O `.env` local contém `FRONTEND_URL=http://localhost:5173`. Esse valor configura
CORS, CSRF e os retornos ao frontend. As credenciais Google continuam privadas
em `.secrets/google.env` ou nas variáveis do ambiente. O callback autorizado no
Google Cloud continua `http://localhost:8000/accounts/google/login/callback/`.
Use localhost tanto no front quanto no back, sem alternar com 127.0.0.1.

A página demonstrativa da raiz e as páginas de conta do Django foram removidas
com `HEADLESS_ONLY=True`. As URLs dos provedores OAuth continuam disponíveis.
A raiz `/` agora retorna 404; o aplicativo deve ser aberto no frontend.
O backend personalizado de mensagens e os logs antigos foram removidos.
Em DEVELOPMENT, o backend padrão do Django exibe códigos apenas no terminal.
Para deploy em dev, configure SMTP e as demais variáveis de ambiente no painel do provedor de hospedagem.
Substitua as URLs locais deste contrato pelos endereços do ambiente publicado.
O frontend não recebe nem gera o código, apenas recebe o que o usuário digitar.

## Cadastro e confirmação

`POST /api/registro/`, JSON:

```json
{"email":"pessoa@example.com","password":"senha-forte","name":"Nome"}
```

Campos opcionais preservados: foto, gang, matriculation, country. Foto, gang e
country recebem IDs existentes, não 0. Role, staff e superuser não são campos
do cadastro. O retorno 201 inclui os dados públicos de cadastro e:

```json
{
  "detail":"Confirme seu e-mail com o código enviado.",
  "email_verification_required":true,
  "session_token":"identificador-temporario"
}
```

Guardar temporariamente o e-mail e session_token em sessionStorage, nunca a
senha. Mostrar `/verificar-email`. A conta ainda não tem acesso autenticado.

`POST /api/registro/confirmar-email/`, JSON `{"key":"012345"}` e header
`X-Session-Token: identificador-temporario`. O código tem seis dígitos e deve
permanecer como string. Sucesso 200 retorna `{"access":"...","refresh":"..."}`.
Armazenar tokens no mecanismo existente do site, apagar a confirmação pendente,
buscar `GET /api/usuarios/me/` com Bearer e entrar na área apropriada ao usuário.

O código expira em 600 segundos e a etapa permite três tentativas incorretas.
Se expirar ou a etapa se encerrar, pedir novo login para iniciar outra tentativa.
Não prometer um número de tentativas restantes se o backend não o informou.

`POST /api/registro/reenviar-codigo/`, sem corpo ou `{}`, mesmo X-Session-Token.
Sucesso 200 usa a estrutura nativa do allauth (status/meta), não retorna JWT.
Caso meta.session_token esteja presente, atualizar o identificador guardado.
O limite atual entre envios é 10 segundos e há limite de reenvios por etapa.
Exibir contador de 15 segundos como ajuda; o servidor é a autoridade final.
429 significa limite de frequência; 409/410 indicam que a etapa não pode ser
usada/retomada. Não reenviar automaticamente em loop.

## Login e uso da API

`POST /api/token/`, JSON `{"email":"...","password":"..."}`.
Sucesso 200: access e refresh. E-mail não verificado: 401 com
email_verification_required=true e session_token; mostrar a confirmação.
Credenciais incorretas/validação do allauth podem retornar 400 com errors[].
Não tratar todo 401 da autenticação como refresh ou logout automático.

`POST /api/token/refresh/`, JSON `{"refresh":"..."}`: retorna novo access.
`POST /api/token/verify/`, JSON `{"token":"..."}`: sucesso 200 com `{}`.
Demais APIs recebem `Authorization: Bearer <access>`.

Os erros podem ter formato DRF (`detail` ou campos com listas) ou allauth
(`errors: [{message, code, param}]`). Tratar também falhas de rede, 429 e 5xx.
Os fluxos de cadastro/login/confirmação por API não exigem cookies nem CSRF.
Uma conta com mesmo e-mail já existente deve fazer login; não recriar a conta.

## Google: navegação e retorno

1. Buscar `GET /api/auth/csrf/` com credentials=include. Retorna csrfToken e
   configura o cookie no navegador.
2. Criar formulário HTML POST para `http://localhost:8000/api/auth/google/`.
   Incluir um campo oculto `csrfmiddlewaretoken` com csrfToken. Submeter o
   formulário como navegação completa. Não fazer fetch ao endpoint de início
   OAuth: ele redireciona o navegador para o Google.
3. O backend define o provedor e o retorno fixo. Não enviar client_secret,
   callback_url ou tokens Google pelo frontend.
4. Google volta para `/accounts/google/login/callback/` no backend, que valida
   state e a identidade e redireciona para `http://localhost:5173/auth/callback`.
5. Se houver `error` na query do retorno, mostrar mensagem compreensível e ação
   para voltar ao login. Não imprimir a mensagem bruta como HTML.
6. Sem erro, obter NOVO csrfToken (o login rotaciona CSRF), com credentials=include.
7. Fazer `POST /api/token/session/`, credentials=include, header X-CSRFToken.
   Não anexar um Bearer antigo nessa operação. Sucesso 200: access e refresh.
8. Salvar JWT, buscar perfil com Bearer e entrar no site pelo fluxo habitual.

Exemplo do início:

```javascript
const base = import.meta.env.VITE_API_BASE_URL;
const response = await fetch(`${base}/api/auth/csrf/`, { credentials: 'include' });
if (!response.ok) throw new Error('Não foi possível iniciar o login.');
const { csrfToken } = await response.json();
const form = document.createElement('form');
form.method = 'POST';
form.action = `${base}/api/auth/google/`;
const input = document.createElement('input');
input.type = 'hidden';
input.name = 'csrfmiddlewaretoken';
input.value = csrfToken;
form.appendChild(input);
document.body.appendChild(form);
form.submit();
```

Login e cadastro usam o mesmo botão Google. O adapter associa uma identidade
Google verificada de Gmail ou Workspace a uma conta local ativa cujo e-mail
principal já esteja confirmado. Para novos usuários, o allauth cria o perfil.
Se a associação exigir prova adicional, o callback retorna
error=google_account_confirmation_required e oferece confirmação de senha.
Nenhum desses casos deve gerar cadastro duplicado no cliente.

## Logout

Obter CSRF e fazer POST `/api/auth/logout/` com credentials=include e X-CSRFToken
para encerrar a sessão OAuth/Django. Apagar os JWT e o estado pendente do cliente,
mesmo se ocorrer uma falha de rede, e voltar ao login. Logout de sessão não revoga
JWT já emitido: ele segue válido até expirar, conforme o mecanismo original.

## Verificação

```powershell
pdm run python manage.py test core.test_auth core.test_auth_api core.test_google_auth
```

Os testes automatizados permanecem como proteção de regressão; não são páginas
ou funcionalidades expostas ao usuário. O teste de Google simula apenas a
resposta externa (troca de código e identidade); valida o fluxo real de callback,
state, cadastro, e-mail verificado, nome, vínculo, sessão, JWT, logout e segundo
login. Também cobre cancelamento, state inválido, conflito de e-mail e CORS/CSRF.
Isso não confirma a tela de consentimento, as credenciais remotas ou uma
aprovação real no Google Cloud. Essa confirmação exige o navegador com a conta
real e as páginas do frontend prontas.

Referências: [modo headless](https://docs.allauth.org/en/latest/headless/installation.html)
e [provedor Google](https://docs.allauth.org/en/latest/socialaccount/providers/google.html).


## Recuperação com senha no fluxo Google

O retorno com google_account_confirmation_required oferece /auth/vincular-google.

1. GET /api/auth/csrf/ com cookies.
2. POST /api/auth/google/vincular/ com JSON {email,password}, cookies e
   X-CSRFToken, sem Bearer. Valida senha pelo allauth com limites de tentativas,
   conta ativa e e-mail SINUCA confirmado. Resposta 200 prepara uma autorização
   por cinco minutos e renova sessão e CSRF; não retorna JWT nem senha.
3. Obter CSRF novamente e navegar por formulário POST para
   /api/auth/google/conectar/ com csrfmiddlewaretoken. O backend usa CONNECT,
   fixa o retorno e guarda a autorização apenas no servidor.
4. Escolher no Google o mesmo e-mail da conta SINUCA. O callback exige e-mail
   Google verificado, mesma sessão/usuário, state válido, autorização recente e
   não utilizada. Uma identidade Google vinculada a outro usuário é recusada.
5. Retorno /auth/callback?flow=connect. Se houver error, não trocar por JWT.
   Códigos de erro incluem link_expired, google_email_mismatch e
   google_already_connected. Cancelamento pode usar o código nativo do allauth.
6. Sem error: novo CSRF e POST /api/token/session/ com cookies, X-CSRFToken e
   JSON {purpose:"google_connect"}. Resposta 200 inclui access, refresh e
   google_connected:true somente depois de verificar o vínculo persistido.
   O comprovante é consumido uma vez; repetição resulta em 409.
7. Salvar JWT e carregar /api/usuarios/me/ com Bearer. A conta, senha, nome,
   delegação e permissões anteriores permanecem. Próximos acessos usam o botão
   Google normal, sem repetir vinculação ou exigir senha local novamente.

Não há migração. Não foram alteradas credenciais Google, banco real nem
credenciais de produção. O código permanece no backend.
Testes em core.test_google_auth cobrem senha, CSRF, expiração, conta incorreta,
conflito, logout, replay, preservação de dados e futuro login Google. A resposta
externa do Google é simulada; consentimento real precisa de uma conta no navegador.
