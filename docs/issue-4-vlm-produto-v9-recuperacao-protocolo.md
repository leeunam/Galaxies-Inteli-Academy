# Produto v9 — adendo mínimo de recuperação autorizada

Registrado em 20/10/2026, antes de qualquer nova aquisição ou inferência. O
usuário autorizou no chat coordenador: “prepara uma proposta de recuperação por
favor, pode executar ja confio em vocÊ”. A delegação confirmou expressamente
os tetos abaixo. Este adendo sucede a decisão pendente do
[relatório parcial](issue-4-vlm-produto-v9-resultados.md); não modifica a
[fila/protocolo original](issue-4-vlm-produto-v9-protocolo.md) nem seus recibos.

## Escopo e orçamento

Completar exatamente os 31 casos pendentes, na ordem original: caso 34 com
reutilização dos três raw válidos e uma única repetição excepcional do frame 4
sem resposta capturada (12,667 s); depois os 30 casos não iniciados, quatro
chamadas cada. Não executar novamente os 33 completos, controles ou piloto.
Não saltar casos, substituir amostras ou selecionar auditoria nova.

| Contador | Base selada | Adicional máximo | Teto cumulativo |
| --- | ---: | ---: | ---: |
| Aquisições | 246 | 31 | 277 |
| Reservas nativas | 1.637 | 121 | 1.758 |
| Tempo contabilizado | 34.439,12766741601 s | saldo do teto | 97.200 s (27 h) |

Cada tentativa/reserva é persistida **antes** da operação, incluindo falhas.
Sem folga adicional para DNS ou retry: uma tentativa de aquisição por caso;
downloader de recuperação sem retries internos. Auth/403/429, DNS, timeout,
memória, identidade divergente, JSON inválido, interrupção ou limpeza incerta
param a fila sem nova tentativa automática. O único retry autorizado é a
reserva sem raw do frame 4 original. Limite 180 s por aquisição/chamada e RSS
do filho VLM ≤3,3 GiB; o teto global conta a base conservadora integralmente.
Não comprar serviços nem executar inferência externa. Runtime/pesos locais já
instalados; nenhum novo pacote, lock, credencial ou cobrança autorizado aqui.

## Proveniência e implementação separadas

Nova fila: `data/private/issue-4-vlm-produto-v9-recuperacao-v1/`. Novas fontes de
plano, execução e downloader serão congeladas com este adendo e seus testes
antes da primeira operação. O plano ancora o SHA do recibo final antigo
`6b5f5e078e530b2ce41a7b30607532f8e1c8df83897bd4b9c541f697c28572a9`,
todos os arquivos da fila selada (incluindo os 184 recibos), os 131 pins
herdados e o checkpoint selado. Nenhum arquivo antigo será reaberto para escrita.
Locks da fila antiga e da recuperação impedem execução simultânea; conferir
processo encerrado, lock livre, resultado ausente e recibo sem raw antes de
preparar. Revalidar pins em cada carregamento/etapa.

Reaquisição reproduz as mesmas propriedades, folha, quatro PNG RGB320×330 e
timestamps contra v8/v9. Exigir hashes iguais antes da inferência; vídeo é
descartado por sessão. Falha de reprodução para sem retuning. Modelo, pesos,
runtime, prompt, schema, parser, seed, tokens, temperatura, CPU e agregação
continuam idênticos. Nada muda nas anotações de produto, pessoa ou texto.

Para o caso 34, copiar byte a byte os três recibos completos para a nova
derivação e preservar o recibo original sem raw no seu local selado. Registrar
a chamada excepcional em novo recibo frame 4, com vínculo explícito à reserva
antiga. Reconstituir os quatro frames pelo mesmo parser/agregação e executar o
verificador v9 congelado. Os outros 30 usam o extrator v9 sem alteração.

Comparação combinada lê os 33 resultados do local original e 31 novos do local
de recuperação; verifica identidade e quatro frames/recibos de todos. Reutiliza
pessoa/texto v8, calcula as mesmas métricas pareadas v9/v8/A-v7 nos 64, B-v7 só
nos 32 antigos, piloto/restante/origem/setor/classes e gates originais apenas
descritivos. Nenhuma coluna é liberada por desenvolvimento; M1, A300, B-cache,
partições 203/66/31 e teste reservado seguem iguais. Não há treino B-VLM.

## Verificação, parada e descarte

Antes de operar: testes sintéticos da recuperação (só frame perdido chamado,
33+3 não repetidos, ordem, limites, tentativa falha contabilizada, interrupção,
pins/identidade, comparação e descarte), Ruff/formatação, suíte completa e
revisão independente somente leitura. O plano congela fontes/testes e os
recibos da preparação. Não alegar dados sintéticos como execução real.

Após execução/revisão: comparação e recibos da nova fila são selados com hashes;
folhas são descartadas com journal idempotente. Em falha, preservar raw e
reservas, relatar comparação parcial e parar; nova repetição exigirá autorização
específica. Não reabrir a fila original para absorver ou ocultar a recuperação.
Publicar somente código, protocolo e resumo permitido, com commits locais
verificados; sem push, fechamento de issue ou deploy. P5/StateGraph/NIM e
P6/teste reservado continuam sujeitos às respectivas dependências/autorizações.
