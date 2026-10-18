# Curadoria do piloto de baseline — 18/10/2026

**Os vinte candidatos receberam decisão para o piloto: doze incluídos e oito
excluídos.** Há sete referências de moda e cinco de beleza, de doze canais
distintos. Essa coorte libera estatísticas observadas de baseline para a #2;
não libera os experimentos supervisionados A/B/C nem constitui a base de
200–300 referências planejada.

## Idioma e inclusão

Os dezesseis áudios pendentes foram adquiridos novamente, processados localmente
e descartados, um por vez. Não houve reprodução nos alto-falantes ou envio de
áudio/transcrição a serviço externo. O faster-whisper small CPU int8 usa a revisão
já congelada no projeto, com detecção automática (`language=None`) e VAD.
O extrator anterior que forçava `language="pt"` não foi usado como prova de idioma.

A triagem foi fixada antes do lote: probabilidade de idioma >= 0,85, ao menos
cinco palavras e dois segundos em segmentos utilizáveis, logprob >= -1 e
probabilidade de ausência de fala < 0,6. Esses limiares são operacionais;
probabilidades do modelo não são acurácia calibrada. Resultado vazio ou curto
não prova ausência de fala nem autoriza atribuir inglês ou português.

| Resultado nos dezesseis | Quantidade | Decisão |
| --- | ---: | --- |
| Português detectado | 9 | Revisão assistida das transcrições e do contexto; oito incluídos, um fora do setor operacional |
| Inglês detectado com evidência suficiente | 1 | Excluído do recorte pt-BR |
| Evidência insuficiente para confirmar português | 6 | Excluídos deste piloto, sem inventar confirmação |

`pt` detectado não certifica dialeto brasileiro. A atribuição pt-BR dos oito novos
incluídos é uma decisão assistida da IA, usando transcrição/contexto e declaração
da API como apoio quando disponível; não são oito novas escutas humanas. Duas
falas de moda são curtas e têm erros lexicais de ASR. Nos dois casos sem declaração
de idioma, a decisão foi registrada individualmente: contexto de comércio brasileiro
com preços em reais, e narração de combinações de roupas interpretada como uso
brasileiro. Não se afirma certificação dialetal independente ou transcrição exata.
Esses limites acompanham o piloto; a transcrição não entra no B0.

As quatro confirmações humanas anteriores de idioma/setor foram preservadas.
A quarta revisão continua parcial quanto à apresentação visual: propriedades
medidas agora confirmam verticalidade/duração e a descrição humana identifica
roupa. O formato de apresentação não é exigido para B0 e permanece desconhecido;
não foi preenchido como se tivesse sido observado.

Os dois casos de inclusão foram resolvidos com a regra de conteúdo anunciada
antes da execução, sem usar views:

- **Organizador de cosméticos (13): excluído.** Fala e imagem demonstram o
  organizador, um acessório de armazenamento; cosméticos ao redor não transformam
  o produto anunciado em cosmético ou aplicação.
- **Anúncio contextual de base (17): excluído.** As amostras visuais não identificam
  produto/aplicação e não houve fala reconhecível que sustentasse essa identidade.
  Descrição da página, sozinha, é insuficiente. A indicação de conteúdo gerado por
  IA não foi usada como motivo de exclusão.

Não há mais decisão de inclusão pendente **nesta coorte operacional do piloto**.
A auditoria humana adicional previamente amostrada não foi realizada. Os quatro
controles humanos conhecidos são de desenvolvimento, não uma amostra independente
para estimar qualidade da IA. Não apresentar a coorte como integralmente revisada
por humanos ou cientificamente validada.

## Integridade, observação e partições

As vinte datas/contagens originais foram preservadas. Nenhum alvo foi substituído
pela consulta mais recente, e o horizonte não foi alterado após observar resultados.
O alvo é a contagem pública acumulada observada com `30 <= idade < 37 dias`;
não são views exatas no dia 30 ou retorno de patrocínio.

Foram conferidos **72 arquivos de evidência**: quarenta de aquisição/propriedades
anteriores e 32 de execução/ASR novos, além das referências de revisão humana.
As novas aquisições têm hashes diferentes das anteriores; não se declarou igualdade
de bytes. ID, URL e publicação correspondem à fonte congelada, e a diferença entre
duração de áudio nova e vídeo anterior é inferior a 0,15 s nos dezesseis.
Isso registra consistência operacional, sem provar ausência de edição.
Não há hash exato repetido nas doze referências incluídas; republicações editadas
ou recodificadas não foram automaticamente detectadas.

| Partição congelada | Moda | Beleza | Referências/canais |
| --- | ---: | ---: | ---: |
| Treino | 4 | 3 | 7 |
| Validação | 2 | 1 | 3 |
| Teste | 1 | 1 | 2 |

Seed 42 e algoritmo por canal/duplicatas já existente. Metadados da coorte e
partições foram persistidos **antes** de publicar os sete rótulos de treino e
ajustar B0/Bcanal. O carregador recompõe as estatísticas somente desses rótulos,
vinculados por hash às identidades/datas originais. Não foram calculadas métricas
de validação/teste nem consultados esses resultados para escolher o baseline.
Como os vinte já eram candidatos de desenvolvimento, chamar uma partição de
`test` não a transforma em teste científico intocado; os três pilotos iniciais
também foram escolhidos por alto alcance.

Os dados privados estão em `data/private/issue-1-curadoria-final-20261018-v3/`:
decisões dos vinte, relatório agregado, bundle congelado e demonstração Python/MCP.
As duas tentativas anteriores interrompidas foram preservadas, sem promover uma
coorte parcial. A primeira parou ao exigir igualdade dos hashes de duas aquisições;
a segunda parou na ausência de idioma declarado em metadados. A consolidação final
registra essas limitações e a base concreta de cada decisão assistida.
Áudios, vídeos, frames temporários, métricas individuais e transcrições não entram
no Git. Ao concluir aquisição e demo: **zero sessões de mídia restantes**, e os
arquivos finais privados têm permissões restritas.

## Autorização e limite da liberação

A instrução expressa do aluno autoriza esta execução operacional e o baseline
do piloto. Ela não foi registrada como aprovação da plataforma ou adesão ao
aditivo: `platform_approval_verified=false`, `metrics_amendment_submitted=false`.
Não houve envio do formulário ou aceite em nome do aluno. Isso é uma limitação
documentada da fonte, não um novo pedido de permissão para o mesmo lote.

A nova elegibilidade é **somente `baseline_pilot_eligible`**. O campo anterior
`training_eligible=false` e a fila histórica bloqueada foram preservados, sem
promover autorização ou validação científica por sucesso do downloader.
Há baseline observado utilizável para demonstrar a #2, mas continuam pendentes
a escala elegível, auditoria humana adicional, avaliação supervisionada,
calibração e explicador NIM. A #1 original permanece aberta por seus critérios
compostos restantes. A integração e o contrato da #2 estão em
[issue-2-baseline-observado.md](issue-2-baseline-observado.md).

Verificação desta unidade: onze testes de triagem/ASR, incluindo ausência de idioma
forçado e de alegação de escuta humana; inspeção dos dezesseis resultados reais,
das exclusões e das evidências privadas. A suíte integrada e a demo são registradas
na documentação da integração.
