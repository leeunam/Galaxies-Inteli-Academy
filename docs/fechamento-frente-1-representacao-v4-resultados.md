# Frente 1 — resultado da escala visual v4, revisão 2

**Veredito: execução técnica válida; gate de desenvolvimento reprovado por
abstenção no positivo sentinela. Qualidade visual não liberada.** A rodada está
encerrada e consumida. Não executar os comandos novamente ou continuar o painel.

O [protocolo congelado](fechamento-frente-1-representacao-v4.md) foi autorizado
pelo humano com renovação pontual dos 17 inputs em 23/10/2026. Houve revisão
independente da origem e do contrato, passagem explícita da coordenação e slot
real. O coordenador anterior emitiu os recibos legados exigidos pelo operador;
o novo Chat3 controla a fila e é o único integrador. Não houve alteração dos
bytes revisados, do painel, do orçamento ou dos gates.

## Observação e denominadores

| Medida | Resultado observado |
| --- | --- |
| Preflight sem modelo | 1; completou em 0,110426344 s; rc0 e limpeza confirmada |
| Chamadas reservadas / concluídas | 1 / 1, na ordem congelada |
| Positivos observados | 1; aceitos 0; abstenções 1 |
| Negativos observados | 0; nenhuma taxa de negativos estimada |
| Casos não executados | 16: 12 negativos e 4 positivos |
| Resposta | `state=uncertain`, `item_configuration=unclear`, `presented_categories=[]`; projeção `unknown` |
| Captura técnica | JSON válido; rc0; encoder e decoder completos; sem falhas ou timeout |
| Tokens visuais | 1.056 observados, iguais à previsão; min/max solicitado 1.024 |
| Tempo nativo | 60,305162526 s, dentro dos 75 s úteis |
| Tempo do proprietário | 60,840436911 s, dentro dos 80 s totais |
| Tempo desde a reserva de preflight | 75,754743338 s, incluindo intervalo entre comandos |
| Pico RSS nativo / agregado do proprietário | 2.800,69921875 MiB / 3.188.543.488 bytes; agregado abaixo de 3,3 GiB |
| Encerramento | ledger selado, `pending=null`, stdout/stderr EOF, limpeza em ambos os níveis, scratch ausente |
| Custo | R$0; rede isolada; sem aquisição, download, instalação, retry ou fallback |

O gate exigia conjuntamente 5/5 positivos com suporte e 12/12 negativos.
A primeira abstenção exige STOP; os 16 casos restantes não recebem rótulos
de erro ou acerto. O painel não passou e não fornece sensibilidade, especificidade
ou qualidade por setor/canal. A sentinela já era revelada e não é auditoria cega.

O worker retornou rc0 por sucesso técnico; o controlador externo retornou rc2
por `perceptual_abstention`. Esse retorno preserva a distinção implementada
antes da rodada. Não houve recusa da ferramenta, falha de isolamento ou timeout.

## O que o contraste permite concluir

A [v3](fechamento-frente-1-ensaio-v3-resultados.md) produziu `unknown` na mesma
sentinela, com 240 tokens e 17,483900587 s nativos. A v4-r2 manteve pixels,
prompt, schema ordenado, pesos, seed e parâmetros científicos, alterando somente
min/max visual de 225 para 1.024. A nova chamada observou 1.056 tokens e também
absteve, em 60,305162526 s. A escala maior não reparou esse caso no contrato
testado e aumentou seu tempo observado. Não se estima efeito geral ou causalidade
exclusiva a partir dessas chamadas históricas únicas.

Encoder/decoder e tokens comprovam a execução da representação prevista;
não comprovam atenção, entendimento ou apoio perceptivo. A captura mantém
`representation_quality_or_attention_proven=false`. O stderr bruto continua
descartado pelo contrato; 19.435 bytes foram observados, com eventos limitados
preservados. O stdout bruto de 95 bytes está preservado e vinculado por SHA-256.

Não há evidência para repetir a mesma célula, afrouxar suporte, ampliar tempo
ou promover o candidato. Uma próxima execução precisará de hipótese distinta,
evidência que a sustente, resultado discriminante, protocolo/orçamento revisados
e nova autorização aplicável. Esta rodada não aprova esse próximo ensaio.

## Evidência persistente e verificação

Raiz privada, preservada fora do Git:

```text
/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/
  representation-product-panel-v4-r2/
  unit-8-representation-v4/revision-2/
```

O primeiro diretório contém plano, autoridade, revisão, slot, reservas,
preflight, dispatch, captura, receipt, proprietário, ledger e terminal. O segundo
preserva a preparação, revisão/errata, admissão reprovada por RAM, admissão
aprovada, recibos das duas ferramentas e `results-verification.json`.
Os arquivos anteriores e a revisão1 não foram sobrescritos.

| Identidade | SHA-256 |
| --- | --- |
| Plano lógico | `cb8e754ab5c1c1ab8afa37cdb9f7566f2b8fe0fe6ad2a3aee6989865ee9c93f7` |
| Autorização humana registrada | `e032723066acae0df5e78f6be15afef4747a2041e3c567618b8f19eb3ccdd531` |
| Revisão independente vinculada | `b462d13b34878ef39a171836d3fc6e9baa8397962c26e1dfd38729d759a2f3cf` |
| Slot real | `fdbb7ce3bb1261de14416358ace589a774b9a62850cc31d640e80920b9ad90f8` |
| Reserva externa | `839263097e7627ec2a42ae54a82475b8045bf3086ddbdc7f330b4b90d91385e0` |
| Captura `result.json` | `1ea30701540c3ec886e9a26ddcf5ddf7122ddfa732253880ad271ab59495f517` |
| Receipt da chamada1 | `ac22dab26386ebb732267a5e77be2f8a196f1eaf1a148c47dcbb881cc84aa725` |
| Terminal | `fa46b8f1f2830e8638fbb46eaff4be82563eec57e63459536031e0ef3feab875` |
| Reconciliação `results-verification.json` | `df3d2700a61dccb7c3ced8752c9c8d3530974f6c8ef083daa0bc85cda620676c` |

A reconciliação em leitura verificou os pins de fontes e antecessores,
autoridade→revisão/reservas, PNG→manifesto/captura, captura→receipt/state,
hash/stdout bruto→resposta, receipt→stdout do proprietário, resultado técnico,
EOF/limpeza e ausência de chamadas adicionais. O helper congelado
`front1_representation_v4.py:panel_outcome` reproduziu `perceptual_abstention`,
zero acertos verificados e 16 não executados. O índice da reconciliação contém
os hashes de todos os 20 arquivos de execução.

`capture_origin=injected_unreleased` e o `proposal_sha256` genérico da captura
pertencem ao contrato público de captura; não são concessões de autoridade ou
QualityRelease. O vínculo específico desta execução é a cadeia do plano,
grant/review/slot, reservas, dispatch e receipt. O inventário de workers da
admissão teve conferência independente do host pelo emissor; o `/proc` confinado
da ferramenta padrão, isoladamente, não comprova ausência global de processos.

## Handoff e aceites ainda abertos

Código e testes do operador/helper: commits `a63dcaf098b15daa77e290148a73cca6d64db7d9`
e `5bf8ef23e5406a8fbd8d99da3ee5c6bbfb2d8612`, na branch
`codex/frente-1-representation-v4`, clone `/tmp/galaxies-frente-1-representation-v4`,
base `a9bdc17b3863b191f0967d9ceda51962c23dd38a`. Antes da execução: 111 testes
passaram, 7 skips, incluindo 31 testes v4 e quatro regressões dos contadores;
o coordenador reproduziu a suíte. Esta entrega acrescenta documentação e
reconciliação dos recibos; não modifica o operador revisado.

Os comandos consumidos estão no protocolo e nos objetos fixados do plano;
servem para auditoria, não para reexecutar. Um novo bundle/índice de resultado
é entregue ao Chat3 para revisão e integração; a Frente1 não integra/publica.
O coordenador controla o encerramento do slot após sua conferência.

Chat2: não há novo atributo, sidecar ou configuração multimodal aprovada.
A200 servido, A300 e B/C-cache históricos permanecem como evidências dos seus
próprios contratos. Não tratar este candidato como handoff final da explicação.

Continuam abertos os atributos obrigatórios do TAPI/proposta, gates de
desenvolvimento e auditoria independente por atributo/setor, QualityRelease,
extração elegível269, B CatBoost/C LightGBM completos e comparação/seleção pela
validação. Nenhum sidecar de produção, artefato completo ou release de features
novo foi criado. O holdout31 permanece fechado, coorte300 e divisão203/66/31
intactas. A Frente1 continua **incompleta**, com causa perceptiva registrada.
