# Retomada da base — auditoria de 18/10/2026

Atualização posterior: a [coleta direta e revisão visual dos setores](issue-1-coleta-direta-e-setores.md)
foram executadas por instrução expressa do aluno. Dezessete novos downloads foram
concluídos; há hashes/propriedades nos vinte e classificação nova nos dezesseis,
com dois casos de inclusão a revisar. As ausências numéricas abaixo descrevem o
checkpoint anterior, preservado para auditoria; não são o estado atual.

Objetivo solicitado: resolver a base elegível da #1 para servir o baseline real da
#2. A auditoria foi executada; **a base ainda não foi liberada**. Nenhum candidato
foi promovido a treino, e as duas issues permanecem abertas. Os números abaixo
descrevem completude e procedência, sem medir desempenho preditivo.

## Evidência local conferida

A seleção de vinte candidatos foi comparada com sua cópia no namespace dos
coletores, a triagem anterior e a fila preparada. Foram conferidos hashes de
dezoito arquivos locais, incluindo revisões humanas e features em cache. As
observações de dezessete candidatos coincidem com o snapshot de descoberta;
as outras três coincidem com os registros originais do piloto. Não foram
substituídos os instantes originais por uma coleta atual.

| Verificação | Resultado |
| --- | --- |
| Candidatos / canais distintos | 20 / 20; uma referência por canal |
| ID/URL, duração declarada até 60 s, contagem inteira não negativa e idade na observação | 20 passaram |
| Idade efetiva na observação congelada | 30,0932 a 36,3496 dias |
| Propostas de setor pela descoberta | 10 moda / 10 beleza; não são confirmação de conteúdo |
| Setor explicitamente registrado em revisão humana existente | 2 moda / 2 beleza, incluindo uma revisão parcial |
| Setor ainda não confirmado | 16 |
| Revisão humana | 3 completas, 1 parcial, 16 não realizadas |
| Propriedades medidas e fingerprint da mídia em cache | 3; mídia temporária já descartada |
| Candidatos sem fingerprint de mídia / propriedades medidas | 17 |
| IDs de vídeo repetidos | 0 |
| Hashes de mídia repetidos entre os três conhecidos | 0; duplicatas nos outros 17 não são verificáveis |
| Uso da mídia / uso das métricas revisados e liberados | 0 / 0 |
| Seleção de desenvolvimento / registros elegíveis de treino | 20 / 0 |
| Fila audiovisual inspecionada com configuração atual | 20 `blocked`, zero tentativas, `halt_reason=null` |

O setor do quarto exemplo foi preservado porque existe revisão humana, embora
essa revisão ainda seja parcial quanto à apresentação visual. Isso não equivale
a quatro registros completos nem exige que o aluno revise individualmente os
dezesseis restantes: continua valendo pré-classificação audiovisual com auditoria
humana de uma amostra e das dúvidas, após resolver o acesso.

## Manifesto e relatório preparados

Arquivos locais privados, ignorados pelo Git:

- `data/private/issue-1-auditoria-20261018/manifesto-candidatos.csv`: vinte linhas no
  esquema do template público. Setor/idioma só são preenchidos a partir da revisão
  humana existente; propriedades/hash só a partir da extração existente. Ausências
  ficam vazias, e todos os estados permanecem `candidate` e uso `pending`.
- `data/private/issue-1-auditoria-20261018/relatorio.json`: motivos por referência,
  suporte, procedência, hashes dos insumos e limitações. Campos propostos ficam
  separados de campos confirmados. Não publica transcrições ou respostas humanas.
- `data/private/development/auditar-base-20261018.py`: procedimento descartável da
  auditoria. Recusa sobrescrever o diretório de evidências. Não é novo pipeline de
  importação de produção nem certificador automático de elegibilidade.

Foi conferida a releitura do CSV: vinte candidatos, contagens idênticas às
observações de origem, três fingerprints reais preservados e dezessete conjuntos
de propriedades ausentes. Arquivos novos têm permissão 0600, diretório 0700.
Nenhuma coleta, inferência, treino, estatística de performance ou partição real
foi executada. As seleções e filas anteriores não foram alteradas.

Verificação direcionada: **19 testes passaram**, cobrindo retomada/bloqueio da
fila, evidências alteradas e preservação da indisponibilidade real em artefatos
não validados e no percurso Python/MCP. Código público e dependências não mudaram.

## Métricas públicas e mídia são dependências diferentes

O aluno esclareceu que o uso pretendido é análise de desempenho. **Consultar
views públicas pela API não exige a mesma aprovação escrita prevista para baixar
conteúdo audiovisual.** O cálculo B0 usa setor e views: não precisa baixar vídeos,
ASR, CLIP ou Qwen. Não condicionar seu cálculo matemático à licença de um novo
download. A conclusão científica da #1 original, porém, inclui origem, recorte,
formato, idioma, correspondência e verificações audiovisuais já acordados.

A [política de métricas derivadas](https://developers.google.com/youtube/terms/derived-metrics-policy)
prevê analytics mediante o aditivo correspondente, com resultados identificados
como calculados pelo projeto. O
[formulário oficial, seção 5 / Analytics & Reporting](https://support.google.com/youtube/contact/yt_api_form)
inclui o aceite e informa que o Google determina se o caso se qualifica. Isso não
é uma proibição geral de análise ou ML, nem permite presumir enquadramento pelo
fato de a finalidade ser acadêmica ou de desempenho. A adesão/enquadramento não
foi demonstrada nos arquivos disponíveis; o dossiê existente continua não enviado.

Se forem mantidas cópias audiovisuais do YouTube, a aprovação escrita prévia da
[política III.E.1](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content)
é uma questão separada, além dos direitos sobre a obra. Não foi solicitado um
novo download nesta retomada, nem houve contato externo ou aceite de termos.

## O que falta para liberar cada percurso

1. **Referência B0 tabular real:** documentar o uso aplicável às métricas e aprovar
   a coorte/rotulagem de setor; conferir fonte, contagens e datas; registrar o
   recorte efetivamente sustentado. Se for proposto um corpus apenas tabular,
   declarar a alteração do protocolo antes do ajuste, sem apresentá-lo como
   conclusão dos requisitos audiovisuais da #1.
2. **Base original de imagem/fala e experimentos A/B/C:** resolver acesso/uso da
   mídia, completar pré-classificação e revisão da amostra/dúvidas, verificar
   propriedades e correspondência; depois avaliar a oferta real frente à
   meta300/piso200. Não completar campos desconhecidos pelo título ou por uma
   flag de elegibilidade.
3. **Servir a referência real na #2:** somente após a liberação da coorte, congelar
   canais e grupos de duplicatas antes do ajuste; usar só rótulos do treino;
   versionar o artefato; demonstrar Python/MCP. Não consultar o teste final para
   escolher o desenho. Faixa empírica não implica cobertura calibrada.

O manifesto preparado torna as pendências auditáveis; não as resolve por
declaração. O modo sintético da #2 continua disponível e a previsão real continua
indisponível.
