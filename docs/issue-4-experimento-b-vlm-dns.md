# B-VLM v3: retomada com falha transitória de DNS contabilizada

Decisão de19/10/2026 anterior a qualquer ajuste preditivo ou leitura das saídas
perceptivas do lote. A fila v2 concluiu3 casos e parou no4º por DNS, em0,407s,
com limpeza confirmada. A sondagem posterior resolveu YouTube/Google/ytimg;
isso não garante acesso à mídia. Nenhuma tentativa de mídia foi repetida.

Arquivar fila v2, fontes e hashes. Nova fila uniforme v3 nos269 IDs, sem copiar
sidecars v1/v2. Mesmos32 IDs de auditoria, pixels, timestamps, prompt, esquema,
pesos, normalizador e gates. Anotações anteriores exigem identidade exata das
imagens. Não usar rótulos ou resultados preditivos para esta correção.

O recibo privado vinculado ao SHA256
`516808bc0f1b4dc423b8b71585c7da33bae21c282218574650e6b07f538b60ec`
prova21 aquisições anteriores (17+4) e1.165,878031401s consumidos. O campo
cumulativo da v2 desconta somente o saldo anterior já contabilizado, verificado
contra a soma das quatro fontes históricas. Os arquivos permanecem intactos.

Teto explícito de300 aquisições:21 anteriores +269 v3 +até10 tentativas extras
exclusivamente por DNS transitório. Mantém27h cumulativas. No máximo1 retry por
ID e10 no lote. A classificação deve capturar o erro específico temporário
`EAI_AGAIN`/`Errno -3`/`Temporary failure in name resolution`, conservando hash do
diagnóstico; DNS genérico/NXDOMAIN não basta. Comando e flags de yt-dlp idênticos
aos congelados, sem cookies, proxies ou outra rota.

Persistir cada tentativa antes da rede e conservar falha, tempo, hash do run e
limpeza. Só considerar retry após limpeza confirmada, espera de5s, DNS positivo
e orçamento disponível. Arquivar a primeira sessão falha em caminho distinto;
não apagá-la. Persistir preflight e contador antes do segundo pedido. Se este
falhar, parar. Autenticação,403/429, timeout, identidade, memória, saída inválida
e limpeza incerta sempre param sem retry. Reinício não apaga falhas, duplica
pedidos nem remove halt. Congelar implementação e revisão antes da execução.

Esta exceção é operacional e não altera seleção de colunas, grade de12 ajustes,
partições203/66/31, comparadores, teste reservado ou M1. Ver
[protocolo](issue-4-experimento-b-vlm-protocolo.md) e
[normalização](issue-4-experimento-b-vlm-deduplicacao.md).
