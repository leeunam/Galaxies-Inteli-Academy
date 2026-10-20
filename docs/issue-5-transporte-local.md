# Issue #5 — transporte injetável local

Preparação de 20/10/2026, independente da fila VLM selada da #4. O módulo
`scripts/explanation_transport.py` acrescenta a execução assíncrona da
[seleção fechada de evidências](issue-5-fronteira-explicacao-local.md).
Recebe um contexto já validado e um callback local confiável; não contém cliente
NIM, acesso a credenciais, SDK de provedor, rede ou integração com serviço/MCP.

## Contrato e limites

`run_explanation(context, transport=None, limits=TransportLimits())` mantém o
relatório numérico original no campo `analysis`. Sem callback, devolve explicação
`incomplete` com `transport_not_configured`, sem tentativa. Uma resposta válida
seleciona somente IDs do catálogo, com o SHA do mesmo pacote; a renderização
continua determinística. Não há geração livre, nova previsão, ranking pelo modelo
ou avaliação de aderência qualitativa (`not_evaluated`).

O callback recebe JSON reduzido, schema, instrução fixa, orçamento restante em
segundos e indicação de até 2.048 tokens de saída. A requisição é recusada antes
do envio se exceder 64 KiB. A resposta textual precisa caber em 16 KiB UTF-8 e
ter envelope `TransportReply` com `finish_reason="stop"`. O limite de tokens é
uma instrução para o futuro adaptador, não uma medição ou garantia de custo.
O limite de resposta é conferido após a entrega; não limita a memória consumida
internamente pelo callback. Um futuro cliente deverá limitar o corpo na leitura.

Há até duas tentativas totais e prazo total de até 45 s, configuráveis somente
para valores menores. Apenas seleção inválida permite um reparo, com o mesmo
pacote e instrução fixa. A saída rejeitada e os detalhes de validação não são
reenviados. Falha de transporte, timeout, envelope inválido, saída truncada/tool
call e excesso de bytes encerram sem reparo. A saída incompleta tem código fixo
e nenhuma afirmação; exceções e conteúdo bruto não aparecem no resultado/log.
Cancelamento solicitado pelo chamador é propagado, sem criar tarefa de fundo.

O prazo usa `asyncio.timeout` e um único relógio monotônico, incluindo reparo e
validação. Uma resposta entregue após o prazo é descartada. Como explica a
[documentação Python sobre cancelamento](https://docs.python.org/3.11/library/asyncio-task.html#task-cancellation),
cancelar uma coroutine depende de cooperação: um callback que bloqueie o loop ou
suprima cancelamento indefinidamente pode impedir o retorno no prazo. Esta função
não isola processos, não torna código arbitrário seguro e não garante SLA de
parede. Um adaptador real precisará ser verificado separadamente.

## Verificação e fronteiras preservadas

Os testes usam exclusivamente callbacks falsos e inputs públicos sintéticos,
com DNS/conexões por socket bloqueados e tentativa de rede fazendo o teste
falhar. Cobrem sucesso para um, três e cinco candidatos, relatório/ranking/faixas
preservados, pacote reduzido, reparo limitado, falhas e sigilo de erros, limites
de bytes, prazo compartilhado, cancelamento e resposta válida tardia.

Passaram **19 testes novos**, **686 testes completos em 429,56 s**, Ruff e
formatação dos 121 arquivos. A revisão independente somente leitura aprovou a
unidade. Os 588 arquivos protegidos, incluindo as oito folhas, e todas as versões
instaladas continuaram idênticos.

`explanation_transport.real_provider_verified` é sempre `false`. Não foram
executados NIM, StateGraph, demo real ou avaliação de qualidade explicativa.
Também não houve instalação, mudança de lock/ambiente, treino, aquisição,
inferência VLM, abertura do teste ou alteração de M1/serviço/MCP. As oito folhas
de recuperação continuam preservadas; as duas filas V9 permanecem seladas.
Recibos locais desta unidade: `data/private/issue-5-transporte-local-v1/`.

O uso externo de dados, o cliente NIM real e o projeto isolado LangGraph seguem
dependendo das decisões específicas registradas na fronteira local. A presença
deste módulo não libera a continuidade da #4 nem autoriza chamadas externas.
