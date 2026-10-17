# Piloto de extração com mídia temporária

Data: 17/10/2026. Parte da [issue #1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1).

## Fonte do ensaio audiovisual

Usar exclusivamente uma cópia da TV Brasil hospedada no Wikimedia Commons:

- [Registro da obra e licença, revisão fixada](https://commons.wikimedia.org/w/index.php?curid=103214103&oldid=1030751044).
- Atribuição: **tvbrasil**, licença [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- Publicação associada: [YouTube, 34w5_poZ2WM](https://www.youtube.com/watch?v=34w5_poZ2WM).
- Arquivo informado: WebM, 25.950.197 bytes, 36,061 s, 1920×1080.
- SHA-1 de referência: `f14859b90f9c27c8356408a507242d2cf44202b8`.

**Fixture de processamento, excluído do treino:** publicação de 2017 e orientação horizontal.
Não muda o recorte aprovado nem resolve a disponibilidade de mídia para toda a base de
Shorts. Não houve aquisição por yt-dlp ou download direto do YouTube neste ensaio.

O script baixa a cópia licenciada do Commons em diretório privado temporário e verifica
bytes e SHA-1 antes da extração. Todas as amostras de imagem e áudio permanecem nessa
sessão. Ao finalizar ou ocorrer exceção, remove o diretório; uma interrupção abrupta da
máquina continua exigindo inspeção de resíduos na retomada.

## Ambiente e reprodução

Python 3.11, dependências em `pyproject.toml`/`uv.lock`, PyTorch 2.8 e torchvision 0.23
exclusivamente CPU. O índice CPU é associado explicitamente a esses pacotes, evitando
dependências de GPU. A decodificação deste fixture usa PyAV, sem exigir os executáveis
FFmpeg/ffprobe; o futuro adaptador yt-dlp ainda precisa validar suas dependências próprias.

```sh
rtk proxy uv sync --locked
rtk proxy .venv/bin/python -m pytest -q tests
rtk proxy env HF_HOME=data/cache/huggingface HF_HUB_DISABLE_XET=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/pilot_licensed_media.py --with-vlm --output data/private/pilot-nova-execucao
```

Usar uma pasta de saída nova. A primeira execução baixa pesos oficiais; downloads não
fazem parte do tempo de extração reportado pela sessão. As revisões dos quatro modelos
estão fixadas no script. Após preparação, cada modelo é carregado de arquivos locais.
Whisper small usa CPU int8; CLIP e MiniLM geram embeddings; SmolVLM2 é um ensaio de
atributos observáveis, com até quatro frames, sem inferir fala a partir de imagens.

Os resultados privados são `features.json` e `run.json`; imagens, vídeo e intermediários
não devem persistir. Transcrições e embeddings também são dados derivados do conteúdo,
portanto ficam privados. O cache dos pesos não é mídia do criativo.

## Resultado medido

O ensaio concluído está em `data/private/pilot-20261017-complete/`, ignorado pelo Git.

| Verificação | Resultado |
| --- | --- |
| Duração de vídeo / áudio decodificado | 36,061 s / 36,037 s |
| Frames amostrados | 6; quatro usados no VLM |
| Fala | 10 segmentos em português; sem legenda fornecida |
| Embeddings | Texto: 384 valores; imagem: 512; todos finitos |
| Tempo da sessão | 43,10 s, incluindo aquisição do fixture e carga/execução dos modelos, sem download inicial dos pesos |
| Pico de memória do processo | 2.711,73 MiB, aproximadamente 2,65 GiB |
| Limpeza real após sucesso | Diretório temporário removido; nenhuma sessão restante |
| Limpeza real após falha | Também confirmada no primeiro ensaio, interrompido por dependência ausente do VLM |

Tempos das etapas: frames 2,95 s; ASR 6,71 s; embedding de texto 0,86 s; CLIP 1,03 s;
VLM 21,70 s. Uma única observação não representa latência média de produção ou orçamento
para milhares de vídeos. O processo registrou um aviso de pacote Opus; o áudio decodificado
teve duração próxima à do vídeo, mas isso não demonstra transcrição correta. Acurácia de
ASR não foi medida com referência humana.

**Atributos do VLM reprovados:** houve JSON legível, mas sem os objetos `value`/`frames`
exigidos. Na inspeção de duas imagens, alegações de produto/closeup/demonstração não
tinham evidência fornecida. `quality_review.json` conserva essa revisão e o hash do
resultado original, sem sobrescrevê-lo. O validador posterior classifica a resposta como
`invalid_schema`; novos resultados precisam de revisão de percepção mesmo quando passam
pelo esquema. Não usar esses atributos reprovados no treino.

O ensaio demonstra aquisição licenciada, extração e descarte operacional. Ainda não
resolve a obtenção de mídia para a coorte YouTube Shorts nem valida desempenho preditivo.

## Verificações

Há seis casos de teste desse piloto, sem chamadas de rede: limpeza de mídia completa e
parcial após sucesso/falhas, preservação de um artefato anterior quando uma gravação é
inválida e rejeição de atributos VLM sem esquema/evidência temporal compatíveis. Somados
aos quatro testes do coletor por canais, são dez casos. O teste real dos modelos é
registrado à parte; passar os testes de contrato não demonstra qualidade de percepção
nem de predição. A etapa de atributos observáveis do VLM continua pendente de correção.

## Referências técnicas

- [Channels: list](https://developers.google.com/youtube/data/reference/rest/v3/channels/list),
  [playlistItems: list](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
  e [videos: list](https://developers.google.com/youtube/data/reference/rest/v3/videos/list).
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
  [SmolVLM2](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct),
  [CLIP](https://huggingface.co/openai/clip-vit-base-patch32) e
  [MiniLM multilíngue](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).
