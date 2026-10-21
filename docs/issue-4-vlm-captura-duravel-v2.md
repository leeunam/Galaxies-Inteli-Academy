# Captura durável aditiva da comparação visual

O helper `scripts/vlm_durable_capture_v2.py` preserva stdout original limitado e
progresso sanitizado antes do retorno do controlador. Esta unidade foi verificada
somente com bytes inventados e filhos Python descartáveis. Não executou modelo,
decodificador de mídia, aquisição, rede, instalação ou leitura de credenciais.
Não mede percepção e não identifica a causa da interrupção histórica.

O código é aditivo ao commit-base
`4d374b546c032434dab72f8063a0185a8aedb5d2`. O coletor
`vlm_encoder_probe.capture`, o parser `vlm_short_answer_capture.decode` e o
controlador anterior permanecem intactos. O namespace novo é
`data/private/issue-4-vlm-native-contrast-v2/captures/<cell>`.
A fila v1 selada, suas reservas, os três slots fechados e seus resultados incertos
não podem ser reutilizados. Nenhum plano, reserva, revisão ou release real foi
criado por esta unidade.

## Interface e persistência

A interface é `capture(argv, root, cell, seconds, reserve, popen)`, com argumentos
nomeados após `argv`. Não há launcher padrão: ausência de `popen` falha antes de
criar diretórios. Injetar um launcher é um mecanismo de integração e teste, sem
valor de autorização. Não há CLI de execução ou preparação. A única CLI faz
inspeção em leitura:

```sh
rtk proxy "$PYTHON" -B -m scripts.vlm_durable_capture_v2 --root "$CHECKOUT" --cell negative-D
```

O diretório exclusivo da célula impede reentrada mesmo após falha anterior à
reserva. Cada componente é aberto por descriptor com `O_NOFOLLOW`; arquivos
novos usam criação exclusiva e modo 0600, diretórios privados usam 0700.
A raiz não pode conter o componente `private`, impedindo aninhar esta captura
em uma fila histórica. A inspeção também recusa symlinks, arquivos especiais,
hardlinks e arquivos acima dos limites.

O coletor congelado continua sendo o único dono do processo: faz spawn,
monitoramento, encerramento do grupo e `wait`. O wrapper devolve esse processo
ao dono mesmo se a publicação da identidade falhar após o spawn. Erros de
leitura ou persistência são sinalizados ao dono e impedem publicar resultado
terminal aceito. Nenhuma exceção bruta é serializada.

`read1` expõe bytes disponíveis sem esperar 4096 bytes ou EOF. Os bytes originais
retornam ao coletor sem recorte ou normalização. Cada prefixo de stdout dentro
do teto passa por escrita e `fsync` antes do checkpoint e do retorno ao parser.
Uma falha nessa cadeia invalida a captura; bytes sem checkpoint confirmado não
são promovidos a resposta. O parser e a classificação técnica são os originais.
O metadado `raw_stdout_retained` passa a `true`, refletindo a retenção privada
aditiva; stderr bruto não é persistido nem tem seu hash publicado.

O checkpoint é JSON atômico com `fsync` do arquivo e do diretório. Seu comprimento
e hash vinculam somente o prefixo confirmado de stdout. Uma cauda de bytes ainda
sem checkpoint é ignorada. Arquivos `.pending` incompletos nunca substituem o
último checkpoint válido. As fases são `created`, `reserved`, `process_started`,
`collecting` e `returned`; um prefixo permanece não terminal e sem confirmação
de limpeza. Linhas incompletas de stderr só são avaliadas no EOF. O progresso
intermediário é sempre provisório, mesmo se já contém eventos completos.

A inspeção valida JSON sem duplicatas/NaN, tipos, chaves, fases, integridade do
prefixo e do resultado, valores fechados de eventos/erros e consistência dos
tokens com o parser congelado. Uma resposta aceita deve corresponder ao stdout
original. Um resultado com processo iniciado exige lease de identidade real;
limpeza terminal exige EOF dos dois streams e returncode. Isso detecta corrupção
e inconsistência, sem autenticar contra alguém capaz de reescrever todos os
arquivos como o mesmo usuário.

## Limites e lacunas

| Item | Limite desta camada |
| --- | --- |
| Stdout original privado | 16.384 bytes |
| Stderr em memória | 262.144 bytes, mesmo teto herdado |
| Progresso persistido | Últimos 32 eventos; até 16 falhas e 16 avisos |
| Checkpoint e lease | Até 32.768 bytes por arquivo |
| Resultado terminal | Até 1.048.576 bytes |
| Prazo aceito pelo helper | Maior que zero e até 55 segundos |
| Limpeza do coletor herdado | Até 5 segundos adicionais |
| RSS do processo | Mesmo limite herdado de 3,3 GiB |
| Reentrada e retry | Proibidos |

SIGINT e SIGTERM cooperativos produzem cancelamento e limpeza pelo dono original.
Um sinal durante o wait final também impede sucesso. Se chegar durante o commit
terminal, interrompe o chamador antes de permitir a próxima célula, preservando
o resultado que eventualmente já tenha sido gravado.
SIGKILL do dono ou queda da máquina podem deixar apenas prefixo/lease e um filho
vivo. O helper não promete limpeza automática após essa morte. Há também uma
janela entre spawn e publicação do lease e entre resultado e checkpoint final.
A ausência do recibo final permanece incerta, mesmo com bytes aparentemente
válidos. Testes de crash não equivalem a teste de perda de energia ou de falha
real do dispositivo de armazenamento. `fsync` bloqueante não oferece um prazo
absoluto; a integração futura precisa contabilizar preparação, persistência e
limpeza no teto externo de cada chamada e no teto global.

Os testes de SIGKILL adotam e recolhem o filho inventado com subreaper apenas no
processo de teste, verificando sua identidade real antes do sinal. O helper não
instala um segundo dono ou um supervisor novo. A limpeza herdada do grupo não é
uma nova garantia sobre descendentes que escapem desse grupo.

A retenção existente dos insumos termina em 21/10/2026 às 23h59 de São Paulo.
Esta unidade não estende retenção nem descarta qualquer insumo. O controlador
futuro deve aplicar prazo e descarte aos novos arquivos privados de captura;
este helper não agenda descarte autônomo.

## Verificação local

A suíte direcionada cobre 33 testes novos e 42 testes existentes, total de 75.
O comando usa o Python já existente, sem escrever no ambiente original ou no
cache do projeto:

```sh
rtk proxy "$PYTHON" -B -m pytest -q -p no:cacheprovider tests/test_vlm_durable_capture_v2.py tests/test_vlm_short_answer_capture.py tests/test_vlm_native_contrast.py
rtk proxy "$PYTHON" -B -m ruff check --no-cache scripts/vlm_durable_capture_v2.py tests/test_vlm_durable_capture_v2.py
rtk proxy "$PYTHON" -B -m ruff format --no-cache --check scripts/vlm_durable_capture_v2.py tests/test_vlm_durable_capture_v2.py
```

As verificações novas incluem stdout Unicode inválido/duplicado, transparência,
progressão antes de EOF, oversize em ambos os streams, timeout, cancelamento,
SIGKILL com prefixo conservado, criação exclusiva, symlink/hardlink, checkpoint
parcial, adulteração de prefixo, falha antes e depois de spawn, falha de leitura,
metadados desconhecidos/duplicados/não finitos e resultado re-hasheado incompatível
com os bytes ou com os eventos. A falha de escrita após spawn foi injetada por
colisão do arquivo exclusivo de checkpoint; o processo real foi recolhido.
Não há PID falso, monkeypatch global ou subprocesso de modelo nos testes novos.

## Ligação ainda necessária antes de nova inferência

Ainda falta um controlador v2 revisado que verifique identidade de código,
configuração, entradas e autoridade; valide nova autorização específica;
registre reservas exclusivas; respeite os prazos incluindo esta persistência;
e una os quatro resultados. A existência deste helper não libera inferência.
Não chamar `execute` da v1 nem adaptar seus saldos fechados.

A menor comparação que produz informação perceptiva continua sendo quatro
chamadas locais, uma por célula na ordem Dneg/Nneg/Npos/Dpos, sobre os dois PNGs
nativos e os dois derivados já retidos. Sem download, retry, troca de pesos,
runtime, prompt, schema ou flags; R$0 de despesa nova. Geometria RGB 360×640,
min=max 1024 e 1.075 tokens observados, com decode completo em cada chamada,
continuam obrigatórios. Até 60 segundos por dispatch e 260 segundos globais,
incluindo preparação e limpeza. Essa nova autorização não existe nesta entrega
e não pode ser inferida da autorização consumida.

Os quatro hashes e as identidades de plano/configuração anteriores devem ser
vinculados pelo controlador seguinte, sem copiar mídia para este checkout.
A fonte C++ calcula 1.075 tokens, mas só o encoder real poderá observá-los.
O ganho científico continua condicionado a quatro observações completas do par
já revelado; não é auditoria independente, aprovação de atributos ou liberação
B/C. A hipótese perceptiva original permanece não testada.
