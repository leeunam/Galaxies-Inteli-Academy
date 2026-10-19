# B-VLM: identidade dos pixels amostrados antes da inferência

Complemento anterior à primeira resposta VLM, em 19/10/2026. Altera somente
o critério de identidade/resize e explicita o gate do
[protocolo inicial](issue-4-experimento-b-vlm-protocolo.md).

## Evidência e decisão

A primeira aquisição de um dos 32 casos de treino pré-fixados funcionou, mas
divergiu no SHA256 do arquivo. O piloto parou antes do VLM e removeu a mídia.
Um diagnóstico separado, sem VLM ou rótulos, readquiriu o mesmo vídeo: todas
as propriedades e timestamps coincidiram exatamente; a folha PNG de curadoria,
reproduzida pelo procedimento original, teve **o mesmo SHA256 congelado**.
Não foi demonstrado que os arquivos de vídeo ou os JPEGs de até512px sejam
idênticos. Igualdade de embedding ou de estatísticas não provaria isso.

Há, porém, um compromisso criptográfico anterior dos pixels que compõem essa
folha: até quatro miniaturas, redimensionadas para caber em320×330, com
legendas fora da região visual. O novo VLM receberá **somente recortes RGB da folha cujo hash foi verificado,
em PNG sem perdas**: célula horizontal320px, y=25 até355, incluindo o padding
branco original. O recorte exclui as legendas desenhadas em y=4. Cada
miniatura mantém proporção e cabe em320×330; não afirmar que seu conteúdo
preenche a célula. O SHA256 da folha e suas dimensões/posições comprometem os
pixels destas entradas reduzidas; não comprovam os pixels512 descartados.

Esse dimensionamento é uma versão nova e explícita de entrada de B-VLM,
`contact-sheet-cell-320x330-v1`. Os269 casos não tinham VLM e não
existe comparador VLM512 congelado. Preservar exatamente o prefixo905 de
B-cache, todos os extratores/fontes antigos e todas as partições. O limite de
resolução deve constar dos resultados; não atribuir ao VLM detalhes ausentes
nas miniaturas ou afirmar identidade do vídeo inteiro.

Antes de chamar Qwen para **qualquer** caso, exigir propriedades/timestamps
idênticos, SHA256 exato da folha congelada, dimensões válidas e hashes dos
PNGs realmente enviados. Nenhuma tolerância numérica/visual ou similaridade
de embedding substitui esse critério. Arquivo de mídia diferente pode ser
aceito somente com essa prova, registrando os dois hashes e a diferença.
Falha no compromisso de pixels interrompe o lote; nenhuma linha é removida.
ASR/CLIP/áudio antigos não são recalculados ou substituídos.

Os dois diagnósticos anteriores permanecem no checkpoint. Autorizar uma nova
extração sob este critério documentado não apaga a falha anterior. Limite total:
271 aquisições (duas diagnósticas mais269 do lote), orçamento27h, sem repetição
automática após falha de fonte, identidade, VLM ou limpeza no novo lote.

## Auditoria antes dos resultados preditivos

Os32 IDs (16 de cada setor) já foram selecionados por hash somente de ID/setor
e gravados antes do primeiro piloto; ele pertence à amostra. A auditoria não
será escolhida após respostas. Registrar primeiro a anotação visual assistida
por campo e seus frames, **sem revelar parsed/resposta VLM, views ou fala**;
só depois revelar a saída para calcular concordância. Não é revisão humana
nem certificação da acurácia geral.

Gate operacional por coluna: pelo menos12 valores conhecidos revisados **em
cada setor**, evidência temporal/visual válida e concordância de pelo menos90%
em cada setor. Nas booleanas, exigir pelo menos três casos conhecidos de cada
valor na amostra total e pelo menos um de cada valor em cada setor. Para
enumerações, valores com menos de três exemplos auditados no total ficam
globalmente `unknown`; recalcular o gate sobre os valores retidos e exigir
pelo menos dois valores retidos. Registrar todos os denominadores, abstenções,
divergências, falsos positivos/negativos e suporte por valor/setor. Colunas que
não passarem são excluídas globalmente antes de qualquer ajuste preditivo.

Close-up/demonstração continuam bloqueados. `format=application` continua
desconhecido. Sem correção individual baseada nas respostas ou nos rótulos.
Se nenhuma coluna passar, registrar falha da etapa sem declarar B completo.
Demais regras de treino, comparação, teste fechado e M1 preservado continuam.
