# Auditoria NIM: integração local e timeout preservado

Em 21/10/2026, a [auditoria offline](issue-5-nim-no-grafo-rejeicao-auditoria-offline.md)
foi integrada sobre `836af34`, preservando a branch atual. Os commits locais
`15a969d` e `8dfbabb` correspondem a `47fa667` e `4463c8d`, respectivamente.
Os três arquivos adicionados conferem byte a byte com o candidato revisado;
links e diff passaram. Nenhuma fonte de runtime, plano ou payload mudou.

Os 44 testes raiz e dois isolados aprovados no clone não foram apresentados
como testes executados na principal. Na principal foram selecionados somente
os dois novos casos isolados, com dados inventados e diretório temporário novo.
Sua primeira sessão **não passou integralmente**: um caso passou e outro
falhou, em 45,61 s. O log original e seus recibos foram preservados.

| Execução na principal | Resultado do teste | Recibo simulado |
| --- | --- | --- |
| Primeira sessão, `valid` | falhou por timeout | `consumed`, `timeout_outcome_uncertain`, 45,0167 s incluindo cleanup |
| Primeira sessão, `wrong_hash` | passou | `observed`, rejeição simulada esperada, 0,3713 s |
| Única repetição, somente `valid`, fora do isolamento e em outro diretório | passou em 0,53 s | `observed`, seleção simulada aceita, 0,3708 s |

Os tempos da última coluna são os dos recibos, diferentes do tempo total de
pytest. A repetição não substitui a primeira execução nem prova que o sandbox
causou o timeout. A causa concreta da diferença permanece desconhecida.
Não houve outra repetição, suíte completa ou nova execução dos 44 casos raiz.

## O que os recibos existentes demonstram

A [evidência de integração](evidence/issue-5-nim-rejeicao-auditoria-integracao.json)
conserva separadamente os três resultados e hashes dos recibos simulados.
A inspeção posterior somente leu arquivos existentes; não executou testes.

No primeiro `valid`, existem reserva, vínculo, dispatch e resultado terminal.
O dispatch é explicitamente `offline_simulation_only=true` e
`consumed_before_transport`. Pelo caminho imutável do worker, esse marcador é
gravado no tratamento de `SELECT`, depois das transições de contexto. Portanto,
o timeout ocorreu depois de alcançar esse dispatch simulado. Não há resultado
ou lista de eventos para localizar em qual etapa posterior ele ocorreu.
O recibo declara zero requisições HTTP reais.

O campo `elapsed_seconds_including_cleanup` não é um recibo explícito de
cleanup. Não foram retidos `cleanup_confirmed`, PID do worker ou seu código
de saída. A inspeção estática mostra que a saída do contexto protege o
recolhimento e aguarda o filho; isso não cria telemetria retroativa do processo.
O processo de pytest terminou com código 1, registrando a falha. A inspeção
atual na visão do host encontrou **zero workers relevantes e de modelos**,
sem processo remanescente identificado. A lacuna histórica continua explícita.

O `wrong_hash` inicial e o `valid` repetido têm resultado completo e sequência
`analyze → shap → comparables → context → select → render → proof`.
São simulações: ambas conservam `real_provider_verified=false` e zero HTTP
real. Nenhuma reprodução aprova o provedor ou recupera a seleção remota original.

## Preservação e limite

Os quatro arquivos do ledger real consumido conferem por SHA-256 antes/depois
dos testes e novamente após a inspeção. Os dez pins live e 137 offline e a
revisão técnica também conferem. Os testes e recibos originais não foram
editados; os temporários simulados ficaram retidos para revisão local.
Sem chave, rede, modelos, instalação, novo POST ou autorização remota.
VLM, oito PNGs, partições, teste reservado, M1 e README permanecem fora desta mudança.

Não foi demonstrado defeito de contrato/validador que sustente correção de
runtime. A rejeição real continua com causa concreta desconhecida, e o timeout
do smoke local permanece uma observação separada. Nenhum sucesso posterior
remove essas limitações ou libera nova chamada.
