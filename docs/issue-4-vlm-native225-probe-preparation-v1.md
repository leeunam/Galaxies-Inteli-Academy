# Nneg nativa com orçamento 225 — preparação interrompida na integração

Base: `d0f0f02ab78c11e0f296adf3e092ab9b59ee53b8`. Clone independente, sem
dados, ambientes, pesos ou `.env` copiados. **EXECUTION_RELEASED=false** é o
estado desta proposta, não um executor entregue. Não houve preparação de fila,
cópia/abertura do PNG, carregamento, inferência, rede, compilação ou teste.
Nenhuma autorização ou revisão de despacho foi criada.

## Contraste exato proposto

Uma única chamada do negativo Nneg nativo já revelado, SHA-256
`efa80be09f41f8250aa34c83521585d6a8c64a23f69c5b7eba0da1b4f1aeebfc`.
Manter PNG/pixels/tempos, runtime, pesos, threads 4, seed 42, temperatura 0,
contexto 3072, saída 64, batch/ubatch 128, GPU 0, prompt e schema/gramática
originais. Alterar exclusivamente os dois valores de argv de
`--image-min-tokens` e `--image-max-tokens`, de 1024 para 225. A leitura do
template congelado confirmou exatamente duas posições alteradas; nenhum
template foi despachado. Não mudar pergunta, parser ou qualquer extrator.

Pins do plano v3 somente lido: arquivo
`f205e930cd4c7909e6d9c8115636ca4e876246a0792ffa2c1299fad13462f168`,
plano lógico `39ec99f9783e91a99adc063d61541261aea4f62baaaae429b70c31d4c6f36dd3`
e configuração `af1fd2503857a32a849b0e5b20ce64c71c8ba90ab5842afdd65becd354625b6b`.
São proveniência consumida, não autorização para esta nova operação.

Hipótese pelo ramo exato: beta = sqrt((225×1024)/(360×640)) = 1;
canvas 384×640, conteúdo 360×640, offset (12,0), patches 24×40 = 960 e
merger 2×2 → **240 tokens**. É previsão geométrica, sem observação do modelo.
Os 225 solicitados não devem ser tratados como contagem efetiva confirmada.

## Orçamento e critérios antes de qualquer implementação operacional

- Uma inferência no máximo, 55 s úteis + 5 s de término, 80 s globais.
- Preflight de MemAvailable ≥6 GiB e executor único, inclusive antes do spawn;
  RSS cooperativo de 3,3 GiB, stdout 16 KiB e stderr 256 KiB.
- R$0; sem retry, downloads, NIM, novo sampler ou reaproveitamento de saldo.
- PNG expira em 22/10 às 02h59 UTC (21/10 às 23h59 de São Paulo); não estender
  lease ou copiar para escapar da expiração.
- Exigir autorização e revisão específicas vinculadas a plano, configuração,
  fontes, original, argv e limites antes de qualquer spawn. Reserva única
  durável fecha o slot também em timeout, cancelamento ou resultado incerto.
- Persistir fases, raw e resultado terminal antes de limpar somente scratch
  próprio. Manter o original e recibos anteriores; limpeza incerta impede aceite.
- Sucesso técnico exige encoder concluído, exatamente 240 tokens completos,
  JSON inteiro válido e cleanup confirmado. Esperado semântico: `answer=no`;
  `yes` ou `uncertain` falham neste caso. Não aprova positivos, atributos ou B/C.

## Lacuna concreta: namespace e captura selada

`scripts/vlm_durable_capture_v3.py:_folder` constrói o caminho com o namespace
fixo `issue-4-vlm-native-contrast-v3`. `Journal.__init__` chama esse roteador e
`capture` instancia `Journal` diretamente. Não há parâmetro de namespace ou
fábrica de journal por chamada. A implementação reutiliza corretamente o
owner, decoder, limites de streams e tratamento de cancelamento anteriores,
mas não pode escrever no novo namespace sem alterar esse encadeamento.

O controlador atual também é de quatro células; o probe de recursos é uma
operação, porém usa outro namespace fixo e acrescenta sampler não requerido.
Apontar para filas anteriores, mudar constantes globais durante o run, copiar
o supervisor inteiro ou inventar outro dono de processo não é uma adaptação
mínima segura. Uma raiz temporária diferente com o nome antigo também tornaria
a proveniência do novo protocolo ambígua e não foi usada como atalho.

Por isso esta preparação **para aqui**, conforme a condição de parada do
pedido. Não entrega um pseudoexecutor com validações falsas ou teste que
simule prontidão operacional. A decisão necessária é revisar uma pequena
extensão explícita de roteamento/fábrica no helper compartilhado, preservando
comportamento padrão e pinando a nova revisão sem reescrever fontes/recibos
selados. Só depois vincular um controlador de uma operação e seu novo namespace
`issue-4-vlm-native225-probe-v1`. Essa extensão não foi implementada nesta unidade.

## Verificações delimitadas e plano de testes

Uma leitura de `/proc/meminfo` às 00h24 UTC de 22/10 mostrou MemAvailable
**5,21 GiB**; é um snapshot, não diagnóstico do OOM ou previsão de RAM futura.
Já seria motivo de recusa do lançamento real pelo preflight proposto.
Foram lidos apenas código e plano/configuração permitidos para conferir
reutilização, parâmetros e identidade; nenhum peso foi lido.

Testes pequenos futuros devem cobrir, num processo por vez: ausência de
liberação/autorização/revisão antes do spawn; RAM insuficiente; exatamente duas
alterações de argv; uma reserva sem reentrada depois de sucesso/timeout/
cancelamento; tokens 239/240/241, encoder incompleto e JSON inválido; raw/fases
duráveis antes do cleanup e retenção de scratch se cleanup incerto. Usar somente
filhos Python inventados. Esses testes **não foram executados**: não existe
adaptação de namespace candidata para testar sem contornar a lacuna acima.

O próximo marco é uma decisão de integração do helper, não nova inferência.
A principal, demo, partições, teste reservado, M1 e evidências continuam intactos.
