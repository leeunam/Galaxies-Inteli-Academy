# Pós-v12 — contradição entre ausência e incidentalidade

Investigação de 20/10/2026, limitada a controles e casos de treino já revelados.
**O schema de geração permitia a combinação que o decoder recusou.** Isso
explica como `no_target`/`incidental` pôde chegar à validação, mas não identifica
por que o modelo escolheu essa combinação naquela imagem. A causa interna da
escolha continua desconhecida.

Recomendação: uma **v13-R com os mesmos prompt e decoder de R, restringindo a
geração a ramos completos compatíveis**. Corrigir o contrato de geração antes
de outra tentativa perceptiva. Esta investigação não implementa extrator ou
fila, não retoma a v12 e não executa inferência, aquisição, treino ou auditoria.
O [resultado parcial v12](issue-4-vlm-v12-resultados.md) permanece selado.

## O que a reconstrução demonstra

A única resposta nativa da v12 foi preservada antes da rejeição:

```json
{"state":"no_target","presented_categories":[],"presentation_cue":"incidental"}
```

O replay confirmou seu hash, vínculo à especificação R e PNG/tempo congelados.
O validador JSON Schema instalado aceita esse objeto com o schema v11/v12.
O decoder herdado recusa exatamente `v11_contradictory_state_or_cue`.
Não há resultado aceito ou agregado; a inconsistência não nasceu no mapper,
nos índices, na janela ≤3 s ou de conversão de string em booleano.

O schema exige os três campos, enums individuais, até quatro categorias e
ausência de campos extras. **Não vincula o enum de pista ao estado**, nem exige
categorias não vazias só no ramo apresentado ou sua unicidade. Portanto permite
as sete pistas com `no_target`. As relações adicionais ficam no prompt e no
decoder; a geração não está obrigada a satisfazê-las pelo schema atual.
Isso é uma diferença entre os contratos, sem demonstrar falha do runtime.

R contém literalmente a associação `no_target with cue absent` no primeiro
bloco de definição. O bloco seguinte associa `incidental_only` a `incidental`.
O contrato final também manda combinar pista e estado. O prompt está correto
em relação à regra pretendida; não houve troca acidental de seus rótulos.
R apenas reordena a prosa aprovada; E/RE mantêm o mesmo schema, mas não rodaram.

O adaptador fornece o schema por `--json-schema-file`, o prompt R e um único
PNG RGB320×330, em processo novo. Sua saída é preservada inteira; não há
busca por fragmento favorável, reparo de campos ou conversa entre controles
nesse caminho. A resposta é completa, sem evidência de truncamento, erro de
runtime ou troca de imagem/pesos. O limite continuava 64 tokens.

No mesmo controle `text-14-0-8`, a v11 em cache retornou garment/`held_display`,
formalmente válido e perceptivamente falso. No controle preto, ela retornou
`no_target`/vazio/`absent`, provando que schema e decoder anteriores admitem
ausência coerente. Esses dois resultados foram reconferidos com pixels/tempos
idênticos. O estado negativo isolado de R não conta como recuperação: o objeto
completo foi rejeitado. Não há comparação de acurácia R/v11 nesta rodada.

## Hipóteses e limites

| Explicação | Evidência e conclusão |
| --- | --- |
| Combinação incompatível permitida durante a geração | Confirmada pelo schema e por validação offline do próprio raw. O decoder funcionou como previsto ao rejeitá-la. |
| Confusão entre os dois ramos negativos próximos na prosa | Compatível com o raw e a posição dos blocos; hipótese, sem atribuição causal. |
| Reordenação de R resolveu presença, mas prejudicou apenas a pista | Não demonstrado por uma saída inválida; E/RE não foram executadas e não há matriz completa. |
| Parser, agregação ou janela temporal criaram o erro | Refutada pelo raw contraditório preservado antes dessas etapas. |
| Atenção visual, quantização, capacidade ou token específico causaram a escolha | Não medido. Sem logits/traço interno ou contraste controlado suficiente para isolar essas causas. |

Os enums separados permitem combinações cruzadas; isso não significa que as
decisões do modelo sejam estatisticamente independentes. Uma pista coerente
também continua sendo declaração do mesmo modelo, sem certificação visual.

## Alternativas e correção recomendada

| Alternativa | Benefício | Limite / decisão |
| --- | --- | --- |
| Executar E/RE em outra fila ou acrescentar mais lembretes | Pode testar efeito dos exemplos no respeito às associações | Mantém as combinações inválidas disponíveis; não é a próxima correção recomendada. Não reabrir o saldo v12. |
| **R com schema de ramos fechados** | Restringe a geração às combinações já aceitas pelo decoder, mantendo prompt, saída pública e regras visuais | Recomendada. Muda o mecanismo de geração; não garante percepção correta. |
| Retirar a pista dos ramos negativos e derivá-la por código | Elimina essa redundância na saída nativa | Muda o contrato e a proveniência da pista; adiar. Derivação não deve ser apresentada como declaração observada do modelo. |

O rascunho privado mantém integralmente o prompt R aprovado e os três campos,
na mesma ordem. Propõe um `oneOf` raiz, sem `properties` irmãos, com sete objetos
fechados. Cada ramo exige todas as chaves e proíbe adicionais:

| Ramo | Estado constante | Categorias permitidas | Pista constante |
| --- | --- | --- | --- |
| 1 | `no_target` | Somente `[]` | `absent` |
| 2 | `incidental_only` | Somente `[]` | `incidental` |
| 3 | `presented_target` | Enum das 64 listas não vazias e sem repetição | `held_display` |
| 4 | `presented_target` | Mesmo enum de 64 listas | `isolated_display` |
| 5 | `presented_target` | Mesmo enum de 64 listas | `visible_use` |
| 6 | `presented_target` | Enum das 49 listas que incluem garment | `worn_detail_focus` |
| 7 | `uncertain` | Somente `[]` | `uncertain` |

As listas são todas as permutações de uma a quatro categorias atuais, sem
repetição; não apenas as 15 combinações em ordem canônica. Isso preserva as
ordens que o decoder aceita. A lista de garment inclui 1 singleton, 6 pares,
18 triplas e 24 quádruplas. `const`/`enum` excluem duplicatas e categorias
inválidas sem depender de `uniqueItems`, `contains` ou condicionais.

A documentação do runtime b11716 informa suporte parcial a JSON Schema e
limitações nessas palavras-chave; também recomenda conferir a gramática
emitida. Por isso não basta acrescentar `if/then` ou confiar só no validador
Python. [Referência oficial fixada](https://github.com/ggml-org/llama.cpp/blob/b11716/grammars/README.md#json-schemas--gbnf).
O código dessa versão contém conversão de uniões, constantes e enums para
regras gramaticais. Isso sustenta a escolha do formato, sem provar o resultado
da conversão do rascunho no binário instalado. [Conversor b11716](https://github.com/ggml-org/llama.cpp/blob/b11716/common/json-schema-to-grammar.cpp).

O decoder estrito continua obrigatório e inalterado, inclusive para chaves
duplicadas, tipos, Unicode inválido e contradições. Não converter a resposta
antiga para `absent`, não preencher pistas e não aceitar somente seu estado.
Mapper, unknown, OR, janela ≤3 s, categorias e rubrica visual ficam iguais.

## Verificação offline do rascunho

O schema anterior admite 341 arrays de tamanho 0–4 sobre quatro categorias,
incluindo repetições. Com quatro estados e sete pistas são **9.548 objetos**
de campos completos. Enumeramos esse domínio e comparamos decoder atual com
validação do schema proposto por `jsonschema` 4.26.0, já instalado:

- **244 aceitos por ambos**, 9.304 recusados por ambos, zero divergências;
- 241 positivos possíveis e um objeto para cada um dos três estados restantes;
- raw contraditório de R recusado pelo rascunho;
- 14 sondas adicionais de campos/tipos/categorias/comprimento inválidos recusadas;
- os **12 objetos v11 em cache continuam válidos**, inclusive seus 11 falsos
  positivos. A restrição não remove essas alucinações formalmente coerentes.

Essa equivalência é de objetos JSON nesse domínio, não de todas as strings,
whitespace, probabilidades ou desempenho. Enums de arrays podem produzir
literais compactos na gramática. A conversão/aceitação nativa desse schema
**ainda não foi executada**; não se atribui ao rascunho garantia operacional.
Os três falsos negativos reais da v10 continuam sem avaliação v11/v12. Os
32 intermediários v10 foram apenas reconferidos pela linhagem, sem inventar
pistas que não existiam no seu contrato de dois campos.

## Próxima execução proposta, sem autorização consumida aqui

Uma implementação futura deve usar versão/fila aditivas, com pré-verificação
offline de conversão e gramática **antes de qualquer inferência**: preservar
prompt R, conferir os 244 objetos válidos e negativos/mutações, rejeitar a
contradição de R, manter a ordem dos campos e verificar os limites de saída.
Usar o conversor/validador do runtime fixado, sem carga de modelo ou geração;
se não for possível verificar esse caminho sem instalar/trocar runtime, parar
e registrar a limitação. Não despachar confiando apenas na prova Python.
Congelar fontes, schema, gramática/conversor verificados e painel; commitar
código/testes/protocolo revisados antes das chamadas. Nenhuma instalação ou
novo conversor foi executado nesta investigação.

Depois dessa pré-verificação, propor **um candidato**, sem procurar entre
variantes após resultados:

1. Até **12 chamadas, zero aquisição**, nos mesmos controles. Exigir 12/12
   false. Falha perceptiva encerra ao concluir o bloco; falha operacional,
   JSON/contradição/identidade interrompe imediatamente, sem retry/reparo.
2. Somente se passar, até **32 chamadas, zero aquisição**, nos quatro crops
   das oito folhas antigas. Exigir 8/8 valores+frames do GT imutável. Revisar
   todas as pistas/categorias positivas, inclusive tardias, contra pixels e
   inspeção anterior congelada. Qualquer falta de suporte/ambiguidade impede
   aquisição, mesmo se o OR acertar. Unknown não é recuperação.
3. Só com valores e revisão aprovados, até **48 chamadas/12 reaquisições** dos
   mesmos oito negativos reais e quatro positivos de beleza já fixados no
   painel v10. Reproduzir pixels, propriedades e tempos, sem substituir casos.
   Revisão vinculada das pistas antes do descarte das novas folhas com journal;
   as oito antigas permanecem presentes. Mesmos critérios descritivos do
   [protocolo v12](issue-4-vlm-v12-protocolo.md), sem aliviar classes ou limiares.

Limites novos propostos: **92 chamadas, 12 aquisições e 2.400 s de sessões**.
Partir dos cumulativos selados **1.723 / 256 / 35.577,11798522601 s**; tetos
novos **1.815 / 268 / 37.977,11798522601 s**. Não reutilizar as 115 chamadas
encerradas da v12. Manter 180 s por operação, RSS 3,3 GiB, um executor, locks,
reserva durável e cobrança conservadora de tentativa incerta, sem reset.

Relatar comparações somente nas interseções existentes: v11 tem 12 controles
e zero vídeos, v12 zero resultados aceitos, v10 oito vídeos, não vinte.
O contraste novo muda o schema como conjunto; não prova efeito isolado de
ordem de ramos, exemplos ou palavra. Outra auditoria cega exige candidato e
protocolo próprios, exclusão de casos/canais revelados e suficiência de classes
pré-declarada, mantendo o [gate original](issue-4-vlm-revisao-perceptiva-protocolo.md).
Não liberar coluna, iniciar B/C, promover M1 ou retomar pessoa/texto/ambiente/
formato por este documento.

## Preservação e recibos

Os **952 arquivos protegidos** conferem antes/depois, incluindo a fila v12,
suas verificações, artefatos M1/A200, A300, B-cache e todos os pins herdados.
O plano/configuração e checkpoint selado ficaram iguais. As 12 fixtures foram
regeneradas temporariamente com hashes iguais; as oito folhas antigas seguem
presentes e seus 32 crops/tempos foram reproduzidos em memória, sem alteração,
remoção ou movimento. Guardas do teste dos manifestos 200/300 ativas.

Partições 203/66/31 preservadas, sem abrir features/rótulos/previsões/métricas
do teste. Ambientes raiz/isolado e runtime/pesos conferidos em leitura, sem
instalação. Zero inferências, aquisições, sessões novas de mídia ou workers
restantes. A consulta externa foi somente a documentação/código oficial do
runtime; nenhuma mídia ou dado privado foi enviado. README não rastreado fora
do escopo, sem leitura, edição ou inclusão no commit.

A única mudança versionada é este relatório. A verificação desta unidade é o
replay, a enumeração/sondas, identidade de controles/crops, pins, ambientes,
links e diff, com revisão local. Não houve mudança de produção ou nova suíte;
os 947 testes anteriores não são apresentados como nova execução. Recibos e
rascunhos privados: `data/private/issue-4-vlm-v12-contradicao-diagnostico-v1/`.

- Raw R: `fa6cf84126dff84fd72b07f173b825643adfd0fddf3a017eef9546359e1e1fe8`.
- Prompt R preservado: `84aa472ab6ad3d5d78a55d1a506415b78367bb4ec7f35aa8b3491805b68626bf`.
- Schema proposto: `82eb456219194736a9387a0785fe99aedadbd434e623990efa1fb8fb0e0f4585`.
