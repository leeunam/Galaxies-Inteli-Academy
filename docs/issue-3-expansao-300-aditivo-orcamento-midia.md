# Continuidade operacional para completar 300 referências

Registrado em 19/10/2026 antes de ultrapassar qualquer orçamento anterior.
Ao ser informado de que 300 tentativas ou 90 minutos poderiam não produzir as
100 inclusões, o aluno respondeu: manter a exigência de 300 referências, buscar
novas abordagens pelos dois setores e treinar depois da coleta. Não autorizou
substituir a meta por uma coorte menor.

As novas vias de domínio já registradas produzem 1.026 propostas sem ampliar
os 300 pedidos de metadados. No checkpoint de 122 tentativas, 28 inclusões estão
confirmadas e dois casos aguardam revisão; a extração consumiu 1.302,88 s.
O teto original de tentativas pode ser insuficiente apesar de haver saldo de
tempo e candidatos. Essa constatação usa elegibilidade, não desempenho do modelo.

Para executar a continuidade solicitada, permitir **até 450 tentativas de mídia
acumuladas**, conservando os **90 minutos acumulados** de aquisição/extração e
300 tentativas de metadados. Não reiniciar contadores ou retry de vídeos já
tentados; a extensão só aumenta o teto de tentativas, não o tempo, a cota de
metadados ou a meta de inclusões. Parar antes se atingir 100 novas inclusões,
50/setor e cinco/canal. Não baixar mais mídia após a meta.

Ativação explícita por parâmetro; o checkpoint deve vincular este arquivo por
hash e persistir orçamento original/estendido. Troca de arquivo, hash ou redução
posterior do orçamento é recusada. Falhas continuam consumindo tentativas e
tempo. Condições de parada por rate limit, autenticação e limpeza incerta seguem
obrigatórias, sem contas/proxies/rotas alternativas.

Todos os critérios de curadoria, extratores, partições, observações e proteção
do teste permanecem iguais. A ampliação do orçamento não autoriza retreinar com
menos de 300 referências nem iniciar B. Se a meta continuar inviável no tempo
remanescente, registrar o checkpoint e a causa concreta, sem inventar inclusões.
