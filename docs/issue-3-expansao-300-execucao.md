# Execução da expansão: interrompida antes da extração

O [protocolo de 300 referências](issue-3-expansao-300-protocolo.md) foi registrado
em `0fb2bff`; extensão de partições e descoberta em `d5567f3`. A execução está
**incompleta por indisponibilidade de acesso à fonte**: a retomada recebeu
`YouTube search returned HTTP 429`. A condição de parada foi respeitada, sem
alternar conta, proxy ou rota para contornar o retorno.

## Estado verificável

- Cinco buscas por data concluídas, nas primeiras cinco consultas fixas do
  protocolo, retornaram 250 propostas de vídeo. Elas propõem 210 canais fora
  dos 80 antigos; isso não confirma idioma, setor, formato ou elegibilidade.
- A continuação e um probe mínimo encontraram falha de rede no ambiente
  restrito. Uma retomada com acesso de rede liberado retornou HTTP 429.
  São oito tentativas locais registradas, cinco com resposta aproveitável;
  as falhas de rede não comprovam que a requisição chegou à plataforma.
- As respostas salvas contêm somente IDs de vídeo/canal. **Nenhuma estatística
  de vídeo novo foi solicitada, nenhuma mídia adquirida e nenhuma nova referência
  liberada.** A escolha completa de canais e sua alocação ainda não aconteceram.
- A base continua com **200 referências/80 canais**, partições **124/45/31**.
  Os 31 IDs/16 canais do teste foram preservados; suas evidências/rótulos não
  foram abertos, inferidos ou avaliados. Arquivos mistos da coorte antiga não
  foram lidos. Os controles antigos fora da coorte foram usados só por identidade.
- B0 e A **não foram retreinados**, não há comparação ampliada nem novo bundle.
  B não foi iniciado. Não há sessão temporária de mídia restante.

A conferência dos 16 arquivos permitidos do checkpoint anterior manteve hashes
idênticos: seis do bundle M1, quatro fontes offline congeladas e seis arquivos
de metadados/baseline da coorte. Coorte e manifesto originais continuam coerentes,
B0 original foi recomputado/verificado e o bundle M1 original recarregou.

## Implementação verificada

`channel_partitions` aceita uma extensão de desenvolvimento com o manifesto pai
embutido. Revalida o pai e exige igualdade integral de todas as atribuições
antigas, inclusive metadados, grupos e partições. Recusa canais/IDs antigos,
duplicatas com a coorte e componentes de duplicatas que cruzem a regra fixa
dos canais novos. O formato original omite o campo opcional de extensão,
preservando serialização e hashes legados.

`expand_reference_pool` faz busca por data, sem resultados de engajamento;
filtra canais antigos antes das consultas de detalhes. Congela a alocação dos
novos canais antes de pedir estatísticas. A seleção de candidatos usa hash e
rodízio, sem priorização por título, idioma declarado ou magnitude de views.

A retomada compara hashes do pai e protocolo com o checkpoint, sem substituí-los;
reutiliza respostas de requisições exatas e seus instantes originais. Conserva
a janela original e conta tentativas falhas no orçamento persistido. HTTP 429
é persistido como parada terminal: `--resume` sozinho recusa a retomada antes
de enviar novas requisições. A revisão
independente identificou a necessidade de validar o vínculo coorte/manifesto
e recusar proveniência divergente; ambas foram cobertas por testes. O cálculo
do checksum usa a serialização canônica do módulo de partições.

Os testes usam apenas dados sintéticos: preservação dos assignments/teste,
adulteração mesmo com hash recalculado, duplicatas, compatibilidade de B0,
ordem invariável aos resultados, alocação antes das estatísticas, pai válido/
stale, retomada incompatível e orçamento após HTTP 429.

Verificação ampla: **338 testes públicos passaram**. Após acrescentar a guarda
terminal de retomada, **67 testes direcionados passaram** na versão final,
incluindo o bloqueio após HTTP 429 e sua forma legada. Ruff e formatação dos
65 arquivos Python passaram; diff sem problemas. A revisão independente aprovou
o diff final. O checkpoint privado real também foi recusado pela guarda antes
de qualquer nova chamada, sem confirmar recuperação da fonte.

## Checkpoint e retomada

Arquivos privados em `data/private/issue-3-expansao-300-v1/`:

- `parent.json`: ascendência e hash do protocolo registrado;
- `calls/0001.json` a `0005.json`: respostas das buscas concluídas;
- `request-attempts.json`: orçamento, incluindo falhas; as três falhas desta
  primeira execução foram registradas retrospectivamente;
- `failure.json`: último retorno HTTP 429;
- `execution-checkpoint.json`: contagens, isolamento e hashes conferidos.

Somente após recuperação da fonte confirmada explicitamente pelo operador,
a descoberta poderá continuar com o mesmo protocolo, sem repetir as cinco
consultas bem-sucedidas. A opção `--source-recovered` registra essa confirmação;
ela não verifica disponibilidade por conta própria nem zera o orçamento:

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.expand_reference_pool \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --output data/private/issue-3-expansao-300-v1 --resume --source-recovered
```

Essa confirmação não foi dada/executada nesta rodada. Não houve repetição
automática após o HTTP 429. A retomada permanece sujeita
às condições de parada e ao orçamento original. Depois da descoberta ainda
faltam aquisição/curadoria assistida, validação das 100 inclusões (50 por setor,
máximo cinco/canal), publicação da extensão/B0 e ajuste de A com o carregador
restrito a desenvolvimento. A comparação deve seguir o protocolo antes de B;
este checkpoint não substitui essas etapas nem declara a meta atingida.
