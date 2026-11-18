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
vapid --gen
vapid --applicationServerKey
```

O primeiro comando gera `private_key.pem` e `public_key.pem` no diretório atual; o segundo mostra a chave pública para o navegador. `VAPID_PRIVATE_KEY` pode apontar para o caminho absoluto do PEM privado. Guarde esses arquivos fora do repositório, com acesso restrito ao servidor. A rotação de chaves exige remover e recriar as inscrições dos navegadores.

```bash
python manage.py migrate
python manage.py notify_overdue_tasks
```

As migrações `0029` (inscrições, introduzida pelo CHORE) e `0030` (avisos de atraso) precisam estar aplicadas. O aplicativo publicado deve usar HTTPS. O CORS permite o header `X-Push-Endpoint`.

## Agendamento de atrasos

Web Push não verifica datas sozinho. Configure um agendador do ambiente publicado para executar diariamente, por exemplo às 08h no fuso America/Sao_Paulo:

```cron
0 8 * * * cd /caminho/SINUCA-BACK && /caminho/venv/bin/python manage.py notify_overdue_tasks >> /caminho/logs/overdue.log 2>&1
```

O exemplo pressupõe que o fuso do agendador seja America/Sao_Paulo e que o processo carregue as mesmas variáveis/banco do aplicativo. Adapte caminhos e ambiente. Este repositório entrega o comando; não configura um agendador externo automaticamente.

`endDate` é uma data: uma tarefa com prazo em 17/11 vence depois do fim desse dia e será encontrada pela próxima execução do dia 18/11. Sem prazo ou concluída não recebe aviso. O campo legado `Task.notification` não representa autorização, entrega ou leitura.

Há um registro único por tarefa, responsável e data de prazo. Mudar o prazo permite outro aviso quando a nova data vencer; reabrir sem mudar o prazo não repete um aviso já enviado. Se não há inscrição, configuração VAPID ou envio bem-sucedido, a próxima execução pode tentar novamente. A entrega é considerada bem-sucedida quando pelo menos um endpoint do responsável aceita o push; falhas em outros dispositivos não geram reenvio para aquele prazo.

O comando revalida status/prazo sob bloqueio da tarefa e serializa execuções concorrentes no PostgreSQL. Evite execuções sobrepostas em SQLite, cujo bloqueio tem outra granularidade. Não existe garantia de entrega exatamente uma vez entre banco e serviço externo: uma interrupção depois do envio e antes de salvar o registro pode repetir o aviso. Aceitação do serviço push não confirma exibição ou leitura.

## Verificação

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
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

Uma inscrição existente no navegador não prova que foi criada com a chave atual. O front agora compara `subscription.options.applicationServerKey` com a chave pública da API em cada sincronização e renova a inscrição quando forem diferentes. Após atualizar o front, sair e entrar novamente dispara essa verificação. Se o erro continuar com a configuração consistente, consulte os logs de execução do **backend**, no horário de uma mensagem nova, e confira se o destinatário é uma conta ativa inscrita da delegação correta. Logs antigos de deploy do frontend não registram esse envio.

### Resultado da varredura de 18/11/2026

- A API publicada respondeu HTTP 200 com chave pública de 87 caracteres e ponto P-256 válido. Isso não permite conferir a chave privada da hospedagem.
- Foram revisados cadastro/autenticação da inscrição, associação ao usuário, header de exclusão da origem, destinatários de chat e tarefas, postagens API/Admin, atrasos, payload, worker, clique, permissões, CORS e configuração de publicação.
- Foi reproduzida e corrigida a reutilização de uma inscrição vinculada a uma chave VAPID anterior. Os testes comprovam a renovação quando a chave muda e a preservação quando continua igual.
- O teste de chat agora executa `pywebpush` real com as versões do `requirements.txt`, valida a assinatura JWT e descriptografa o conteúdo nos dois sentidos da conversa. Somente o transporte HTTP externo é substituído; isso não representa uma entrega real pelo Fabroku.
- O `.env` local não tem VAPID configurado. Essa observação descreve o ambiente local e não determina as variáveis publicadas. O front está apontando para a API publicada; alterações locais no backend precisam ser publicadas para afetar esse teste.
- A falha específica que ainda ocorre no servidor só pode ser confirmada após verificar a configuração nesse processo e observar uma tentativa de entrega. Os logs fornecidos até aqui são de um deploy do frontend em 27/10.

A criação pelo Django Admin agora usa o mesmo serviço e payload da API, após a confirmação da transação. Edições não repetem a notificação. Criações diretas no banco ou pelo ORM fora desses fluxos não disparam o evento automaticamente. Esta correção precisa ser publicada no backend para valer no Admin do Fabroku.

## Mudanças acumuladas desde os CHORE

- **CHORE back `3b06c02`:** modelo/CRUD de inscrições, chave pública VAPID, envio Web Push, evento de postagem, dependência `pywebpush`, lockfile/requirements e ajustes locais PDM/VS Code.
- **CHORE front `df274f7`:** serviço de inscrição, helpers de apresentação, header de origem, integração inicial com login/logout, testes e plano de notificações.
- **Esta implementação — back:** eventos de atribuição e chat; verificação agendada de atraso com registro por prazo; CORS; timeout, retenção e falhas isoladas por endpoint; acesso do responsável à tarefa explicitamente atribuída mesmo quando ele ou o criador administrativo não tem país; novos testes. Alunos sem país continuam sem permissão de escrita.
- **Esta implementação — front:** `injectManifest` e worker próprio; banner de permissão; recebimento/clique com navegação segura e retorno após login; tarefa destacada no Kanban, ou visualização somente leitura do aviso se a conta não tem delegação; limpeza de inscrição protegida contra registro em andamento; proteção contra respostas antigas também nas mutações de tarefas; estado compartilhado de conversas; indicadores no desktop/celular e reutilização do símbolo da lista de países. O toggle legado de notificação foi removido do formulário porque não controlava a entrega; o campo de API foi preservado por compatibilidade.
- **Contadores:** delegado vê o número de mensagens não lidas na sua conversa (outros autores, conforme a API existente); organizador vê quantos países têm não lidas. A lista por país mantém a contagem individual. Funciona por consultas periódicas mesmo sem push.

As alterações desta implementação ficam no workspace para revisão, sem criação automática de commits ou publicação.
