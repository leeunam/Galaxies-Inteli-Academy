# Diagnóstico positivo pós-v16: perda de sensibilidade com state_first

A rodada única concluiu **dez chamadas e cinco pares**, em **348,81 s**
globais, com zero aquisições e zero chamadas NIM. `item_first` acertou quatro
positivos com suporte; `state_first`, nenhum. A melhora anterior nos negativos
veio acompanhada de perda nos positivos conhecidos deste recorte. O diagnóstico
não sustenta escolher `state_first` como correção aprovada.

Execução em 20/10/2026, após a liberação técnica específica do
[plano preparado](issue-4-vlm-pos-v16-pares-positivos-preflight.md), código
`4bf8d66`. O [recibo público sanitizado](evidence/issue-4-vlm-pos-v16-pares-positivos-resultados-20261020.json)
registra consumo, comparação e preservações. Identidades dos casos e raws
ficam somente nos recibos privados da fila.

## Resultado reconstruído dos raws

| Ordem | Concluídos | true | false | unknown | true com suporte |
|---|---:|---:|---:|---:|---:|
| item_first | 5/5 | 5 | 0 | 0 | **4/5** |
| state_first | 5/5 | 0 | 1 | 4 | **0/5** |

Nos cinco pares completos, `state_first` teve **zero ganhos e quatro perdas**
de acerto com suporte em relação a `item_first`. O quinto par foi erro dos
dois braços. True com suporte manteve exatamente o critério congelado:
categorias `["garment"]` e configuração na lista admissível original do crop.

`item_first` produziu `hand_holds_hanger_out` nas cinco respostas. Quatro
correspondem às testemunhas admissíveis; em um crop essa configuração está
fora da lista congelada. Seu true bruto não foi contado como reconhecimento
correto. Não houve revisão de anotação ou expansão de alternativas depois
das respostas.

`state_first` produziu quatro `uncertain`/`unclear`, projetados corretamente
como unknown, e um `incidental_only`/`incidental`, projetado como false.
Nenhuma resposta foi true, com ou sem suporte. O efeito aparece nos raws;
parser, projeção e agregação não introduziram a perda observada.

Como contexto separado, a [v16 anterior](issue-4-vlm-v16-resultados.md) tinha
0/12 negativos corretos em `item_first` e 11/12 em `state_first`, sem executar
positivos. Os novos resultados não completam retroativamente aquela fila nem
convertem o diagnóstico em um novo gate de aceitação.

## Alcance da conclusão

O contraste manteve prompt, schemas semânticos, ordens dos ramos/required,
categorias, projeção, modelo/runtime, parâmetros, pixels, tempos e anotações.
A ordem de serialização permaneceu a única diferença entre os dois braços.
Nos mesmos cinco crops conhecidos, o ganho anterior de especificidade não
conservou a sensibilidade a produto apresentado.

O resultado é compatível com uma tendência de `state_first` a respostas não
positivas nesse desenvolvimento; não demonstra percepção correta de ausência
nem identifica sua causa interna. Não há logits ou justificativas para
atribuir o efeito a tecido, atenção, capacidade ou quantização. `item_first`
também conserva uma testemunha sem suporte.

São cinco crops correlacionados de **três vídeos de moda de treino já
revelados**, sem casos de beleza e sem nova amostra independente. Não estimar
generalização ou concluir que a ordem nunca funciona. Os gates continuam
12/12 negativos e 5/5 positivos: **v16 reprovada, nenhuma candidata ou coluna
liberada**, sem auditoria nova, treino B/C, troca de M1 ou próxima rodada
automática. Este diagnóstico encerra a autorização delimitada.

## Consumo, selo e preservação

- Dez reservas novas, todas com resultado completo; zero aquisições, downloads,
  falhas operacionais, retries ou chamadas NIM nesta unidade.
- Tempo global final **348,81396392700117 s**, incluindo inicialização e checks;
  runtime nativo somado **267,80 s**, maior chamada **28,86 s**, pico de RSS
  **2.608,15 MiB**, abaixo de 3,3 GiB. O relógio não reiniciou por chamada.
- Cumulativos **1.845 reservas, 256 aquisições e 37.917,05598000701 s**.
  As dez chamadas antigas não usadas da v16 continuam encerradas; não foram
  saldo reutilizado. Reserva incerta histórica e seu tempo continuam cobrados.
- Liberação literal, origem e ID reais foram preservados sem truncamento e
  submetidos pelo CLI, vinculados ao plano/configuração. Um marcador exclusivo
  precedeu os checks de runtime. A fila terminou selada com
  `positive_probe_authorized_diagnostic_completed` e saldo novo zero.
- A CLI de inspeção validou o terminal. A reconstrução independente conferiu
  os dez raws, hashes, sequência alternada, inputs, projeções, testemunhas e
  métricas, com criação de processo proibida nessa fase. O guard terminal foi
  verificado em leitura, sem tentar reentrar no executor ou gerar de novo.
- Os **9.978 arquivos protegidos** conferem, assim como as oito folhas PNG e
  os **32 hashes de crops** reconstruídos em memória. Tempos e anotações iguais;
  nenhuma folha foi alterada ou removida.
- Ambientes raiz/isolado com as mesmas **130/42 distribuições**, pesos/runtime
  conferidos sem geração, M1/A200 e modelos protegidos iguais. Partições
  **203/66/31** e teste reservado preservados, sem leitura semântica do teste.
- Ao finalizar a conferência, não foram observados workers VLM/NIM/mídia nem
  temporários desta rodada. A janela nativa terminou. Nenhuma integração NIM
  foi feita durante ela.

O código não mudou nesta conclusão: permanecem os 10+44 testes direcionados
aprovados na preparação, sem repetição de suíte por documentação. O verificador
privado registra a reconstrução de produção e as conferências de preservação,
sem novas inferências.

Identidades finais: plano `efec450cc89b54a5a3ca28bdd2f6eda5bd7fdf3facf8b936a5447a01d4c2bebc`,
configuração `b8a50a2cd0a526fc80fe516d1b57625335e2d18f946fa132be23a756355614d4`,
comparação canônica `f52ac37e0869108e09c089075ac755e1238f433204ca20d8c4ccb7d6ec5282e3`.
O recibo privado final de verificação tem digest
`31e161edf834b837e4e39b39ed8d043f59128f502976cda14b6a8cc6ab65eda0`.
