# Uso do YouTube e corte da entrega

Decisão confirmada pelo aluno em 17/10/2026, horário de São Paulo.

## Escopo e limite assumido

Meta de 300 vídeos utilizáveis, piso operacional de 200, procurando 50–60 canais,
aproximadamente metade de moda e metade de beleza. Esses números não garantem suficiência
estatística. A primeira etapa continua sendo vinte candidatos de desenvolvimento;
somente depois da curadoria e da confirmação das condições da fonte se amplia a mídia.

O aluno escolheu manter YouTube, moda/beleza e entrega em 21/10 às 23h59. Se não houver
aprovação do uso a tempo, aceita entregar **protótipo executável com treino e avaliação
supervisionados reais pendentes**. Essa aceitação altera a entrega demonstrável; não
dispensa requisitos da fonte nem permite anunciar A/B/C ou qualidade preditiva reais.

Sem base utilizável, a demonstração pode verificar extração de mídia própria ou
independentemente licenciada, integração/MCP, tratamento de falhas e explicação de
evidências permitidas. Exemplos sintéticos só verificam contratos e comportamento.
Respostas identificam o modo demonstrado, sem apresentar pontuação de viralidade,
intervalo calibrado ou ranking supervisionado como resultado treinado e validado.

O treino/avaliação com dados reais só deixa de ser pendência quando houver base compatível
e evidências efetivas. Uma amostra licenciada fora do recorte é fixture técnico, não
substituto silencioso do corpus. O marco científico original continua não atendido.

## O que a verificação oficial encontrou

Há duas questões diferentes:

| Uso pretendido | Evidência necessária | Situação deste projeto |
| --- | --- | --- |
| Obter e processar cópias temporárias de mídia do YouTube | As políticas III.E.1 exigem aprovação escrita prévia do YouTube; os direitos sobre a obra também precisam ser compatíveis | Não demonstrada; o sucesso do yt-dlp não resolve |
| Usar dados da API para novas métricas/analytics | O aditivo de 2026 prevê um processo específico; o Google determina se o caso se qualifica | Não aprovado; a aplicação a rótulos, treino, previsões e derivados deve ser descrita expressamente |

O formulário oficial orienta a solicitação de métricas na Seção 5, **Analytics & Reporting**,
com dados do projeto e evidências da aplicação. Enviar o formulário ou aceitar o texto não
equivale a receber aprovação; o aditivo mantém outras políticas e não concede por si só
permissão audiovisual. Não foi identificado prazo oficial garantido até 21/10.

O Researcher Program anuncia acesso a metadados públicos pela Data API, com elegibilidade
acadêmica e análise do pedido; não anuncia fornecimento dos arquivos audiovisuais.
Não é uma rota de acesso imediato para este cronograma. Licença Creative Commons pode
resolver parte dos direitos de reutilização da obra, sem substituir as condições da
plataforma. Apagar depois, usar outra ferramenta ou contratar um intermediário também
não demonstra automaticamente um enquadramento compatível.

Isso é uma conclusão de viabilidade baseada nos textos consultados, não uma conclusão
geral sobre todo uso de ML. Para preservar o desenho completo, preparar o pedido específico
ao YouTube e aguardar resposta aplicável. Para preservar o prazo sem essa resposta,
aplicar o corte de protótipo escolhido pelo aluno. Não depender do contato com cada criador,
nem repetir solicitação de base à Academy, que já informou não a fornecer.

## Trabalho já iniciado e curadoria

A nova descoberta fez oito chamadas somente de metadados: quatro buscas e quatro lotes
de detalhes. Retornou 162 registros, dos quais 109 atendem apenas à duração e idade
propostas, com contagem disponível. A primeira triagem foi refinada para não priorizar
declarações de idioma incompatíveis. O conjunto atual tem vinte candidatos de vinte
canais: dez com proposta de moda e dez de beleza; dezessete declaram português na API.
Declaração de idioma, resultado da busca e título **não confirmam** fala pt-BR ou setor.

Os três exemplos usados para depurar os extratores continuam no desenvolvimento. Os
demais foram selecionados por prioridade de idioma declarada no protocolo, hash fixo e
limite de concentração, sem ordenar por views. A descoberta é de conveniência; não
representa enumeração exaustiva ou amostra representativa da plataforma. Nenhuma mídia
nova foi baixada nessa etapa. Não há vinte exemplos audiovisuais aprovados para treino.

Arquivos privados, ignorados pelo Git:

- `data/raw/youtube-pilot20-discovery-20261017.json`: requisições não secretas, respostas e instantes reais.
- `data/private/vinte-candidatos-20261017-v2.json`: protocolo, vinte referências e pendências.
- `data/private/vinte-candidatos-20261017-v2.records.json`: os mesmos registros no namespace dos coletores.
- `data/private/curadoria-vinte-candidatos.md`: roteiro sem views/likes para revisão de setor, formato e áudio.
- `data/private/youtube-use-request/dossie-para-revisao.md`: rascunho do pedido, sem envio ou aceite de termos.

Os registros conservam `training_eligible=false`; uso da mídia e das métricas permanecem
pendentes. A versão inicial da seleção foi preservada para auditoria, sem substituir
observações anteriores ou fingir que os novos frames já foram inspecionados.

A [retomada foi implementada e documentada](retomada-coleta.md). Preparar e inspecionar
`data/private/fila-issue-1-20-v2/` resultou em vinte registros `blocked`, zero tentativas
e nenhuma aquisição audiovisual. A versão anterior da fila permanece como evidência;
a alteração do extrator exigiu criar nova fila, sem reaproveitar uma assinatura antiga.
Suíte integrada: **47 testes passaram**, Ruff e formatação aprovados. Os testes usam
API, downloader e extratores sintéticos; não medem percepção ou desempenho preditivo.

## Próximos marcos

1. Conferir setor, formato, idioma e duplicatas das vinte referências; manter dúvidas e
   exclusões explícitas. Views/likes ficam fora do roteiro de curadoria.
2. Verificar a retomada sem refazer sucessos, protocolo imutável, limites e bloqueio de
   fonte pendente, usando testes sintéticos. Documentar os limites reais do executor.
3. Concluir compatibilidade CatBoost/LightGBM e teste NIM sintético, sem alegar treino
   real por usar dados fabricados. A configuração NVIDIA está preenchida localmente,
   mas isso não significa que a chamada já tenha sido validada.
4. Só com fonte utilizável e revisão concluída: 20 → 60 → meta300, piso200. Medir tempo
   e falhas antes do trabalho noturno; um worker audiovisual inicialmente.
5. Congelar a base efetivamente disponível ao iniciar o bloco de segunda, 19/10.
   Se a fonte continuar pendente, congelar também essa limitação e concluir a versão
   de protótipo, reservando terça à verificação e quarta à reprodução/entrega.

A issue #1 continua aberta. A seleção de candidatos e o aceite do corte não são
comprovação de fonte utilizável nem conclusão de todos os critérios originais.

## Fontes primárias consultadas

- [YouTube Developer Policies, III.E](https://developers.google.com/youtube/terms/developer-policies#e.-handling-youtube-data-and-content).
- [Aditivo para métricas derivadas e armazenamento](https://developers.google.com/youtube/terms/derived-metrics-policy).
- [Formulário oficial de auditoria e uso da API](https://support.google.com/youtube/contact/yt_api_form).
- [Researcher Program: funcionamento](https://research.youtube.com/how-it-works/), [elegibilidade](https://research.youtube.com/policies/) e [termos](https://research.youtube.com/policies/terms/).
- [Licenças no YouTube](https://support.google.com/youtube/answer/2797468?hl=en) e [termos do serviço](https://www.youtube.com/t/terms?hl=en).
