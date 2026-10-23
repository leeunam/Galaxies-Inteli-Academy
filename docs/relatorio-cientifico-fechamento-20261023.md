# Relatório científico de checkpoint — 23/10/2026

**Veredito: parcialmente concluído.** Há comparação supervisionada real na
validação e evidência de fidelidade/integracão, mas não há configuração final
com todos os aceites nem avaliação científica dos 31 casos reservados. Não
apresentar este documento como relatório do teste final.

## Pergunta, dados e desenho

O iSee estima views antes da publicação para apoiar a comparação exploratória
de um a cinco criativos de divulgação em moda/beleza. O alvo é
`log1p(views observadas)` com `30 <= idade < 37` dias; não são views
reconstruídas no dia 30. A fonte é YouTube Shorts, com contagens/metadados da
Data API e features locais de mídia. Autorização operacional, licença e
aprovação da plataforma são questões separadas; as duas últimas não estão
comprovadas como liberação pública da base.

Coorte preservada: 300 referências, 166 canais; 203 treino, 66 validação,
31 teste. As partições reservam canais/duplicatas. Resultados, idade posterior,
IDs e estatísticas atuais do canal não são entradas do criativo inédito.
Transformações aprendidas usam somente o treino. A200 é o modelo servido,
ajustado na coorte original de 200 com 124 exemplos de treino; A300 não o
substituiu automaticamente.

O desenho aprovado distingue A→B (ganho de informação no CatBoost) e B→C
(biblioteca, com a mesma representação completa). B0 é a mediana do treino
por setor; Bcanal usa somente suporte de treino e fallback B0 para canal
novo. Falta histórico anterior confiável para alegar ganho relativo ao canal
no momento de publicação.

## Resultados históricos válidos de desenvolvimento

A [comparação cacheada real](issue-4-experimento-c-cache-resultados.md) usou
as mesmas 66 referências/37 canais de validação. B/C-cache têm 905 colunas:
prefixo A388, CLIP512 e cinco atributos/estados técnicos; não usam VLM.

| Medida na validação | A300 | B-cache | C-cache |
| --- | ---: | ---: | ---: |
| MAE log médio por canal | 1,7761 | 1,6584 | 1,5444 |
| MAE views micro | 8.249,9097 | 8.007,8255 | 7.873,5181 |
| Cobertura micro | 0,7121 | 0,7576 | 0,7576 |
| Cobertura média por canal | 0,7342 | 0,7680 | 0,7905 |
| Pares corretos, média por canal | 0,4533 | 0,6417 | 0,6683 |
| Spearman, média dos canais estimáveis | −0,0192 | 0,2070 | 0,3292 |
| Pinball q10, média por canal | 0,4631 | 0,4610 | 0,4659 |
| Pinball q50, média por canal | 0,8881 | 0,8292 | 0,7722 |
| Pinball q90, média por canal | 0,4083 | 0,4120 | 0,3420 |

São métricas de validação usada para selecionar hiperparâmetros, sem
estimativa independente de qualidade. O controle A200 tem MAE log por canal
1,7349 nesses mesmos casos. C-cache melhora o agregado, mas q10 piora frente
a B-cache e a cobertura de beleza cai de 0,7000 para 0,6750. Os cinco casos
de alto alcance continuam subestimados; três estão acima da faixa superior
de C-cache. Não há garantia de cobertura nominal de 80% ou de retorno pago.
Consultar o relatório vinculado para os recortes e limites completos, sem
somar métricas de grupos como se fossem uma decomposição da macro global.

O resultado favorável de C-cache não aprova a representação completa nem
promove um modelo. A regra final exige B/C completos elegíveis, menor MAE log
por canal sem piora na média das três perdas quantílicas e desempate para
CatBoost. A escolha pertence à validação; o teste não escolhe ou retoca modelos.

## Experimento visual v4-r2: resultado negativo delimitado

O [protocolo e resultado](fechamento-frente-1-representacao-v4-resultados.md)
compararam uma escala visual maior mantendo pixels, prompt, schema, pesos,
seed e demais parâmetros no contrato revisado. O painel foi autorizado para
até 17 chamadas, com STOP no primeiro erro/abstenção.

Após preflight válido, a única chamada observou 1.056 tokens visuais, encoder
e decoder completos e 60,305 s nativos. No positivo sentinela já revelado,
respondeu `unknown`. O proprietário terminou rc0, com limpeza e pico agregado
de 3.188.543.488 bytes; rc2 do controlador representa o STOP perceptivo.
Uma chamada reservada/concluída, zero aceita; 16 não executadas. Não existe
taxa estimável de negativos, de generalização por setor ou de auditoria cega.

Na mesma sentinela, v3 teve `unknown` com 240 tokens/17,484 s. A escala maior
não reparou esse caso; duas chamadas históricas únicas não identificam um
efeito causal geral. R$0, sem retry, nova aquisição ou fallback. A fila foi
liberada após conferência independente. Nenhum atributo, QualityRelease,
sidecar de produção ou B/C completo foi liberado.

## Explicação e percurso

O [par histórico v6](issue-5-paridade-independente-resultados.md) demonstrou
igualdade integral Python/MCP com A200 e três mídias reais. A execução
cacheada de 23/10 calculou três previsões, SHAP nativo, comparáveis só do
treino e texto local, em 0,310 s; não extraiu mídia, executou grafo/MCP ou
chamou NIM. São evidências diferentes, que não devem ser somadas como um
ensaio integral novo da futura configuração completa.

A [revisão NIM](issue-5-nim-quality-review-v1.md) usa uma chamada real sobre
fatos inventados: 12 claims fiéis, mas cobertura comparativa parcial e
aderência não avaliada. Seleção de IDs com renderer local é a arquitetura
aceita; prosa livre da NVIDIA não foi adicionada como requisito. Fidelidade
matemática de SHAP não substitui avaliação do texto ou do briefing real.

## Avaliação final e temporal ainda não executadas

O [procedimento P6](issue-6-protocolo-final-e-checklist-v1.md) continua
bloqueado. Foram preparados e revisados um
[motor de métricas](issue-6-motor-metricas-v1.md) e um
[planejador temporal](issue-6-diagnostico-temporal-v1.md). Trinta e um testes
de código passaram no checkout integrado, sem abrir dados científicos.
Esse número não é uma avaliação de 31 vídeos. O preflight do inventário
público retorna os 20 bloqueios esperados, código 2, sem autoridade de acesso.

Faltam aceites de qualidade visual e de explicação/integracão, B/C completos,
seleção na validação, congelamento das identidades, carregadores científicos
restritos, limites/reserva revisados e autorização específica de abertura.
A avaliação final deve comparar B0/Bcanal/A300/B/C no mesmo conjunto e
reportar erro, ranking, quantis, cobertura/largura, suporte por setor/canal,
falhas e maiores erros, sem seleção posterior.

O diagnóstico temporal ainda exige **ajustar no anterior e avaliar no
posterior**. Não foram escolhidas datas reais de corte, ajustados modelos ou
calculadas métricas temporais nesta preparação. O plano conserva suporte,
duplicatas, sobreposição de canais e idade; não altera as partições originais.
Em snapshot único, publicação e exposição estão confundidas. Nem um quadro
de datas, nem o futuro resultado retrospectivo provariam validade prospectiva.

As obrigações, responsáveis, evidências e condições de aceite estão na
[matriz detalhada](fechamento-requisitos-e-evidencias.md). A ausência desses
resultados permanece explícita, sem reduzir o escopo ou substituir
observações por dados sintéticos.
