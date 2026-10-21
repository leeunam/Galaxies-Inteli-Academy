# Auditoria estática do runtime visual

Não foi encontrado defeito demonstrável de encaminhamento de threads ou formato
dos eventos. Esta unidade não executou binário de modelo, encoder, decoder,
inferência, benchmark, download ou instalação. Não alterou produto, parâmetros,
filas, recibos ou orçamento. O [recibo sanitizado](evidence/issue-4-vlm-runtime-audit-v1.json)
registra as verificações e os limites de causalidade.

## Threads e sequência de execução

O argv efetivo do probe solicita `--threads 4 --threads-batch 4`, GPU layers 0 e
projector offload desligado. O launcher usa `vlm_encoder_probe.environment()`:
whitelist própria com OMP_NUM_THREADS=4 e OPENBLAS_NUM_THREADS=1, sem herdar
LD_LIBRARY_PATH, LD_PRELOAD ou seletores GGML do ambiente do controlador.

Na [CLI fixada em 797de63b2](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/mtmd-cli.cpp):

| Ponto | Fonte/efeito verificado |
| --- | --- |
| Construção do contexto, linha 109 | common_init_from_params(params) cria modelo/contexto LLM |
| Linha 117 | ctx.n_threads recebe params.cpuparams.n_threads |
| Linha 160 | mparams.n_threads recebe params.cpuparams.n_threads antes de mtmd_init_from_file |
| Linha 538 | ggml_backend_load_all precede construção dos contextos |
| Linhas 422–483 | percorrer chunks, montar lote de mídia e chamar mtmd_batch_encode |
| Linhas 493–503 | só depois do retorno do encode, chamar decode do chunk da imagem |

O encoder recebe o parâmetro global de threads, não cpuparams_batch. Assim, mudar
somente threads-batch não altera esse campo de entrada do encoder. Os valores 4/4
são configuração solicitada; a implementação completa de common/mtmd/CLIP não
integra o conjunto de fontes locais fixadas desta inspeção. Não se convertem esses valores
em medição de quatro workers efetivos ou de concorrência sustentada no encoder.

A inspeção **sem execução** do ELF libmtmd mostra o argumento inteiro de
clip_image_batch_encode sendo repassado a clip_encode. Este consulta a procedure
ggml_backend_set_n_threads no registro do backend e, se disponível, chama o setter
antes de ggml_backend_sched_graph_compute. É evidência do caminho compilado;
não prova qual registro/procedure foi escolhido no processo já encerrado, nem
que o número efetivo foi observado. Não há correção fundamentada de threads agora.

## Identidade e backend

Os hashes atuais da CLI, libmtmd e fonte CLI coincidem com os pins registrados.
Os ELF inspecionados são x86-64; CLI/libmtmd têm RUNPATH=$ORIGIN e identificação
de compilador GCC 11.4.0. O bundle contém 14 variantes libggml-cpu, e o loader
compilado expõe mecanismo de score/load de backend. Nome de arquivo, string de
compilador e presença de instruções não comprovam equivalência reprodutível entre
fonte e build, flags completas de otimização ou qual variante foi utilizada.

Os cabeçalhos GGUF lidos, somente 355 e 358 bytes, identificam respectivamente
qwen3vl/model/Qwen3Vl 2b Instruct e clip/mmproj/Qwen3Vl 2b Instruct. Não foram lidos
tensores, vocabulário completo nem pesos integrais. Os hashes integrais dos pesos
são pins previamente verificados, não foram recalculados nesta unidade. Metadados
compatíveis não substituem uma nova verificação integral dos bytes dos pesos.

Lease e telemetria preservados não contêm maps, DSO selecionado ou confirmação do
setter/threads do encoder. Stderr bruto foi descartado. Portanto a variante CPU
efetiva permanece desconhecida; não se atribui o timeout a backend genérico,
quantização, compilador, fallback ou número de threads sem essa observação.

## O que significa encoder_start [1,1,3]

O literal da linha 479 imprime n_added, i e n_chunks: **um chunk de mídia adicionado,
índice atual 1 (base zero), três chunks de entrada no total**. Não são três imagens,
três threads, dimensões, tokens ou um contador de progresso interno do encoder.
O início antecede mtmd_batch_encode; o fim é impresso depois do retorno dessa
função. O marcador não localiza trabalho dentro dela.

Os literais de início/fim da CLI coincidem com as regex fullmatch existentes.
Os formatos compilados de decode também são compatíveis, substituindo o tipo
de mídia por image. A verbosidade efetiva é 4, incluindo os eventos do helper
já demonstrados nas capturas v2/v3. Não foi encontrado desvio de prefixo/formato
que explique a ausência do encoder_done no probe atual. Isso não é prova de cada
operação interna não registrada, nem elimina perda de mensagem ainda pendente
no runtime no momento do kill.

| Captura anterior | Encoder concluído reportado | Último estágio observado |
| --- | ---: | --- |
| v2, chamada 1 | 30,076 s | decode completo, resposta concluída |
| v2, chamada 2 | 38,417 s | oitavo lote de decode iniciado |
| v3, chamada 1 | 51,620 s | sétimo lote de decode iniciado |
| Resource probe | indisponível | somente encoder_start [1,1,3] |

O probe atual teve timeout terminal e limpeza confirmados; EOF de ambos os
streams, 18.101 bytes de stderr, sem truncamento de eventos. Não se atribuem os
74,448 s do processo inteiro ao encoder. CPU média de 3,18 núcleos no prefixo de
73,317 s não mede contagem efetiva de threads nem backend; fases de inicialização
e encoder não foram temporizadas separadamente nesse prefixo. A variação das
capturas não comprova sua causa. Não se reabre a hipótese de gramática já refutada.

## Discriminante que pode mudar a correção

Uma futura observação útil, **somente se houver autorização própria**, precisa
identificar a implementação realmente carregada. O loader já contém o formato
loaded CPU backend from; CLIP contém CLIP using CPU backend. Uma projeção fechada
desses eventos poderia guardar somente basename de variante conhecida e seu hash
fixado, confrontados com mapeamento do processo. Maps isolados podem incluir
bibliotecas apenas carregadas/probadas e não demonstram execução de um kernel.
Nenhum caminho arbitrário ou log livre deve ser retido.

Isso distingue seleção de variante genérica de seleção da variante esperada e
pode justificar corrigir o carregamento/build; se a variante esperada já estiver
selecionada, essa hipótese perde suporte. Para provar o setter/valor efetivo seria
necessária observação numérica no ponto de chamada ou uma API verificável; contador
total de threads do processo não basta. Essa instrumentação não foi implementada
e não há proposta de recompilar ou executar um binário nesta unidade. Aumentar
80 s ou variar flags às cegas não responde a essas perguntas.

Os testes existentes já cobrem os quatro formatos nativos e os prefixos de fase.
Não se acrescentou teste que apenas repita regex, nem se repetiu suíte. Foram
feitos checks documentais/JSON, comparação estática de literais, hashes dos três
artefatos pequenos e inspeção de ELF/metadados. Somente estes dois documentos são
novos; nenhuma inferência ou campo visual foi liberado.
