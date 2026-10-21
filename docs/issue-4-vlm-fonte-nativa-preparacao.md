# Recuperação nativa do par: preparação sem aquisição

Unidade aditiva do [plano proposto](issue-4-vlm-fonte-nativa-proposta.md).
Implementa somente a recuperação e a ponte de dois casos de treino já revelados.
**Código/testes offline autorizados; aquisição ainda pendente de decisão
específica do pai e revisão técnica vinculada.** Nenhum modelo, download,
novo rótulo, novo peso, cookie, credencial ou API de métricas faz parte da preparação.

## Fronteira reutilizada

O controlador `vlm_native_source_recovery.py` reutiliza, sem alterar fontes
anteriores, `download_command`, `guarded_command`, `run_lock`,
`quiescent_receipts` e `clean_scratch` de `demo_recovery.py`.
O mesmo subreaper, pidfds, limites e child `RLIMIT_FSIZE` continuam responsáveis
pelos processos. Não foi criado supervisor, downloader alternativo ou serviço.

Cada fonte usa dois jobs sequenciais: downloader com rede, depois ponte de
pixels em sandbox com `--unshare-net`. O segundo job usa somente PyAV/Pillow
e as funções de preparação antigas. Ele não chama o extrator de features,
ASR, CLIP, Qwen, NIM ou treino. Imports dos módulos antigos não executam modelos.

| Limite efetivo | Valor |
| --- | --- |
| Tentativas de fonte / geração | 2 / 0 |
| Janela por fonte / global | 180 s / 420 s |
| Jobs úteis | até 80 s de download + até 20 s de ponte |
| Margem de recolhimento | até 50 s por job em encerramento incerto |
| Arquivo / workspace | 32 MiB / 128 MiB |
| RSS / stdout / stderr | 3,3 GiB / 64 KiB / 64 KiB |
| Retry / substituição / paralelismo de fontes | 0 / 0 / 1 |

Os 100 s úteis são mais restritos que o teto útil de 150 s proposto.
A redução reserva também o caminho de falha do wrapper existente: um download
concluído pode usar 30 s de coleta/ack, e a ponte ainda dispõe de 20 s úteis
mais 50 s para encerramento incerto do supervisor. Se o download falhar,
não haverá ponte. Os jobs encolhem para respeitar o restante da janela por fonte.
O relógio global começa
antes dos preflights, nunca reinicia e reduz os jobs quando falta orçamento
ou aproxima a expiração. Os mesmos limites de socket 20 s, taxa 5 MiB/s,
seletor histórico, retries 0, configuração ignorada e plugins remotos ausentes
são mantidos. Duas tentativas não significam duas conexões HTTP.

RSS/workspace são amostrados a 50 ms; não há promessa de teto instantâneo
entre amostras. Cleanup irrecuperável, morte do pai/host ou ausência de ack
conservam o consumo e impedem reentrada; não há garantia artificial de
remoção. O lease do supervisor existente registra a necessidade de recuperação
manual sem confirmação. Nenhuma falha autoriza outra tentativa.

## Plano, revisão e execução

`prepare` cria somente o plano privado novo, por criação exclusiva.
Ele vincula o SHA da proposta já revisada, o plano histórico de linhas,
as duas identidades/URLs/PTS, receitas e propriedades, oito folhas/proteções,
fontes novas e herdadas, lock, versões de av/Pillow/numpy/yt-dlp e hashes dos
executáveis Python/ffmpeg/node/bwrap existentes. Exige a versão histórica
do downloader e partição de treino nas duas linhas. Não lê o teste reservado.

`inspect` reconfere a configuração, sem aquisição ou geração.
`acquire` exige revisão no namespace próprio, com exatamente:

- protocolo `revealed-pair-native-source-recovery-v1`;
- decisão `approved_for_two_source_recoveries_no_generation`;
- SHA do plano e configuração final;
- SHA dos bytesUTF-8 do caminho resolvido da árvore executora;
- ID do chat revisor, ID real da mensagem de origem;
- mensagem literal da liberação e seu SHA-256.

A revisão é uma guarda de integridade/coordenação; não autentica contra o
proprietário dos arquivos. Nenhum CLI cria aprovação. Fontes alteradas depois
do plano invalidam a execução; não reaproveitar revisão de filas antigas.
Ausência de liberação ou retenção expirada recusa antes de criar o run.
Diretório de run existente consome a etapa mesmo se a inicialização foi interrompida.

Na raiz da árvore executora, a preparação permitida é:

```sh
rtk proxy .venv/bin/python -B -m scripts.vlm_native_source_recovery prepare
rtk proxy .venv/bin/python -B -m scripts.vlm_native_source_recovery inspect
```

**Comando futuro exato, não executado nesta preparação**, somente depois da
decisão de aquisição, revisão e janela sem workers concorrentes:

```sh
rtk proxy .venv/bin/python -B -m scripts.vlm_native_source_recovery acquire
```

Não há parâmetros de URL, outro caso, formato, orçamento, modelo ou retry.
IDs, localizadores, jobs e recibos permanecem privados; stdout público só
contém status, hashes e contadores. Nenhuma credencial é necessária.

## Ponte antes de reter qualquer PNG

Para cada fonte: reserva durável antes do downloader, identidade canônica
estrita, arquivo único de até 32 MiB e cleanup de rede confirmado.
Sem remux adicional; o contêiner selecionado pelo comando histórico é
decodificado diretamente. O adaptador offline então:

1. reconfere plano, reserva e confirmação do job de rede;
2. exige todas as propriedades históricas iguais;
3. exige os quatro tempos selecionados e o PTS do crop congelado;
4. reproduz a folha inteira por SHA-256 e o crop específico por SHA-256;
5. decodifica exatamente o PTS pedido no mesmo arquivo, sem aproximação,
   thumbnail ou JPEG, e exige RGB 360× 640;
6. salva um PNG novo somente após toda a ponte passar.

O pai aceita apenas projeção fechada correspondente a essas identidades,
confere hash/geometria do PNG e bytes da mídia, depois copia por criação
exclusiva e reconfere o hash. Falha de propriedade/PTS/pixels/identidade,
limite ou cleanup encerra toda a etapa antes da segunda fonte.
Uma falha semântica observada do adaptador usa código estático; processo
concluído não equivale a ponte aprovada. Não se retém exceção arbitrária.

Bytes de contêiner diferentes são registrados, sem alegar identidade nativa
histórica indisponível. A ponte valida a reprodução do derivado e a origem da
nova extração, não novos rótulos ou qualidade perceptiva.

## Retenção, falhas e verificações

Somente os dois PNGs verificados (ou parcialidade explicitamente registrada)
e recibos novos ficam para revisão até **21/10/2026,23h 59 São Paulo**.
Não há timer nem exclusão automática dos PNGs retidos. Mídia/partes/JPEGs e
scratch próprios são removidos somente com todos os acks de cleanup válidos.
Sem ack, scratch é preservado e resultado terminal explicita incerteza.

O run é um diretório novo fixo, sem symlinks, separado de qualquer fila antiga.
O código não possui descarte de inputs preexistentes. Oito folhas, M 1, coortes,
holdout, recibos NIM consumidos e os três inputs de demo até 23/10 ficam protegidos.
Nenhuma mudança de extrator, atributo, gate ou aprovação B/C é feita.

Testes usam apenas pixels inventados, supervisores falsos e guardas contra
processo, socket e chave. Cobrem reserva anterior ao spawn, dois casos/ordem,
fechamento da etapa, reentrada, revisão/árvore/plano, expiração, orçamento que
não reinicia, symlink, retenção do scratch incerto e ponte antes de PNG.
Não repetem as suítes antigas do supervisor e não contam como validação real
de aquisição ou de provedor. Preparação e revisão devem registrar seus checks
antes de qualquer download. Nenhuma geração é autorizada nem após a recuperação.

Nesta preparação passaram **36 testes inventados**, Ruff e formatação dos três
arquivos novos. A configuração real foi conferida sem processo de mídia ou
modelo: os tempos selecionados permanecem 0,2/1,5/2,8/11,367 s no positivo e
0,2/1,5/2,8/35,333 s no negativo. O frame nativo exige exatamente 0,2 ou 2,8 s;
não se ajustou PTS para obter uma ponte válida. O teste do wrapper existente
confirma a criação de `alias-bridge` antes da tentativa de spawn, sem criar filho.
