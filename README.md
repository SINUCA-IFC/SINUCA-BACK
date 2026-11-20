# SINUCA-BACK

Veja o [contrato de autenticação](docs/django-allauth.md) para Google, JWT e
confirmação de e-mail por código de 6 dígitos.

## Deploy em dev

Configure as variáveis de ambiente diretamente no painel do provedor de hospedagem.
Use `MODE=DEPLOY` e `DEBUG=False`; `DEVELOPMENT`
é reservado à execução local. O banco remoto deve ser PostgreSQL, com backup
antes das migrações de um banco existente. Não envie `.env`, banco SQLite,
dump, mídia local ou `.secrets` para o servidor.

Configure SMTP e um remetente autorizado: a confirmação obrigatória de e-mail
depende de entrega real. No Google Cloud, cadastre o callback
`https://<host-do-backend>/accounts/google/login/callback/`.
`FRONTEND_URL` deve ser a origem HTTPS exata do frontend, sem caminho.
Para autenticação por cookies, prefira front e API no mesmo site (subdomínios
do mesmo domínio); domínios distintos exigem configuração adicional de cookies.

O build é `bash build.sh` e o início é `gunicorn app.wsgi --log-file -`.
O build instala dependências, coleta estáticos e aplica migrações.
O `Procfile` também oferece migração na fase release para provedores que a suportam.

Valide com as variáveis do ambiente configuradas:

```sh
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
```

Após o deploy, valide cadastro, recebimento do código por e-mail, login e Google.
Os testes automatizados de autenticação permanecem no projeto como proteção
contra regressões e não são executados pelo servidor web.
