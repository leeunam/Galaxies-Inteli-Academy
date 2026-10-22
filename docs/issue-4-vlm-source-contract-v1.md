# Contrato visual das fontes fixadas

Revisão offline de 22/10/2026, sobre a base `277804223eb6121dbeb541c0663af89ccf334eac`.
**Não foi demonstrado defeito de representação para o projector e os parâmetros
congelados; nenhuma correção de produto é proposta.** A inspeção fecha ligações
que ficaram fora da [prova anterior de pixels](issue-4-vlm-representacao-offline-v1.md),
sem repetir aquela prova ou executar loader, graph, encoder ou modelo.

O [recibo público](evidence/issue-4-vlm-source-contract-v1.json) contém os hashes,
tamanhos e URLs oficiais das fontes realmente consultadas, todas na revisão
`797de63b2`. A CLI de controle conserva SHA-256
`72c9163dcc2e0e491c74b6b0ee15406765e6e4c1b868ea1d3e73c2a87c9369d3`.
Os textos foram obtidos separadamente pelo coordenador e apenas lidos nesta revisão.

| Ligação conferida | Resultado e fonte |
|---|---|
| PNG → bitmap | O chamador solicita três canais e copia `nx×ny×3` bytes antes de liberar o buffer, sem permutação nesse trecho. [helper:404–408](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/mtmd-helper.cpp#L404), [bitmap:182–187](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/mtmd.cpp#L182). |
| Dispatch e normalização | Qwen3VL seleciona o preprocessor dinâmico, ligado por referência aos hparams carregados. Mean/std vêm do GGUF; não se presumem constantes CLIP. [dispatch:741–750](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/mtmd.cpp#L741), [hparams:31–33](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/mtmd-image.h#L31), [leitura:1441–1452](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/clip.cpp#L1441). |
| Ordem RGB | O buffer intercalado vira planos R/G/B preservando `(x,y)`. [clip.cpp:4882–4901](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/clip.cpp#L4882). |
| Imagem estática | Duas convoluções temporais recebem o mesmo input e seus resultados são somados; o bias Qwen3VL é adicionado uma vez. Isso é algebricamente compatível com repetir a imagem nas duas fatias temporais. [qwen2vl.cpp:12–16](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/models/qwen2vl.cpp#L12), [qwen3vl.cpp:33–35](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/models/qwen3vl.cpp#L33). |
| Ordem espacial e merger | O reshape/permutation agrupa quatro patches por bloco 2×2, com `dx` antes de `dy`, compatível com o loop de posições. A projeção final reduz quatro patches por token. Deepstack concatena características, sem aumentar a contagem de tokens. [qwen3vl.cpp:20–30 e 143–180](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/models/qwen3vl.cpp#L20), [posições:5163–5182](https://github.com/ggml-org/llama.cpp/blob/797de63b2/tools/mtmd/clip.cpp#L5163). |

Uma leitura limitada do projector confirmou `qwen3vl_merger`, **patch 16,
merge 2 e mean/std `[0.5, 0.5, 0.5]`**. A normalização efetiva é
`(RGB/255 − 0.5)/0.5`; o padding preto corresponde a −1 por canal.
A geometria já preservada continua 360×640 → canvas 800×1376, conteúdo
775×1376 e offset (12,0). A grade de patches é **50×86 = 4300**; o merger
produz **25×43 = 1075** posições, percorridas pelo decoder por `i%25` e `i/25`.
Essa distinção esclarece a contagem anterior e posterior ao merge, sem medir
tempo, memória ou explicar a causa dos timeouts.

O leitor privado percorreu somente metadados: **1031 bytes lidos + 149 pulados,
término no offset 1180**, antes das informações de tensores. Usou arquivo sem
buffering, teto de 64 KiB e whitelist; o stat permaneceu estável antes/depois.
A identidade do projector vem do manifesto existente: o hash integral não foi
recalculado, pois isso leria o payload. A primeira tentativa recusou um array
desconhecido no offset 370 e seu recibo foi preservado. Após teste discriminante,
o leitor passou a pular conteúdos de pequenos arrays de strings, com teto
cumulativo de 4 KiB; vocabulário, estruturas grandes e acesso a tensores
continuaram recusados.

A revisão final desse leitor passou **15 testes com cabeçalhos inventados em
0,001 s**, incluindo streams que falham se valores pulados ou informações de
tensores forem lidos. Os hashes do leitor, testes e dois recibos privados estão
no JSON público. Essa contagem não soma rodadas sobrepostas; nenhum teste foi
repetido para produzir este documento e nenhum harness foi adicionado ao produto.

A hipótese específica de que o contrato congelado seleciona outro preprocessor,
troca R/B no trecho inspecionado ou usa defaults incompatíveis de normalização
não se sustenta nessas fontes e metadados. Isso não resolve a hipótese perceptiva
de informação nativa versus cadeia JPEG/redução/reamostragem: os resultados
anteriores continuam insuficientes para esse contraste, e o falso positivo
anterior permanece registrado.

O próximo bloqueio real é obter evidência perceptiva válida e execução
tecnicamente completa dentro de um protocolo específico. Coerência estática
não substitui esse resultado nem libera atributos, B/C ou auditoria cega.
Permanecem fora desta prova o decoder interno STB, a paridade com configuração
HF, a conversão/valores dos tensores e a equivalência binária e numérica do
backend. Não houve pixels reais, holdout, inferência ou mudança de gates;
esta entrega não autoriza reabrir filas, repetir chamadas ou ampliar prazos.
