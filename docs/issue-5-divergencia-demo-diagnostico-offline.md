# Divergência da demo — diagnóstico offline e entrega parcial

O diagnóstico confirmou os mesmos arquivos, pedido, configuração, modelo e
linhagem de treino nas duas rotas. **A causa da divergência numérica permanece
desconhecida.** Não foi repetida inferência, recuperado scratch ou acrescentada
tolerância. Uma entrega privada parcial foi registrada com os três inputs,
as duas respostas reais e o status de igualdade reprovada.

O [recibo agregado](evidence/issue-5-divergencia-demo-diagnostico-offline-20261020.json)
vincula os arquivos inspecionados e os recibos privados por SHA256. Os
[resultados anteriores](issue-5-demo-local-python-mcp-resultado.md) e a parada
original permanecem preservados.

## Famílias numéricas

| Família | Diferenças observadas | Maior diferença absoluta |
| --- | --- | --- |
| q10 servido | Duas de três entradas | 3,4939184904349716 views |
| q50 | Duas de três entradas | 56,292847557117966 views |
| q90 servido | Duas de três entradas | 2.551,7943928820414 views |
| SHAP agrupado de fala | Duas de três contribuições | 0,04549805077534991 em log1p(views) |
| SHAP de setor, propriedades e estado da fala | Iguais nas três entradas | 0 |
| Base SHAP | Igual nas três entradas | 0 |
| Similaridades dos comparáveis | Seis de nove posições ordenadas | 0,03517549055155578 |

O ranking e a ordem dos candidatos são iguais. O pacote conserva a mesma
ordem dos identificadores de evidência; 12 afirmações diferem somente em
números, com textos não numéricos iguais. Seus hashes e o hash da análise
mudam em consequência do conteúdo diferente. A comparação integral continua
reprovada nos 22 campos já registrados.

q10/q90 são os limites servidos após a política congelada de reparo de quantis;
os quantis brutos anteriores ao reparo não ficaram retidos. As similaridades
constam nas frases, mas os IDs das referências escolhidas não constam nesse
pacote reduzido: igualdade das identidades dos comparáveis não pode ser
inferida de posições ou similaridades. Não foi recarregado o índice de treino
para tentar reconstruir essa informação.

## Identidade e configuração

- Os hashes do pedido, cadastro, configuração e resposta Python continuam
  iguais aos vinculados antes do suplemento. Os três arquivos de mídia foram
  reconferidos; a ordem dos IDs corresponde nas duas respostas.
- Modelo e extrator publicam os mesmos hashes e versões nas duas respostas.
  Os hashes atuais dos três arquivos CatBoost conferem com o manifesto. A
  configuração do extrator confere com seu digest. Não foi carregado modelo
  para previsão durante este diagnóstico.
- Baseline, coorte e partição têm identidades iguais. O artefato registra 124
  referências de treino e um único digest do split. O caminho nativo valida
  bundle/runtime/fontes e o índice verifica a linhagem e o split de treino
  antes de formar o pacote. Esta conferência não abriu features/rótulos de
  treino nem atribuições ou conteúdo do teste reservado.

Os jobs externos têm os mesmos tetos, timeout, diretório de trabalho e
workspace. Diferem em argv, lease e `TMPDIR`, devido à rota e aos diretórios
próprios de cada chamada. Os recibos mostram somente `TMPDIR` diferente no
ambiente externo explícito.

A camada stdio do MCP filtra o ambiente intermediário. Porém o serviço
compartilhado cria o supervisor com ambiente literal; o supervisor faz o mesmo
para o grafo; o grafo e o launcher nativos recriam ambientes literais para
worker e extração. Ambos usam os mesmos interpretadores/configuração, CPU,
OpenBLAS com uma thread, OMP com quatro e ASR/Torch com quatro. IDs de grupo,
nomes temporários e processos são próprios de cada chamada. Não foi detectada
diferença de configuração a jusante por leitura do código; não havia captura
do ambiente efetivo de cada processo interno para conferir retrospectivamente.

A ordem do pedido é preservada pelo cadastro e pelo handoff, validada antes
da extração e na vinculação posterior. Ambos os caminhos usam o mesmo
launcher, extrator e operações do grafo. Não foi encontrada mudança de ordem,
modelo, treino ou gate que fundamente uma correção de configuração.

## Limite da evidência e menor continuidade justificável

Os vetores de entrada, transcrições e quantis brutos não foram retidos.
`M1Handoff` calcula um digest das features em memória e verifica sua integridade
na própria sessão, mas não o serializa no resultado. O hash do áudio decodificado
é calculado no extrator compartilhado e também não sai no contrato reduzido
de candidato. Nenhum desses hashes pode ser recuperado dos recibos atuais.

As diferenças nas projeções ligadas à fala são observáveis. Elas não permitem
atribuir a causa a ASR, embeddings, previsão CatBoost ou execução de bibliotecas.
Não há evidência suficiente para escolher uma alteração numérica corretiva.
O menor ajuste diagnóstico justificável, se uma execução futura for autorizada
separadamente, seria reter o digest de features já calculado e digests das
etapas pertinentes, vinculados ao pedido, antes de limpar temporários. Isso
não exige publicar vetores/texto nem mudar a autoridade numérica ou a igualdade.
Esse ajuste e uma nova execução não foram implementados ou autorizados aqui.

## Entrega privada parcial

Foi criado um recibo novo, ignorado pelo Git, contendo caminhos e hashes dos
três inputs, pedido, cadastro, configuração, respostas Python/MCP e recibos
de execução/diagnóstico. Ele declara `partial_delivery_exact_parity_mismatch`,
`full_acceptance=false` e `handoff_v3_claimed=false`. Os dados ficam disponíveis
para revisão e demonstração técnica com essa limitação explícita.

Essa passagem parcial não altera marcadores consumidos nem cria o resumo de
sucesso ou o handoff v3. Não declara apresentação concluída, não autoriza nova
inferência e não antecipa o descarte. Os inputs continuam retidos até
**21/10/2026 às 23h59, São Paulo**; não há automação de exclusão. Recibos de
recolhimento foram conferidos sem reabrir o scratch removido.

Não houve mudança de código, nova aquisição, treino, chamada externa, inferência,
acesso a conteúdo de holdout ou escrita na árvore principal. Esta unidade
acrescenta apenas diagnóstico, evidências e a entrega parcial explícita.
