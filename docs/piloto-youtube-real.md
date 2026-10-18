# Piloto temporário com três vídeos reais do YouTube

Execução em 17/10/2026, vinculada à [issue #1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1).

Este relatório preserva o primeiro ensaio com SmolVLM2. A [correção posterior](correcao-extratores.md) usa Qwen3-VL GGUF local e registra a conferência das três transcrições; close-up e aplicação continuam bloqueados. O comando abaixo executa o backend atual, não reproduz os resultados históricos do SmolVLM2.

## O que foi validado

O fluxo API → três referências públicas → yt-dlp → extração local → atributos privados →
remoção da mídia foi executado com sucesso nas três referências. O teste anterior no
Commons não demonstrava acesso ao YouTube; este teste demonstra acesso técnico aos três
candidatos escolhidos neste ambiente e nesta execução. Não assegura acesso futuro a
qualquer vídeo, condições de uso para toda a base ou qualidade preditiva.

Os candidatos vieram da sondagem da API, com idade de 30–37 dias na observação original.
Foram escolhidos dois exemplos de beleza com alto alcance e um de moda para cobrir os
dois setores. A seleção por alcance é deliberada para o ensaio técnico, não uma amostra
de treino/teste. IDs, links, métricas exatas e resultados ficam em arquivos locais ignorados.
Um frame de cada vídeo foi inspecionado: maquiagem nos dois primeiros e composição de
looks no terceiro. Isso não equivale à revisão integral do conteúdo, idioma ou condições
de uso. O manifesto continua sem registros elegíveis de treino.

## Ambiente e execução

- Python 3.11 e dependências fixadas em `uv.lock`.
- yt-dlp 2026.08.19, yt-dlp-ejs 0.8.0 e Node 22.22.1.
- FFmpeg 7.0.2 fornecido por imageio-ffmpeg 0.6.0; sem instalação global.
- Extração com PyAV, Whisper small, MiniLM, CLIP e SmolVLM2, nas revisões fixadas.
- Modelos previamente baixados; carregamento local, CPU e quatro threads.
- Sem chave da API no downloader, cookies do navegador, login ou rotação de proxies.

O adaptador aceita até três IDs canônicos comprovados no arquivo de candidatos, limita
downloads a vídeos de até 60 s, resolução de até 720 px de altura, 32 MiB por stream e
64 MiB no arquivo final; timeout de download de 180 s e tentativas finitas. Os três
arquivos obtidos mediram 360×640. As durações do contêiner foram 19,248 s, 7,888 s e
12,168 s, distintas dos segundos inteiros declarados pela API.

Entradas e saídas do comando são restritas a `data/private`. A sessão temporária contém
vídeo, frames e intermediários; apenas atributos e relatórios são persistidos. O grupo do
downloader é encerrado em timeout/cancelamento antes da remoção da pasta. Uma queda da
máquina ainda exige conferir resíduos na retomada. O comando atualizado desabilita
também diretórios de plugins e obtenção remota de componentes; EJS já está instalado.

```sh
rtk proxy uv sync --locked
rtk proxy env HF_HOME=data/cache/huggingface HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false OPENBLAS_NUM_THREADS=4 .venv/bin/python -m scripts.pilot_youtube_media --candidates data/private/youtube-pilot-candidates.json --output data/private/youtube-real-pilot-novo --with-vlm
```

Usar uma pasta de saída nova. O arquivo privado de candidatos usa os namespaces do
coletor por canais. Não recebe URLs arbitrárias, tags ou campos de auditoria como
entradas do extrator. O modo offline acima se refere aos modelos Hugging Face; yt-dlp
continua usando rede. A preparação dos pesos é descrita no
[piloto inicial](piloto-extracao-temporaria.md).

## Resultados observados

| Candidato | Alcance observado na coleta | Tempo da sessão | Frames | Segmentos ASR | VLM |
| --- | --- | ---: | ---: | ---: | --- |
| Beleza 1 | Aproximadamente 2,28 milhões de views | 65,99 s | 6 | 6 | Esquema reprovado |
| Beleza 2 | Aproximadamente 1,20 milhão de views | 49,82 s | 6 | 5 | Esquema reprovado |
| Moda | Aproximadamente 13,7 mil views | 45,15 s | 6 | 4 | Esquema reprovado |

São 160,96 s somados de sessões, incluindo aquisição e extração, sem download inicial
dos pesos. Esse número não inclui todo o tempo de preparação do ambiente. O pico
acumulado do processo Python chegou a 2.761,07 MiB, aproximadamente 2,70 GiB. É uma marca
máxima do processo, herdada pelos vídeos seguintes, e exclui os subprocessos do downloader;
não comparar os três valores de memória como consumo independente por vídeo.

Cada vídeo gerou embedding de texto com 384 valores e de imagem com 512, todos finitos,
além de propriedades, medidas acústicas, transcrição e tempos. ASR é saída do modelo,
não anotação humana; os quinze segmentos não demonstram acurácia da fala. Houve um aviso
Opus no primeiro vídeo, preservado no relatório. Ausência de fala em outras entradas será
registrada explicitamente, com embedding de texto ausente, sem inventar texto.

**Os atributos VLM dos três vídeos foram reprovados por `invalid_schema`.** As respostas
não respeitaram os objetos `value`/`frames`; não devem entrar na matriz de treino. JSON
legível não comprova percepção correta. A qualidade do ASR também não foi medida por
referência humana. O modelo preditivo ainda não foi treinado.

A remoção do diretório temporário foi confirmada nas três sessões e restaram **zero
sessões de mídia**. As evidências estão em `data/private/youtube-real-pilot-20261017/`:
`batch.json`, cada `run.json`/`features.json` e `quality_review.json`, com hashes dos
resultados originais. O manifesto privado foi atualizado com origem temporária, hash,
duração e dimensões, sem reter caminho para uma mídia que já foi removida.

## Foco em viralidade

O foco confirmado é priorizar criativos com potencial de viralização. A operacionalização
atual continua sendo prever e ordenar views observadas no horizonte aprovado; não foi
aprovado um limiar binário universal de "viral". Hashtag, nome do canal ou um número alto
isolado não estabelecem esse rótulo.

A base experimental deve conter baixo, médio e alto alcance, coletados por critério
de setor/formato/idade e com canais reservados. Treinar somente com sucessos cria uma
base condicionada ao resultado e impede avaliar bem a distinção pretendida. O piloto
por alcance fica separado dessa base e da escolha de hiperparâmetros.

Uma extensão possível, ainda não definida, é avaliar precisão/recall dos casos acima
de um percentil por setor, com limiar calculado somente no treino e congelado antes do
teste. Isso não exige trocar imediatamente o regressor por outro modelo. Não confundir
alto alcance observado com retorno garantido de patrocínio ou viralidade causal do criativo.

## Verificações e pendências

Quatorze testes locais passam: os dez anteriores, validação de IDs/caminhos privados,
continuidade e limpeza de um lote com falha e encerramento do grupo em timeout. Não
fazem rede nem avaliam qualidade preditiva. Ruff e revisão estática também passaram.

O acesso técnico deixou de ser uma hipótese para esses três casos. Continuam pendentes:
curadoria completa e condições da fonte para uso experimental em escala, correção ou
decisão sobre os atributos VLM, definição da amostra de treino/validação/teste e os
experimentos A → B → C. A issue #1 permanece aberta.

Referências: [yt-dlp e dependências](https://github.com/yt-dlp/yt-dlp#dependencies),
[políticas de conteúdo da API](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content).
O êxito técnico e o descarte dos arquivos não demonstram conformidade com essas condições.
