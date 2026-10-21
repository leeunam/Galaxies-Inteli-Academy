# Frente 1 — rubrica para auditoria cega futura

Protocolo: `front1-visual-audit-20261021-v1`. Complementa o
[plano de decisão](issue-4-front1-visual-validation-plan-v1.md), sem executar
seleção, anotação ou inferência. Nenhum dos 32 casos está selecionado aqui.

## Seleção antes de abrir pixels

Manter a base 300 e assignments 203 treino/66 validação/31 teste. Selecionar
**32 casos do treino existente, 16 por setor, 32 canais distintos**. Não pedir
32 vídeos novos. Excluir IDs, canais e hashes de mídia de **todo** o histórico
revelado/desenvolvimento, incluindo auditorias, controles e diagnósticos.
Selar esse conjunto completo antes de ordenar. Não usar views, títulos,
descrições, transcrições, features semânticas ou arquivos mistos com teste.

Definir H como SHA256 de UTF-8 dos componentes separados por byte NUL, sem NUL
final. Ordenar canais por H(protocolo, setor, canal), desempate lexical pelo
canal; dentro do canal, vídeos por H(protocolo, ID), desempate lexical pelo ID.
Processar beleza antes de moda, selecionando um vídeo por canal e recusando
canal já selecionado globalmente. Parar a seleção se faltar 16 em algum setor;
sem reposição, mudança de ordem ou preenchimento com outro setor. Essa é uma
seleção prospectiva nova; não reordena ou reescreve manifestos históricos.

Selar IDs, assignments, setores, canais, exclusões, ordenação, hashes esperados
de mídia/frames, tempos e candidato antes de inferir. Não trocar casos por
ambiguidade, indisponibilidade, classe rara, erro ou timeout. Este trabalho não
abre o manifesto real nem confirma suficiência da reserva.

## Papéis e anotação

Desenvolvedor vê somente controles e casos revelados. Anotador separado vê
crops e tempos da auditoria sem saídas do extrator, views, transcrições,
ranking ou métricas preditivas. Registra valores e suporte por frame antes da
comparação. Revisão assistida não equivale a verdade certificada ou aceite
humano. Registrar procedimento e limites. Revisor independente verifica
seleção, rubrica e proveniência; conflitos viram consenso ou `unknown` antes
de abrir previsões, nunca depois para favorecer o candidato.

Após selar anotações/candidato, não ajustar instrução, schema, parser,
agregação, frames ou rótulos. Auditoria revelada vira desenvolvimento; outra
correção exigirá outro protocolo e outra amostra ainda não revelada.

## Definições observáveis

| Campo | Suporte visível | Ausência / incerteza |
| --- | --- | --- |
| Pessoa | Pessoa ou parte humana real, inclusive mão/braço | Manequim, roupa isolada ou rosto impresso não bastam; ambiguidade é `unknown` |
| Produto até 3 s | Cosmético/aplicador, peça ou acessório apresentado como objeto de interesse, no próprio frame e tempo ≤3 s | Roupa incidental não basta; mão próxima não prova contato/sustentação/apresentação; relação não verificável é `unknown` |
| Texto | Caracteres visíveis no crop, sem exigir transcrição OCR | Não inferir pela fala, título ou provável marca; padrão sem caracteres verificáveis não estabelece texto |

Anotar por frame antes do agregado. Índices são base 1, únicos, limitados aos
frames recebidos. Produto após 3 s não conta. `true` cita frames positivos;
`false` exige ausência em todos os elegíveis e cita-os; nos outros casos,
`unknown` com lista vazia. Ausência de frame elegível não é `false` automático.
Um frame não é testemunha de relação encontrada somente em outro.

Se a saída declarar categoria, configuração, relação mão–objeto ou pista,
verificar cada declaração no mesmo crop e registrar suporte separadamente.
Essas subdeclarações não têm anotação legada independente. Não deduzir suporte
de booleano correto/gramática válida nem reparar raw. Declaração sem suporte
reprova prontidão descritiva e impede alegar interpretação correta, mesmo se o
gate legado passar. Esse registro adicional não muda o cálculo do gate original.

## Gate original, sem aliviar limiares

Preservar `scripts/experiment_b_vlm_quality.py:evaluate_gate`,
`b-vlm-blind-assisted-sector-gate-v1`, com a restrição da revisão perceptiva:
somente pessoa, produto e texto são candidatos; ambiente/formato e
close-up/aplicação continuam não liberados.

Para **cada coluna e setor**, exigir no mínimo 12 previsões conhecidas de 16,
acerto de valor **e** suporte de frames ≥90% das conhecidas e zero evidências
citadas sem suporte da anotação. Suporte exige lista não vazia e subconjunto
dos frames anotados. Valor certo com frame inválido é erro. Abstenções não são
acertos; denominador é previsões conhecidas, como no avaliador existente.

Booleanos exigem também ao menos três previsões `true` e três `false` no total,
e uma de cada por setor. Falta de classe reprova; não reamostrar. Publicar
denominadores, abstenções, confusões e evidências inválidas por setor e decisão
por coluna. A amostra pequena não certifica acurácia geral.

Falha técnica, imagem divergente, raw inválido ou limpeza incerta interrompe
sem retry, sem chamar lote parcial de auditoria completa. Se nada passar,
selar sem B-VLM. Se alguma coluna passar, encaminhar somente essas colunas e
configuração para proposta separada de lote uniforme nos 269 IDs de
desenvolvimento. Sem corrigir células usando GT, promover M1, abrir o teste ou
declarar B/C completos nesta etapa.
