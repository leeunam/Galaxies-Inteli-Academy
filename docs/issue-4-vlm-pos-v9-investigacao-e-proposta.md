# VLM após v9 — investigação e próxima etapa proposta

Em 20/10/2026, o aluno orientou continuar a investigação do VLM para cumprir
o escopo original de B/C com atributos aprovados. Isso não libera uma coluna
por decisão administrativa. Aprovação continua dependendo de evidência em
auditoria cega de treino, com o gate original; teste reservado e M1 preservados.

Esta unidade realizou **somente investigação de evidências já reveladas**:
zero aquisições, chamadas nativas, NIM, treinamento ou seleção de auditoria.
As filas antigas continuam seladas, incluindo a comparação v9 de 41/64 e o
caso 42 sem identidade de pixels aprovada. Não se completaram os 23 pendentes.

## Reconstrução e inspeção limitada

Reconstruímos os 41 resultados a partir dos **164 recibos nativos existentes**,
conferindo hashes do resultado e das chamadas, respostas brutas, parser,
intermediários e agregação. Nos 123 frames elegíveis de produto: 57
`presented_target`, 65 `incidental_only` e um `no_target`; nenhum `uncertain`.
Os nove falsos negativos continuam todos de moda, com 27 estados precoces
`incidental_only`. Não há erro de conversão desses estados em false.

Inspecionamos apenas as **oito folhas preservadas**, verificadas contra os
hashes anteriores. Todas são de moda e positivas nas anotações antigas.
Não se reobteve imagem dos quatro outros falsos negativos. A descrição visual
abaixo é posterior às respostas, assistida e exploratória; não é anotação
cega, novo GT ou estimativa de qualidade populacional.

| Descrição exploratória das oito folhas | Casos | Acertos v9 de valor+frames |
| --- | ---: | ---: |
| Roupa vestida, com enquadramentos da peça/look | 5 | **0/5** |
| Peças em cabide ou recortes de roupas sobrepostos | 3 | **3/3** |

Entre os cinco erros há close da camisa/cinto/calça, enquadramento de saia
sem rosto e um vestido cujo tecido é segurado para fora pela mão. Essas
observações motivam testar se a instrução contra roupa incidental está
suprimindo também apresentações de roupas vestidas. **Não isolam esse efeito**:
há somente cinco casos, escolhidos pela disponibilidade de folhas, e a decisão
de apresentação em cada frame pode continuar ambígua pela rubrica original.

Os três acertos também não certificam as subdecisões. Uma peça em cabide recebe
false no frame 2 e true no 3; o OR permite acerto do vídeo. No caso com roupas
sobrepostas e pincel, as categorias emitidas incluem cosmético/acessório,
não uma identificação validada das peças sobrepostas. As anotações anteriores
não rotulam estado/categoria por item. Não pontuar essas categorias como se
houvesse GT independente, nem chamar acerto final de prova da testemunha correta.

## Insuficiência de classes separada de erro perceptivo

Aplicamos o `evaluate_gate` existente a um cenário **contrafactual**, copiando
somente as anotações perceptivas para a entrada prevista. Isso não é previsão
de modelo, publicação de gate ou liberação de colunas.

| Grupo de 32 | Campo | Negativos anotados beleza / moda | Com cópia perfeita |
| --- | --- | ---: | --- |
| Antigos | Pessoa | 0 / 2 | Falha: false ausente em beleza e menos de três no grupo |
| Revelados | Pessoa | 1 / 1 | Falha: menos de três false no grupo |
| Antigos | Produto | 3 / 0 | Falha: false ausente em moda |
| Revelados | Produto | 3 / 2 | Passaria nesse cenário contrafactual |

Logo, exigir passagem literal nos dois grupos antigos não distingue sozinho
percepção perfeita de insuficiência de suporte. Não introduzir previsões erradas
para produzir false, mudar anotações, aliviar o gate ou escolher novos casos
após ver respostas. Esse diagnóstico não remove os erros reais de pessoa,
produto e texto registrados anteriormente.

Uma futura auditoria precisa pré-declarar seleção e análise de suficiência
de classes, com candidato congelado e anotações cegas às suas respostas.
Se faltar suporte, registrar insuficiência, sem reposição oportunista.
O contador de metadados já existente registra 42 vídeos elegíveis de beleza e
35 de moda, em 31/28 canais, alguns compartilhados entre setores, após excluir
os 64 casos/56 canais revelados. Isso não garante disponibilidade de mídia ou
classes; nenhuma evidência desses candidatos foi aberta nesta investigação.

## Correção delimitada recomendada: produto v10

**Proposta, ainda sem implementação ou execução autorizada por este documento.**
Antes de trocar pesos ou resolução, testar uma única adição de instrução
positiva para apresentação de roupa vestida. Itens grandes já aparecem nos
erros inspecionados; não há evidência que isole resolução como sua causa.
Trocar modelo/runtime seria outra ablação com orçamento e contrato próprios.

Manter o prompt v9 inteiro, acrescentando somente este parágrafo antes da
instrução de saída JSON, sem remover as condições de ausência/incidentalidade:

> Presentation may involve a garment that is being worn. Visible close framing
> of the garment's cut or details, or a hand holding the worn garment out to
> display it, can establish the garment itself as the item of interest. Do not
> require removal from the body or a hanger. A person wearing clothes, a full-body
> view, ordinary accessories, or clothes behind a speaker alone does not establish
> presentation; use uncertain if this image cannot distinguish presentation from
> incidental wear.

Não inferir apresentação por setor, views, texto de venda, áudio, outro frame
ou intenção comercial. Não converter toda roupa vestida em produto. Schema,
ordem das alternativas/exemplos, parser, categorias, mapper, OR, janela ≤3 s,
pesos, runtime e pixels/tempos permanecem iguais. Pessoa/texto ficam em cache;
não acrescentar campos ou reparo. Congelar a nova especificação antes da primeira
chamada. Não retocar a instrução depois das respostas.

## Plano concreto para aprovação operacional

Uma fila nova, separada das três filas v9 seladas, com duas fases sequenciais:

1. **Até 44 chamadas, sem download:** reconstruir os 12 controles existentes,
   exigir seus hashes anteriores e executar uma chamada v10 por controle.
   Concluir o bloco se as operações forem válidas; prosseguir somente com
   12/12 false. Depois executar quatro frames de cada
   uma das oito folhas preservadas, mantendo crops e tempos exatos. Exigir
   Concluir esse bloco sem retuning e exigir 8/8 valores+frames corretos para
   avançar. Esses testes verificam ausência
   básica e recuperação dos positivos disponíveis; não medem especificidade
   em vídeos reais. Falha perceptiva sela a fase ao terminar seu bloco; falha
   operacional para imediatamente, sem retry.
2. **Se a fase 1 passar, até 48 chamadas e 12 aquisições:** usar os oito
   negativos e os quatro positivos de beleza do piloto v9 já fixado. Nenhum
   novo ID selecionado por erro, imagem ou views. Cada reaquisição deve
   reproduzir folha, crops, propriedades e tempos antigos; bytes diferentes
   do contêiner não autorizam ignorar a identidade dos pixels. Sem reposição
   ou retry. Uma divergência para a fila e preserva o resultado parcial.

O painel final teria 20 casos revelados, **dez/setor**, com 12 positivos e
oito negativos: beleza 4/6 e moda 8/2. Comparar v10, v9, v8 e A/v7 somente
nesse mesmo painel; B/v7 apenas onde existir cache. Relatar cada fase, ganhos/
perdas, confusão, abstenções e evidência. As oito folhas disponíveis e os casos
escolhidos para diagnosticar falhas não constituem amostra independente.

Critério descritivo proposto para considerar um protocolo cego posterior:
ao menos oito conhecidos em cada setor de dez, ≥90% de valor+frames entre
conhecidos, zero índices sem suporte, ≥3 previsões por valor no painel e
≥1 por valor/setor. **Não é o gate de liberação de 32 casos**, não o substitui
e não aprova treino. Se falhar, preservar a conclusão negativa, sem iniciar
outra variante automaticamente. A referência de desenvolvimento dos 64 mantém
suas métricas e razões de suporte; não é transformada em auditoria independente.

Tetos propostos: **92 reservas novas**, cumulativo máximo **1.758**;
**12 aquisições novas**, cumulativo máximo **268**, abaixo do teto 277;
até **30 minutos de sessões novas**, somados aos 34.792,3041 s registrados,
sem exceder 27 h. Por operação: 180 s e RSS filho de 3,3 GiB. Um executor,
reserva durável antes de operar, tentativa incerta consumida, zero retry,
reparo ou fallback. A fase 1 sozinha termina no máximo em 1.710 reservas,
sem aquisições novas. O plano deve carregar os valores exatos do checkpoint
selado, sem reinicializar contadores. Não executar NIM/API externa, instalação ou mudança
de ambiente/lock. Validar e commitar código/testes/protocolo antes de operar.

Preservar as oito folhas inclusive ao terminar, todas as filas/recibos antigos,
M1/A200, A300, B-cache, serviço/MCP, partições 203/66/31 e teste reservado.
Descartar somente scratch e mídia temporária desta nova execução, com recibos.
Este plano não autoriza completar os casos 42–64, outra auditoria cega,
treinamento B/C ou promoção de modelo. Esses passos precisam de seus próprios
contratos após os resultados, sem prometer aprovação antecipada.

## Caminho ao escopo original

A orientação do aluno mantém a trilha de B/C com VLM aprovado; não foi adotada
uma redução para C-cache. Produto é o próximo diagnóstico, mas não encerra
o VLM inteiro: pessoa/texto ainda têm erros de evidência, pessoa tem insuficiência
de classes nos grupos antigos, e ambiente/formato seguem sem retomada aprovada.
Cada coluna que entrar no treino precisa de sua liberação auditável. Uma nova
auditoria deve excluir os casos/canais já revelados e manter o gate original.
O teste reservado não é usado para obter esse aceite.

## Verificação desta investigação

Os **729 arquivos protegidos** conferem antes e depois, incluindo oito folhas,
fontes, partições, bundles e recibos anteriores. Só foi adicionado este relatório
público; os recibos de reconstrução, inspeção exploratória e cenário contrafactual
ficam privados em `data/private/issue-4-vlm-produto-pos-v9-diagnostico-v1/`.
Não houve alteração de código ou dependências, portanto não se atribui nova
suíte de testes a esta análise. Foram verificados hashes, reconstrução das
164 chamadas, agregação, classes do gate, links e diff.

Referências: [rubrica/gate](issue-4-vlm-revisao-perceptiva-protocolo.md),
[desenvolvimento v8](issue-4-vlm-v8-resultados.md),
[protocolo v9](issue-4-vlm-produto-v9-protocolo.md),
[adendo limitado selado](issue-4-vlm-produto-v9-adendo-limitado-protocolo.md)
e [comparação de 41 casos](issue-4-vlm-produto-v9-adendo-limitado-resultados.md).
