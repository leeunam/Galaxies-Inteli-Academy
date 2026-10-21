# Demonstração de três criativos — inventário de mídia disponível

**Resultado: zero criativos reais distintos confirmados como disponíveis nos
locais autorizados inspecionados. Faltam três arquivos reais atuais para o trio.**
O único vídeo da demonstração M1 anterior foi descartado. Seus cinco cadastros
não constituem cinco criativos; as três URLs do piloto também não são três
arquivos locais disponíveis.

Levantamento de 20/10/2026, somente leitura na árvore principal. O
[recibo estruturado](evidence/issue-5-inventario-midias-demo-20261020.json)
registra horários de São Paulo, commit observado, contagens, escopo e hashes
apenas de fontes/documentos públicos consultados. A outra frente pode escrever
na árvore principal; este é um instantâneo, sem promessa de atomicidade.
Relatório, recibo e inventário detalhado novos foram escritos exclusivamente no
clone isolado, em branch separada. Os três arquivos entregues pela #7 e os
comprovantes históricos não foram alterados.

Não foram abertos bytes de vídeo/áudio/imagem, features, transcrições, rótulos ou
conteúdos do holdout. Foram lidos metadados de filesystem, cadastros de fixtures,
recibos de demos já reveladas e documentação/código. Nenhum extrator, decoder,
modelo, teste, instalação, geração de mídia, download ou API foi executado.

## Escopo e contagens atuais

Localizadores privados são representados abaixo por parâmetros; seus valores
ficam apenas no recibo novo ignorado do clone. Parâmetros de fixtures/índices
identificam o local consultado, sem publicar identidades ou URLs das peças.

A busca foi limitada à árvore do projeto e aos três clones de projeto já
identificados nos relatórios. Excluiu `.git`, ambientes `.venv`, diretórios de
agentes/credenciais e diretórios pessoais alheios. Não seguiu symlinks de
diretórios; na principal, os 209 encontrados pertencem a caches de pacotes ou
aliases/canários de testes. Não foi realizada busca no restante da máquina.

Foram considerados MP4/MOV/WebM e extensões comuns de vídeo/áudio, além de
`.media` e `.part` usadas em cópias/transferências intermediárias. Nenhum arquivo
de mídia ficou sem classificação pelos metadados dos locais observados. Isso
não equivale a uma inspeção de MIME ou conteúdo em arquivos arbitrários.

| Material encontrado | Quantidade | Local verificado | Por que não fornece o trio real |
| --- | ---: | --- | --- |
| Vídeo/áudio real atual identificado | **0** | `${DEFAULT_UPLOADS}`, raízes de dados/caches/artefatos e diretórios de demonstração do projeto | Não há arquivo real atual para cadastrar/processar |
| MP4 de testes na principal | 109 | `${MAIN_VIDEO_FIXTURES}` e `${NIM_VIDEO_FIXTURES}` | Fixtures; 107 arquivos de 1.051 bytes e dois de sete bytes em casos de falha |
| WAV de testes de dependência | 44 | `${SCIPY_AUDIO_COPY_A}` e `${SCIPY_AUDIO_COPY_B}` | 22 nomes de testes em duas cópias de pacote; são áudio de teste, não criativos de campanha com vídeo |
| Folhas PNG VLM preservadas | 8 | `${PROTECTED_VLM_SHEETS}` | Frames de referências históricas, sem vídeo/áudio completo |
| Crops dessas folhas | 32 hashes no recibo anterior | Provas VLM preservadas | São recortes derivados; nenhum arquivo individual de crop foi encontrado nem regenerado |
| Outros arquivos de imagem na principal | 27 | Dois gráficos de diagnóstico, 20 imagens de fixtures e cinco recursos de pacotes | Não são vídeos reais de entrada |
| MP4 no clone `${REPRO_CLONE}` | 7 | Temporários dos testes públicos da #7 | Todos fixtures de 1.051 bytes |
| MP4 no clone `${NATIVE_CLONE}` | 294 | Diretórios privados `pytest-*` | 287 fixtures de 1.051 bytes e sete arquivos de falha de sete bytes |
| Mídia no clone `${NIM_CLONE}` | 0 | Raízes de mídia/dados/cache do clone | Apenas código e recibos de simulação |

A raiz `${DEFAULT_UPLOADS}` e o cadastro operacional padrão
`${DEFAULT_REGISTRY}` estão ausentes. Os **109 cadastros
persistidos na principal são de testes**: 501 linhas registradas, com um único
SHA de mídia e propriedades declaradas de 64×96, 0,2 s e 1.051 bytes.
O [gerador público](../tests/conftest.py) cria esse controle sem áudio.
A conferência leu o digest já registrado; não reabriu os MP4 para calcular
hashes ou conferir se seus bytes ainda coincidem com o cadastro.

As contagens são de arquivos físicos encontrados por caminho, não de peças
criativas independentes. Os aliases de pytest não foram contados outra vez.
Os sete MP4 da #7 e os 294 do clone nativo não se somam como exemplos reais.

## URLs, fontes históricas e procedência

| Fonte | O que existe hoje | Origem/permissão já documentada | Limite comprovado |
| --- | --- | --- | --- |
| Piloto YouTube de três referências | Índice com três IDs/URLs e recibos; sem vídeo/áudio | Autorização operacional histórica do piloto; licença registrada como `youtube`, idioma declarado `pt-BR` | 3/3 sessões concluídas e mídia removida; não há três arquivos atuais |
| Índice de um candidato | Uma referência, subconjunto exato das três | Mesmo contexto do piloto | Não acrescenta outra fonte |
| Demo M1 real | `${M1_SOURCE_RECEIPT}` e `${M1_PARITY_RECEIPT}`; fonte pertence às mesmas três referências | `operator_authorized=true`, `platform_approval_verified=false` | Um criativo independente, repetido em 1/2/5 cadastros; fonte e cópias removidas |
| Fixture TV Brasil/Commons | URL/licença e recibos | CC BY 3.0 e atribuição documentadas | Mídia removida; vídeo histórico horizontal 1920×1080/2017, incompatível com o cadastro vertical atual |
| Referências do índice M1 | Recibo de índice descritivo, caminhos e evidências derivadas | Recibo anterior confirma 124 referências exclusivamente de treino | Embeddings/URLs/recibos não fornecem o arquivo de vídeo atual nem substituem entrada registrada |

Os índices do piloto são `${PILOT_INDEX_THREE}` e
`${PILOT_INDEX_ONE}`. Seus campos antigos de curadoria
registram `sector_status=unverified` e `format_status=unverified`; não foram
atualizados aqui. O [relato audiovisual do piloto](piloto-youtube-real.md)
descreve **dois vídeos de beleza e um de moda**. Mesmo com os arquivos de volta,
esse conjunto não formaria três candidatos do mesmo setor no contrato atual.
Não substituir a curadoria pelo título ou por uma nova inferência não executada.

O índice original declara idioma, mas isso não demonstra aprovação da triagem
ASR atual. A [revisão assistida anterior](validacao-transcricoes.md) confirmou
hipóteses de fala/vocal/canto; ela não é uma nova extração nem garante passagem
dos gates na ausência dos bytes. Não foram lidas as referências textuais privadas.

O recibo da demo M1 registra `outside_frozen_cohort=true`, sustentando exclusão
da **coorte original de 200** naquele ensaio. O relatório não transfere essa
flag automaticamente para a expansão de 300. A pertença atual das três URLs a
treino/validação/teste não foi consultada nem presumida; nenhuma tabela mista de
features/rótulos ou assignment do holdout foi aberta.

As folhas VLM são material da fila de desenvolvimento já revelada, descrita
como treino nos [resultados do adendo](issue-4-vlm-produto-v9-adendo-limitado-resultados.md).
Não constituem uma amostra nova ou vídeos de demonstração. Nenhuma folha foi
aberta visualmente neste inventário.

O recibo `${TRAIN_INDEX_RECEIPT}`
registra 124 embeddings elegíveis, abertura histórica de 248 pares features/run
de treino e zero abertura de evidência de outras partições. Esse registro foi
lido; o índice não foi carregado e os 248 arquivos não foram reabertos aqui.
O código do índice usa treino para referências descritivas, não autoriza abrir
holdout ou tratar uma referência de treino como demonstração independente.

## Controles gerados e provas anteriores

O recibo de produção em
`${GENERATED_DEMO_RECEIPT}`
identifica três controles `locally_generated_synthetic`, com extração de
produção histórica, `real_media_demo=false` e `scratch_cleaned=true`:

| Controle histórico | Estado registrado | Motivo da previsão indisponível |
| --- | --- | --- |
| Vídeo sem áudio | `no_audio_stream` | `unsupported_text_status` |
| Vídeo com silêncio | `no_speech_detected_by_asr` | `unsupported_text_status` |
| Vídeo com fala portuguesa sintetizada | `extracted` | `language_inconclusive` |

Os arquivos gerados, áudio, cadastro e temporários dessa prova foram removidos,
conforme o [relatório da integração](issue-5-integracao-na-arvore-principal.md).
Não houve nova tentativa para melhorar o idioma ou fabricar previsão positiva.
Já as provas com worker de teste usam features/SHAP/comparáveis inventados e
não demonstram percepção de um vídeo real. Paridade de serviço com fixture e
extração real de um controle são evidências distintas; nenhuma fornece três
mídias reais atuais.

O [registro da demo M1](issue-3-servico-m1.md) demonstra uma execução positiva
histórica com um único vídeo real e preserva seus limites. Ela não deve ser
contada novamente como arquivo ainda disponível nem multiplicada pelo número
de IDs. A mesma fonte aparece nos índices antigos, evitando dupla contagem.

## O que falta para uma demonstração positiva atual

| Requisito | Estado deste levantamento |
| --- | --- |
| Três peças reais distintas e arquivos completos presentes | **Faltam três arquivos** nos locais autorizados inspecionados |
| Procedência e autorização de uso de cada arquivo | Há registros históricos de fontes; não há recibo de três arquivos atuais disponíveis. Licença `youtube` não prova licença aberta ou aprovação de plataforma |
| Mesma campanha, mesmo setor, objetivo `divulgacao`, brief e IDs registrados | Não há cadastro operacional atual; o trio histórico mistura setores |
| Entrada técnica atual | MP4/MOV/WebM local regular, sem symlink, até 100 MiB e 60 s, um stream de vídeo, vertical com largura ≤1080 e altura ≤1920; não foi feita nova validação de arquivo |
| Fala suportada e idioma sob a política congelada | M1/A200 aceita somente `text_status=extracted`; ausência de áudio/fala não tem suporte. Nenhum arquivo real atual teve passagem confirmada |
| Previsão disponível nos três candidatos | Não medida aqui; sem todas as previsões, ranking comparativo fica indisponível |
| Explicação real validada/aderência | Continua pendente e é bloqueio separado da disponibilidade de mídia; obter arquivos não libera envio NIM |

A triagem em [language_audit.py](../scripts/language_audit.py) exige português
sem forçar idioma, probabilidade ≥0,85, ao menos cinco palavras e dois segundos
nos segmentos utilizáveis. Estes precisam ter texto não vazio, tempos válidos,
`avg_logprob ≥ -1` e `no_speech_prob < 0,6`. A flag de português detectado ainda
pede revisão de localidade; não certifica dialeto brasileiro. Declaração `pt-BR`,
título, brief ou transcrição manual antiga não substituem essa triagem.

O [serviço M1](../scripts/m1_service.py) também verifica compatibilidade do
bundle/extratores e finitude/ordem dos quantis. O cadastro confere os bytes de
novo na análise. Três IDs únicos satisfazem parte do contrato, mas três cópias
da mesma peça não satisfazem a demonstração de três criativos distintos.
Uma nova aquisição de uma URL também não garante os bytes do arquivo descartado.

A entrada concreta que o usuário precisa disponibilizar são **três arquivos
completos de três peças diferentes**, de um mesmo setor (moda ou beleza),
próprios/licenciados ou já autorizados para esse ensaio. Precisam cumprir os
limites técnicos acima e ter fala portuguesa audível suficiente para a triagem
congelada; essa passagem será verificada, não presumida pela declaração de
idioma. Acompanhar cada arquivo com sua procedência e indicação de uso fora da
avaliação reservada, além de uma campanha/brief comuns. URL, folha PNG, ID de
cadastro repetido ou transcrição isolada não preenchem a falta do arquivo.

Com esses materiais presentes, o trabalho local seguinte pode:

1. Conferir procedência e separação da avaliação por registros permitidos,
   distinguir as três peças e validar/cadastrar os arquivos na raiz configurada.
2. Executar o percurso já existente de ASR/MiniLM/M1 offline por Python e pelo
   cliente MCP/StateGraph, sem download nem inferência externa, e comparar as
   respostas. Manter os gates de idioma e suporte de fala; uma falha produz
   indisponibilidade explícita, sem forçar idioma ou inserir texto manual.
3. Se houver três previsões disponíveis, conferir ranking, faixa e evidências
   locais nativas (SHAP e referências só de treino). O seletor externo continua
   ausente e a aderência não avaliada; uma demo local não libera NIM.

Essas etapas descrevem o uso possível dos arquivos que faltam. Nenhuma delas,
reacquisição ou processamento foi executada neste inventário. A pendência é de
materiais concretos e verificação dos gates, sem pedido de aprovação humana
genérica para a autorização operacional já registrada.

## Evidência e limites da conclusão

O inventário detalhado, sem bytes de mídia, fica em
`${INVENTORY_RECEIPTS}` do clone. As fontes/documentos públicos
estão identificados no JSON público por caminhos relativos; localizadores
privados e comandos completos ficam somente no recibo novo ignorado;
nenhuma URL/ID privado, transcrição, vetor ou contagem de views foi copiado para
este relatório. A descoberta bruta e arquivos mistos de coorte foram apenas
localizados por metadados, sem abrir conteúdos que possam incluir o holdout.

Zero arquivos reais atuais confirmados não é uma medição de rejeição por ASR,
nem afirmação de que todos os vídeos das URLs falhariam. A causa imediata é a
**ausência dos arquivos reais**, com condições adicionais de setor, procedência,
idioma e validação ainda não satisfeitas para um trio atual. Nenhuma issue,
resultado científico ou demonstração positiva foi declarada concluída.
