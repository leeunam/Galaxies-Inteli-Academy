# VLM: detalhe nativo — investigação e proposta mínima

Investigação local em 21/10/2026 sobre `4569d8b`, sem download, geração,
instalação ou novos rótulos/outcomes. A [evidência sanitizada](evidence/issue-4-vlm-fonte-nativa-investigacao.json)
registra observações, inventário e limites. O plano privado congela somente as
duas identidades do par já revelado, localizadores, PTS, propriedades e hashes.
SHA-256: `2ba897f61fedc9893bf7e85098f0fb0112924cbf4626bac475effabc19bbd246`.
**Proposta sem autorização de aquisição; nenhum recibo de liberação foi criado.**

## Achado e hipótese

As fontes históricas são **360× 640**. `frames_and_properties` reduz para
até 512× 512 e salva JPEG; `verified_cells` reduz novamente e cola à esquerda.
Nos dois crops de 320× 330, o conteúdo útil é **186× 330**, com **134 colunas
brancas à direita** (41,875% da área). Há cerca de 3,75 vezes menos pixels úteis
que no frame 360× 640, além da compressão JPEG intermediária.

Isso corresponde à receita comprometida; não demonstra bug de índice, PTS,
cor ou parser. A [chamada de 1.056 tokens](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-espacial-negativo-60-resultados.md)
ampliou esse derivado e manteve o falso positivo; não recuperou detalhe nativo.
Não repetir gramática/densidade. A hipótese nova é perda de informação pelo
caminho de preparação, a distinguir de falha relacional do modelo. Nenhuma
dessas causas foi provada.

O inventário por nomes/extensões encontrou 109 arquivos de vídeo no projeto,
todos com 7 ou 1.051 bytes em diretórios de testes. Em sete raízes temporárias
relacionadas, foram 397 arquivos com extensão de vídeo; os três maiores que
esses stubs pertencem ao run preservado da demonstração. Nenhuma fonte nativa
do par foi identificada. Não foram decodificadas outras mídias. As duas sessões
históricas registram remoção dos temporários; aquisições de 729.241 e 2.175.950
bytes, com derivados preservados. O inventário não cobre toda a máquina:
ausência do ID no nome não exclui uma cópia opaca. Esta é uma conclusão de
**fonte não identificada no escopo**, sem alegação de ausência universal.

## Recuperação proposta: duas fontes, zero inferências

Recuperar apenas positivo/frame 1/PTS 0,2 s e negativo/frame 3/PTS 2,8 s, pelas
duas URLs privadas congeladas. Não substituir caso, formato após falha ou PTS.

| Limite | Proposta |
| --- | --- |
| Tentativas | **2**, uma por fonte, sequenciais |
| Gerações / novas fontes / novos rótulos | **0 /0 /0** |
| Por fonte | até 180 s incluindo cleanup/protocolo; job útil até 150 s para download e verificação |
| Global | **420 s**, sem reinício por fonte |
| Arquivo / workspace | **32 MiB /128 MiB** |
| RSS da árvore | **3,3 GiB** |
| stdout / stderr | até 64 KiB cada; bruto sem projeção pública |
| Socket / taxa | 20 s /5 MiB por segundo |
| Retries / substituições | **0 /0** |

Duas tentativas não significam duas conexões HTTP: o downloader pode consultar
página/player e baixar streams/segmentos. Quantidade de conexões desconhecida
antecipadamente. Bytes acima limitam arquivos/workspace, não a soma da rede.

Reutilizar sem alteração os mecanismos existentes de `demo_recovery.py`,
`demo_recovery_process.py` e `demo_recovery_child.py`: ambiente literal sem
chave/proxy, sandbox, subreaper, pidfd, coleta de descendentes e recibo de
cleanup. Arquivo limitado por `RLIMIT_FSIZE`; RSS/workspace amostrados a 50 ms,
com possível ultrapassagem entre amostras. Não prometer teto instantâneo
desses dois ou cleanup após falha irrecuperável do host.

Somente depois de revisão, preparar adaptador restrito às duas identidades e
extração/ponte, dentro dessa fronteira. Não criar supervisor ou infraestrutura
geral nova. Preservar ferramentas/versões e seletor histórico
`best[height<=720][vcodec!=none][acodec!=none]/bestvideo[height<=720]+bestaudio`.
Sem instalação, configuração pessoal, cookies, login, credencial, plugins
remotos, contorno de acesso, API de métricas ou leitura/persistência de views.

1. Reserva exclusiva por fonte antes do processo; plano/revisão próprios e
   bloqueio de reentrada após resultado incerto.
2. Validar fonte e propriedades históricas completas:360× 640,
   duração 18,928/58,868 s, PTS e demais propriedades congeladas.
3. Reproduzir a **folha inteira por SHA-256**, o PNG do crop e PTS exato com
   as funções antigas. As oito folhas existentes não são sobrescritas.
4. Só então extrair, do mesmo arquivo e PTS, RGB 360× 640 antes de thumbnail/JPEG:
   exatamente dois PNGs, hashes e recibos, sem retocar ou escolher outro frame.

Contêineres podem diferir em bytes, como já ocorreu; registrar e aceitar
somente com a ponte integral. Isso não certifica bytes nativos históricos
indisponíveis: prova reprodução do derivado e proveniência da nova extração.
Esperados/anotações permanecem congelados.

Acesso indisponível, autenticação,403/429, identidade/propriedade/PTS/folha
divergente, geometria inadequada, limite ou cleanup incerto encerram toda a
etapa na primeira falha, sem gastar outra tentativa para contornar/substituir.
Nenhum saldo antigo é reutilizado.

Após cleanup confirmado, remover somente novos vídeos/partes/JPEGs/scratch.
Propor retenção dos dois PNGs verificados e recibos para revisão até
21/10/2026,23h 59 São Paulo, com descarte explícito posterior e sem timer.
Cleanup incerto conserva o próprio scratch e interrompe. As oito folhas e os
três inputs da demo, retidos até 23/10, nunca são alvos dessa limpeza.

## Discriminante posterior: outra decisão, nenhum modelo agora

Se a ponte passar nos dois, congelar em protocolo separado quatro chamadas,
dois casos × duas representações. NativaRGB 360× 640 versus conteúdo congelado
186× 330 sem margem, ampliado deterministicamente para 360× 640. Essa ampliação
não recupera detalhe. Originais/PNG antigos permanecem intactos.

Mesma geometria/posição, pergunta relacional já congelada, schema/gramática,
modelo/projetor, parâmetros e orçamento visual; ordem alternada prévia.
Exigir contagens visuais efetivamente iguais, sem ajustar flags após observar
saída. Esperados diagnósticos `yes`/`no` já existentes; não criar perguntas
de objeto com sublabels novos para perseguir aprovação.

Melhora nativa do negativo sem perda no positivo frente ao derivado daria
apoio pontual ao efeito da preparação, sem separar JPEG de redução. Falha
nativa não prova ausência de benefício geral; ambos corretos não isolam a
causa histórica com margem. Abstenção/técnica separadas de acerto. Nenhum
resultado aprova atributos, relaxa gates ou libera auditoria/B/C.

## Viabilidade até 19h UTC /16h São Paulo

A recuperação proposta tem janela operacional de sete minutos, além de
preparação/revisão. Diagnóstico pequeno posterior pode caber hoje, condicionado
à fonte íntegra, liberação própria e runtime; nenhum resultado é garantido.

**Aceite integral de VLM/B/C até o prazo não tem sustentação técnica.**
Ainda exige evidência independente e extração uniforme de 269 referências de
treino/validação. Só três frames/vídeo seriam 807 inferências: a 20 s/frame,
4,48 h; a 50 s/frame, próximo do diagnóstico espacial,11,21 h, antes de auditoria,
outros atributos e treino/comparação. São cenários condicionais, não throughput
medido do lote. Não assumir concorrência ou redução de protocolo para caber.

M 1/A 200, partições, teste reservado, oito PNGs e gates permanecem preservados.
Nenhuma autorização NIM resta. A unidade termina na proposta para decisão do
pai e revisão técnica **antes de qualquer aquisição**.
