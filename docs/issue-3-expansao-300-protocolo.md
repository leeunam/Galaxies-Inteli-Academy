# Expansão de desenvolvimento de 200 para 300 referências

Protocolo registrado antes de nova coleta/ajuste, autorizado pelo aluno neste
chat: ampliar até 300, preservar partições/teste, retreinar B0 e A e comparar
antes de iniciar B. A versão de 200 e M1 v1 permanecem disponíveis e imutáveis.

## Seleção e orçamento

- Acrescentar 100 referências: até 50 de moda e 50 de beleza, no máximo cinco
  por canal novo. Não consultar nem ampliar qualquer dos 80 canais da coorte
  antiga. Excluir também os controles de desenvolvimento conhecidos e duplicatas
  exatas da coorte, usando somente IDs, canais e fingerprints de metadados.
- Descoberta por consultas fixas de assunto e data, ordenadas por data,
  nunca views: moda (look, roupa, vestido, moda feminina, moda masculina, provador,
  acessórios, calçados); beleza (maquiagem, batom, skincare, cosmético, perfume,
  base maquiagem, cuidados cabelo, tutorial maquiagem). Consultas pt/região BR
  propõem candidatos; não comprovam idioma ou setor.
- Congelar janela de publicação compatível com observação de 30 <= idade < 37
  dias. Verificar a idade no instante real de cada observação. Nunca renovar
  rótulos antigos, preencher o dia 30 ou transformar contagem atual em passada.
- Filtrar canais antigos antes de pedir detalhes/estatísticas dos novos vídeos.
  Ordem entre canais por hash fixo, com rodízio entre suas publicações. Idioma
  declarado e títulos ficam na auditoria, sem alterar a ordem de curadoria.
  Não ordenar, eliminar ou enriquecer por valor do desfecho.
- No máximo 300 chamadas de metadados, incluindo até 20 buscas; no máximo
  300 tentativas novas de mídia e 90 minutos de aquisição/extração. Parar na
  meta, orçamento, erro de autenticação/bloqueio/rate limit ou limpeza incerta.
  Registrar insuficiência se a oferta não alcançar 100 elegíveis; não relaxar
  critérios ou repetir seleção até melhorar métricas.
- Mesma aquisição temporária e extratores congelados: vertical, até 60 s,
  fala pt por ASR sem idioma forçado, MiniLM384 e CLIP512. Curadoria assistida
  de frames e fala real, sem declarar revisão humana ou aprovação automática
  pelo VLM. Ambiguidades ficam excluídas/pendentes; sem fala inventada. Remover
  mídia/frames de revisão após decisão. Nenhum novo provedor ou envio ao NIM.

## Partições e artefatos

Todos os 200 metadados, seus grupos/partições e observações permanecem iguais.
Não abrir arquivos mistos antigos (`records.json`, `predictor-inputs.json`) nem
evidências/rótulos do teste; usar coorte e manifesto sem rótulos e carregar
evidência somente após selecionar treino/validação.

Antes de consultar views, atribuir cada canal novo por
`int(sha256("issue-3-expansion-300-v1:42:" + channel_id), 16) % 4`:
zero = validação; demais = treino. É proporção esperada 75/25, sem garantir
contagem exata. Não mover canais para equilibrar resultados. Nenhum novo teste.
Duplicatas exatas/relações reconhecidas que cruzem partições são recusadas,
sem deslocar os registros antigos ou mudar a regra. Mesmo canal fica sempre
junto; exclusão de canais antigos é verificada novamente na liberação.

O novo manifesto carrega sua ascendência e valida as atribuições antigas
integralmente, sem executar novamente o divisor sobre a coorte ampliada. O
formato antigo mantém sua serialização/hash e continua sendo aceito. Novo
diretório privado para coorte/B0; novos modelos em `artifacts/`, sem substituir
pesos ou configuração do serviço atual. Teste final continua com os 31 IDs
e 16 canais originais; não será inferido nem terá métricas calculadas aqui.

## Ajuste e comparação previamente definidos

1. Recalcular B0/Bcanal só no treino ampliado. A mantém as mesmas 388 colunas,
   alvo log1p e ausência, pesos uniformes no treino e protocolo original:
   quantis 0,1/0,5/0,9, profundidades4/6 × L2 3/10, taxa0,05, seed42, CPU2,
   até500 iterações/parada50. Máximo12 ajustes; sem nova busca após resultados.
2. Selecionar pelos mesmos critérios na validação ampliada: MAE log médio por
   canal para q50, perda quantílica média por canal para extremos. Mesma política
   de reparo, conversão e recarga exata. Não reajustar na união treino/validação.
3. Comparar B0/A antigos e novos **nos mesmos 45 IDs de validação antigos**,
   e todos os quatro também na validação ampliada. Separar o novo subconjunto.
   Ambos os conjuntos são desenvolvimento; a validação antiga já foi usada
   para seleção e a ampliada também passa a sê-lo. Não apresentar resultado
   como avaliação final independente ou ganho causal puro de dados: a mudança
   da validação pode mudar a configuração/iteração selecionada.
4. Métrica principal continua MAE log por canal. Registrar MAE views, perdas
   quantílicas, ranking por canal, cobertura e largura. Diagnóstico de alto
   alcance comparável usa os p90 originais de treino por setor: moda6.403,5,
   beleza33.835,3. Mostrar n de vídeos/canais, subestimação, mediana de
   `(observado+1)/(previsto+1)`, erro log e falhas acima da faixa. Distribuição
   ampliada e seus p90 são descritivos adicionais, sem redefinir o recorte
   para favorecer um modelo. Alto alcance não vira classe de viralidade.
5. Documentar ganhos e regressões. Não alterar perdas, pesos, representação,
   limiar, extração ou dados após ver os resultados desta rodada. Não iniciar B
   neste pedido. B usará a mesma coorte/partições se posteriormente autorizado.

## Verificação e unidades de commit

Protocolo primeiro; extensão de partições/seleção com testes sintéticos depois;
coleta/curadoria e liberação verificadas; por fim ajuste/comparação reproduzíveis
e registro dos resultados. Dados privados e modelos não entram no Git.
Um executor nesta árvore; revisão independente somente leitura para isolamento,
preservação de versões e fidelidade da comparação. Verificar hashes de arquivos
permitidos antigos, igualdade dos 200 metadados/assignments e zero sessões
temporárias restantes. A instrumentação deve proibir leitura do teste, não só
declarar ausência de métricas.
