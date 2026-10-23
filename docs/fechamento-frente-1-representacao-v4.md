# Frente 1 — candidata única de escala visual, preparação v4, revisão 2

**Estado: pacote preparado, sem autorização, slot, reserva ou execução nova.**
Base `a9bdc17b3863b191f0967d9ceda51962c23dd38a`, posterior à integração da
[v3](fechamento-frente-1-ensaio-v3-resultados.md). Clone independente
`/tmp/galaxies-frente-1-representation-v4`, branch
`codex/frente-1-representation-v4`. Principal preservada; somente o Chat3 integra.

O coordenador conferiu a instrução humana de preparação e recomendou um único
painel finito. Parecer persistente:
`data/private/fechamento-20261023/frente-1/next-representation-review-chat3.md`.
Isso permite preparar/revisar; não cria autorização humana ou slot.

A revisão inicial encontrou um P2 nos contadores: um receipt contraditório
com `accepted=true` e falha técnica/limpeza incerta podia incrementar acertos,
embora o painel permanecesse reprovado. A revisão2 conta somente outcomes
`accepted_development_case`, com quatro regressões (técnica/limpeza × classe
positiva/negativa). Operador/helper/plano/proposta têm identidades novas.
O namespace inicial `representation-product-panel-v4` e seus recibos continuam
intactos, sem autoridade ou execução; seu plano `0822cf2d…` não está aprovado
para o pedido. A autorização solicitada será vinculada somente ao plano e
namespace **r2** identificados abaixo.

## Hipótese e evidência contrária

A v3 completou encoder/decoder, JSON e limpeza, em 17,48 s, mas respondeu
`unknown` ao produto positivo conhecido com 240 tokens observados. Retirar a
cláusula textual não demonstrou reparo. O contraste textual terminou e não será
repetido. A candidata v4 testa **outra escala interna no mesmo contrato
estruturado de produto**, sem nova redação ou ordem de campos.

Hipótese operacional: o mesmo produto/state_first pode discriminar o painel
revelado com min/max visual 1024, previstos 1056 tokens efetivos, onde a
sentinela v3 a 240 tokens absteve. O aviso de grounding capturado é um indício
para investigar escala, sem garantir melhoria nesta classificação. A v3 é
referência histórica, sem braço 225 novo ou comparação contemporânea pareada.
Não se atribuirá causalidade exclusivamente ao orçamento visual.

Evidência contrária permanece explícita: o [negativo espacial](issue-4-vlm-espacial-negativo-60-resultados.md)
respondeu errado com 1056 tokens em 50,6565 s; o
[contraste nativo v2](issue-4-vlm-contraste-nativo-v2-resultados.md) teve falso
positivo com 1075 tokens em 53,1219 s e outra célula expirou. O
[contraste posterior](issue-4-vlm-contraste-nativo-v3-resultados.md) também
expirou aos 75 s úteis. Eram perguntas relacionais diferentes deste contrato.
Esses resultados impedem tratar maior densidade como reparo ou desempenho
garantido. Não aumentar timeout para compensar eventual falha.

O [contraste de ordens](issue-4-vlm-pos-v16-pares-positivos-resultados.md)
também não aprovou uma restauração: item_first teve 4/5 positivos suportados,
mas 0/12 negativos no contexto anterior; state_first, 0/5 e 11/12. Não há nova
varredura de prompt, ordem, modelo, quantização ou densidades intermediárias.

## Única mudança científica e geometria

Trocar somente `--image-min-tokens` e `--image-max-tokens`, ambos de 225 para
1024. Preservar pixels, prompt antigo, schema ordenado state_first, projeção,
Qwen3VL Q4_K_M, projector Q8_0, llama b11716, contexto3072, saída64, seed42,
temperatura0, CPU4, batch/ubatch128 e todos os demais argumentos científicos.
Os caminhos de input/schema são próprios da nova rodada, sem alterar conteúdo.

| Identidade | SHA-256 |
| --- | --- |
| Prompt, igual à v3 | `afaf965f12fd76b2426b4e6d2ef6e82a795a1c34d4d2bd83035ace7a8a5f0b12` |
| Schema ordenado, igual à v3 | `47bf27350b557bb6223b1213654d3a1f21b7099c159408dd8960b0ecd387baef` |
| Operador privado v4 | `d9236911fa9d286269e22a6f9f53779679f23ffaf78f72b8c2d5468cc2c67dd7` |
| Contrato/receitas privado v4 | `5581398c63d5f4b18d6bd9a14b32ac4d2a6763c3649e8aed363c83560a1dadb0` |
| Plano lógico | `cb8e754ab5c1c1ab8afa37cdb9f7566f2b8fe0fe6ad2a3aee6989865ee9c93f7` |
| Bytes de `plan.json` | `197547cd8d713c652b2f7d236133bf59a8fcc27f52e7fa25a6fe2150c90011e2` |
| Proposta lógica | `4799d89c20300539239fa60ca52ebf2120e9f07ba55a203e8a39cb76ef85f3f3` |
| Manifesto dos 17 casos | `7dee0cd779bfecd4ab2820b262fa46bd598028e689a277be573e44374ce71ffd` |

Todas as entradas são PNG RGB320×330. A prova escalar existente da fonte fixada
prevê canvas1024×1056, grade32×33 e **1056 tokens**, distintos dos 1024
solicitados. Fonte/recibo/binário aritmético foram conferidos por hash, sem
reexecução do helper, compilador ou modelo. Recibo de geometria SHA-256:
`2dbf08acf646d6575a3bbf1518af81f6d2233c20ff334c8184e83df51a21c0cc`.

Com 225, o canvas anterior já era 480×512, maior que o crop original. A nova
escala não acrescenta amostras de origem nem recupera detalhe perdido. Tokens
previstos não serão preenchidos como observados: exigir encoder/decoder
completos e **1056 efetivamente observados em cada chamada**. Divergência encerra
sem ajustar flags ou repetir. Exposição de pixels não prova atenção/percepção.

## Painel e critérios congelados

Ordem: sentinela positiva da v3 → os mesmos 12 negativos na ordem histórica →
os quatro positivos restantes na ordem histórica. A sentinela é contada uma
única vez entre os cinco; não é repetida no final. Os cinco crops provêm de três
vídeos de moda de treino já revelados; três crops são correlacionados de um
mesmo vídeo. Os negativos são controles sintéticos antigos, não vídeos reais
de beleza. Não se produz estimativa geral de qualidade ou de diversidade.

Reutilizar exatamente rótulos, tempos ≤3 s, hashes e mapa admissível de cada
crop. Cabides permitem as alternativas físicas originais; o vestido mantém
suas alternativas próprias de tecido puxado ou recorte gráfico. Não emprestar
relação da mão de um item para outro, generalizar o gabarito da sentinela ou
acrescentar alternativas após a resposta.

Critério conjunto de desenvolvimento: **5/5 true com categoria/configuração
suportadas por cada mapa congelado e 12/12 false**. Booleano certo com testemunha
errada reprova. `unknown` não é ausência nem acerto. Parar no primeiro erro,
abstenção, JSON inválido, falha técnica, divergência ou limpeza incerta. Sem
substituição, reparo, retry, continuação dos casos restantes ou retuning.

Se 17/17 passarem, registrar somente candidatura ao próximo desenvolvimento.
Se houver erro/abstenção, encerrar este contraste sem promover/repetir. Falha
técnica ou falta de prazo registra prefixo incompleto; os casos não executados
não recebem rótulo de erro. Publicar denominadores efetivamente observados.

A [rubrica original](issue-4-front1-blind-audit-rubric-v1.md) permanece:
por coluna/setor, pelo menos12/16 conhecidos, ≥90% de valor+frames, zero suporte
inválido; booleanos também exigem diversidade de classes e os mínimos previstos.
Seleção/anotação independente, exclusões de casos/canais revelados e o contrato
obrigatório de 5–8 atributos não são substituídos por este painel. Mesmo17/17
não libera auditoria32, QualityRelease,269sidecars, B/C, serviço ou holdout.

## Implementação, orçamento e parada

`scripts/front1_representation_v4.py` define receitas/critério do painel;
`scripts/front1_representation_operator_v4.py` controla a execução finita.
As cópias privadas do operador e helper são fontes do plano. Não dependem do
clone temporário para executar. Não modificar v3 ou seus terminais.

O worker retorna rc0 após captura técnica completa, inclusive quando a percepção
é rejeitada. O controlador verifica o receipt vinculado e encerra com rc2/status
perceptivo nesses casos. Falha do proprietário ou limpeza incerta continua
técnica, conservando pending quando falta confirmação de ambos os níveis.
Esse tratamento separa os retornos sem reescrever o histórico v3.

- Um preflight sem modelo, até8s; até17 inferências sequenciais condicionais.
- **R$0**, zero rede/download/aquisição/instalação; sem fallback ou retry.
- CPU4; RSS agregado cooperativo até3,3GiB; MemAvailable≥6GiB e disco≥1GiB
  antes de cada dispatch. Slot real será coordenado somente após aprovação.
- **1500s globais desde a primeira reserva de preflight**, incluindo intervalo
  entre comandos, verificação, persistência e fechamento. Cada chamada mantém
  75s úteis +5s de limpeza. Se restarem menos de80s, encerrar sem outro filho.
- 17×80+8 deixa132s para o restante. Não se promete completar os17. Os limites
  são cooperativos e não garantem prazo físico rígido diante de fsync/kernel.
- Stdout nativo≤16KiB, stderr≤256KiB; scratch≤128MiB. Stdout bruto e eventos
  limitados são retidos; stderr integral continua descartado pelo contrato.
- Autoridade/slot novos devem cobrir pelo menos1500s na reserva externa e são
  limitados pelo menor deadline. Nenhum dos prazos ou saldos v3 é reutilizável.
- Reservas exclusivas e duráveis antes da ferramenta externa, do preflight e
  de cada chamada; deadline único e proprietário/watchdog. Recusa de permissão
  consome a rodada mesmo sem filho; registrar e parar, sem outro modo.

Invólucro externo explicitamente `require_escalated`; bwrap interno preservado:
rede isolada, raiz somente leitura, ambiente limpo, escrita persistente somente
no namespace próprio, `/dev`/`proc` próprios e `/tmp` efêmero. Nenhuma mudança de
kernel/AppArmor. A ferramenta aplica seu parâmetro; o processo interno não o
atesta. O chamador deve usar os objetos fixados e respeitar qualquer recusa.

## Inputs, destinos e comandos do pedido

Diretório persistente novo, sem sobrescrever evidências anteriores:

```text
/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/
  unit-8-representation-v4/revision-2/
  representation-product-panel-v4-r2/
```

O plano contém o manifesto/hash de todos os17 inputs, tempos, mapas de suporte,
fontes e os17 argv efetivos. Renovação solicitada somente para esses17 insumos:
reproduzir os cinco crops das três folhas protegidas e os12 controles antigos
por receita determinística, localmente em scratch após autoridade/admissão.
Conferir hash antes do modelo; remover scratch somente após limpeza confirmada.
Não copiar dados/ambientes/pesos/.env ao clone, baixar mídia ou substituir bytes.

Na preparação, os17 hashes foram reproduzidos somente em memória e nenhuma
imagem nova persistiu. Os quatro assets foram rehashados em streaming, com
fingerprints estáveis; 35 fontes e141 antecessores conferiram. A preparação
usou uma CPU,1,08s e123.520KiB de pico, sem cápsula, modelo ou chamada externa.

Workdir de ambos os comandos: raiz principal. Objetos completos em
`unit-8-representation-v4/revision-2/tool-requests.json` e no plano; ambos
`sandbox_permissions=require_escalated`, yield1000ms/output2000. Digest da
sequência: `a3fd444c8a8022945926c08564c314e97c1cc4e3025a57203587e4952bb615a4`.

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/representation-product-panel-v4-r2/control_worker.py --preflight-only
```

Somente se o preflight passar/limpar e os gates continuarem válidos:

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/representation-product-panel-v4-r2/control_worker.py
```

Antes do primeiro pedido à ferramenta: autorização humana específica com
renovação do manifesto17, revisão independente ligada a seus bytes, slot real,
admissão e `reserve_external_attempt()` durável. A validade de autoridade/slot
será nova, coerente com25min. Esta preparação não cria esses arquivos.

## Verificação e handoff

Os testes usam dados, autoridades e proprietário inventados antes de importar
o owner privado. Cobrem o painel17, parada por classe/abstenção, suporte errado,
prefixo incompleto, orçamento entre chamadas, limpeza incerta, preflight/crash,
falta/expiração/reuso de autoridade e argv que não pode voltar a225. Não são
validação perceptiva nem contagem de casos reais. A execução conjunta com os
operadores/reconciliador anteriores passou em **111 testes, com7skips**, em1,00s;
31 testes são da camada v4. Ruff/formatação e links são conferidos junto ao
commit; revisão e bundle são aditivos no diretório próprio antes do pedido.

Chat2: nenhum atributo/sidecar/preditor novo disponível; A200/payload/serviço
permanecem como estavam. Chat3: somente integrar/publicar após sua revisão;
pedido humano único no chat Frente1. Os aceites obrigatórios continuam abertos.
