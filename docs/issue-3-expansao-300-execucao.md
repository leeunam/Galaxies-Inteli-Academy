# Expansão para 300 — execução e checkpoints

## Nova verificação de acesso e retomada — 19/10/2026

A nova solicitação do aluno foi atendida com a [sondagem única auditada](issue-3-retomada-midia.md),
usando o downloader existente, sem trocar cliente, conta ou rota. A tentativa
254 confirmou download, decodificação e descarte em 3,78 s. O recibo foi gravado
antes de liberar a parada; a tentativa técnica ficou excluída do treino.
O checkpoint passou a 2.762,47 s acumulados e o lote normal retomou na tentativa
255, preservando as 68 inclusões, observações e fila anteriores. Os 16 arquivos
congelados permitidos e a seleção permaneceram idênticos. O teste segue fechado.

O relato abaixo registra a interrupção que precedeu essa prova de recuperação.
As novas inclusões só entram no checkpoint após revisão efetiva de fala e imagens.

## Interrupção anterior pela aquisição de mídia — 19/10/2026

**Meta de 300 ainda pendente.** A tentativa 253 terminou em
`authentication_or_bot_check` no YouTube. A condição de parada do
[protocolo aprovado](issue-3-expansao-300-protocolo.md) foi mantida: nenhum novo
download, troca de conta, rota, cliente ou uso de cookies após o bloqueio.
Esse retorno ocorreu na aquisição de mídia; não é um novo HTTP 429 da API.

A API de metadados voltou a responder: uma consulta real às 8h26 de São Paulo confirmou
recuperação e retomou o checkpoint. Até a descoberta final desta rodada há
**289 tentativas de metadados: 285 concluídas e quatro falhas**, incluindo
27 tentativas de busca. Respostas e instantes já salvos foram reutilizados,
sem atualizar observações anteriores. O probe das 8h26 foi a sexta busca salva,
nona tentativa acumulada; as três falhas anteriores não foram apagadas. A falha
adicional da API nesta retomada foi de rede, sem HTTP 429.

Três vias de descoberta, todas sem seleção por magnitude de views:

| Via | Candidatos após filtro de metadados |
| --- | ---: |
| Consultas originais e playlists de 80 canais novos | 361 |
| [Tópicos/hashtags](issue-3-expansao-300-aditivo-descoberta.md), vídeos diretos | 250 |
| [IDs diretos das buscas de domínio salvas](issue-3-expansao-300-aditivo-cache-dominio.md) | 415 |

São **1.026 propostas**, não referências liberadas. Alocação dos novos canais
foi persistida antes das estatísticas, excluindo os 80 canais originais e IDs
já observados. Os aditivos de descoberta foram registrados antes de suas novas chamadas.
A segunda fila filha preservou integralmente 82 tentativas anteriores e passou
a priorizar idioma declarado pt/pt-BR entre os ainda não tentados; ASR sem idioma
forçado e revisão de frames/fala continuam obrigatórios. Candidatos sem idioma
declarado não foram eliminados. O [aditivo de domínio](issue-3-expansao-300-aditivo-prioridade-dominio.md)
preservou 122 tentativas e priorizou termos fixos de moda/beleza entre os ainda
não tentados, sem transformar título em feature. A amostra é de conveniência
adaptativa; não houve ordenação por views/curtidas nem escolha por métricas de A.

## Checkpoint da interrupção anterior

| Verificação | Resultado |
| --- | ---: |
| Tentativas de mídia acumuladas | 253 |
| Extrações concluídas / falhas | 245 / 8 |
| Inclusões novas verificadas | **68** |
| Moda / beleza | **35 / 33** |
| Canais novos nas inclusões | **54** |
| Exclusões, incluindo falhas | 185 |
| Revisões pendentes / sessões temporárias / folhas de contato | **0 / 0 / 0** |
| Aquisição e extração acumuladas | 2.758,68 s (45,98 min) |

Faltam **32 inclusões: 15 de moda e 17 de beleza**. O aluno manteve 300 obrigatórias;
a base publicada continua **200/80 canais**, divisão **124/45/31**. As 68 adições
permanecem privadas no checkpoint, sem publicar uma coorte menor. B0 e A
ampliados **não foram ajustados**, não há comparação ampliada nem novo bundle,
e B não começou. Os modelos/configuração do serviço anterior permanecem iguais.

O [aditivo de continuidade](issue-3-expansao-300-aditivo-orcamento-midia.md)
permitiu 450 tentativas, mantendo os 5.400 s acumulados e 300 pedidos de metadados.
Foi ativado explicitamente, com hash vinculado ao checkpoint e sem reiniciar
contadores. A parada ocorreu por autenticação/bot, antes de esgotar o orçamento.

Curadoria: domínio deve estar demonstrado em frames ou fala, com português real
inteligível; roupa incidental em humor/entrevistas não basta. Adornos pessoais,
como tiaras, ficam em moda; cosméticos/técnicas de cuidado ficam em beleza.
Letra musical inteligível pode estabelecer português quando o domínio visual
é claro; fala fragmentária/ininteligível não é reparada para obter inclusão.
São decisões assistidas, sem alegar escuta humana ou certificação independente.
Uma possível variante reconhecida gerou, na prévia de metadados, um grupo
conservador de duas referências do mesmo canal/partição, sem afirmar identidade
de bytes. Republicações editadas
não têm detecção geral garantida.

As ferramentas de [extração, publicação e comparação](issue-3-expansao-300-ferramentas.md)
foram implementadas e verificadas. A suíte final passou em **379 testes**;
Ruff e formatação passaram nos 73 arquivos Python. A revisão independente,
somente leitura, aprovou isolamento, migrações, orçamento e variantes.
Há teste sintético integrado de publicação 200+100 com guarda ativa do teste,
rollback de staging, recibos estritos, isolamento de leitura e migrações
retomáveis. Esses testes não acrescentam referências reais.

Os 16 arquivos congelados permitidos foram reconferidos sem alterações:
bundle M1 anterior, quatro fontes offline protegidas e metadados/baseline do pai.
Nenhum arquivo misto antigo ou evidência/rótulo reservado foi aberto. A auditoria
final verificou hashes de cada evidência nova incluída, recibos, dimensões 384/512,
finitude, geometria/duração reais, idioma e igualdade integral da observação
com o `run.json`, sem renovar contagens. Um ensaio de append **em memória**, sem
liberação, conservou exatamente os 200 assignments e os 31 IDs/16 canais do teste.
Nenhuma previsão ou métrica do teste foi produzida.

O checkpoint recusou `run` antes de carregar modelos ou acessar a rede, sob
instrumentação que falharia se esses caminhos fossem executados. Limpeza de
todas as 253 tentativas foi confirmada. Não existe diretório de coorte ampliada
nem de modelos A300. A prova privada está em
`data/private/issue-3-expansao-300-v1/halt-verification-20261019.json`.

## Condições registradas na interrupção anterior

Restabelecer o acesso normal à mídia do YouTube antes de qualquer nova aquisição.
Uma resposta HTTP 200 da API de metadados, sozinha, não verifica essa recuperação.
Não apagar `halt_reason`, reiniciar contadores ou tentar outros clientes/contas/
rotas para passar pela exigência. Este checkpoint não contém uma retomada
automática que contorne o bloqueio. A nova verificação da fonte deve ser explícita
e registrada antes de liberar a guarda terminal.

Continuar a partir de `extraction/checkpoint.json`, hash
`b94522c0dce68f4df9c7a65ca72da913465c517bc5166fd21b34e3f7ca2f4f45`,
e da seleção filha já persistida em `candidates.json`. Saldo operacional:
197 tentativas de mídia e 2.641,32 s; 11 chamadas de metadados, no máximo uma busca
pelos aditivos atuais. Preservar as 68 inclusões e observações já verificadas,
sem retry dos IDs tentados ou novo sorteio. Depois das 32 inclusões restantes,
liberar 300, recalcular B0 e ajustar/comparar A conforme a receita registrada.

## Histórico da primeira interrupção — 18/10/2026

O relato abaixo descreve o checkpoint anterior, superado pela retomada acima.

O [protocolo de 300 referências](issue-3-expansao-300-protocolo.md) foi registrado
em `0fb2bff`; extensão de partições e descoberta em `d5567f3`. A execução está
**incompleta por indisponibilidade de acesso à fonte**: a retomada recebeu
`YouTube search returned HTTP 429`. A condição de parada foi respeitada, sem
alternar conta, proxy ou rota para contornar o retorno.

### Estado no checkpoint de 18/10

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

### Implementação naquele checkpoint

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

### Retomada de metadados descrita em 18/10

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

Essa confirmação ainda não havia sido dada na rodada de 18/10. Não houve repetição
automática após o HTTP 429. A retomada permanece sujeita
às condições de parada e ao orçamento original. Depois da descoberta ainda
faltam aquisição/curadoria assistida, validação das 100 inclusões (50 por setor,
máximo cinco/canal), publicação da extensão/B0 e ajuste de A com o carregador
restrito a desenvolvimento. A comparação deve seguir o protocolo antes de B;
este checkpoint não substitui essas etapas nem declara a meta atingida.
