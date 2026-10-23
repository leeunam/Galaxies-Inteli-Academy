# P6 — preparação do diagnóstico anterior→posterior

Unidade de 23/10/2026. A [proposta](proposta-tecnica.md#partições-e-baselines)
prevê ajustar modelos em publicações anteriores e avaliar em publicações
posteriores. O diagnóstico **ainda não foi executado**. A tabela de datas e o
planejador abaixo não cumprem esse aceite. O teste reservado continua fechado.

## Contrato implementado

`scripts.temporal_diagnostic.plan_temporal_diagnostic` recebe metadados de
desenvolvimento já separados do holdout, sem alvos, features ou caminhos. Cada
linha identifica sua partição original de treino/validação, setor, canal,
componente de duplicatas, publicação e observação em UTC. O componente deve
representar equivalência de mídia/republicação; não reutilizar o `group_id`
das partições, que também une vídeos distintos do mesmo canal.

O corte UTC é obrigatório e explícito. Publicação anterior ao corte vai para
o ajuste; publicação igual ou posterior vai para avaliação. Duplicatas que
atravessam o corte são removidas apenas do lado de ajuste. A configuração
principal declara a sobreposição de canais; a separação conjunta é um
diagnóstico adicional explícito, removendo os canais que atravessam o corte
do lado de ajuste. Não deslocar a data, sortear novamente ou relaxar a regra
para obter um resultado mais favorável.

O plano informa IDs e suporte por setor/canal, partições de origem, datas,
faixas de idade e exclusões; conserva um digest dos metadados. Recusa idade
fora de `30 <= idade < 37`, campos de alvos, partição `test`, UTC ausente,
duplicação ou ordem instável de IDs. Partições originais 203/66/31 permanecem
iguais: o corte é uma vista diagnóstica independente dos manifestos originais.
Lados vazios ou setor sem suporte ficam bloqueados, sem inventar métricas.

O campo de disponibilidade informa se todas as observações do lado anterior
precedem a primeira publicação posterior. Mesmo se isso acontecer, o plano
não prova que metadados, histórico de canal e extratores estariam disponíveis
à época; não declara avaliação prospectiva. Em snapshot único, data de
publicação e idade de exposição estão confundidas.

## Execução científica restante

Antes de ler alvos para esse diagnóstico, congelar em recibo privado:

1. Vista permitida dos 269 casos de desenvolvimento, vinculada aos manifestos
   originais e sem abrir arquivos monolíticos contendo alvos do holdout.
2. Regra e data concreta de corte, escolhidas somente pelos metadados e suporte,
   antes dos erros. Congelar a política de canais e os componentes de duplicata.
3. Receitas A/B/C já aprovadas, representação visual liberada, quantis, política
   de ausência e validação interna anterior ao corte para selecionar ajustes.
   Transformações aprendidas e estatísticas de B0/Bcanal usam somente o lado
   anterior permitido; histórico de canal nunca usa os próprios alvos posteriores.
4. Grade limitada original, sequência A→B→C, mesmos exemplos e representação
   de B/C; nenhuma biblioteca adicional. Fixar teto de ajustes, CPU/RAM/tempo,
   custo R$0, fila exclusiva e condição de parada antes da execução real.
5. Registrar recarga e avaliar os modelos ajustados no anterior sobre o posterior
   com erro, quantis, ranking, cobertura/largura, suporte e falhas. Aplicar o motor
   de métricas com tamanho explícito do diagnóstico, sem chamá-lo de teste de 31.
6. Relatar sobreposição, disponibilidade dos rótulos, idade e limites. O resultado
   não escolhe ou retoca o vencedor da avaliação principal. Reutilizar parâmetros
   escolhidos com o lado posterior seria um diagnóstico condicionado à seleção;
   essa dependência deve ser declarada e impede alegação de independência temporal.

O planejador não escolhe uma data real, não ajusta modelos e não materializa
dados científicos. O futuro carregador/runner deve preservar esse limite e
ligar seu resultado ao plano congelado. Ainda faltam a representação aprovada,
a vista privada verificável, a data concreta, os recursos e os ajustes/avaliação.

## Verificação

Dez testes inventados cobrem ordem anterior→posterior, empates na data do corte,
purga de duplicatas/canais, suporte vazio, UTC, ausência de alvos/holdout, idade
e ausência de leitura de arquivos. Com métricas e preflight, **31 testes passaram
em 0,17 s**. São testes de código, sem fit, peso, extração ou chamada externa.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/test_temporal_diagnostic.py
```
