# Demonstração real — proposta de recuperação de fontes já usadas

**Há uma alternativa concreta a pedir três vídeos novos ao usuário:** recuperar
três fontes de beleza já adquiridas/processadas sob autorização operacional no
projeto, preservando o contrato atual. Esta proposta está delimitada e aguarda
revisão técnica; **nenhum download ou processamento foi executado**.

Este adendo complementa o [inventário anterior](issue-5-inventario-midias-demo.md),
sem apagá-lo ou alterar as entregas da #7. A ausência de arquivos naquele
instantâneo não significa ausência de trabalho real: o projeto já realizou
pilotos, ASR e extração reais, treino, previsão M1 e paridade Python/MCP sobre
mídia real. A recomendação anterior de disponibilizar três novos arquivos era
incompleta porque não explorava a recuperação das fontes já autorizadas.

O [resumo público do plano](evidence/issue-5-recuperacao-midias-demo-proposta-20261020.json)
contém limites e critérios. Identidades, URLs, propriedades históricas e textos
humanos originais estão somente em recibos novos ignorados do clone, sob os
parâmetros `${RECOVERY_PLAN_PRIVATE}` e `${HUMAN_AUTHORIZATION_EVIDENCE_PRIVATE}`.
O plano privado ativo v2 tem SHA256
`f61bcf849d2f61b701c00ef447486494d302a86029c5f14e8f11547ed1377f80`.
A execução continua desabilitada até a revisão desse plano concreto.

## Autorizações humanas conferidas

Foram consultadas as mensagens humanas originais, com identificadores reais e
texto literal preservados privadamente, em três chats do projeto:

| Chat | Autorização encontrada | Escopo que continua relevante |
| --- | --- | --- |
| Definir escopo e arquitetura | Testar yt-dlp em três vídeos reais encontrados pela API, extrair atributos e apagar os arquivos | Aquisição temporária dos pilotos, processamento local e descarte |
| Iniciar protótipo da issue #2 | Consultar a API e baixar os vídeos do lote existente sem aguardar formulário | Vinte fontes operacionais já delimitadas, incluindo reutilização dos pilotos |
| Iniciar experimento A com CatBoost | Na ausência de arquivo próprio local, obter vídeo público de um dos setores para demonstrar M1 | A demo real já executada usou uma fonte desse contexto |

Os recibos e [a orientação operacional versionada](issue-1-coleta-direta-e-setores.md)
corroboram essas mensagens. Não foi encontrada revogação nos trechos posteriores
consultados. O pedido atual de recuperar o trabalho existente e executar uma
proposta técnica mantém essa intenção, com a revisão prévia explicitamente
exigida nesta frente. Não é necessário transformar isso em pedido genérico de
consentimento nem presumir que o usuário precisa produzir três peças novas.

Autorização operacional não é uma licença aberta, aprovação de plataforma,
renovação dos orçamentos científicos encerrados ou autorização de envio privado
a um provedor. A proposta não muda nenhuma dessas condições e não depende de
pesquisa web para inferir uma permissão humana.

## Mesmo setor e campanha: origem da exigência

A exigência vem da API atual, não foi criada pelo inventário:

- [AnalysisRequest](../scripts/creative_contracts.py) contém um único `sector`
  e `campaign_id` para toda a lista de um a cinco IDs.
- [CreativeRegistry.validate_creatives](../scripts/creative_registry.py) confere
  esses campos em cada cadastro e retorna `sector_mismatch` ou
  `campaign_mismatch` quando houver divergência.
- O [aceite P5](backlog-proposto.md) pede uma demo integrada que **compare três
  arquivos**, além dos modos de um e cinco candidatos.

A campanha comum é o contexto de decisão cadastrado pelo operador para a demo.
Não é exigido que as publicações históricas tenham sido produzidas para uma
mesma campanha comercial real. A proposta usa contexto de demonstração
explicitamente redigido pelo operador, sem afirmar intenção original das fontes.
As mídias continuam reais; o contexto de campanha é demonstrativo.

Os três pilotos originais (dois de beleza e um de moda) poderiam ser usados em
uma requisição comparativa de dois e uma individual. Isso reaproveitaria três
fontes, mas ainda não demonstraria comparação conjunta de três no contrato
atual. Repetir cadastros da mesma peça também não fornece três criativos.

## Seleção mínima, fora do holdout

O plano fixa **três fontes distintas de beleza do lote original de vinte**:

1. A fonte da demonstração anterior com M1 real e paridade Python/MCP.
2. Duas outras fontes do mesmo lote, selecionadas pela ordem original entre as
   de beleza com triagem não forçada de português aceita no recibo de curadoria.

Não houve seleção por views, curtidas, previsões ou outro outcome. Não há busca
nova, fonte de reserva, troca automática por falha ou escolha de um vídeo para
cada tentativa de produzir resultado favorável. URLs e identidades exatas
estão congeladas no plano privado. Os registros de declaração de idioma e os
recibos de ASR antigos são **históricos**, não passagem dos gates atuais.

A [formação da coorte A200](issue-1-base-para-experimento-a.md) registra que os
vinte IDs originais de desenvolvimento ficaram fora. A
[expansão de 300](issue-3-expansao-300-execucao.md) preservou o mesmo holdout de
31 referências. A exclusão original e essa preservação permitem concluir que
as três fontes selecionadas ficam fora do teste reservado, sem abrir features,
rótulos, previsões, métricas ou assignments desse teste. Não se reivindica
independência científica nem pertença atual das fontes às outras partições.

O helper Commons é uma alternativa histórica licenciada, mas seu vídeo
horizontal não atende à entrada atual; não é necessário convertê-lo ou buscar
uma fonte nova para este trio. Índices, vetores, folhas PNG e controles gerados
também não são substitutos para os três arquivos recuperados.

## Limites propostos para revisão

| Recurso | Teto congelado na proposta |
| --- | --- |
| Fontes | Três URLs exatas já processadas, todas de beleza |
| Tentativas de aquisição | Três, serializadas, uma por fonte; zero retries ou substituições |
| Descoberta / API de métricas | Zero buscas novas e zero chamadas à YouTube Data API; nenhum rótulo/data/views renovado |
| Aquisição | Até 180 s por tentativa; 600 s para a fase completa |
| Análise nativa | Uma chamada Python e uma MCP de três candidatos; até 480 s por percurso |
| Tempo total | Até 1.800 s desde o início; interromper ao limite e concluir o recolhimento necessário |
| Arquivo de mídia | Até 32 MiB por arquivo, até 96 MiB nos três arquivos completos |
| Diretório próprio de execução | Limite agregado de 384 MiB; exigir ao menos 1 GiB livre antes de começar |
| Saída do downloader | Até 64 KiB por stream, retida somente no recibo privado permitido |
| Recursos locais | Um thread de processamento por biblioteca, RSS da árvore até 3,5 GiB; sem VLM concorrente |
| Inferência externa / NIM | Zero |

O `--max-filesize` do yt-dlp não basta como limite rígido de disco. A execução
precisará acrescentar `RLIMIT_FSIZE` no filho, monitorar o total do diretório,
aplicar deadline externo e encerrar/recolher o grupo que possui se algum teto
for ultrapassado. Os limites de mídia/disco não são um teto de bytes TCP/TLS.
Três aquisições são três tentativas de mídia, não três requisições HTTP: o
yt-dlp pode realizar várias requisições internas para cada fonte. A cota zero
refere-se à API de métricas com chave, que não será chamada.

O [piloto existente](../scripts/pilot_youtube_media.py) inclui retries e pode
mesclar em MKV. A proposta não executa sua CLI inteira nem altera esse código
selado: prepara um invólucro aditivo com retries zero e seleção determinística
de um arquivo MP4/WebM com áudio, até altura 720, sem merge/transcodificação.
Se não existir formato compatível, registrar falha e parar. Manter sem cookies,
login, proxy, configuração pessoal, plugins ou componentes remotos baixados.
Autenticação, captcha/antibot, 403/429 ou fonte removida encerram a fase, sem
contorno de acesso ou repetição.

## Percurso local a demonstrar depois da revisão

Antes de começar, registrar a liberação técnica vinculada ao hash do plano e
aguardar uma janela sem execução VLM/modelos concorrentes. Confirmar hashes das
fontes/contratos e dos recursos já congelados; usar somente o clone e diretório
privado novo para escrita, com ambientes novos já existentes em leitura.

1. Reservar de forma durável o diretório e cada tentativa antes do spawn. Não
   retomar uma execução iniciada/incerta após crash ou receber segundo processo.
2. Recuperar sequencialmente as três fontes. Conferir identidade canônica,
   formato e duração/propriedades esperadas. Registrar novos hashes de bytes;
   não alegar igualdade com contêineres descartados ou substituir qualquer
   pixel/entrada das filas científicas preservadas.
3. Validar os arquivos pelo cadastro original e atribuir três IDs opacos à
   mesma campanha demonstrativa de beleza. Manter os mesmos bytes até concluir
   os dois percursos, sem nova aquisição para a segunda chamada.
4. Executar **o worker nativo** e a mesma função `analyze_via_graph` por Python
   e por `analyze_creatives_with_explanation` via MCP stdio. Usar M1/A200,
   ASR/MiniLM e evidências nativas, sem fixture ou transcrição injetada. Caches,
   bundle e evidências de treino originais ficam somente leitura; a fase de
   modelo/grafo roda com rede isolada e desabilitada, sem pesos novos.
5. Comparar as respostas integrais. Uma demonstração local positiva requer
   três previsões disponíveis, handoff nativo, q50/faixa/ranking preservados,
   SHAP e busca de comparáveis somente no treino. Manter limiar 0,5 e aceitar
   ausência de referências com justificativa, sem relaxamento para preencher lista.
6. Recolher todos os processos próprios antes de excluir mídia, áudio, frames,
   cópias e scratch. Guardar somente recibos novos e projeções sanitizadas de
   resultado; diretório 0700 e arquivos 0600. A morte do supervisor/host pode
   exigir recuperação por lease/PID/identidade; não prometer descarte instantâneo.

Uma falha atual de idioma, suporte ou previsão continuará indisponível e será
registrada. Não se forçará português, afrouxará seleção, mudará fonte ou tentará
novamente para fabricar um resultado positivo. As três fontes têm evidência
histórica útil, mas disponibilidade da origem, identidade dos bytes e passagem
atual do ASR não são garantidas antes da execução.

## O que esta demonstração resolveria

O percurso proposto pode demonstrar três **mídias reais recuperadas**, extração
real, previsão M1 e evidências locais pelo serviço compartilhado Python/MCP,
se os gates atuais passarem. Resolveria a disponibilidade do trio sem exigir
novas peças do usuário e sem alterar o contrato.

O seletor externo permanecerá ausente, `real_provider_verified=false` e
`adherence_status=not_evaluated`. Portanto, esse marco não comprova uma
explicação por provedor, aderência real, desempenho científico ou aceite
integral da #5. A declaração de NIM gratuito feita pelo usuário está sendo
tratada na frente correspondente; ela não é necessária para recuperar mídia
e não autoriza envio privado por este plano.

Esta etapa termina com a proposta concreta e os recibos de autorização para
revisão, sem adquirir arquivos. A autorização vigente permite avançar após a
revisão técnica delimitada, sem uma nova aprovação humana genérica. O inventário
histórico, a entrega #7, as oito folhas, crops, filas, modelos e holdout
permanecem preservados.
