# Contraste visual v3: proposta específica, sem execução

Este candidato permite uma comparação local nova de quatro células, condicionada
à aprovação humana específica do plano preparado e à revisão externa que vincule
essa aprovação. Nenhum plano real, autorização, selo, reserva ou inferência foi
produzido nesta implementação. As filas v1/v2 permanecem consumidas e fechadas.

## Hipótese e ganho informacional

No par já revelado, a informação preservada no PNG nativo pode alterar a
discriminação do predicado em relação à cadeia histórica JPEG, redução e
reamostragem. Ambos os braços chegam ao encoder como RGB 360 × 640. O teste
compara essa cadeia inteira; não isola JPEG nem constitui auditoria independente.
Nenhum rótulo, threshold, peso, prompt ou gate muda.

A execução v2 registrou um falso positivo derivado em 53,1219 s, com encoder de
30,076 s e decode completo de 17,892 s. O negativo nativo foi encerrado em
54,9211 s, com encoder de 38,417 s e sete de nove lotes concluídos; o oitavo havia
iniciado. Não houve resposta desse braço. A causa da variação do encoder é
desconhecida. O limite de geração não explica um encerramento antes de concluir
o processamento da imagem.

Uma referência temporal combina o encoder nativo observado com o decode completo
e o restante não localizado do derivado: 38,417 + 17,892 + 5,1539 = 61,4629 s.
75 s úteis acrescentam aproximadamente 22% a essa referência, sem garantia de
conclusão. Aumentar o prazo somente viabiliza a comparação; não corrige percepção.

## Contrato congelado e orçamento novo

A ordem é fixa. O preparo futuro copia os quatro arquivos congelados de v2 byte a
byte, verifica os hashes e a geometria, e não recorta, regenera ou reamostra nada.

| Célula | Resposta de referência | SHA-256 do PNG |
| --- | --- | --- |
| Dneg (`negative-D`) | no | `ee884ab32ba1535291932d38b19f867e28cd833f3e5c1fe6c8dd49228d7ce998` |
| Nneg (`negative-N`) | no | `efa80be09f41f8250aa34c83521585d6a8c64a23f69c5b7eba0da1b4f1aeebfc` |
| Npos (`positive-N`) | yes | `238d3b775563fdffe47c3bfdce9c6623058642194f108107f58fcd9a10ae89e1` |
| Dpos (`positive-D`) | yes | `8727f0e6185cd5f4d859ee7eff34839ac282fb67f54a1e8737d80bcf5f645177` |

O novo namespace é `issue-4-vlm-native-contrast-v3`. Seu limite é quatro chamadas,
80 s por dispatch (75 úteis + cinco para limpeza pelo proprietário original) e
340 s globais, incluindo 20 s de margem para verificações e coordenação entre
dispatches. O comando `prepare` ocorre antes, offline e sem inferência; seu tempo
não faz parte desses 340 s. Permanecem CPU quatro threads,
RSS 3,3 GiB, stdout 16 KiB e stderr 256 KiB. O limite global ou a retenção podem
reduzir o prazo útil; sem cinco segundos de margem nenhuma chamada começa.

Pesos, runtime, prompt curto, schema, seed 42, contexto 3072, geração máxima 64,
batch/ubatch 128, temperatura zero, min=max 1024 e demais flags vêm da configuração
v2 congelada. O plano registra o argv **efetivo**, após as transformações puras
existentes, com apenas os lugares de PNG/schema substituídos no dispatch.
Cada célula exige exatamente 1075 tokens observados, encoder e decode completos,
JSON original válido e limpeza confirmada. O cálculo estático do canvas não
substitui observação. Não há retry, download, custo externo ou envio de dados.

A retenção existente dos quatro PNGs termina em 21/10/2026 às 23h59 de São Paulo.
Preparo e execução recusam retenção expirada. O candidato não prorroga nem remove
arquivos, não toca os oito PNGs protegidos ou o trio demo e não abre o holdout.

## Decisões prévias ao resultado

| Resultado com quatro células tecnicamente válidas | Conclusão permitida |
| --- | --- |
| Nneg=no, Npos=yes e pelo menos um derivado erra (Dneg=yes ou Dpos=no) | Suporte diagnóstico limitado à hipótese neste par revelado. Inclui correção do negativo, do positivo ou de ambos. |
| Nenhum ganho, regressão ou ambos os negativos errados | Hipótese não sustentada; não promover o braço nativo. |
| Ambos os braços corretos em ambos os exemplos | Nenhum benefício nativo demonstrado; preservar o falso positivo derivado anterior no histórico. |
| Qualquer `uncertain` | Inconclusivo/abstenção; não forçar uma decisão. |
| Primeira falha técnica, de identidade, formato, tokens, prazo ou limpeza | Encerrar e selar; fechar todos os slots restantes. Nenhuma retomada. |

A ordem fixa não elimina variação temporal do runtime. Mesmo a primeira linha
não generaliza o efeito nem libera atributos, B/C, M1/A200 ou alteração de produto.
Os gates originais e uma auditoria cega continuam necessários. Não existe
repetição automática, reutilização de saldo, ajuste de threshold ou próximo aumento
de tempo. Resultado inconclusivo ou falta de ganho encerra esta tentativa; qualquer
investigação futura precisaria de hipótese diferente, evidência e nova autorização.

## Identidade, aprovação e durabilidade

Plano/configuração incluem ROOT por hash, revisão externa designada, quatro hashes,
limites, configuração herdada, argv efetivo e hashes das fontes v3 e reutilizadas.
O plano v2 e seu checkpoint selado têm hashes explícitos. Antes de lock, started,
reserva ou Popen, o executor exige os dois recibos externos. Revalida a identidade
antes de cada dispatch, na reserva e no launcher interno.

`authorization.json` deve conter os vínculos do plano/configuração/ROOT/revisor,
namespace/protocolo/limites/quatro hashes, retry falso/custo zero, mensagem humana
nova e literal com hash, e decisão `authorize_exact_four_cell_v3_once`.
`review-seal.json` deve repetir esses vínculos, incluir o hash do arquivo de
autorização, mensagem externa distinta e decisão
`reviewed_exact_v3_plan_and_authorization`. A revisão confere o teor e a proveniência
humana da mensagem; arquivos locais não autenticam por si a identidade de quem
os escreveu. Autorizações consumidas e o pedido genérico anterior são recusados
por digest. A CLI não escreve recibos nem oferece ROOT/modelo/payload/aprovação
arbitrários. Não há saldo atual autorizado.

O helper v3 adapta somente namespace, construção do journal e teto útil de 55 para
75 s. Reutiliza o journal v2, seus validadores estritos, streams, parser e único
proprietário do processo. Mantém o formato de armazenamento v2 para leitura
verificada. Bytes são persistidos e sincronizados antes de chegarem ao coletor;
o stream entregue permanece completo, inclusive para detectar excesso. Prefixo
não equivale a resposta completa. Falha de persistência após spawn continua
entregando o filho ao proprietário para sua limpeza.

SIGTERM/cancelamento e falhas comuns recolhem o grupo e interrompem a sequência.
SIGKILL, queda do kernel ou falha do disco podem impedir o selo final; o marcador
irreversível de início e os journals tornam essa execução consumida/incerta e
impedem reentrada. Não se promete recuperar bytes que o processo ainda não
escreveu nem conclusão de limpeza não comprovada. O diagnóstico por fase é
calculado a partir de captura terminal; prefixos de journal não são promovidos.

## Revisão e preparo futuro

Usar o interpretador já instalado e o diretório do checkout revisto, definidos
pelo operador. Os testes criam somente bytes inventados e subprocessos Python;
não chamam o runtime com pesos nem preparadores de filas reais.

```sh
rtk proxy "$PYTHON" -B -m pytest -q -p no:cacheprovider tests/test_vlm_native_contrast_v3.py
rtk proxy "$RUFF" check --no-cache scripts/vlm_native_contrast_v3.py scripts/vlm_durable_capture_v3.py tests/test_vlm_native_contrast_v3.py
rtk git diff --check
```

Após revisão e integração, o integrador pode fazer o preparo offline no ROOT
principal, antes de pedir autorização específica. Esse comando só copia os quatro
PNGs já congelados e escreve plano/checkpoint inicial no namespace novo:

```sh
rtk proxy "$PYTHON" -B -m scripts.vlm_native_contrast_v3 prepare
rtk proxy "$PYTHON" -B -m scripts.vlm_native_contrast_v3 inspect
```

Conferir os hashes concretos de plano/configuração/fontes e ROOT antes de apresentar
a proposta humana. Somente depois da nova autorização e do recibo externo que a
vincule, a fase `execute` do mesmo módulo poderá ser considerada. Nesta entrega,
nenhuma dessas fases foi chamada contra dados reais. A aprovação mínima futura é
uma tentativa local de até quatro chamadas, quatro PNGs acima, 80 s por dispatch e
340 s globais, custo externo zero, sem retry; não autoriza auditoria, novos dados
ou novos modelos.
