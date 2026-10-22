# P6/P7 — Procedimento da avaliação final e conferência do fluxo

**Procedimento v1, `p6-final-procedure-v1`; execução bloqueada.** Este documento
fixa o procedimento e as definições de métricas antes do acesso ao teste.
Não congela uma solução final inexistente, não concede autorização e não
registra avaliação executada. A versão é vinculada pelo commit deste arquivo;
mudanças posteriores exigem versão explícita e justificativa antes da abertura.

Base de trabalho: `277804223eb6121dbeb541c0663af89ccf334eac`, clone independente.
Escopo original: [P6/P7 no backlog](backlog-proposto.md#p6--congelar-a-solução-e-avaliar-o-teste-reservado).
Estado de referência: [guia da entrega](entrega-20261021.md),
[expansão para 300](issue-3-expansao-300-resultados.md) e
[B-VLM reprovado](issue-4-experimento-b-vlm-resultados.md).

## 1. Dependências que impedem a avaliação agora

| Dependência | Evidência necessária antes da abertura | Estado nesta base |
| --- | --- | --- |
| Dados | Manifestos imutáveis da mesma coorte de 300 e partições 203/66/31, sem canais/duplicatas cruzados | Contagens documentadas; identidades não recopiadas nem auditadas nesta unidade |
| Representação | Contratos/versionamento de extratores, ordem de colunas, ASR compartilhado, PCA e transformações aprendidas somente no treino | Manifesto final completo ainda não fixado |
| Visão | Auditoria perceptiva independente aceita pelos gates originais, com evidências/unknown e revisão das falhas | Não aprovada; timeout resolvido ou JSON válido isoladamente não bastam |
| Modelos | B completo CatBoost e depois C LightGBM com os mesmos atributos completos, linhas e partições de A300 | Ausentes; A300 e B-cache não substituem B/C completos |
| Seleção | Comparação A300/B/C na validação, configuração escolhida e artefatos recarregados, com identidades reais | Ausente; A200 segue servido, sem promoção automática |
| Explicação | Aceite de fidelidade, evidência e aderência qualitativa no fluxo previsto, preservando números/ranking | NIM global aceito em fixture inventada; mídia real e aderência não avaliadas |
| Integração | Recibo pré-teste do fluxo escolhido em dados de desenvolvimento autorizados | Par real v6 de A200 não prova a futura solução multimodal completa |
| Abertura | Revisão independente e autorização específica, vinculadas à configuração e aos destinos/limites | Ausentes; não solicitar enquanto as dependências científicas estiverem pendentes |

O [inventário público de prontidão](evidence/issue-6-final-readiness-v1.json)
mantém `identities` e `gates` vazios. Ausência é bloqueio, não hash fictício,
recibo simulado ou aceite presumido. Um resultado futuro de outra frente deve
ser integrado e revisado antes de atualizar esse inventário.

## 2. Congelamento futuro da configuração, separado deste procedimento

Antes de qualquer leitura de assignments, labels ou features do teste, registrar
na passagem privada, sem copiar esses conteúdos para o Git:

1. Identidades reais de coorte/partições e dos manifestos de desenvolvimento;
   contrato de features do teste, sem materializar a matriz reservada.
2. Modelos B0/Bcanal, A300, B completo e C completo, com arquivos/versões/hashes,
   quantis, ordem de colunas, tratamento de ausências e recarga compatível.
   A200 pode entrar como controle adicional explicitamente congelado;
   não substitui A300 na ablação A/B. B-cache fica como resultado histórico.
3. Relatórios de auditoria visual, comparação B→C, aderência e integração de
   desenvolvimento; registrar quem revisou e a decisão. Hash de relatório
   reprovado não é recibo de aceitação.
4. Configuração selecionada **somente na validação**, com preditor q50,
   política de faixa, SHAP correspondente e índice de comparáveis só do treino.
   Não refazer ajuste na união treino/validação nesta abertura.
5. Identidade do código/locks e allowlist estática dos carregadores, sem aceitar
   módulo/callback ou comando arbitrário do manifesto. Verificar compatibilidade
   antes de importar/carregar o modelo. O preflight desta unidade não implementa
   esse carregamento e não afirma que ele já foi validado.
6. Autorização específica de abertura: operador, objetivo, hashes aprovados,
   diretório privado novo, quantidade, teto de tempo/memória/disco e R$0.
   Sem limites acordados, continuar bloqueado. Não reaproveitar autorizações
   consumidas de demo, VLM, NIM ou prova pública.

Na seleção pela validação, aplicar a regra já fixada na
[proposta técnica, “Métricas e decisão”](proposta-tecnica.md#métricas-e-decisão):
um candidato completo só substitui CatBoost M1 se reduzir o MAE log médio por
canal sem piorar a perda quantílica média dos três quantis. Entre completos
elegíveis, escolher o menor MAE log; empate favorece CatBoost. Sem ganho,
manter M1. Resultados negativos de B/C continuam sendo comparação experimental
válida e devem ser relatados; não justificam ocultação ou seleção pelo teste.

O futuro executor deve recusar antes de abrir qualquer caminho do teste ou
carregar/inferir modelo se faltar um pré-requisito. Deve reservar a execução
de maneira exclusiva/durável antes dos efeitos, registrar início/terminal e
impedir retry após resultado incerto. Esse executor não é entregue aqui.

## 3. Procedimento único após liberação específica

1. Conferir novamente código, identidades e autorizações já revisadas, sem
   consultar o teste para escolher configuração ou exclusões.
2. Registrar a abertura; acessar somente os 31 exemplos da partição congelada,
   pelos carregadores restritos revisados. Não renovar views, metadados ou
   observações; preservar o alvo público observado com `30 <= idade < 37` dias.
3. Avaliar B0/Bcanal, A300, B completo e C completo no **mesmo conjunto**.
   Baselines usam somente estatísticas de treino; Bcanal sem canal conhecido
   usa o fallback já definido. Nenhum fit, early stopping, seleção, calibração
   ou construção de índice de comparáveis usa o teste.
4. Conservar saídas brutas e servidas vinculadas por exemplo/configuração.
   Reportar toda falha e ausência. Não excluir silenciosamente linhas difíceis,
   preencher modalidade sem suporte de treino ou comparar conjuntos distintos.
   Havendo falhas, mostrar denominador total e disponível por modelo; eventual
   interseção pareada é diagnóstico identificado, não avaliação completa de 31.
5. Produzir as métricas abaixo uma vez, com contagens por setor/canal e erros
   individuais privados. Publicar somente projeção sanitizada revisada.
6. Selar recibo/relatório, registrar tempo/memória/cache/limpeza e conclusões
   negativas. Não trocar o vencedor, retunar nem promover modelo pelo teste.
   Qualquer adaptação motivada por ele transforma esse conjunto em revelado;
   nova alegação independente exige outro desenho, não reutilização oculta.

O teto proposto de dados é 31 referências, cinco configurações obrigatórias
(B0, Bcanal, A300, B, C), sem treino; A200 só se incluído antes da abertura.
Quantidade de carregamentos/chamadas e tetos de recursos devem ser derivados
dos artefatos efetivos e propostos à coordenação antes de liberar o executor.
Nenhuma extração, inferência, chamada externa ou abertura é inevitável nesta
unidade de preparação: **zero execuções científicas solicitadas agora, R$0**.

## 4. Métricas fixadas antes do teste

Definir `y = log1p(views_observadas)` e `p = q50_log`; converter previsões por
`expm1`, sem arredondar antes das métricas. Recusar quantis não finitos,
negativos ou fora dos limites físicos do contrato. Usar a política servida:
limite inferior = mínimo dos três quantis brutos, superior = máximo, q50
preservado. Registrar cruzamentos brutos; não ordenar q50 para corrigir a faixa.

| Medida | Definição e suporte |
| --- | --- |
| Principal: MAE log por canal | Média de `abs(y-p)` dentro de cada canal, depois média dos canais com igual peso |
| MAE log por vídeo | Média micro de `abs(y-p)`; informar número de vídeos e canais |
| MAE em views | Média de `abs(views-expm1(p))`, global e por setor/canal |
| MAPE | Média de `abs(views-previsto)/views` apenas onde views > 0; informar exclusões de zeros e suporte; sem epsilon inventado |
| Pinball q10/q50/q90 | Média por canal de `max(q*(y-pq), (q-1)*(y-pq))`, com quantis servidos |
| Cobertura q10–q90 | Fração com `q10 <= y <= q90`, micro e média por canal; faixa nominal de 80% não é garantia de calibração |
| Largura da faixa | Média de `q90-q10` em log e `expm1(q90)-expm1(q10)` em views |
| Spearman intra-canal | Ranks médios nos empates; mínimo de três vídeos e variação no observado e previsto; senão `null` e motivo |
| Acerto de pares intra-canal | Excluir empates no alvo; previsão empatada recebe 0,5; sem pares, `null`; informar pares e canais com suporte |
| Ranking agregado | Média apenas dos canais estimáveis, com contagem explícita; Spearman global é secundário e não demonstra ordenação dentro de canal |

Repetir as medidas por setor e por canal sem confundir suas médias com uma
decomposição aditiva da macro global. B0/Bcanal têm faixas descritivas do treino,
rotuladas separadamente dos quantis preditivos. Mostrar diferenças pareadas
A300→B (informação multimodal) e B→C (biblioteca), sem interpretar A→C como
isolamento das duas causas. A200 é controle histórico adicional, se congelado.

A descrição temporal usa datas UTC preservadas: intervalo de publicação e
observação por partição, suporte por mês de publicação e faixas fixas de idade
`[30,32)`, `[32,34)`, `[34,37)`. Células vazias/sem suporte ficam explícitas.
Ela é retrospectiva: idade e data de publicação podem estar confundidas;
não reconstrói views no dia 30 nem constitui backtest prospectivo.

Essa descrição **não cumpre integralmente o diagnóstico temporal por corte**
previsto na [proposta técnica, seção 3](proposta-tecnica.md#3-alvo-e-avaliação):
ajustar modelos no lado anterior da data de publicação e avaliar no posterior,
declarando sobreposição de canais ou separação conjunta quando houver suporte.
Esse diagnóstico permanece pendente de protocolo/execução próprios; nenhuma
data de corte ou resultado foi inventado e nenhum treino foi liberado aqui.
Mesmo executado, o snapshot único não isolaria deriva temporal nem atenderia
à avaliação prospectiva estrita sem dados históricos adequados.

Listar privadamente os cinco maiores erros absolutos em log e os cinco em
views, desempatados pelo identificador congelado, com falhas e setores/canais.
São exemplos escolhidos pelo erro para diagnóstico, não nova amostra de
validação perceptiva. Não criar limiar de viralidade ou alegação de retorno pago.

As fórmulas existentes de [métricas de desenvolvimento](../scripts/experiment_a_metrics.py)
orientam a compatibilidade, mas `evaluate_development` não vira avaliador do
teste por este documento. MAE views por canal e diagnóstico temporal exigem
verificação do futuro executor; não se declara implementação só por especificar.

## 5. Checklist do fluxo completo e evidência já disponível

- [ ] Fixar artefatos/contratos e aceites científicos dos itens 1–2; abrir o
  teste somente depois de autorização própria. P6 continua bloqueada agora.
- [ ] Conferir limites contratuais de um a cinco candidatos, individual com um,
  comparação com dois a cinco, mesma campanha/setor e IDs/ordem preservados.
- [ ] No fluxo selecionado, conferir extração versionada → features elegíveis →
  quantis/ranking → SHAP na escala correta → comparáveis apenas do treino →
  explicação validada → resposta Python/MCP, sem alteração dos números.
- [ ] Conferir evidência por afirmação, português, abstenção/ausências e
  interpretação qualitativa do brief. Aderência ao objetivo é distinta de
  previsão de views; não inventar semântica de embeddings nem causalidade.
- [ ] Conferir timeout/falha de modalidade/provedor sem fallback não autorizado,
  ausência de segredos/corpos privados nos logs e recolhimento dos processos.
- [ ] Vincular os recibos novos necessários à configuração final. Evidência
  histórica que já cobre um contrato inalterado deve ser citada, sem repetir
  execução apenas para preencher checklist.
- [ ] Consolidar relatório de P6, limitações, instruções e passagem privada;
  revisar pacote público e destino de entrega. Não tocar no README alheio.
- [ ] Aceite humano e eventual publicação/encerramento de issues são passos
  separados. Este protocolo não os executa nem declara projeto 100% concluído.

Evidências preservadas, sem reexecução nesta unidade:

| Evidência | O que cobre e seu limite |
| --- | --- |
| [Guia atual](entrega-20261021.md) e [par independente v6](issue-5-paridade-independente-resultados.md) | Python/MCP integrais iguais com A200, três peças reais; sem provedor e sem comprovar a solução multimodal futura |
| [Reprodução offline](issue-7-reproducao-offline.md) e prova pública única no guia | Locks/ambientes/protocolo com fixture inventada; prova consumida, não repetir |
| [NIM global](issue-5-nim-global-diagnostic-v1-resultados.md) | Seleção/renderização reais aceitas com dados inventados; não valida aderência/mídia real |
| [Ferramentas da expansão](issue-3-expansao-300-ferramentas.md) | Publicação/guardas existentes de desenvolvimento; não é autorização de abertura do teste |
| [Testes existentes de dados](../tests/test_experiment_a_data.py) e [métricas](../tests/test_experiment_a_training.py) | Fonte das verificações de fronteira/quantis/zeros/empates; citados, sem nova execução ou treino |

Não consultar o canônico para esta checklist; cache histórico, par independente
real e fixture pública conservam suas origens distintas. Vídeos, PNGs, recibos,
retenções e autorizações anteriores não foram alterados.

## 6. Preflight de metadados, sem efeito científico

O [verificador mínimo](../scripts/final_evaluation_preflight.py) inspeciona
somente o JSON de declarações fornecido. Não segue hashes/caminhos, não abre
coorte/partições, não importa carregadores e não conhece callbacks de inferência.
Digests com formato válido **não são verificados contra arquivos** por ele.
Mesmo com todos os campos preenchidos, retorna apenas
`metadata_complete_requires_independent_review`, com
`identities_verified=false`, `holdout_access_authorized=false` e
`inference_authorized=false`. Não é sandbox nem substitui a futura guarda do
executor, revisão científica ou autorização específica.

```sh
rtk proxy python3 -B -m scripts.final_evaluation_preflight --metadata docs/evidence/issue-6-final-readiness-v1.json
```

Com o inventário atual, a saída esperada é **bloqueada, código 2**, listando as
identidades/gates ausentes, sem valores privados. Só esse arquivo de metadados
é lido. A validação nova usa `unittest` da biblioteca padrão e dados inventados;
não instala ambiente nem repete suítes, modelo, demo ou smoke público.

Conferência desta unidade: seis testes novos passaram em 0,011 s; o preflight
do inventário público devolveu os 20 bloqueios esperados e código 2. Conferidos
14 links locais, sintaxe e diff; nenhuma abertura de dados científicos,
carregamento/inferência, instalação ou chamada externa. As evidências antigas
da tabela anterior foram consultadas como documentação, sem repetir seus testes.
