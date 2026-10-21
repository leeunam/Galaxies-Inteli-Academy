# Diagnóstico positivo pareado pós-v16

Protocolo separado, preparado em 20/10/2026, sob a autorização operacional
continuada do aluno e o recorte adotado pelo principal/supervisor. A
[investigação offline](issue-4-vlm-pos-v16-investigacao-e-proposta.md) motivou
a pergunta: a melhora de especificidade nos negativos causada pela ordem
serializada vem acompanhada de perda nos positivos conhecidos?

Não é continuação da v16, candidata nova ou auditoria cega. A v16 permanece
selada e reprovada com 0/12 e 11/12 negativos; seus dez despachos não usados
continuam encerrados. O orçamento abaixo é novo, separado e único.

## Casos, contraste e critérios fixos

Usar exatamente os cinco corpos de caso positivos já congelados no plano
v16 ativo, com digest
`382ab73dc0d03b0b930c0c2f8de36f64e6ceb8ce949ae2b232dde256cf890aef`.
São cinco crops conhecidos, de três vídeos de moda exclusivamente de treino.
Preservar anotações, testemunhas admissíveis, folhas RGB 1280×360, recorte
RGB 320×330 e tempos 0,2/1,5/2,8 s. Não adquirir mídia nem criar casos novos.

Executar os braços `item_first` (I) e `state_first` (S) da v16 sem alterações.
A sequência por crop é **I/S, S/I, I/S, S/I, I/S**. O prompt neutro, os 22
objetos semânticos, categorias, ordem dos ramos/required, projeção, modelo,
quantização, resolução e parâmetros continuam iguais. Não alterar rótulos
ou alternativas admissíveis após ver respostas.

Medir por braço, com denominador concluído e requerido=5 explícitos:

- `true`, `false`, `unknown` brutos;
- `correct_supported_true`: valor true, categorias exatamente `["garment"]`
  e configuração pertencente à lista admissível original do crop;
- existência de qualquer true bruto e de qualquer true com suporte, em campos
  distintos: só o segundo demonstra reconhecimento correto nesse exemplo;
- ganhos/perdas de S em relação a I usando acerto com suporte, apenas na
  interseção de pares completos, com denominador e requerido=5 explícitos.

Concluir dez respostas mesmo diante de erros perceptivos. Uma execução parcial
nunca é descrita como cinco pares completos. Não estimar generalização ou
incerteza estatística a partir destes cinco crops correlacionados de moda.

Os gates originais continuam **12/12 negativos e 5/5 positivos**. O diagnóstico
não completa retroativamente a v16. Nenhum resultado, inclusive dez acertos,
produz candidata, coluna liberada, nova auditoria, treino B/C ou promoção de M1.
Relatórios sempre registram listas de candidatas/atributos vazias e essas
ações como falsas. Não há próximo experimento automático.

## Orçamento e interrupção

Uma única fila efetiva:
`data/private/issue-4-vlm-pos-v16-pares-positivos-v1/`. Preparar ou carregar
outro caminho é proibido, inclusive uma cópia do plano. Preparação não pode
reescrever fila existente. Não reutilizar a liberação técnica da v16.

| Recurso | Limite novo |
|---|---:|
| Chamadas locais | 10 |
| Aquisições / downloads / chamadas externas | 0 |
| Tentativa global | 400 s acumulados |
| Chamada nativa | até 180 s, limitada também ao saldo menos 5 s |
| RSS do runtime | 3,3 GiB |
| Threads CPU / batch | 4 / 4 |
| Tokens de saída / contexto | 64 / 3.072 |

Um único relógio monotônico contabiliza desde o marcador de início técnico,
incluindo inicialização, checks entre operações, recortes, respostas,
persistência e limpeza. O saldo não é reiniciado por chamada. Os checks e a
chamada nativa têm prazos cooperativos limitados ao saldo menos cinco segundos;
qualquer excesso observado é registrado e encerra a tentativa. A inspeção
offline anterior à entrada técnica não executa modelo. Mesmos
Qwen3-VL-2B Q4_K_M, mmproj Q8_0, runtime b11716,
temperatura zero, seed 42, imagem 64–128 tokens solicitados, sem GPU.

Antes do novo orçamento: 1.835 reservas, 256 aquisições e
37.568,24201608001 s. Tetos cumulativos desta autorização: 1.845 reservas,
256 aquisições e 37.968,24201608001 s. A coincidência numérica com o antigo
teto de chamadas não reabre o saldo antigo. Consumo e reserva incerta históricos
continuam cobrados.

Cada despacho deve ter reserva exclusiva com fsync, associada a plano,
operação e crop, e checkpoint durável com cobrança provisória do tempo
alocado. Sem saldo de sessão, não reservar nem invocar. Timeout, cancelamento,
falha operacional, JSON/ordem inválidos, drift de fonte/pixels/tempo ou limite
de recurso encerra a rodada sem retry, reparo, fallback ou próximo braço.
Reserva em andamento/resultado incerto não é retomada nem descontada.
Falhas de `no_workers`/runtime após liberação técnica selam a fila mesmo com
zero chamadas. Antes desses checks há um marcador exclusivo/durável de início,
vinculado ao plano, configuração e liberação. Qualquer novo `execute` depois
dele recusa antes de runtime, inclusive após crash antes da primeira reserva
ou entre operações completas. O avanço dentro da tentativa atual usa o mesmo
relógio e não cria outra entrada técnica. Inspeção em leitura continua possível.

O raw que efetivamente retorna do adaptador é persistido pelo extrator antes
de julgar seus limites de tempo/RSS, mesmo se a operação for reprovada depois.
Não se promete capturar uma resposta que nunca retornou ao pai. Morte forçada
do pai/host pode impedir limpeza, captura ou selo final; o marcador conserva
o teto de cobrança incerta de 400 s, as reservas anteriores não são liberadas
e não existe retomada automática. Não declarar ausência de workers/temporários
sem conferência posterior, nem reduzir consumo incerto ao último tempo medido.

## Identidade e revisão técnica antes de geração

`scripts/vlm_positive_order_plan.py` e `scripts/vlm_positive_order_run.py`
acrescentam o fluxo; os extratores, gramáticas e filas antigos não mudam.
Reusar as provas nativas/tokenização/comandos da v16 **somente por identidade**
de fontes, schemas ordenados, gramáticas, bibliotecas e recibos. Não recompilar,
retokenizar ou executar o gate nativo de novo para contratos iguais.
O checker puro de recibos pode reconstruir seus objetos e confrontar hashes;
isso não é nova execução nativa ou forward pass.

O plano fixa seus próprios fontes/testes/protocolo e a configuração v16;
protege os 9.974 pins iniciais e os novos recibos de replay. O inventário
documental da mídia foi integrado localmente em `994d227`, antes do selo,
sem operação de mídia. Teste reservado permanece sob as duas guardas de
coorte, sem leitura semântica; partições 203/66/31 e M1/A200 permanecem iguais.
NIM v3, serviço Python/MCP/StateGraph, lock, ambientes e pesos não mudam.

Preparar e inspecionar não libera execução. A revisão técnica do supervisor
deve vincular mensagem literal/ID real, SHA do plano e SHA da configuração.
Até esse recibo concreto, `execute` recusa antes de runtime e mantém zero
operações. A decisão operacional do aluno não exige nova aprovação humana
genérica; o ponto pendente é a revisão técnica específica desta preparação.

O draft corrigido passou em 44 testes sintéticos direcionados: inclui relógio
global com custo de inicialização/checks, retenção do raw em reprovação por
tempo/RSS e recusa de segunda entrada com marcador sozinho, uma operação,
um par completo ou reserva incerta. A tentativa inicial de preparar a fila
foi interrompida antes de escrever plano/checkpoint; restou apenas `.lock`.
O código está disponível para revisão antes de congelar a fila real.

Após liberação, a CLI `scripts.vlm_positive_order_run` aceita `clearance`
e `execute` com `--parent`, `--cohort-dir` e `--folder` privados explícitos.
Na conclusão/parada, sela comparação privada reconstruível, consumo, hashes
dos raws/resultados e saldo encerrado; o relato público deve omitir IDs,
URLs e conteúdo privado, conservando denominadores e limitações científicas.
