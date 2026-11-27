# Notificações Web Push

Implementação baseada na [Unidade 8](https://eduardo-da-silva.github.io/desenvolvimento-mobile/unidade8/), com VAPID e uma inscrição por navegador. O usuário precisa entrar no aplicativo e autorizar notificações.

## Eventos

| Evento | Destinatários | Quando |
| --- | --- | --- |
| `post_created` | Todos os usuários ativos inscritos | Nova postagem salva pela API ou pelo Django Admin |
| `task_assigned` | Responsáveis recém-adicionados | Criação ou edição de tarefa |
| `task_overdue` | Cada responsável ativo inscrito | Prazo anterior ao dia atual e status diferente de concluída |
| `message_created` | Organizadores, se aluno enviou; alunos do país destinatário, se organização enviou | Mensagem salva |

Nos eventos iniciados pelo navegador, `X-Push-Endpoint` exclui somente a sessão de origem. O próprio remetente não entra nos destinatários de chat. Outras sessões do autor podem receber avisos de postagem. O corpo do push de chat não contém o texto privado da conversa.

O envio de postagem, atribuição e chat acontece após a confirmação da transação, sem fila externa. Falhas de push não desfazem a ação original. O serviço aplica timeout de 10 segundos por endpoint e retenção de até 24 horas (`TTL=86400`) no Push Service para dispositivos temporariamente offline. Uma falha de rede ou chave inválida em uma inscrição não interrompe as demais nem descarta os envios aceitos. Inscrições que retornam 404/410 são desativadas. Em um evento comum, falhas não têm fila automática de novas tentativas.

## Configuração e publicação

Instale as dependências do projeto, configure no ambiente do backend:

```dotenv
VAPID_PUBLIC_KEY=<chave pública base64url>
VAPID_PRIVATE_KEY=<chave privada VAPID>
VAPID_SUBJECT=mailto:contato@seu-dominio.com
```

As chaves devem formar o mesmo par. Somente a chave pública é retornada por `/api/vapid-public-key/`; nunca configure a chave privada no front. Para gerar um par usando a biblioteca já instalada:

```bash
pdm run vapid --gen
pdm run vapid --applicationServerKey
```

O primeiro comando gera `private_key.pem` e `public_key.pem` no diretório atual; o segundo mostra a chave pública para o navegador. `VAPID_PRIVATE_KEY` pode apontar para o caminho absoluto do PEM privado. Guarde esses arquivos fora do repositório, com acesso restrito ao servidor. A rotação de chaves exige remover e recriar as inscrições dos navegadores.

```bash
pdm run migrate
pdm run python manage.py notify_overdue_tasks
```

As migrações `0029` (inscrições) e `0030` (avisos de atraso) precisam estar aplicadas. O aplicativo publicado deve usar HTTPS. O CORS permite o header `X-Push-Endpoint`.

## Agendamento de atrasos

Web Push não verifica datas sozinho. Configure um agendador do ambiente publicado para executar diariamente, por exemplo às 08h no fuso America/Sao_Paulo:

```cron
0 8 * * * cd /caminho/SINUCA-BACK && /caminho/pdm run python manage.py notify_overdue_tasks >> /caminho/logs/overdue.log 2>&1
```

O exemplo pressupõe que o fuso do agendador seja America/Sao_Paulo e que o processo carregue as mesmas variáveis/banco do aplicativo. Adapte caminhos e ambiente. Este repositório entrega o comando; não configura um agendador externo automaticamente.

`endDate` é uma data: uma tarefa com prazo em 17/11 vence depois do fim desse dia e será encontrada pela próxima execução do dia 18/11. Sem prazo ou concluída não recebe aviso. O campo legado `Task.notification` não representa autorização, entrega ou leitura.

Há um registro único por tarefa, responsável e data de prazo. Mudar o prazo permite outro aviso quando a nova data vencer; reabrir sem mudar o prazo não repete um aviso já enviado. Se não há inscrição, configuração VAPID ou envio bem-sucedido, a próxima execução pode tentar novamente. A entrega é considerada bem-sucedida quando pelo menos um endpoint do responsável aceita o push; falhas em outros dispositivos não geram reenvio para aquele prazo.

O comando revalida status/prazo sob bloqueio da tarefa e serializa execuções concorrentes no PostgreSQL. Evite execuções sobrepostas em SQLite, cujo bloqueio tem outra granularidade. Não existe garantia de entrega exatamente uma vez entre banco e serviço externo: uma interrupção depois do envio e antes de salvar o registro pode repetir o aviso. Aceitação do serviço push não confirma exibição ou leitura.

## Verificação

```bash
pdm run python manage.py test --settings=app.settings_test --noinput
pdm run python manage.py makemigrations --check --dry-run --settings=app.settings_test
```

Testes automatizados simulam o Push Service e verificam destinatários, inscrições, isolamento, falhas, atribuições e atrasos. Para verificar entrega real, publique front/back com VAPID, entre em dois navegadores, autorize notificações e exercite os quatro eventos. Confirme a exclusão da origem e clique nos avisos com sessão ativa e expirada.

Para testar o front local no Firefox, prefira `npm run build` e `npm run preview` em vez do worker de desenvolvimento do Vite. Use dois navegadores normais ou perfis separados, e autorize notificações na origem exibida pelo preview. O front local continua apontando para a API publicada configurada em Axios; as inscrições precisam chegar a esse mesmo backend. Verifique a resposta 200/201 do cadastro e a existência de inscrições ativas.

No Fabroku, confira se `GET /api/vapid-public-key/` devolve uma chave preenchida e se `VAPID_PRIVATE_KEY` está configurada. Procure nos logs `Web Push skipped`, `Web Push delivery failed` e `Falha no envio do evento push`. Não é necessário agendar o comando de atrasos para testar postagens ou chat: esses eventos são imediatos.

### Diagnóstico no Fabroku

Depois de publicar esta versão do backend, execute no painel o comando permitido:

```bash
python manage.py showmigrations
```

As verificações do Django agora validam a configuração VAPID antes de listar as migrações. O comando não altera o banco, não envia notificações nem mostra valores das chaves.

| Aviso | Significado |
| --- | --- |
| `core.W001` | Uma ou ambas as chaves VAPID estão ausentes no processo do backend. |
| `core.W002` | A chave privada não pode ser carregada ou não usa a curva P-256. Use base64url RAW/DER ou um caminho PEM existente no servidor. |
| `core.W003` | A chave pública está inválida ou não corresponde à privada. Configure as duas do mesmo par. |
| `core.W004` | O contato VAPID não é aceito pela biblioteca. Para e-mail, inclua o prefixo `mailto:`. |

Os avisos ajudam a localizar a falha e não impedem o uso do restante do sistema. A ausência deles confirma apenas a consistência da configuração; não testa a conexão de saída do servidor com o Push Service, nem confirma exibição no dispositivo.

Se o painel não exibir a saída de `showmigrations`, o diagnóstico também aparece nos logs da aplicação quando um envio recebe HTTP 401/403. Depois de publicar o backend e enviar uma mensagem nova, filtre por `Web Push`. A linha `Web Push configuration core.W003`, por exemplo, confirma que as chaves configuradas não correspondem. Se os testes da configuração passarem, aparece `Web Push VAPID configuration is valid`; nesse caso, a rejeição ainda precisa ser investigada na inscrição e na resposta do provedor. Esses registros não incluem valores das chaves, endpoints nem corpo privado das mensagens.

Cada evento com chave privada configurada também registra um resumo em nível INFO, habilitado no console apenas para o serviço de push:

```text
Web Push result event=message_created attempted=2 accepted=1 failed=1.
```

`attempted=0` significa que nenhuma inscrição ativa correspondeu aos destinatários após os filtros e a exclusão da origem. `accepted` conta envios aceitos pelo serviço de push, sem confirmar chegada ao navegador, exibição ou leitura. `failed` conta tentativas rejeitadas ou com erro de rede/criptografia. O resumo não contém endpoints, chaves ou conteúdo das notificações.

Para observar a chegada ao navegador, execute no Console do **front**, mantenha a aba aberta e envie uma mensagem pelo outro navegador:

```js
navigator.serviceWorker.addEventListener('message', async ({ data }) => {
  if (data?.type !== 'PUSH_RECEIVED') return;
  console.log('PUSH CHEGOU AO NAVEGADOR:', data.payload?.event);
  await new Promise(resolve => setTimeout(resolve, 1000));
  const registro = await navigator.serviceWorker.ready;
  console.log('Notificações registradas:', (await registro.getNotifications()).map(n => n.title));
});
```

O listener observa apenas eventos novos e desaparece ao recarregar a página. Se houver aceitação no backend, mas nenhum evento no navegador, investigue a conexão do navegador ao serviço de push e o worker ativo. Se chegar `PUSH_RECEIVED`, verifique erros de `showNotification` no console do service worker e a exibição pelo navegador/sistema operacional. A lista de notificações pode estar vazia se o aviso já tiver sido fechado.

Uma inscrição existente no navegador não prova que foi criada com a chave atual. O front compara `subscription.options.applicationServerKey` com a chave pública da API em cada sincronização e renova a inscrição quando forem diferentes. Após atualizar o front, sair e entrar novamente dispara essa verificação. Se o erro continuar com a configuração consistente, consulte os logs de execução do **backend**, no horário de uma mensagem nova, e confira se o destinatário é uma conta ativa inscrita da delegação correta. Logs antigos de deploy do frontend não registram esse envio.

## Postagens pelo Admin e testes

A criação pelo Django Admin usa o mesmo serviço e payload da API, após a confirmação da transação. Edições não repetem a notificação. Criações diretas no banco ou pelo ORM fora desses fluxos não disparam o evento automaticamente.

Os testes de chat também validam assinatura JWT e criptografia do payload usando pywebpush, com transporte HTTP simulado. Isso protege o contrato, mas a entrega real deve ser confirmada em navegadores inscritos na versão publicada.
