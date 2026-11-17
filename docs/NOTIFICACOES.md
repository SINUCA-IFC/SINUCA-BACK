# Notificações Web Push

Implementação baseada na [Unidade 8](https://eduardo-da-silva.github.io/desenvolvimento-mobile/unidade8/), com VAPID e uma inscrição por navegador. O usuário precisa entrar no aplicativo e autorizar notificações.

## Eventos

| Evento | Destinatários | Quando |
| --- | --- | --- |
| `post_created` | Todos os usuários ativos inscritos | Nova postagem salva |
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

## Mudanças acumuladas desde os CHORE

- **CHORE back `3b06c02`:** modelo/CRUD de inscrições, chave pública VAPID, envio Web Push, evento de postagem, dependência `pywebpush`, lockfile/requirements e ajustes locais PDM/VS Code.
- **CHORE front `df274f7`:** serviço de inscrição, helpers de apresentação, header de origem, integração inicial com login/logout, testes e plano de notificações.
- **Esta implementação — back:** eventos de atribuição e chat; verificação agendada de atraso com registro por prazo; CORS; timeout, retenção e falhas isoladas por endpoint; acesso do responsável à tarefa explicitamente atribuída mesmo quando ele ou o criador administrativo não tem país; novos testes. Alunos sem país continuam sem permissão de escrita.
- **Esta implementação — front:** `injectManifest` e worker próprio; banner de permissão; recebimento/clique com navegação segura e retorno após login; tarefa destacada no Kanban, ou visualização somente leitura do aviso se a conta não tem delegação; limpeza de inscrição protegida contra registro em andamento; proteção contra respostas antigas também nas mutações de tarefas; estado compartilhado de conversas; indicadores no desktop/celular e reutilização do símbolo da lista de países. O toggle legado de notificação foi removido do formulário porque não controlava a entrega; o campo de API foi preservado por compatibilidade.
- **Contadores:** delegado vê o número de mensagens não lidas na sua conversa (outros autores, conforme a API existente); organizador vê quantos países têm não lidas. A lista por país mantém a contagem individual. Funciona por consultas periódicas mesmo sem push.

As alterações desta implementação ficam no workspace para revisão, sem criação automática de commits ou publicação.
