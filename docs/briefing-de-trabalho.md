# Briefing de trabalho e aprendizagem

Atualizado em 20/10/2026. Horários de São Paulo.

**Observabilidade local v2 concluída, sem nova chamada externa:** a
[camada aditiva](issue-5-observabilidade-local-v2.md) registra fases/códigos
estáticos depois da autoridade selada, conservando sua aceitação, números e
ranking. Somente uma projeção canônica da fixture pública inventada pode ser
retida; corpo arbitrário, cabeçalhos, exceções e seus hashes são suprimidos.
JSON profundo mantém falha antes de resultado, agora identificada localmente.
Passaram 56 testes direcionados raiz, 81 isolados e cinco CLIs offline,
Ruff/formatação de 153 arquivos e revisão independente. Os 716 hashes,
versões raiz/isoladas e oito PNGs conferem, sem workers restantes. M1/A200,
partições e teste reservado preservados. A ponte de resposta limitada foi
testada em processo raiz com objetos falsos; dispatcher/abertura HTTP reais
continuam ausentes. Nenhuma nova autorização, nonce ou reserva real. A causa
da tentativa histórica abaixo continua desconhecida; C e produto 42–64
não foram executados.

**NIM único concluído: HTTP 200, sem seleção validada, sem retry:** o
[resultado registrado](issue-5-nim-sintetico-unico-resultados.md) confirma uma
chamada exclusivamente sintética em 2,9134 s, 763 bytes e 91 tokens. O envelope passou,
mas `selection_validated=false`; não houve explicação aceita ou aderência
qualitativa avaliada. Corpo bruto e `reason_code` final não persistidos: causa
e estágio não foram identificados, sem atribuir inadequação ao provedor.
Autorização consumida, sem repetir/reparar/trocar alvo.
A suíte completa única no código final `c0ef8ab` passou em **748 testes/575,14 s**;
após o [diagnóstico offline](issue-5-nim-diagnostico-offline.md), passaram 45
isolados e seis CLIs inventados sem rede; o replay Unicode mostra que a falha
pode ocorrer antes do validador. As fontes seladas continuam iguais. Os 695 pins,
selo externo, versões raiz/isoladas e oito PNGs conferem; zero sessões de mídia
ou workers NIM/VLM/explicação no host. M1/A200 e teste reservado intactos.
O [estado de #3–#7](issue-3-a-7-estado-e-caminho-minimo.md) separa integração ainda
pendente e decisões de protocolo. A pergunta sobre C-cache continua sem decisão,
não autoriza mudar #4 e não bloqueou esta execução. README não rastreado intacto.

**Checkpoint anterior — StateGraph isolado implementado, sem NIM nesta unidade:** o
[projeto independente](issue-5-stategraph-isolado.md) instalou LangGraph 1.2.16
pelo PyPI, com lock e `.venv` próprios. O grafo e subgrafo compilados executam
análise por stdio no Python raiz e validação local de seleção fechada. Passaram
10 testes isolados e 33 direcionados na raiz (oito novos), Ruff/formatação de
137 arquivos. As 648 proteções, versões raiz e oito folhas conferem. Não houve
mídia, VLM, chamada NIM ou abertura do teste. SHAP/comparáveis automáticos,
geração livre, aderência e integração final MCP/grafo continuam pendentes.
Naquele checkpoint, a autorização NIM sintética única ainda não havia sido consumida.

**Checkpoint anterior — composição local da #5 verificada:** a
[camada aditiva Python/MCP](issue-5-composicao-aditiva.md) preserva o analisador
e sua ferramenta, acrescentando catálogo/transporte com callbacks locais.
Passaram 25 testes novos/109 direcionados em 61,95 s, Ruff/formatação de 129.
Ela não é StateGraph nem NIM real e ainda não captura features/SHAP/comparáveis
automaticamente. As 641 proteções, filas seladas e oito PNGs permanecem iguais.
O aluno aprovou em 20/10, 13:06 UTC, LangGraph 1.2.16 em projeto/lock/ambiente
próprios de `orchestration/` e uma chamada NIM sintética, sem retry/reparo/fallback,
com 2.048 tokens, 45 s, 16 KiB e gasto R$0, sem dados privados. Nenhuma chamada
ou instalação foi feita nesta unidade; registrar reserva durável antes de operar,
não repetir resultado incerto e parar diante de cobrança/termos novos. O teste
reservado e a recuperação V9 permanecem fechados. A suíte completa do HEAD
final será executada uma vez na validação final apropriada das próximas unidades.

**Adendo limitado da #4 concluído, produto ainda sem liberação:** a
[nova comparação selada](issue-4-vlm-produto-v9-adendo-limitado-resultados.md)
reúne 41/64: v9 acerta produto+frames em 27, contra 29 de v8 e 33 de A/v7.
Os sete novos são positivos de moda; v9 acerta 2/7 contra 7/7 dos dois anteriores.
Seus nove falsos negativos são de moda, com 27 estados precoces `incidental_only`.
O resultado não sustenta outra auditoria cega; nenhuma coluna ou modelo liberado.
A aquisição diagnóstica única do caso 42 encontrou propriedades iguais às
congeladas, mas bytes diferentes dos dois runs anteriores; a causa da divergência
passada permanece desconhecida. Não houve inferência nesse caso. As 28 chamadas
dos sete casos preservados concluíram sem retry, em nova proveniência, mantendo
as duas filas antigas e todas as oito folhas. Cumulativos 256 aquisições,
1.666 reservas e 34.792,3041 s; zero temporários/workers ao terminar. Os 588 pins,
cinco arquivos congelados, ambiente, M1, partições e teste conferem. Passaram 710 testes
completos em 564,53 s; após ajustar o detector para ignorar o próprio wrapper RTK,
passaram 26 direcionados finais em 97,30 s, Ruff/formatação de 125 e revisão
independente. O runtime foi conferido em leitura, sem reinstalação. Fontes no
commit `b44ea1c`; a unidade local da #5 foi concluída antes, em `9458259`.

**Recuperação da #4 interrompida no caso 42:** o [adendo autorizado](issue-4-vlm-produto-v9-recuperacao-protocolo.md)
completou o caso 34 com uma chamada, preservando os três raw e 33 resultados.
A [comparação selada reúne 34/64](issue-4-vlm-produto-v9-recuperacao-resultados.md):
produto acerta 25 valores+frames, contra 22 de v8 e 26 de A/v7. A aquisição do
caso 42 divergiu das propriedades congeladas; os valores atuais não foram
persistidos e a causa exata não foi identificada. Todos os oito downloads
bem-sucedidos também diferem em bytes, apesar de seus pixels/tempos coincidirem.
Sem retry ou inferências após a parada: nove aquisições/uma reserva nova,
cumulativos 255/1.638 e 34.491,6163 s, dentro dos tetos 277/1.758/27 h.
Há oito folhas presentes, hashes conferidos, zero sessões temporárias/workers;
a orientação posterior pediu auditoria em leitura, sem descarte ou alteração
de fila. Continuar exige decisão específica e outro adendo, conforme relatório.
Passaram 667 testes em 422,65 s, Ruff/formatação de 119 arquivos e revisão
independente. Os 542 pins e fontes novos conferem; M1, partições, teste reservado,
serviço/MCP, lock e ambiente permanecem iguais. Nenhum campo VLM foi liberado.

**Produto v9 selado com comparação parcial:** a [interrupção externa no caso 34](issue-4-vlm-produto-v9-resultados.md)
deixou 33 resultados completos e uma reserva sem resposta capturada. Não houve
retry ou declaração de 64 avaliados. A estruturada acertou 12/12 controles e
o piloto passou apenas no mínimo de continuidade (11/16). Nos mesmos 33,
produto acertou 24 valores+frames, contra 21 da v8 e 25 de A/v7; corrigiu quatro
negativos e introduziu quatro falsos negativos. Gates dos grupos de origem não foram
calculados, nenhum campo liberado ou auditoria nova selecionada. As 64 folhas
e cinco temporários foram descartados após revisão, com zero sessões restantes;
184 reservas e recibos originais preservados. O orçamento cobra o intervalo
não medido conservadoramente, sem aumentar os limites. Completar os 31 casos
pendentes exigiu o adendo acima; o relatório parcial descreve o checkpoint
anterior à nova autorização.
Passaram 624 testes, Ruff/formatação de 112 arquivos e revisão independente.
Os 125 pins herdados, quatro fontes congeladas, partições, teste reservado e
M1 permanecem intactos.

**Componentes locais da #5 verificados:** [SHAP q50 nativo](issue-5-shap-m1.md)
reproduziu o bundle M1 em três inputs sintéticos (erro máximo 8,88×10⁻¹⁶), e os
[comparáveis](issue-5-comparaveis-treino.md) abriram somente 248 evidências dos
124 IDs de treino. Passaram 27 testes direcionados e a suíte completa citada.
Serviço/MCP, lock e ambiente não mudaram; StateGraph/NIM/demo continuam pendentes.
Não instalar LangGraph, enviar dados privados ou abrir teste sem a autorização
necessária. A [fronteira local de explicação](issue-5-fronteira-explicacao-local.md)
agora vincula relatório, SHAP e referências, com seleção fechada de evidências;
passaram 22 testes novos e 65 direcionados, sem transporte externo ou grafo.
O [transporte injetável local](issue-5-transporte-local.md) acrescentou prazo
cooperativo e reparo único sobre o catálogo, somente com callbacks falsos.
Passaram 19 testes novos, 686 completos em 429,56 s, Ruff/formatação de 121
arquivos e revisão independente. Os 588 pins, oito folhas e ambiente conferem;
NIM real, grafo, serviço/MCP e aderência qualitativa continuam pendentes.
O [guia local](guia-reproducao-local.md) prepara a reprodução de #7.
A [conferência da #3](issue-3-conclusao-tecnica-local.md) separa os cinco critérios
técnicos implementados de aceite humano e fechamento remoto.

**Checkpoint anterior — diagnóstico do produto v8 e proposta:** a
[investigação nos casos já revelados](issue-4-vlm-produto-diagnostico-e-proxima-correcao.md)
confirmou que os true já estavam nas respostas brutas: 180 true, 12 unknown
e zero false nos 192 frames elegíveis. B/v7 já marcava os 32 antigos como
positivos; seu schema de produto é idêntico ao v8 e permitiu false. O OR e
o filtro ≤3 s estão corretos. A causa exata da tendência de resposta ainda
não foi isolada; a proposta é classificar item apresentado/meramente incidental/
ausente/incerto por frame, com testemunha do mesmo item e mapeamento
determinístico, antes de outra auditoria. Inclui contrastes predefinidos de
instrução/schema nos controles existentes e piloto com positivos/negativos
dos mesmos 64, sem alegar independência ou validar sublabels não anotados.
Não houve implementação, download ou chamada nova. Os 116 hashes de arquivos
e recibos protegidos conferem; partições, teste reservado e M1 preservados.

**VLM v8 concluído nos 64 casos revelados, sem atributos liberados:** a
[comparação pareada](issue-4-vlm-v8-resultados.md) manteve os mesmos pixels,
tempos e anotações de treino. Acertos de valor+frames: pessoa 61→62/64,
produto 54→50/64 e texto 11→57/64 frente a A/v7. Texto ganhou cobertura,
mas manteve três evidências sem suporte; produto respondeu true nos 64 e
piorou. Nenhum campo passou no gate original aplicado aos dois grupos de 32;
pessoa acertou 32/32 nos revelados, mas só há dois negativos nesse grupo.
Foram 804 chamadas novas válidas, zero falhas/repetições, 182 aquisições
cumulativas e 15.159,68 s contabilizados. Revisão independente reproduziu
respostas/métricas/gates. As 64 folhas foram descartadas, sem temporários;
a etapa selada bloqueia novas aquisições/inferências. Passaram 567 testes
completos, 58 direcionados e Ruff/formatação. O [checkpoint de preparação](issue-4-vlm-v8-execucao.md)
registra controles e pareamento; não houve retuning, nova auditoria, resolução
nativa ou treino B-VLM. Os 99 arquivos protegidos, partições 203/66/31,
comparadores, M1, serviço/MCP e teste reservado permanecem intactos.

**Diagnóstico VLM e proposta de correção:** a
[investigação dos erros restantes](issue-4-vlm-diagnostico-e-proxima-correcao.md)
encontrou zero previsões true de texto em 384 respostas por frame (com repetição
dos frames antigos entre A/B) e falhas de pessoa/produto
anteriores à agregação. Em nove controles sintéticos locais, o schema aceitou
true/false/unknown, e a pergunta curta com JSON explícito reconheceu texto
grande e fundo vazio; os prompts antigos falharam no texto grande. Isso motiva
desenvolver primeiro instruções explícitas de presença, sem alegar qualidade
em vídeos reais. Resolução nativa é uma segunda ablação proposta. Não houve
implementação, nova aquisição de mídia real, auditoria ou treino; os 67 arquivos
protegidos e os recibos v7 permanecem iguais, M1 e teste preservados.

**Revisão perceptiva VLM concluída, sem colunas liberadas:** a
[nova auditoria cega](issue-4-vlm-revisao-perceptiva-resultados.md) avaliou o
candidato A congelado em outros 32 casos de treino. Pessoa acertou 31/32, mas
falhou por evidência sem suporte; produto ficou em 13/16 e 14/16; texto teve
somente 7 conhecidos, todos false, com 25 abstenções. O gate original não mudou.
Foram 640 chamadas locais válidas, sem falha/retry; 118 aquisições cumulativas
e 8.226,57 s, dentro dos limites. A etapa foi selada sem treino B-VLM, mantendo
M1, serviço/MCP, comparadores e teste reservado. A revisão independente
reproduziu seleção/gate; as 64 folhas foram descartadas, com zero temporários
e bloqueio confirmado de novas aquisições/inferências nesta etapa. A
[preparação verificada](issue-4-vlm-revisao-perceptiva-execucao.md) fixou os 32
casos antigos de desenvolvimento e outros 32 de treino para auditoria cega,
em 32 canais novos e 16 por setor. As 64 folhas reproduziram os hashes originais,
com descarte confirmado dos vídeos e sem retries. O novo adaptador por frame e
o fluxo separado passaram em 549 testes e revisão independente. Os 67 arquivos
protegidos, partições 203/66/31, teste reservado e M1 permanecem intactos.
A [seleção concluída](issue-4-vlm-revisao-perceptiva-desenvolvimento.md) usou
somente os 32 antigos: A acertou 62/96 pares valor+evidência, B 54/96.
A foi congelado antes das inferências novas; suas 27 respostas desconhecidas
e quatro pares com evidência sem suporte no desenvolvimento não constituem aprovação.
A auditoria usou as anotações previamente seladas e agora está revelada;
não pode validar futuras correções. Nova revisão exige outro protocolo e
outra amostra cega de treino antes de retomar a parte VLM de B.

**Experimento B — VLM avaliado, nenhuma coluna liberada:** a
[auditoria B-VLM](issue-4-experimento-b-vlm-resultados.md) concluiu os 32 casos
fixos de treino (16/setor), com anotação assistida cega às respostas e às views.
Todas as cinco colunas falharam no gate anterior à execução; não houve treino
preditivo B-VLM nem comparação sua com os modelos anteriores. A execução parou
antes dos 237 sidecars restantes e dos 12 ajustes. Foram 54 tentativas cumulativas
(33 na fila v3, incluindo uma recuperação DNS limitada), 2.404,72 s de sessões,
limpeza confirmada, 509 testes, Ruff/formatação de 93 arquivos e revisão
independente. Os 45 arquivos congelados continuam iguais, teste fechado e M1
preservado. Uma nova rodada perceptiva exige versão/protocolo e outra amostra
cega de treino; não reutilizar a auditoria revelada para validar correções.

[B-cache com CLIP e medidas técnicas](issue-4-experimento-b-resultados.md)
continua sendo B treinado nas 300 referências/partições 203/66/31, com 905 colunas
e 12 ajustes. Na união da validação, MAE log por canal é 1,6584, contra 1,7761 de
A300 e 1,7349 de A200, com regressão pequena em moda frente a A300 e em q90.
Os cinco casos fixos de alto alcance seguem subestimados; quatro excedem a
faixa superior. Validação foi usada para seleção, sem avaliação independente.
A parte Qwen de M2 permanece bloqueada pela percepção; nenhum C ou modelo
promovido ao serviço.

**Expansão solicitada:** a meta foi concluída em 19/10. A segunda sondagem
única solicitada confirmou acesso à mídia na tentativa 311, liberando a guarda
mediante aquisição/decodificação/limpeza reais. A fila preservada completou as
100 adições na tentativa 343: **300 referências/166 canais**, 50 adições por
setor e nenhuma renovação de observações. As [partições ampliadas](issue-3-expansao-300-execucao.md)
ficaram **203 treino/66 validação/31 teste**. Os 200 metadados/assignments e as
169 linhas antigas de desenvolvimento são idênticos; os 16 hashes permitidos
continuam congelados, e o teste reservado permanece fechado. B0 foi recalculado
somente nos 203 rótulos de treino, em novo diretório privado. A e a [comparação](issue-3-expansao-300-resultados.md) foram executados com
12 ajustes e recarga exata: MAE log por canal nos 45 antigos piorou de 1,8569
para 1,9327; nos 66, A300 marcou 1,7761 contra 1,7349 de A200 e 1,8830 de
B0 ampliado. O erro log no recorte fixo de alto alcance melhorou, mas todos os
cinco casos continuam subestimados e acima do limite superior de A300. A rodada
A300 terminou sem promoção ao serviço; B foi iniciado depois, conforme registro
acima. Foram
343 tentativas de mídia, 4.076,53 s acumulados, zero revisões/mídia/folhas
pendentes; 26 testes direcionados, Ruff/formatação e curadoria independente
somente leitura passaram. A suíte completa anterior teve 388 testes; não houve
mudança de código/extratores nesta retomada.

O relato de M1 abaixo se refere à versão original de 200, preservada.

**Checkpoint atual:** o [piloto de baseline da #2](issue-2-baseline-observado.md)
permanece concluído com doze referências e suas partições preservadas. Na retomada
solicitada pelo aluno, os [extratores foram corrigidos e versionados](issue-1-extratores-e-treino.md)
e o [importador de treino](issue-1-manifesto-de-treino.md) passou nas verificações
locais. O aluno dispensou a conferência humana adicional dos quatro controles,
solicitando ferramentas/IA; decisões assistidas não são novas escutas humanas.
A [base ampliada](issue-1-base-para-experimento-a.md) concluiu a curadoria com
**200 referências/80 canais**, evidências verificadas e partições 124/45/31.
O [treino offline de A](issue-3-treinamento-offline.md) foi executado nas 124
referências de treino, com escolha nas 45 de validação e teste reservado sem
previsões/métricas. MAE log médio por canal: 1,8569 contra 1,9768 de B0/Bcanal;
q90 piorou e cobertura permanece não validada. Modelos foram persistidos e
recarregados. A [integração de M1 na função/MCP](issue-3-servico-m1.md) foi
implementada e demonstrada com pesos reais para 1/2/5 cadastros de um mesmo vídeo
público de beleza fora da coorte. Respostas idênticas, com modos anteriores
preservados e teste reservado fechado. A demo subestimou fortemente o alcance
do vídeo escolhido; a integração não valida qualidade preditiva ou calibração.
O [diagnóstico da subestimação](issue-3-diagnostico-subestimacao.md), restrito a
treino/validação, encontrou raríssimo suporte extremo e falhas de alto alcance
também no treino. Não encontrou erro de escala nas saídas auditadas; não houve
reajuste nem abertura de evidências/rótulos do teste. A validação tem apenas
quatro exemplos no recorte de maior alcance, sem avaliação independente final.
O novo baseline foi ajustado só no treino e demonstrado por Python/MCP;
o piloto antigo da #2 permanece intacto. A #1 conclui a preparação, e a #3 tem
o percurso técnico de M1 implementado localmente; fechamento remoto e explicação
dos resultados pelo aluno não foram realizados. O teste NIM passou somente no contrato
sintético restrito de cópia de evidências; explicação livre continua na #5.
Autorização operacional não foi transformada em aprovação da plataforma;
o aditivo não foi enviado. Os relatos abaixo são históricos.

Este documento registra os compromissos confirmados e o plano de execução autorizado pelo aluno em 16 e 17/10/2026. Em 17/10 foram aprovados A → B → C, Ridge opcional e a publicação das sete issues. Fonte de dados, horizonte efetivamente sustentado e viabilidade dos extratores serão verificados no checkpoint inicial; aprovação do plano não significa que esses dados já existem ou foram validados.

O desenho técnico está em [proposta-tecnica.md](proposta-tecnica.md), acompanhado das sete entregas e links reais em [backlog-proposto.md](backlog-proposto.md). As issues #1–#7 foram publicadas e suas dependências nativas verificadas. Começar pela [#1 — amostra auditável e viabilidade](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1); ela libera o primeiro fluxo baseline após resolver o checkpoint dos dados.

O início guiado da #1 está em [issue-1-primeira-amostra.md](issue-1-primeira-amostra.md). A Academy não fornecerá base, conforme consulta do aluno. Ele mantém YouTube, moda/beleza e prazo de 21/10; TikTok/SMP-Video foi descartado. A sondagem inicial retornou 40 metadados, com 15 candidatos de 14 canais atendendo somente à idade/duração propostas. O novo coletor por links consultou duas playlists e trouxe cem registros em seis chamadas, com cobertura parcial. Houve também extração audiovisual real em um fixture licenciado fora do recorte: não há ainda amostra elegível de treino ou modelo preditivo treinado. Resultados e limites estão em [coleta-por-canais.md](coleta-por-canais.md) e [piloto-extracao-temporaria.md](piloto-extracao-temporaria.md).

Orientação mais recente de 17/10: o aluno pediu testar yt-dlp diretamente em três candidatos reais encontrados pela API e reafirmou o foco em potencial de viralização. O [piloto real do YouTube](piloto-youtube-real.md) concluiu os três downloads, extração local e descarte: dois candidatos de beleza com alto alcance e um de moda. As sessões levaram 65,99 s, 49,82 s e 45,15 s; restaram zero sessões temporárias. Há metadados, fala, embeddings e medidas técnicas, mas os atributos VLM dos três foram reprovados. A disponibilidade técnica foi demonstrada nesses casos; condições da fonte, curadoria completa e elegibilidade de uma base de treino continuam pendentes. O fixture anterior do Commons permanece fora do recorte. Não substituir fala por título nem prometer exclusão imediata após queda da máquina.

O aluno confirmou remover tags e conservar canal/datas somente para auditoria, fora das entradas do modelo. A chave de canal serve à separação por criador, e publicação/coleta verificam o horizonte observado. Views são rótulo; curtidas permanecem somente no diagnóstico. Os atributos usados para prever continuam sendo os sinais do criativo disponíveis também nos inéditos.

No piloto concluído, uma sessão de 36,061 s de vídeo levou 43,10 s para aquisição e extração com pesos já baixados, com pico de 2,65 GiB. Houve seis frames, dez segmentos de fala e embeddings de 384/512 dimensões. Limpeza foi confirmada tanto após sucesso quanto após falha real. SmolVLM2 gerou JSON sem o esquema/evidências exigidos; os atributos foram reprovados e a rubrica continua pendente. Esses números são viabilidade operacional de um exemplo, não acurácia de percepção, desempenho preditivo ou capacidade em escala. A primeira etapa tinha dez testes locais; com o adaptador do YouTube, são quatorze testes passando para coleta, limpeza, validação e timeout.

Atualização do diagnóstico: as três transcrições originais foram ouvidas e confirmadas pelo aluno (primeiro fala, terceiro canto; segundo sem classificação separada). Qwen3-VL-2B GGUF local substitui o SmolVLM2 no extrator. O novo lote concluiu 3/3 casos com esquema válido e revisão assistida dos frames; aplicação teve um falso positivo e close-up ficou ambíguo. Ambos permanecem globalmente desconhecidos, preservando saída bruta e sem aprovação automática de treino. Método, tempos, memória e pendências estão em [correcao-extratores.md](correcao-extratores.md) e [validacao-transcricoes.md](validacao-transcricoes.md). Não houve expansão da base ou inferência externa.

Atualização do plano: o aluno aprovou meta de 300 e piso de 200, começando por vinte candidatos e retomada. Escolheu manter YouTube/moda/beleza e, se autorização não chegar a tempo, entregar protótipo executável com treino/validação supervisionados reais pendentes. A descoberta adicional consultou 162 registros e preparou vinte candidatos de vinte canais (dez propostas por setor), sem novos downloads. Condições, corte e próximos marcos estão em [uso-youtube-e-plano-de-entrega.md](uso-youtube-e-plano-de-entrega.md). Não confundir candidato com base elegível ou protótipo com desempenho validado.

## Compromissos confirmados

- Entrega: quarta-feira, 21/10/2026, até 23h59.
- Apresentação: sexta-feira, 23/10/2026.
- Início planejado: 16/10, com duração não informada.
- Sábado, 17/10: das 8h às 20h, podendo se estender até 21h.
- Domingo, 18/10: aproximadamente 5 horas.
- Segunda, terça e quarta: 3 horas por dia, totalizando 9 horas.
- A janela originalmente informada para 17–21/10 soma 26–27 horas, antes de descontar pausas e trabalho já realizado.
- Não foi recebida base de dados; o material disponível é o TAPI.
- Em 17/10, após consultar a organização, o aluno confirmou que não haverá base fornecida pela Inteli Academy. A obtenção de dados passa a depender de uma fonte independente.
- Fonte pretendida: YouTube Data API v3. Setores inicialmente pretendidos: moda e beleza.
- Em 17/10, após avaliar alternativas, o aluno reafirmou YouTube, moda/beleza e prazo fixo. Autorizou buscar criadores e conteúdo da plataforma com ferramentas/IA para captura em lote. A captura de metadados foi iniciada pela API; disponibilidade da mídia é verificada separadamente. A referência a virais não será usada para eliminar publicações de baixo desempenho da base.
- Prioridades: qualidade preditiva, avaliação válida, explicação do fluxo e prevenção tanto de vazamento estatístico quanto de exposição de dados e credenciais.
- O aluno quer conseguir explicar o que acontece, como, onde e por que cada escolha foi feita.
- O aluno já programa em Python e está aprendendo machine learning.
- O aluno concordou com a estratégia conjunta para os dois setores, a comparação multimodal e a organização do trabalho descritas abaixo.
- O aluno informou ter plano Enterprise e poder deixar chats e agentes trabalhando enquanto dorme, se necessário.
- Em 18/10, o aluno confirmou Google AI Plus e pediu proposta para dividir trabalho com o Codex, incluindo instalação/configuração. O [roteiro de agentes](configuracao-de-agentes.md) propôs ferramentas independentes e troca de relatórios; naquele checkpoint ainda não havia instalação, autenticação Google ou mudança de configuração global executadas. Benefícios de Pro e créditos de API não foram presumidos.
- Na etapa seguinte de 18/10, o aluno autorizou aplicar a configuração. Antigravity CLI 1.4.2 já estava instalado; Codex foi configurado com Sol/high, Luna/medium e até dois subagentes, e o perfil Google de revisão foi mesclado preservando as demais opções. Houve backups privados e teste mínimo de disponibilidade do Luna. O aluno executou a revisão Google; geração confirmada por JSON `SUCCESS`, código 0 e diagnóstico vazio, com relatório conferido. Isso valida uma execução, sem garantir outros modelos ou cotas; detalhes no roteiro.
- Os commits devem ser frequentes e organizados por mudanças coerentes, sem acumular assuntos independentes nem fragmentar artificialmente uma mesma mudança.
- A primeira versão foca divulgação, com visualizações como alvo principal e curtidas como informação complementar para análise.
- Em 17/10, o aluno reafirmou o foco em identificar potencial de viralização. A previsão/ranking de views no horizonte aprovado continua sendo a operacionalização; não há limiar binário de viralidade definido. A seleção de alto alcance para o piloto técnico não elimina exemplos de baixo/médio alcance da futura base de treino e avaliação.
- A YouTube Data API v3 está ativada e a chave foi configurada no `.env` local, ignorado pelo Git. Em 16/10, uma consulta mínima de verificação retornou HTTP 200 e um vídeo, sem exibir a chave nem salvar a resposta. O cliente OAuth existente no console não foi necessário para essa consulta pública.
- Em 17/10, o aluno escolheu API externa para o subagente explicador e quer testar NVIDIA NIM. Execução local via Ollama deixa de ser a escolha desse componente. A preferência se refere ao explicador, não autoriza transferir arquivos de mídia nem mudar os extratores automaticamente.
- Em 17/10, o aluno confirmou o limite operacional inicial de cinco vídeos por requisição. Adotar análise individual para um candidato e comparação para dois a cinco; três permanece um exemplo de demonstração.

## Caso de uso confirmado

Um produtor de conteúdo de moda envia de um a cinco vídeos inéditos e descreve, em texto, a intenção da campanha. Com um vídeo recebe análise individual; com dois a cinco, comparação para escolher qual criativo priorizar para patrocínio. Os arquivos já são os dados brutos dos criativos; o que ainda não existe são métricas observadas de suas publicações. A demonstração principal pode continuar usando três candidatos.

Os candidatos pertencem à mesma decisão de campanha. O treinamento, por sua vez, deve usar referências de diversos canais do setor. O usuário deseja que o sistema consiga analisar conteúdo de um canal novo, em vez de depender de ter visto aquele canal durante o treinamento.

## Objetivo e métricas aprovados

O objetivo de campanha suportado nesta primeira versão é divulgação. O modelo estatístico terá visualizações como alvo principal; o horizonte de observação ainda precisa ser definido conforme a viabilidade dos dados. A ferramenta apoiará a priorização de criativos para um teste de divulgação, com previsão, intervalo, ordenação e explicação. Esse resultado não representa uma previsão validada de retorno da mídia paga.

Curtidas serão uma informação complementar na análise retrospectiva da base e dos resultados, quando disponíveis. A expressão do aluno "feature extra para análise" é entendida como informação analítica complementar: as curtidas observadas do próprio vídeo não serão uma entrada para prever suas visualizações antes da publicação.

Um criativo inédito não tem curtidas observadas. Nesta versão, não será exigida uma previsão numérica adicional de curtidas. Se a explicação citar métricas de referências históricas, deverá identificar sua origem e respeitar os limites temporais e de separação dos dados. Histórico de curtidas de outras publicações só poderá virar atributo se sua disponibilidade anterior ao instante previsto for demonstrada e se isso fizer parte do contrato aprovado.

Vendas, leads e conversões ficam fora dos alvos preditivos desta entrega. Compartilhamentos e retenção não serão exigidos, pois a coleta pública planejada não fornece essas métricas dos canais de terceiros.

### Consequências para o desenho ainda em discussão

- Extrair sinais visuais, de áudio e de texto dos vídeos de referência e dos vídeos inéditos de maneira consistente.
- Só usar entradas que também possam estar disponíveis antes da publicação dos candidatos. Contexto e histórico do canal, se adotados, devem ter contrato e disponibilidade declarados; não podem ser presumidos a partir das métricas futuras do candidato.
- Interpretar o objetivo textual como informação de campanha. Alterar esse texto não muda automaticamente o alvo para o qual o modelo estatístico foi treinado.
- Avaliar a generalização com canais inteiros reservados, mantendo também a análise temporal exigida pelo projeto. Diversidade de canais e retirada de identificadores, sozinhas, não comprovam independência do canal nem efeito causal do conteúdo.
- Distinguir a previsão do indicador público aprendido da análise qualitativa de aderência ao objetivo da campanha. A forma de combinar essas evidências na recomendação ainda será definida.
- Prever desempenho público observado não equivale a prever retorno do investimento em mídia paga. A contagem pública pode incluir visualizações orgânicas e de anúncios sem que a consulta pública informe a composição.
- Como os candidatos são inéditos, definir quem pode receber seus arquivos, onde serão armazenados e por quanto tempo antes de escolher os serviços de processamento.

## Estratégia de modelos aprovada

Começar com um pipeline conjunto para moda e beleza, com o setor como informação de entrada. Separar os resultados de avaliação por setor e canal, além do resultado agregado.

Especializar por setor restringe o domínio de aplicação, mas não elimina a necessidade de generalizar para vídeos novos. A divisão também reduz os exemplos disponíveis para cada ajuste. Não há evidência coletada que demonstre qual abordagem será superior neste projeto.

Priorizar uma referência simples e duas configurações comparáveis do pipeline: metadados/texto e metadados/texto acrescidos da camada multimodal definida no escopo. Essa comparação mede o ganho da informação multimodal; é diferente de comparar especialistas por setor.

Em 17/10, o aluno aprovou os três experimentos: A = CatBoost com metadados/texto da fala; B = CatBoost completo; C = LightGBM com os mesmos atributos completos de B. São três configurações, não uma matriz com todos os algoritmos e modalidades. A mediana é uma referência calculada no treino, não outra cadeia de extração. A transcrição é compartilhada na ablação. Random Forest e XGBoost ficam fora do caminho obrigatório; Ridge voltou à discussão somente como comparador opcional.

A comparação A/B mede o acréscimo de atributos no CatBoost; B/C compara bibliotecas nos atributos completos. Esse desenho é válido para essas duas perguntas, mas não demonstra ganho multimodal no LightGBM nem resolve a interação entre biblioteca e representação. A ordem aprovada é mediana → A → B → C. No piloto, verificar todas as modalidades em poucos arquivos para descobrir falhas cedo. A execução não muda automaticamente de ordem nem elimina A após ver resultados.

Extensão opcional aprovada: acrescentar Ridge com os atributos completos depois do núcleo A/B/C, como referência linear de erro e ranking. Não bloqueia avaliação ou entrega se adiada. Imputação, codificação de categorias e escala devem ser ajustadas somente no treino. Não incluir outra cadeia de extração, todos os cruzamentos de modalidades, intervalos ou integração de Ridge no serviço. Ele não vira candidato completo de produção automaticamente: a entrega exige faixa e explicação compatíveis. Registrar resultado negativo ou superioridade, se observados, sem selecionar pelo teste final.

Para o explicador NIM, o aluno confirmou o ID `meta/llama-3.3-70b-instruct` em 17/10. Ele será o primeiro candidato testado para a função, sem superioridade experimental já demonstrada. A configuração NVIDIA foi posteriormente preenchida no `.env` local; nenhuma inferência NIM foi validada até este checkpoint. `.env.example` declara `NVIDIA_API_KEY` e `NVIDIA_MODEL` vazios; isso não equivale a um carregador implementado. Primeiro teste: evidências sintéticas, verificando português, fidelidade aos números, esquema e tempo de resposta. Uso com informação confidencial depende das condições do endpoint e não está liberado pela escolha do provedor.

Checkpoint técnico de 18/10: CatBoost 1.2.10 e LightGBM 4.7.0 passaram em treino/inferência/recarga com dados inteiramente sintéticos; as dependências foram travadas e os 47 testes existentes passaram. As duas requisições NIM ao Llama escolhido retornaram HTTP 410; o catálogo NVIDIA informa que seu endpoint gratuito foi descontinuado. Procedimento, evidências e limites estão em [issue-1-primeira-amostra.md](issue-1-primeira-amostra.md). Treino real, A/B/C e condições da fonte continuam pendentes.

O diagnóstico adicional esclareceu a dúvida sobre API ativa: a listagem NIM respondeu HTTP 200, mas não inclui o Llama escolhido. Uma solicitação mínima ao mesmo modelo retornou HTTP 410 com mensagem explícita do provedor de fim de vida em 26/08/2026. API/conta ativa não implica disponibilidade desse modelo hospedado; o acesso da chave a uma inferência utilizável ainda não foi demonstrado.

Após o aluno enviar a captura e o View Code com o Nemotron selecionado, `NVIDIA_MODEL` foi atualizado para `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, preservando a chave e demais linhas. O ID consta na listagem NIM, mas as tentativas limitadas retornaram HTTP 503 com mensagem de capacidade local do worker atingida (16/16). Não houve resposta gerada para avaliar; a validação do explicador permanece pendente. Esta escolha continua restrita ao explicador de texto: não autoriza envio de mídia real nem muda os extratores. O seletor do painel ainda mostrar o Llama não contraria a mensagem explícita de fim de vida no endpoint.

Investigar especialistas apenas se a validação apresentar erros sistemáticos por setor e houver tempo para uma comparação justa. Escolher usando validação; usar o teste reservado para avaliar a solução já escolhida.

## Organização aprovada dos chats

- Chat principal: problema, escopo, arquitetura, decisões de experimento, integração e aprendizagem.
- Chat de execução: uma issue relevante, pequena o bastante para concluir e demonstrar em um bloco de trabalho. Mudanças dependentes e pequenas podem continuar no mesmo chat.
- Subagentes: investigação, consulta a documentação e revisão de alterações bem delimitadas.
- Um executor de código por árvore de trabalho. Um revisor pode analisar o resultado sem editar os mesmos arquivos.
- Até duas frentes de implementação apenas quando os contratos e responsabilidades estiverem estáveis, em worktrees diferentes. O limite é um teto, não uma meta.
- Um responsável pela integração: conferir o resultado combinado e executar a verificação do fluxo completo.

Subagentes dividem o trabalho e o contexto; worktrees separam cópias de trabalho do código. Uma coisa não substitui a outra. Worktrees também não isolam automaticamente serviços externos, cotas de API ou pastas de dados compartilhadas.

Antes de usar worktrees, consolidar um primeiro estado versionado com instruções e decisões comuns. Cada chat de execução recebe explicitamente a issue e as referências necessárias; o histórico de conversa não deve ser a única fonte das decisões.

Para a passagem da #1 à implementação da #2, recomenda-se um novo chat de execução com este briefing, a seção P2 do backlog e o checkpoint da primeira amostra. A tarefa atual pode ser concluída no chat principal; o novo chat recebe uma entrega delimitada, o estado real dos dados e as pendências do NIM. A mudança de chat organiza o contexto; não libera dependências científicas nem autoriza implementações concorrentes na mesma árvore. O aluno pediu aviso antes dessa passagem, em vez de acumular as próximas issues no histórico principal.

A [passagem para a #2 no corte de protótipo](issue-2-inicio-prototipo.md) registra a fatia de cadastro, contratos e transporte que pode começar sem baseline real. Os critérios científicos originais continuam pendentes. Em 18/10, a primeira revisão Google foi executada pelo aluno e conferida. A passagem pode começar, preservando indisponibilidade explícita da previsão; a sugestão externa de empate em modo baseline foi rejeitada por não existir baseline calculado.

Atualização da execução em 18/10: a fatia de protótipo da #2 foi implementada com um
executor nesta árvore, depois da prática e revisão de `determine_mode`. Há contrato
estrito, cadastro local seguro, função/CLI e FastMCP stdio; 103 testes passaram,
incluindo paridade por cliente real e stdout reservado ao JSON-RPC. A demo gera mídia
sintética e mostra indisponibilidade explícita em análises com um, dois e cinco IDs.
O [roteiro de execução](issue-2-execucao.md) registra uso e limites. A issue #2 original
permanece aberta pelos critérios científicos dependentes da #1; não houve nova coleta,
treino, geração NIM ou previsão real.

Na continuação, o aluno autorizou implementar e publicar as rotinas restantes com
testes sintéticos. A [extensão estatística da #2](issue-2-baseline.md) implementa
partição por canal e duplicatas, manifesto imutável, B0/Bcanal e faixa empírica
calculada somente no treino. Há demo inteiramente gerada e 150 testes passando.
Artefatos e estimativas distinguem `synthetic` de `unvalidated` e mantêm
`real_results_available=false`. A função/MCP preserva indisponibilidade; critérios
científicos reais da #2 e elegibilidade da #1 permanecem pendentes.

Em seguida, o aluno autorizou integrar B0 e faixa à função Python e ao MCP em modo
sintético. A opção explícita do operador `synthetic_baseline=True` / `--synthetic-baseline`
usa exclusivamente a fixture inventada compartilhada com a demo offline. A entrada
dos criativos não mudou; o host não escolhe arquivos de artefato nem fornece rótulos.
A resposta `prototype-synthetic-v1` publica a referência e faixa setoriais, com
`scientific_status=pending_issue_1` e `real_results_available=false`. A faixa não é
intervalo individual calibrado. Previsão real, intervalo preditivo e ranking continuam
indisponíveis; o modo padrão preserva também o baseline indisponível. Um executor
nesta árvore; sem coleta adicional, ajuste com dados reais ou chamada NIM.

Retomada da #1 após a integração sintética: o aluno solicitou resolver a base e
esclareceu o uso para métricas de desempenho. A
[auditoria de 18/10](issue-1-auditoria-da-base.md) conferiu vinte observações/canais,
preparou manifesto privado sem preencher ausências e confirmou zero elegíveis.
São quatro setores explícitos em revisões existentes (uma parcial), dezesseis
sem confirmação, três fingerprints e dezessete ausentes. Views públicas pela API,
métricas derivadas e cópias audiovisuais têm condições distintas; B0 dispensa novo
download. Não houve evidência de adesão/enquadramento do uso de métricas nem
liberação da base original. Não houve alteração do recorte, treino, nova coleta,
contato externo ou aceite de termos; a previsão real segue indisponível.

## Briefing mínimo de cada issue

### Orientação posterior de 18/10: coleta direta autorizada

Depois da auditoria e do início da preparação do aditivo, o aluno pediu
expressamente consultar a API e adquirir os vídeos sem o formulário. Essa é a
autorização operacional atual para os vinte candidatos existentes; não repetir
o pedido de consentimento nem marcar aprovação do YouTube como verificada.
O [registro desta execução](issue-1-coleta-direta-e-setores.md) documenta uma
consulta bem-sucedida com vinte registros, dezessete novos downloads temporários
concluídos e três pilotos anteriores reutilizados. Há hashes/propriedades nos vinte,
zero sessões temporárias restantes e dezesseis classificações novas de setor.
Dois casos requerem revisão de inclusão; dezesseis idiomas seguem sem confirmação.
O aluno pediu navegação sem áudio: player silenciado e encerrado após a revisão.
Não houve envio do formulário, expansão da seleção, novas extrações ASR/CLIP/Qwen,
treino ou NIM. A previsão real continua indisponível até liberação da coorte.

### Estrutura do briefing

1. Resultado observável e motivo de ele ser necessário.
2. Entradas, saídas e contratos a preservar.
3. Critérios de aceitação, limites e dependências.
4. Verificação apropriada, incluindo riscos de dados relevantes.
5. Conceito que o aluno praticará e precisará explicar.
6. Evidências finais: alterações, verificações realizadas, resultados e limitações.

As issues devem entregar um percurso estreito e demonstrável. A primeira passagem pode usar uma referência simples de predição, explicitamente identificada. Evoluções acrescentam capacidades ao mesmo fluxo e mantêm os contratos verificáveis.

## Política de commits

Fazer commits ao concluir unidades lógicas de trabalho. A frequência acompanha a conclusão dessas unidades, sem metas artificiais de tempo, quantidade de commits ou número de linhas.

- Cada commit deve ter uma intenção principal, descrita por uma mensagem clara e específica.
- Manter juntos o código, os testes e a documentação necessários para entender e verificar a mesma mudança.
- Separar mudanças independentes, inclusive refatorações sem relação com a entrega em andamento.
- Dividir uma entrega maior em passos coerentes e verificáveis. Uma issue pode resultar em vários commits quando cada passo fizer sentido isoladamente.
- Revisar o conteúdo selecionado e executar as verificações apropriadas antes de registrar o commit.
- Excluir segredos, dados sensíveis, arquivos temporários e resultados locais que não devam ser versionados.
- Aplicar a mesma política a chats de execução, subagentes e trabalho noturno.

Por exemplo, adicionar uma regra de validação de entrada com seus testes é uma unidade coerente; criar commits separados para cada arquivo dessa mudança não é necessário. Coleta de dados e explicação de previsões, quando independentes, devem ser registradas em commits distintos.

## Ciclo de execução e aprendizagem aprovado

Em cada bloco, reservar tempo para definir o resultado, praticar uma parte pequena, concluir a implementação, verificar o comportamento e explicar a solução. Em um bloco de 3 horas, uma distribuição inicial possível é: 15 minutos de orientação, 105 de execução, 30 de verificação/integração e 30 de explicação e registro. Ajustar depois da primeira experiência.

O aluno conduz hipóteses, critérios de avaliação e interpretação dos resultados. Nas partes que quer dominar, pratica primeiro uma versão pequena. A IA ajuda com investigação, revisão e ampliação de tarefas repetitivas após haver um exemplo compreendido e verificável.

Como o aluno já programa em Python, a prática deve priorizar formulação do alvo, disponibilidade das informações, baseline, separação dos dados, interpretação de métricas, intervalos e análise de erros. O aluno percorre uma amostra pequena para entender a transformação dos dados e as saídas do modelo; a IA pode ampliar a execução depois desse entendimento.

Na curadoria dos vinte candidatos, a IA faz a primeira triagem e o aluno revisa uma amostra e resultados ambíguos ou contraditórios. A sequência de vinte confirmações manuais foi suspensa em 18/10. Separar sugestões baseadas em metadados, atributos extraídos de imagem/fala e observações humanas, preservando a origem de cada informação. Campos sem evidência ficam desconhecidos; a falta de acesso audiovisual utilizável não transfere ao aluno a obrigação de preencher todos manualmente. As revisões já conhecidas são controles de desenvolvimento, não uma amostra independente para medir qualidade. A auditoria por amostragem acontece após a pré-classificação audiovisual e não constitui uma estimativa precisa de acurácia com poucos exemplos.

O coordenador e o revisor das decisões de ML devem usar capacidade de raciocínio adequada. Modelos econômicos podem executar tarefas estreitas com critérios claros. Paralelismo acrescenta trabalho de coordenação e consumo de recursos; a economia precisa ser avaliada pelo esforço total e pelo retrabalho, não só pelo modelo escolhido.

## Uso de execução noturna

Usar o período noturno para tarefas delimitadas e previamente verificadas em uma amostra: coleta autorizada com limites de cota, extração de atributos com cache, experimentos definidos com treino/validação e revisão de resultados. O aluno confere evidências, falhas e conclusões ao retomar o trabalho.

Cada tarefa deve declarar entrada, resultado esperado, orçamento de tempo/cota/custo, condições de parada e localização dos resultados. Manter o teste final fora da seleção automática de modelos. Decisões sobre alvo, novos serviços externos, dados confidenciais ou mudanças de arquitetura devem voltar para a discussão.

A execução que depende da pasta local requer a máquina ligada, disponível e o aplicativo em execução. Uma tarefa exclusivamente na nuvem precisa receber contexto acessível naquele ambiente; o acesso à pasta local não é automático. Disponibilidade e permissões dependem também das configurações do workspace Enterprise.

Não foi configurada automação nem iniciado trabalho noturno: a conversa ainda está definindo os contratos que permitirão tarefas autônomas úteis. A possibilidade de trabalho noturno não amplia as horas disponíveis para aprendizado, revisão e integração pelo aluno.

## Requisitos de prevenção de vazamento

No experimento, declarar quais informações estariam disponíveis no momento da previsão. Separar treino, validação e teste conforme a pergunta, antes de ajustar transformações aprendidas. Impedimento de acesso ao futuro exige verificar datas de observação e disponibilidade dos rótulos, além das datas de publicação.

A coleta atual de contagens acumuladas não reconstrói automaticamente desempenho aos 30 dias nem estatísticas históricas do canal. A interpretação dos resultados deve registrar essa limitação. Títulos e descrições atuais também podem diferir das versões publicadas inicialmente.

Na proteção de informações, manter segredos fora de prompts, commits, logs, notebooks e documentos compartilhados. Usar somente conteúdo autorizado nas ferramentas externas. Regras de leitura e permissões devem proteger arquivos sensíveis; ignorar um arquivo no Git não basta para torná-lo inacessível a um agente. Definir separadamente o acesso de cada componente ao que ele precisa para executar.

O `.gitignore` exclui credenciais, ambientes/caches e pastas locais destinadas a dados coletados, mídias, experimentos e modelos. Manter esses arquivos nas pastas previstas, como `data/raw/`, `data/processed/`, `uploads/` e `artifacts/`; não espalhar dados privados pela árvore de código. Documentação pública, exemplos sintéticos, esquemas, configurações sem segredos e arquivos de dependências devem continuar versionáveis. O TAPI externo recebido permanece ignorado.

A configuração pública de referência é `.env.example`, com `YOUTUBE_API_KEY` vazia. A chave real foi preenchida somente no `.env` local; sua configuração deve manter a restrição à YouTube Data API v3. A verificação de conexão enviou a chave em um cabeçalho HTTPS, sem colocá-la na URL ou nas saídas exibidas. Essa verificação não implica que exista um carregador de configuração ou coletor implementado. A política de exclusão não substitui revisão dos arquivos selecionados para cada commit.

## Marcos propostos

| Data | Entrega verificável |
| --- | --- |
| 16/10 | Definir problema, alvo, protocolo e desenho; verificar acesso viável a dados e mídia. |
| 17/10 | Obter amostra auditável, baseline e primeiro fluxo executável; iniciar multimodal e integração. |
| 18/10 | Fechar multimodal mínimo iniciado no sábado e executar a comparação principal. |
| 19/10 — 3h | Consolidar previsão, intervalo, explicação e integração; resolver pendências obrigatórias. |
| 20/10 — 3h | Encerrar funcionalidades; verificar avaliação final, reprodução e documentação. |
| 21/10 — 3h | Corrigir falhas, conferir pacote e entregar com margem antes de 23h59. |

O checkpoint principal é o fluxo executável no sábado. Se os dados ou a integração não forem viáveis, revisar imediatamente volume e complexidade. Qualquer redução de requisito obrigatório deve ser explícita e discutida. Os dias após a entrega ficam disponíveis para ensaio e preparação da apresentação.

## Decisões ainda abertas

- Prioridades específicas de aprendizagem dentro de machine learning.
- Qualidade preditiva e calibração no alvo definido: contagens públicas observadas com 30 <= idade < 37 dias, sem reconstruir o dia 30.
- Aprovação da plataforma não verificada e aditivo não enviado; autorização operacional expressa e viabilidade local estão registradas, sem equivalência entre essas condições.
- Aprovação dos atributos VLM e comparação A/B/C na coorte ampliada, mantendo as mesmas referências e partições.
- Confirmar execução dos contratos e critérios publicados; qualquer revisão necessária deve registrar o impacto antes de ampliar coleta ou treino. A divisão das sete issues já foi aprovada e publicada.

## Referências consultadas

- [Codex: subagentes e escolha de modelos](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- [Codex: worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).
- [Codex: permissões de leitura](https://learn.chatgpt.com/docs/permissions#deny-reads-with-exact-paths-or-globs).
- [Codex: tarefas em segundo plano](https://learn.chatgpt.com/docs/automations).
- [Scikit-learn: validação e generalização](https://scikit-learn.org/stable/modules/learning_curve.html).
- [Scikit-learn: avaliação de grupos não vistos](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
- [YouTube: composição das visualizações públicas](https://support.google.com/youtube/answer/2375431?hl=en-NG).
- [YouTube: chave de API e OAuth](https://developers.google.com/youtube/registering_an_application).
- [Google Cloud: proteção de chaves de API](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices).
- [Skills de Matt Pocock](https://github.com/mattpocock/skills).
- TAPI disponível localmente, com prazo de entrega corrigido pelas informações do aluno.
