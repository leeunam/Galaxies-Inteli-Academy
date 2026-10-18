# Retomada dos extratores e da base — 18/10/2026

O aluno pediu resolver as pendências da #1 para chegar ao treino real da #3 e,
na sequência, solicitou usar a ferramenta para conferir a amostra em lugar de
preenchimentos manuais. A revisão passa a ser **automática/assistida**, sem alegar
escuta ou anotação humana nova. As evidências humanas anteriores são preservadas.
Autorização operacional não foi convertida em aprovação da plataforma.

## Extração compartilhada corrigida

`creative-features-v1` substitui o contrato experimental `pilot-features-v3` para
a nova preparação. As extrações antigas permanecem intactas e não são misturadas
silenciosamente com as novas.

- ASR local small int8 com revisão congelada, **sem forçar idioma**, beam 1,
  temperatura zero, VAD e sem condicionamento no texto anterior. A mesma função
  recebe referências e criativos inéditos; títulos/OCR não substituem a fala.
- Ausência de trilha é `no_audio_stream`; áudio sem transcrição é
  `no_speech_detected_by_asr`. Nenhum desses estados certifica silêncio real ou
  idioma. A extração guarda hash do PCM de 16 kHz e os diagnósticos dos segmentos.
- Frames mais próximos dos alvos fixos são deduplicados pelos timestamps reais.
  Um alvo depois do último frame usa esse último frame; vídeos de um ou dois
  frames não falham por não fornecer seis imagens distintas. Política
  `nearest-fixed-targets-deduplicated-v2`, sem inventar timestamps.
- MiniLM: média de chunks não sobrepostos de 126 tokens, vetor de 384 dimensões.
  CLIP: média dos frames amostrados distintos, 512 dimensões. Vetores não finitos
  ou de dimensão incompatível são recusados. Texto ausente preserva embedding nulo.
- Modelos/revisões, pacotes, políticas e fontes do extrator integram a assinatura
  da fila. Alteração de configuração exige nova execução; a fila histórica da #1
  não recebeu aprovações artificiais.

As **doze referências do piloto** percorreram novamente aquisição temporária,
ASR, MiniLM e CLIP: doze conclusões, doze embeddings de texto/imagem finitos e
limpeza das doze sessões confirmada. Soma operacional de **341,73 s**,
18,08–55,55 s por sessão neste ambiente; não é benchmark controlado ou SLA.
Os artefatos estão em `data/private/issue-1-extratores-20261018-v2/`, fora do Git.
Datas/contagens originais foram mantidas. Uma nova aquisição não foi declarada
idêntica em bytes à mídia anterior.

A comparação das novas transcrições com as três referências humanas assistidas
anteriores encontrou três edições em 109 palavras: **WER 2,75% e CER 1,15%**.
Não é uma amostra independente de acurácia populacional, nem demonstra melhora
frente à configuração antiga; aquisições e parâmetros diferem. As demais
transcrições não receberam WER inventado sem referência humana.

## Diagnóstico visual e limites

A primeira execução integrada de Qwen atingiu o limite de 180 s. A mídia dessa
tentativa foi removida, e a execução falha permaneceu preservada. A etapa de
ASR/embeddings foi concluída separadamente para não depender da disponibilidade
do VLM. Uma interrupção posterior da auditoria foi identificada e sua pasta
temporária órfã removida após conferir ausência de executor ativo.

O perfil visual seguinte mantém os quatro frames e o modelo/revisão congelados,
com teto reduzido de 256 para 128 tokens visuais por imagem, para conter custo
de CPU. A versão passa a `visual-attributes-v5-qwen-gguf-cpu128`; isso requer
conferência própria e não herda aprovação perceptiva do perfil anterior.
Close-up e aplicação continuam globalmente desconhecidos por qualidade;
`approved_for_training=false` permanece. Erros do runtime não expõem stderr bruto.

Os quatro casos amostrados são conferidos com extração local e evidência visual,
sem abrir player ou reproduzir som. A classificação assistida não é avaliação
humana. Resultados dessa auditoria, do importador e do NIM serão registrados no
checkpoint de liberação, sem promover uma execução interrompida a sucesso.

## Situação da base para treino

Doze referências não atendem ao piso acordado de **200 referências e 50 canais**.
O piloto da #2 e suas partições não foram alterados. A ampliação foi preparada
com sessenta candidatos de 53 canais, trinta sugestões por setor, sem ordenar
por views e sem tratar título/idioma declarado como confirmação audiovisual.
São candidatos de metadados, não sessenta registros elegíveis adicionais.

Duas sondagens novas da API concluíram trinta chamadas no total. A primeira
retornou 284 registros, 215 compatíveis apenas com idade/duração; a segunda,
355 registros, 238 compatíveis. Após combinar com o snapshot anterior, excluir
os vinte já examinados, idiomas declaradamente incompatíveis e sugestões de setor
ambíguas, restaram 367 candidatos potenciais. Os snapshots e a seleção dos sessenta
ficam privados. Novas observações não substituem rótulos congelados.

Nenhum treino supervisionado foi executado neste checkpoint. Um treino exploratório
abaixo do piso precisaria ser uma decisão explícita de escopo, sem alegação de
qualidade validada; o padrão mantém o acordo de 200/50.

Verificação da correção: 36 testes direcionados passaram, incluindo frames reais
de vídeos de um/dois frames, ASR sem idioma forçado, ausências, limpeza, filas e
barreira visual. Os controles seguintes e a suíte integrada são registrados no
checkpoint de liberação. Dados individuais, transcrições, pesos e mídias não entram
nos commits.
