# Verificação de mídia solicitada pelo operador

Em 19/10, após a parada por autenticação/bot, o aluno pediu expressamente verificar
se o acesso voltou e retomar até 300. Essa solicitação autoriza uma sondagem normal,
não presume recuperação e não autoriza contornar a exigência da plataforma.

`scripts.probe_media_recovery` faz uma única aquisição temporária com o downloader
existente, sem cookies, mudança de cliente, conta ou rota. Seleciona o próximo ID
não tentado da fila, respeitando cinco inclusões/canal, sem consultar novas views.
Reserva a tentativa no checkpoint antes de rede e conta tempo/tentativa no mesmo
orçamento de 450 tentativas/5.400 s. A guarda de parada permanece ativa durante a sondagem.

Confirma download e decodificação real, descarta a mídia e grava recibo antes de
liberar a parada. A sondagem técnica fica excluída do treino, sem ASR/embeddings
inventados, e o ID não é novamente tentado. Falha conserva a parada; limpeza
incerta bloqueia aquisições. Uma execução interrompida sem recibo exige auditoria.
Repetir o mesmo identificador de solicitação reutiliza o resultado, sem rede.

```bash
rtk proxy .venv/bin/python -m scripts.probe_media_recovery \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --pool data/private/issue-3-expansao-300-v1 \
  --operator-request-id 20261019-rechecagem-midia-1
```

Cada identificador novo corresponde a uma nova solicitação explícita do aluno;
não criar identificadores em loop para repetir uma falha. Após prova real de
recuperação e limpeza, o comando normal `expansion_media run` continua dos mesmos
contadores/partições/observações. A exigência de 300 e o teste reservado permanecem.

## Resultado real de 19/10

A solicitação `20261019-rechecagem-midia-1` confirmou aquisição, decodificação
e limpeza em 3,78 s, usando o mesmo downloader. A tentativa 254 ficou excluída
como sondagem técnica, preservando as 253 entradas anteriores. O recibo durável
liberou a parada e o lote normal retomou na tentativa 255, sem novo sorteio ou
atualização de observações. Foram reconferidos os 16 arquivos congelados
permitidos e o hash da seleção; nenhum arquivo reservado foi aberto.

Recibo e verificação ficam privados em
`data/private/issue-3-expansao-300-v1/source-recovery/20261019-rechecagem-midia-1/`.
O estado posterior da coleta está no [registro de execução](issue-3-expansao-300-execucao.md).
