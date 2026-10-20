# Produto v14 — um item, uma categoria, uma pista

O aluno autorizou em 20/10/2026 implementar e executar a
[proposta pós-v13](issue-4-vlm-pos-v13-investigacao-e-proposta.md), incluindo
gramática nativa antes da geração e avanço condicional pelos casos revelados.
Uma versão, um candidato e uma fila nova; as filas anteriores continuam seladas.
Não inclui auditoria cega, produto 42–64, treino B/C ou promoção do M1.

## Contrato congelado

Derivar do prompt R v13, alterando somente o bloco de vinculação e duas frases
de cardinalidade conforme o rascunho aprovado. Escolher um item apresentado
identificável, uma categoria e uma pista desse mesmo item. Outros itens
apresentados podem ser omitidos. Proibir transferência de pista entre itens;
maquiagem já vestida no rosto não demonstra cosmético apresentado, e segurar
um aplicador não demonstra cosmético ou roupa held_display.

Os três campos e a ordem dos sete ramos fechados permanecem: ausência,
incidental, apresentado/held, apresentado/isolated, apresentado/use,
apresentado/worn, incerto. Lista vazia nos três ramos não positivos. Cada um dos
três primeiros ramos positivos permite os quatro singletons: cosmetic,
applicator, garment, accessory. Worn permite somente garment. São 16 objetos
semânticos, dos quais 13 positivos. Não filtrar categorias por setor.

`presented_categories` passa a testemunhar um item; não é inventário completo.
Decoder estrito herdado acrescido de exatamente uma categoria positiva. Não
recortar listas antigas, reparar raw, derivar pista, aceitar só o booleano ou
corrigir pelo GT. Definições visuais das pistas, unknown, mapper, OR e janela
≤3 s inalterados. Singleton e coerência formal não garantem suporte nos pixels.

Mesmo Qwen3-VL-2B Q4_K_M, projetor Q8_0, b11716, CPU4, seed42, temperatura0,
saída64 e limites visuais solicitados64/128; um PNG RGB320×330 por chamada.
Pessoa/texto em cache; demais atributos não retomados. Prompt e schema devem
corresponder integralmente ao rascunho privado e aos hashes públicos aprovados.

## Gate nativo antes de inferir

Reutilizar a ponte C++ v13 imutável, ligada às bibliotecas b11716 instaladas,
com os nove cabeçalhos oficiais já conferidos em cache. Compilar somente a ponte
em diretório privado novo, sem instalar, extrair ou substituir runtime/pesos.
Conversão `json_schema_to_grammar(..., false)` e aceitação por caracteres com
término completo; sem vocabulário, modelo ou forward pass.

Exigir zero divergências nos 9.548 objetos do domínio finito (16 aceitos),
16 variações de whitespace dos campos e 25 mutações brutas: total 9.589 sondas.
Incluir multicategoria, duplicatas, worn/cosmetic, estado/pista incompatíveis,
truncamento, conteúdo extra e ordem de chaves não permitida pela gramática.
Schema/decoder operam sobre objetos; a geração mantém a ordem das chaves fixada.

Registrar fontes, bibliotecas, cabeçalhos, compilador, schema, gramática, ponte,
sondas e respostas. Warnings, conversão parcial ou divergência bloqueiam geração.
Carregador e cada reserva verificam a integridade do recibo, fontes e ambiente.
Conferir limite de saída; whitespace arbitrário não tem garantia de caber em
64 tokens. Saída truncada é falha terminal, sem ampliar limite ou repetir.

## Fases, revisão e paradas

1. Até **12 chamadas, zero aquisição**, mesmos controles/receita/fonte/hashes.
   Exigir 12/12 false. Falha perceptiva conclui o bloco e sela sem vídeos.
2. Somente se passar, até **32 chamadas, zero aquisição**, nos quatro crops
   das oito folhas antigas, com tempos idênticos. Exigir 8/8 valor+frames do GT
   imutável; unknown não recupera. Falha perceptiva conclui o bloco e sela.
3. Com valores aprovados, pausar para revisão assistida de todas as categorias
   e pistas positivas, inclusive tardias, contra pixels e inspeção congelada
   anterior à v11. Recibo exclusivo vinculado a plano, resultado, crop, tempo,
   categoria e pista. Exigir todo suporte true; false/unknown sela sem aquisição.
   Ausência do recibo mantém pausa, sem consumir nova chamada.
4. Só com ambos aprovados, até **48 chamadas/12 reaquisições** dos oito negativos
   e quatro positivos de beleza do painel v10 já fixado. Mesmas propriedades,
   pixels e tempos; divergência interrompe, sem substituir caso. Pausar para
   revisão das pistas/categorias e publicar recibo antes do descarte das novas
   folhas com journal. As oito folhas antigas nunca são alvo de descarte.

Falha operacional, JSON, contradição ou identidade interrompe imediatamente,
sem retry/reparo. Tentativa running/incerta exige auditoria; não reentrar no
executor para recuperá-la. Revisões são assistidas após revelação, sem validação
independente ou certificação humana. Não redefinir ambiguidade pelo raw.
Retomar só sufixo não executado após pausa prevista, nunca fila selada.

## Comparação e preservação

Comparar controles com caches v13-R e v11 por inputs idênticos. V12 tem zero
resultados aceitos. Comparar vídeos com v13-R somente nos quatro completos;
seus três raws parciais do quinto não são resultado nem referência de vídeo.
Comparar v10/v9/v8/A-v7/B-v7 somente nas interseções existentes, com ganhos,
perdas, unknown, denominadores e evidências. V11/v12 não têm vídeos completos.
O contraste muda prompt e cardinalidade; não isola efeito de uma frase.

Herdar prontidão descritiva nos20: ≥8 conhecidos/setor, ≥90% valor+frames entre
conhecidos, zero índices sem suporte, ≥3 previsões por valor global e ≥1 por
valor/setor, ambas revisões aprovadas. Não substitui o
[gate cego original](issue-4-vlm-revisao-perceptiva-protocolo.md), não libera
colunas. Nova auditoria requer protocolo próprio e casos/canais não revelados.

Preservar pins herdados, oito PNGs presentes, pixels/tempos, anotações e
partições203/66/31. Guardas200/300; teste fechado, sem abrir suas features,
rótulos, previsões ou métricas. M1/A200, A300, B-cache, serviço Python/MCP,
dependências, locks e ambientes intactos. Sem NIM ou inferência externa.
README não rastreado fora do escopo, sem leitura, edição ou staging.

## Orçamento e execução verificável

Até **92 reservas novas /12 aquisições /2.400 s de sessões**. Base selada
**1.755 /256 /36.159,609599731004 s**; tetos cumulativos
**1.847 /268 /38.559,609599731004 s**. Até180 s por operação, RSS3,3GiB,
um executor, locks da linhagem/fila, reserva durável antes de operar e cobrança
conservadora da tentativa incerta. Manter consumidos a 32ª reserva v13 e seus
180 s não medidos. Nenhum saldo de fila anterior reaberto.

Commitar código/testes/protocolo verificados antes das inferências. Ao fechar,
reconstruir raw→decoder→mapper→OR, comparações, revisões, consumo, descarte,
pins, pixels/tempos, versões e workers; commitar resultados. Código novo
aditivo mantém as versões anteriores e seus módulos congelados inalterados.
Saída: `data/private/issue-4-vlm-v14-v1/`; provas:
`data/private/issue-4-vlm-v14-verificacao-v1/`. CLI
`scripts.vlm_product_v14_grammar --headers ... --folder ...` para pré-verificação;
`scripts.vlm_product_v14_run` com prepare, execute, inspect, review e cleanup,
manifestos200/300 e --phase/--review-file na revisão. Parada é terminal.
