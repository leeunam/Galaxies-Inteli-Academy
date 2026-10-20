# Produto v9 — adendo limitado: diagnóstico 42 e sete folhas preservadas

Autorização específica do aluno em 20/10/2026, 12:04 UTC: “sim” à proposta de
uma aquisição diagnóstica do caso 42 e até 28 chamadas locais nos casos 35–41.
Este adendo é uma extensão delimitada da recuperação interrompida. Não autoriza
completar os 64, alterar identidades nem descartar as oito imagens preservadas.

## Proveniência e execução sequencial

Fila nova: `data/private/issue-4-vlm-produto-v9-adendo-limitado-v1/`. Fontes novas
`vlm_product_limited_plan.py`, `vlm_product_limited.py` e
`vlm_product_limited_compare.py`, teste próprio e este protocolo são congelados
por SHA antes da primeira operação. As filas de desenvolvimento e recuperação,
suas respostas, reservas, relatórios e oito folhas permanecem em leitura.
O relatório parcial anterior continua válido, sem ser substituído.

O plano deve conferir a recuperação selada com 34 resultados completos, nove
aquisições (oito completas/uma falha), uma reserva nova e oito folhas íntegras.
Base cumulativa exata: **255 aquisições, 1.638 reservas, 34.491,61625775001 s**.
Os sete IDs e o ID diagnóstico vêm exclusivamente da ordem já congelada;
não há seleção por erro, views ou novas anotações. Antes de operar, conferir
hashes, ausência de sessões temporárias/workers concorrentes e locks das filas.
Encerrar a unidade local da #5 antes destas etapas; não executar em paralelo.

1. **Uma aquisição diagnóstica do caso 42.** Mesma rota, seletor de formato,
   limite de resolução e decodificador existentes, zero retries internos ou
   externos. Persistir propriedades observadas, fingerprint e versões do
   decodificador **antes** da comparação exata com as propriedades congeladas.
   Registrar diferenças por propriedade, sem tolerância, novos recortes ou
   inferência. Vincular o novo SHA ao download v9 antigo e ao run falho da
   recuperação. Bytes iguais ao run falho constituem evidência adicional;
   bytes diferentes descrevem somente o download atual e não reconstroem a
   propriedade da tentativa anterior. Não buscar outro hash com nova aquisição.
   Medir uma divergência esperada é um resultado diagnóstico, não liberação de
   identidade: este caso continua fora das inferências e comparações novas.
2. **Até 28 chamadas locais nos sete casos 35–41**, quatro por caso, somente
   com as folhas já preservadas; nenhum download. Recortar em scratch temporário
   e conferir todos os hashes/tempos contra os caches antes de inferir. Usar
   exatamente o schema/prompt estruturado v9 congelado, agregação, modelo e
   runtime local instalados. Não repetir os 34 completos nem inferir o caso 42.
   Guardar respostas/recibos na nova proveniência, sem escrever nas filas antigas.

O runtime já instalado é conferido em leitura contra o arquivo oficial em cache,
incluindo binários/bibliotecas/links e hashes dos pesos; não extrair/reinstalar
o arquivo nem consultar Hugging Face ou baixar componente algum nesta etapa.

## Orçamento, falhas e parada

Tetos deste adendo: **uma aquisição e 28 reservas**, cumulativos máximos
**256/1.666**, dentro de **277/1.758 e 27 h**. Cada operação tem até 180 s; o
runtime nativo mantém monitoramento amostrado e corte em RSS de 3,3 GiB.
Tempo novo soma à base conservadora, sem zerar o tempo anterior. Reservar e
persistir antes de cada operação. Falha, interrupção ou operação incerta consome
a tentativa/reserva, interrompe a fila e exige auditoria; não há retry automático.
Não prosseguir para casos 43–64 ou elevar o teto a 278.

Download/decodificação malsucedidos ou limpeza não confirmada param antes da
etapa 2. Uma medição concluída com propriedades diferentes permanece diagnóstico
concluído, sem aprovação de identidade. As chamadas só começam após esse registro
concluído. Falha de chamada/JSON/hash para imediatamente, preservando raw e
reserva. A fila não oferece descarte, seleção arbitrária ou retomada de operação
incompleta. Ao finalizar ou parar, selar relatório parcial em nova proveniência.

## Verificação e interpretação

Testar localmente com mídia/outputs sintéticos: consumo exato e persistência
antes de operar, diagnósticos igual/divergente e fingerprint, falhas sem retry,
limites e interrupção, tampering de fonte/folha/recibo, pixels/tempos idênticos,
seleção fixa, conservação de filas/imagens e comparação pareada parcial.
Passar Ruff/formatação, suíte apropriada e revisão independente antes de operar.
Não alterar fontes congeladas depois da primeira operação real.

Comparar somente os mesmos casos completos entre v9, v8 e A/v7; B/v7 só no
subconjunto antigo compatível. Máximo **41/64**; não declarar 64 avaliados.
Pessoa/texto continuam do cache v8. Nenhum gate completo, coluna liberada,
treino B-VLM, nova auditoria cega ou promoção. Preservar partições 203/66/31,
teste reservado, M1/A200, A300, B-cache, serviço/MCP, lock e ambiente. Sem API
paga, credencial nova, instalação, publicação ou deploy; dados privados locais.
Preservar **as oito folhas e todos os recibos inclusive ao terminar**; remover
somente scratch criado nesta execução, nunca as imagens protegidas.
