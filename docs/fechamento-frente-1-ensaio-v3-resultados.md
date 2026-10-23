# Frente 1 — resultado v3: envelope viável, percepção inconclusiva

Em 23/10/2026, a [rodada v3 autorizada](fechamento-frente-1-ensaio-v3.md)
executou exatamente um preflight e uma inferência condicional, com custo R$0.
O novo envelope permitiu a cápsula interna. O modelo respondeu **`unknown` no
positivo conhecido**, sem timeout. Isso não demonstra reparo perceptivo e não
libera nenhum atributo, auditoria, extração dos 269 casos ou B/C completos.

## Execução e percepção

| Verificação | Resultado |
| --- | --- |
| Preflight | `completed`, rc0, limpeza confirmada; 0,127054 s |
| Prova do preflight | Rede isolada, `/dev/null` utilizável, zero chamadas de modelo |
| Inferência nativa | rc0, `technical_success=true`, `stop_code=null` |
| Encoder/decoder | Ambos observados; 240 tokens visuais |
| Formato | JSON válido; 95 bytes de stdout bruto |
| Resposta | `state=uncertain`, `item_configuration=unclear`, `presented_categories=[]` |
| Projeção | `unknown`; `accepted=false` |
| Tempo nativo | 17,483901 s |
| Pico RSS nativo | 2.628,453125 MiB |
| Pico RSS agregado do proprietário | 2.825.232.384 bytes, abaixo de 3,3 GiB |
| Tempo global reconstruído | 26,345097 s desde a primeira reserva de preflight |
| Contagens | Um preflight, uma reserva, um dispatch e uma captura de modelo |
| Finalização | Ledger selado, `pending=null`, limpeza confirmada; sem scratch restante |
| Rede/custo/recusas externas | Zero requisições, R$0, zero recusas de permissão |

Ambos os pedidos à ferramenta usaram os objetos fixados no plano, com
`sandbox_permissions=require_escalated`. O bwrap interno manteve rede isolada,
raiz somente leitura, escrita persistente no namespace próprio, ambiente limpo
e proprietário/watchdog. Não houve instalação, aquisição, mudança de kernel ou
AppArmor, fallback ou repetição. O sucesso demonstra viabilidade desse envelope
nesta execução; não identifica a regra exata que impediu a v2.

O crop, prompt antigo, schema ordenado, seed42, pesos, CPU4 e native225 foram
preservados. MemAvailable na admissão era 6.769.491.968 bytes, acima de 6 GiB;
o segundo gate registrou 6.687.002.624 bytes. Disco livre: 24.295.063.552 bytes.
Os 30 hashes de fontes, 113 antecessores e quatro referências/fingerprints dos
assets continuaram iguais. O holdout não foi aberto e coorte/partições não mudaram.

## Terminal bruto e reconciliação aditiva

O worker revisado retorna rc2 quando a resposta não é aceita. O proprietário
genérico classifica esse rc2 como `child_failed`; o operador então encerra com
`owned_call_failed`, rc1 externo, e terminal `technical_or_uncertain_failure`.
Neste caso isso ocorreu **depois de uma captura nativa completa com rc0**.
O terminal original permanece intacto.

A função somente de leitura `scripts/front1_diagnostic_reconciliation.py`
separa esses níveis. Após conferir as vinculações de arquivos, o leitor verifica
concordância de captura/receipt, suporte da categoria/configuração, stdout do
worker, código de saída previsto e finalização. Uma falha distinta do proprietário,
timeout nativo, limpeza incerta ou recibo contraditório não é convertido em erro
perceptivo. A reconciliação desta rodada é `abstention_diagnostic_only`.
Mesmo o ramo de acerto do caso conhecido mantém `quality_release=false`.
Nenhum arquivo congelado do operador ou plano foi corrigido durante a execução.

A captura conserva a marca genérica `capture_origin=injected_unreleased` e o
digest da proposta do contrato genérico de captura. Essa marca não é o digest
da autorização desta rodada nem uma liberação de qualidade. A proveniência
específica é a cadeia plano → autorização/revisão/slot → reserva externa →
reserva de preflight → dispatch → receipt → hashes da captura/stdout, verificada
pelo reconciliador privado. Não houve uso da marca genérica como autorização.

O stdout bruto foi preservado e os 19.116 bytes de stderr foram descartados
pelo contrato existente, com eventos/avisos limitados retidos. Não há stderr
integral para diagnóstico retrospectivo. O aviso `qwen_grounding_1024_token_notice`
foi registrado; o orçamento native225 não foi alterado. Encoder/decoder executados
não provam adequação da representação ou atenção visual.

O worker removeu o scratch da chamada após confirmar limpeza, deixando somente
o diretório pai vazio. A primeira conferência de leitura exigiu ausência também
desse pai e parou antes de produzir reconciliação. O pai vazio foi removido por
`rmdir`, após as confirmações de limpeza; a conferência então passou. O recibo
`scratch-parent-cleanup.json` preserva essa distinção. Não houve outra inferência.
A amostra posterior de workers estava vazia, mas a visão `/proc` da ferramenta
padrão é confinada: essa amostra não atesta todo o host. A confirmação de limpeza
vem dos proprietários da execução e da captura/estado terminal vinculados.

## Conclusão da hipótese e limites

Remover a cláusula adicional não produziu um positivo aceito: a resposta antiga
foi `unknown`, enquanto o contraste histórico com a cláusula havia sido `false`.
Essa diferença de cobertura é inconclusiva para a hipótese causal. Não se converte
abstenção em falso e não se afirma que a cláusula era a causa exclusiva do erro.
O argv histórico efetivamente executado continua indisponível; sua equivalência
é uma reconstrução estática, sujeita também a variação temporal/de execução.

O contraste termina aqui, conforme o orçamento e o resultado predefinidos.
Não se justifica repetir a mesma célula, reverter o prompt como reparo demonstrado
ou iniciar auditoria cega. Um candidato distinto precisa de sustentação perceptiva
em painel de desenvolvimento com positivos e negativos antes de propor nova
validação independente, preservando os gates originais e orçamento próprio.

A versão deste relatório registra qualidade **não liberada**. Continuam abertos
os atributos obrigatórios do TAPI/proposta — os três candidatos atuais não
substituem os 5–8 atributos previstos —, a QualityRelease versionada, os 269
sidecars elegíveis e os treinos/comparação observados B/C completos. A300 e os
resultados históricos B-cache/C-cache permanecem referências; nenhum modelo
foi selecionado, promovido ou escolhido usando o teste nesta unidade.

## Identidades e reprodução

Evidências persistentes em
`/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/`:

- `diagnostic-old-prompt-positive-v3/`: plano, operador, autorização, revisão,
  slot/liberação, reservas, dispatch, captura, receipt e terminal bruto.
- `unit-7-envelope-v3/`: preparação, recibos das ferramentas, admissão,
  reconciliação aditiva, limpeza e revisões independentes do Chat3.

| Artefato | SHA-256 |
| --- | --- |
| Plano lógico | `7d7e3f449efa1cacbefe3300e22e5d39895f037a08fa5e129883d82ce1b75f20` |
| Operador revisado | `6c23fd9afa4d1998c52dac3a6890a6603e5cdaf2b62ca73da45df9c13b4e26bf` |
| Autorização humana | `e8e4b4767f193a07ac61d514e27f9dd1fc05c8240ab5dcf812156ec5c76aa863` |
| Revisão vinculada à autorização | `c07d941dde7f6c35428b51e7987c4ce04efa16866b9e03ffc28698eb969182cd` |
| Slot | `8f7858692dd2852e5354374229e53b443dc820198fa08cb8e3d4673508370da0` |
| Reserva externa | `d0a2a6bfa83e4757bba80bb8c248543fa39055f35e28c7ce24ae1ce080748d7e` |
| Primeira reserva de preflight | `75aea4a9619ad0431a20806306d9a8cf11bc4fde1262985ed4f2bc7c9e0f85a0` |
| Resultado da captura | `d5d792f0eaabd570b134fd0e790e00907276fc71e36af3b5df0debf15d92fe1c` |
| Stdout nativo | `ec20ae6d30a63b96bb6132ba92b64c1a5b7cc0470b1c259411cb0c70ab1bbccf` |
| Liberação aditiva do slot | `3e0f1fa3f7858658268376cd54bdcb8624d226252a226b567786b907bf55c395` |
| Revisão independente do resultado | `441270987ae279de6536d861ff0b1bab512c15582c7f9482e3fb5068e2c6e9b0` |

A autorização veio da mensagem humana `01a16937-c650-7020-8455-267167263821`,
no chat Frente1 `01a168be-42d9-7873-a069-4f46c3b4cbfe`, conferida pelo Chat3.
O slot foi liberado; não há GO ativo ou orçamento reutilizável.

Preparação/operador nos commits `2c4591c` e `d73e5cc`, clone independente
`/tmp/galaxies-frente-1-envelope-v3`, branch `codex/frente-1-envelope-v3`, sobre
`f5f8d830db48cf68fd3ba7471a7cc1ee1e685347`. Código de reconciliação, testes e
este relatório formam uma unidade posterior, sem alterar o operador congelado.
Integração e publicação continuam exclusivas do Chat3.

As 69 verificações de preparação passaram, com 7 skips específicos da v3
quando parametrizados na v2; o Chat3 as reproduziu. O reconciliador passou
em 11 testes novos inventados em 0,02 s, sem importar operador privado ou iniciar
filhos. Esses testes não contam como casos de validação perceptiva.

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_front1_diagnostic_reconciliation.py
```

O comando real desta rodada não deve ser repetido. Para conferir resultados
posteriormente, reutilizar os leitores de captura e a função de reconciliação
em leitura; o script privado `unit-7-envelope-v3/reconcile_result.py` também
documenta os checks e exige criação exclusiva de seu resultado. Uma nova cópia
de conferência deve usar outro destino de recibo, sem reescrever a evidência.
