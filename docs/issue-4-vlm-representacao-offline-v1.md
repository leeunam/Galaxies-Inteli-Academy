# Representação visual: prova parcial com pixels sintéticos

**Nenhum defeito de pixels foi demonstrado no trecho exercitado.** Sete casos inteiramente gerados passaram nos 19 invariantes definidos antes da execução. Quatro controles negativos em Python rejeitaram alterações intencionais. Isso sustenta a implementação local de acesso RGB, resize e padding dessas funções; não certifica o caminho completo até os tokens nem explica o falso positivo ou o timeout do VLM. Não há correção de produto justificada por este ensaio.

A unidade contém apenas um [harness manual](verification/vlm_pixel_contract.py) e seu [recibo sintético](evidence/issue-4-vlm-representacao-pixels-sinteticos-v1.json). Não muda fontes seladas, flags, modelos, gates, filas ou orçamento. Base do trabalho: `d4c8bd4b00918e7fbddc8fbdd6de3bb0f25635eb`. Nenhum quadro real, label ou holdout foi aberto. Não houve modelo, tensor de modelo, encoder, inferência, aquisição, rede ou instalação.

## Fonte exercitada e fronteira

O harness aceita somente os três arquivos fixados no preflight do commit C++ `797de63b2`, com estes hashes completos:

| Fonte | SHA-256 |
|---|---|
| `mtmd-image.cpp` | `2552b9200162160ccb29122371601586c8cd29e5c07f075f0c156f1c47ac38e6` |
| `clip-impl.h` | `bdaabef3cfce02215d27c7929af398fa3d062041d83216f75a0441d9bd9931e0` |
| `clip-model.h` | `32c0b4e18e6ad76be843c524a012c1ee0bd07ff78286b2f9bdeee7a8d119f51f` |

Foram extraídos **byte a byte**, sem edição interna, os blocos `img_tool`, `clip_image_u8`, `resize_algo` e `pad_style`. Seus hashes individuais estão no recibo. A execução chamou o resize real, incluindo `resize_pillow`, `fill`, `composite` e os métodos de tamanho/acesso/cópia RGB de `clip_image_u8`. Não substituiu resize, fill ou leitura/escrita de pixels por stubs. O cálculo `calc_size_preserved_ratio` foi compilado junto com a struct, mas **não foi chamado**; os targets da prova foram explícitos, incluindo a geometria já comprovada anteriormente.

O suporte declarado no harness é uma struct mínima `clip_image_size`, com largura, altura e igualdade por valor; o macro `GGML_ASSERT` usa `assert`. Cabeçalhos são somente stdlib C++: algorithm, array, cassert, cmath, cstdint, iostream, stdexcept, string e vector. O driver gera pixels por coordenada; não carrega arquivos de imagem ou bibliotecas de modelo. Foram usados o compilador previamente fixado por SHA-256 `e6718f7e0c7d057c3ff77b550c603da9bc4030e3ede3c053705acce1293dbe4d` e flags `-std=c++17 -O0 -Wall -Wextra -pedantic`.

A fronteira não exercitada inclui loader PNG nativo, seleção do preprocessor por dispatch, valores de normalização do modelo, montagem de tensores, ordem/reshape dos patches, merger e encoder. As fontes fixadas disponíveis contêm helpers e declarações, mas não fecham o dispatch/merger Qwen3VL. O cache adicional contém somente `mtmd-cli.cpp`; essa limitação não foi preenchida com suposições ou download. A leitura estática mostra RGB intercalado e normalização canal a canal em `clip-impl.h` (from_u8/normalize), mas esses métodos float não foram executados nesta prova.

## Invariantes e resultado

| Caso gerado | Verificação independente |
|---|---|
| Grade RGB assimétrica, 7×5 sem resize | Identidade dos bytes, ordem RGB e stride das linhas |
| RGB constante com canais distintos, 1×1 → 7×11 | Cor preservada em todos os pixels e tamanho exato |
| RGB constante, 360×640 → 800×1376 | Conteúdo 775×1376 no offset 12,0; 12 colunas pretas à esquerda e 13 à direita |
| Quadrado constante, 5×5 → 9×12 | Conteúdo 9×9; padding de uma linha acima e duas abaixo |
| Rampa vermelha horizontal e verde vertical | Eixos preservados, monotonicidade e ausência de mistura de canais |
| Impulso vermelho com verde constante | Suporte local do bicúbico e azul zero |
| Checker vermelho reduzido, 64×48 → 16×12 | Valores intermediários na redução e ausência de vazamento para verde/azul |

Os 19 checks passaram. A troca R/G e três alterações de um byte nos resultados de identidade, padding e impulso foram rejeitadas pelos mesmos invariantes, em controles negativos separados, sem recompilar ou reexecutar o C++.

Houve **uma compilação** (1,1214 s) e **uma execução** (0,2334 s), ambas exit 0 e stderr vazio. São tempos desta verificação pequena, não benchmark ou estimativa de desempenho do VLM. Todos os processos de teste foram recolhidos pelo harness. O byte count total da saída sintética foi 3.306.895, incluindo os cabeçalhos de casos.

Pillow 12.3.0 foi uma comparação exploratória: zero bytes diferentes nos sete casos, usando os mesmos targets, conteúdo e offsets declarados. A igualdade não era requisito dos invariantes nem confere autoridade sobre o modelo. A fonte C++ informa filtro bicúbico com parâmetro −0,5, duas passagens e coeficientes inteiros de 22 bits; bibliotecas com outras convenções podem divergir legitimamente. Este resultado não valida tamanhos, kernels ou rotas que não foram exercitados.

## Informação e custo que a geometria permite afirmar

A cadeia derivada preserva uma região de 186×330 = **61.380 amostras RGB**, depois reamostrada a 360×640. A fonte nativa possui 230.400 amostras, aproximadamente 3,754 vezes essa quantidade; isso não é uma razão de qualidade ou de entropia. Ampliar o derivado não recupera detalhes eliminados.

Uma demonstração separada, inteiramente artificial, usou duas imagens cinza 360×640 que diferem por **um nível de vermelho em um único pixel**. Seus thumbnails de 512 diferiram, mas o JPEG produzido pela receita padrão do Pillow ficou idêntico, assim como a imagem final 360×640 após thumbnail 186×330 e LANCZOS. É uma testemunha concreta de não invertibilidade da cadeia. Não prova perda de uma diferença perceptivamente relevante, não isola o efeito de JPEG no par real e não demonstra que essa perda causou a resposta incorreta. Os hashes por estágio e a versão do Pillow estão no recibo; a receita é uma réplica em memória, sem executar o decoder de vídeo.

Para os dois braços do contraste, a geometria fixada continua sendo canvas **800×1376**, conteúdo **775×1376**, offset **12,0**, grade **25×43 = 1075**. A aritmética float/ceil já era conhecida e não é reapresentada como bug. A conta idealizada em double que fornece 1032 continua inadequada para essa fonte.

O canvas contém 1.100.800 pixels, 4,778 vezes a quantidade da fonte 360×640. Desses pixels, 34.400 (3,125%) são padding preto. Na grade geométrica de células 32×32, 989 células ficam inteiramente na região redimensionada e 86 interceptam as bordas; **nenhuma célula é exclusivamente padding**. Isso descreve sobreposição geométrica, não relevância semântica ou pesos de atenção. Não justifica eliminar células ou reduzir o gate de 1075 tokens observados.

Dneg e Nneg chegam com as mesmas dimensões/grade esperadas apesar da diferença de informação de origem. Essa observação não mede FLOPs, tempo de encoder ou throughput. O timeout recente, sem encoder_done nem resposta, continua uma falha técnica com causa não estabelecida por este ensaio. A apuração de backend, threads e recursos é uma frente separada.

## Reprodução delimitada

Use o Python já existente com Pillow e o compilador cujo hash consta acima. `PREFLIGHT_SOURCES` designa somente a pasta dos três arquivos fixados; `PROOF_WORK` deve ser um diretório novo, destinado apenas a esta prova sintética. Não aponte o trabalho para filas antigas.

```sh
rtk proxy "$PYTHON" -B docs/verification/vlm_pixel_contract.py --sources "$PREFLIGHT_SOURCES" --work "$PROOF_WORK"
rtk proxy "$RUFF" check --no-cache docs/verification/vlm_pixel_contract.py
rtk proxy "$RUFF" format --check --no-cache docs/verification/vlm_pixel_contract.py
rtk git diff --check
```

Fonte desconhecida, compilador diferente ou destino já existente são recusados antes da compilação. O diretório de prova retém C++ montado, binário, stdout/stderr sintéticos e receipt, inclusive quando ocorre falha. Os timeouts são 20 s para compilação e 10 s para execução, com limpeza do grupo. Esta verificação manual não acrescenta dependência de compilador/cache privado à suíte pytest padrão e não contém caminho para executar pesos.

O recibo público acrescenta ao receipt bruto a contagem de checks, controles negativos, hashes das três receitas Python lidas e a aritmética de área/células. Esses acréscimos são projeções dos artefatos sintéticos; não são nova execução C++. O hash do harness executado é `af8c350df3be348616431c148dbb52a4a181caf24c4a415bba5cd002e738a5cb`.

Nenhuma mudança operacional ou nova chamada é proposta por esta evidência. A lacuna concreta restante é conferir, por fonte/metadados fixados, o loader/dispatch e a ordem dos patches/merger correspondentes ao binário e modelo. Se isso confirmar o contrato, a hipótese perceptiva continua exigindo uma comparação própria autorizada; os resultados atuais não a resolvem, não liberam atributos/B/C e não reabrem filas consumidas.
