# NIM no subgrafo: HTTP 200, seleção rejeitada

Em 21/10/2026, após confirmação direta do usuário nesta conversa, a revisão
automática permitiu executar uma vez o [candidato integrado](issue-5-nim-no-grafo-live-v1.md).
O único POST retornou **HTTP 200**, mas a autoridade raiz rejeitou a seleção:
`selection_rejected`. A renderização não foi aceita e
**`real_provider_verified=false`**, com estado `live_not_validated`.
Não há prova aceita do provedor no subgrafo.

A [evidência sanitizada](evidence/issue-5-nim-no-grafo-live-v1-resultados.json)
vincula plano, configuração e recibos. O [bloqueio anterior](issue-5-nim-no-grafo-live-bloqueio.md)
permanece como registro histórico, sem alteração: naquela ocasião o processo
não iniciou e nenhum POST foi consumido. A nova mensagem humana confirmou
explicitamente uma chamada sintética; não houve troca de executor, payload,
modelo, endpoint ou limites para contornar a rejeição.

## Execução observada

| Medida | Resultado |
| --- | --- |
| Processo / recibo | código 0 / `observed`, autorização consumida |
| POSTs / invocações do seletor | **1 / 1** |
| HTTP / código local | **200 / `selection_rejected`** |
| Seleção / renderização aceitas | false / false |
| Tempo incluindo recolhimento | **8,0073 s** |
| Resposta / tokens de saída | **1.338 bytes / 262** |
| Limites | 45 s de execução, 16 KiB, 2.048 tokens |
| Teto financeiro / custo medido | R$0 / indisponível |
| Workers raiz / modelos ao concluir | 0 / 0 |

Endpoint `https://integrate.api.nvidia.com/v1/chat/completions`, modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`. Corpo fixo de **8.576 bytes**,
três criativos e 24 fatos inteiramente inventados. Nenhuma mídia, previsão,
SHAP ou referência de dados reais foi enviada. A chave foi usada somente pelo
getter existente no worker autorizado, após a reserva e o dispatch duráveis;
não foi exposta ao operador, IPC, documentação ou logs.

A sequência fresca registrada foi `analyze → shap → comparables → context →
select → render → proof`, no grafo/subgrafo compilados. Alcançar esses nós
não significa seleção ou renderização aceita. O código de saída 0 indica
conclusão do executor com recibo, sem equivaler a aprovação semântica.

O recibo identifica rejeição pela autoridade local, mas não conserva corpo
bruto, cabeçalhos, exceção, hash do conteúdo remoto rejeitado ou campo exato
que falhou. Não é possível atribuir a causa concreta, nem equiparar esta
rejeição ao erro de tipo de uma tentativa histórica. O pedido tipado aceito
fora do grafo continua sendo outra execução, com seu próprio resultado.
Não houve reparo, retry, fallback ou reaproveitamento dessa autorização.

## Verificação e preservação

O código integrado continua em `48ab4f4`, previamente verificado com **13 testes
raiz e 14 isolados**, todos offline. Nenhuma fonte foi modificada e nenhum
teste adicional foi necessário nesta unidade operacional/documental.
Conferem os dez pins live e os 137 pins offline, a revisão técnica e os
26 arquivos protegidos, incluindo M1 e oito folhas. Quatro manifestos/partições
das coortes200/300 conferem por hash, sem leitura semântica do teste reservado.

Reserva, vínculo do grafo, dispatch e resultado foram gravados no ledger fixo
com consumo único. A captura do operador coincide com o recibo final; os
recibos privados estão em arquivos 0600. O registro do bloqueio anterior foi
preservado. Zero workers ao concluir; sem nova aquisição, geração VLM, treino,
instalação, publicação, abertura do teste ou mudança do M1/A200.

O escopo de uma chamada terminou. Nenhum saldo autoriza nova tentativa e
nenhuma flag da demonstração real foi promovida. Geração livre, aderência
qualitativa, mídia real no provedor e qualidade preditiva continuam sem
validação por este ensaio sintético.

Plano: `4e5f3acbfcf49b788894ac5072807aabad803743e58deeba36f87e17f6e794d6`.
Configuração: `277ce579b81403b819620f924063eb9970e64a52f57242b5b9ebf202dda17a1f`.
Payload: `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`.
