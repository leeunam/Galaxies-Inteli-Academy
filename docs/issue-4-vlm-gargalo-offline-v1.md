# Gargalo VLM: diagnóstico offline do comando e das fases

Não foi demonstrado bug no comando efetivo, na geração ou no preprocessamento.
O timeout da negativa nativa ocorreu durante o decode da imagem, antes da geração
da resposta. A adição `vlm_phase_diagnostic.diagnose` torna essa distinção explícita
usando os eventos terminais já preservados. Não altera captura, execução,
pré-processamento, prompt, modelos, limites ou gates. Nenhuma nova inferência,
aquisição, preparação, reserva ou autorização foi realizada.

## Comando efetivo conferido

A reconstrução aplicou `spatial.command` ao `original_argv` dentro do plano v2.
O argumento herdado contém a instrução longa antiga; o comando final substitui
esse argumento pelo prompt curto sobre a mão segurando e afastando tecido.
Seu schema admite somente a chave `answer` com `yes`, `no` ou `uncertain`.
O [registro sanitizado](evidence/issue-4-vlm-gargalo-offline-v1.json) conserva o
argv final completo com caminhos parametrizados, schema e pins do runtime.

| Configuração efetiva | Valor |
| --- | --- |
| `--n-predict` | 64 |
| `--ctx-size` | 3072 |
| `--threads`, `--threads-batch` | 4 e 4 |
| `--batch-size`, `--ubatch-size` | 128 e 128 |
| `--image-min-tokens`, `--image-max-tokens` | 1024 e 1024 |
| `--temp`, `--seed`, `--verbosity` | 0, 42 e 4 |
| GPU e projector offload | Desligados |
| `--ignore-eos`, template/stop/reasoning explícitos | Ausentes |

O `--help` do binário existente foi consultado sem pesos: saída 0, 29.666 bytes.
A fonte fixada `mtmd-cli.cpp` retorna do processamento de argumentos antes de
inicializar modelos quando se pede ajuda. O help informa Jinja desligado por
padrão e template obtido dos metadados do modelo. Não se inferiu a renderização
exata do template a partir desse default nem se alterou reasoning.

Na fonte `797de63b2`, linhas 543–545, prompt+imagem selecionam single-turn e
`n_predict=64` limita a geração. Nas linhas 612–615, `generate_response` só é
chamada depois de `eval_message` concluir. Nas linhas 217–249, a geração termina
em EOG ou no teto; não há flag para ignorar EOS no comando efetivo. A chamada D
terminou com saída válida e returncode 0. A N não alcançou esse estágio.
Reduzir `n-predict`, mudar EOS ou template não corrige o timeout observado na N.
A quantidade total de tokens textuais não foi registrada; não se inventou essa
contagem ou uma causa por estouro de contexto.

O preprocessamento já provado na fonte resulta em canvas 800×1376, grade 25×43
e 1.075 tokens, com conteúdo 775×1376 e offset [12,0]. Os 1.024 solicitados não
significam exatamente 1.024 observados depois do alinhamento. A D confirmou
1.075; a N incompleta não confirmou seu total. Nove lotes de até 128 correspondem
a oito de 128 e um de 51 no caso completo. Nenhuma mídia foi aberta nesta unidade;
a prova existente e seu código foram lidos, sem executar o preprocessor ou pesos.

## O tempo que faltou

| Intervalo observado | D negativa | N negativa |
| --- | ---: | ---: |
| Encoder reportado | 30,076 s | 38,417 s |
| Decode concluído | 17,892 s, 9/9 lotes | 13,705 s, 7/9 lotes |
| Soma dos intervalos conhecidos | 47,968 s | 52,122 s |
| Duração total | 53,1219 s | 54,9211 s |
| Restante não localizado | 5,1539 s | 2,7991 s |

Os sete primeiros lotes da D somam 13,700 s; os da N, 13,705 s.
O encoder da N demorou 8,341 s a mais. A causa dessa variação permanece
**desconhecida**. Não foi atribuída a pixels, scheduler, temperatura, memória,
Jinja ou journaling. Os journals confirmam EOF dos dois streams, limpeza e
18.772/19.436 bytes de stderr, abaixo do teto de 262.144.

Na N, o oitavo lote começou e não terminou. Seus 896 tokens em lotes concluídos
e 1.024 em lotes iniciados não viram um total de tokens confirmado. O restante
não localizado inclui lote em voo e quaisquer tempos não cobertos pelos eventos;
na D pode incluir inicialização, texto, geração e supervisão. Não é uma medição
isolada da geração nem da sobrecarga de captura.

O teto de 60 s reservava 5 s para limpeza, deixando aproximadamente 55 s úteis.
Só encoder+sete lotes da N já consumiram 52,122 s. Como referência aritmética,
38,417 s do encoder N + 17,892 s do decode completo D + 5,1539 s restantes da D
somam **61,4629 s úteis**. Essa combinação não é previsão de duração nem prova
sobre o tempo de outro criativo; evidencia por que 55 s não ofereciam margem
para completar a observação nativa que já havia chegado ao oitavo lote.

## Adição e verificação

A função pura aceita capturas terminais verificadas, com coleta completa do
stderr limitado e limpeza confirmada. Valida prefixos ordenados de eventos,
lotes correspondentes, inteiros e tempos coerentes. Localiza encoder/decode
incompletos; depois do decode completo mantém a fase posterior desconhecida.
Recusa coleta truncada por oversize, sucesso sem imagem completa, contagens
inconsistentes e stdout de resposta junto a um prefixo de imagem incompleto.
Não consulta filas, arquivos, modelo ou rede e não concede orçamento.

Os testes usam somente sequências e argv inventados. Discriminam lote iniciado
versus concluído, falhas durante encoder versus decode, timeout depois do decode
sem atribuí-lo à geração, corrupção de sequência e a substituição real do prompt
herdado pela cadeia `spatial.command`. A evidência real foi analisada em leitura
após esses testes; não é fixture de teste ou nova anotação perceptiva.

```sh
rtk proxy "$PYTHON" -B -m pytest -q -p no:cacheprovider tests/test_vlm_phase_diagnostic.py tests/test_vlm_short_answer_capture.py tests/test_vlm_native_contrast.py tests/test_vlm_native_contrast_v2.py
rtk proxy "$PYTHON" -B -m ruff check --no-cache scripts/vlm_phase_diagnostic.py tests/test_vlm_phase_diagnostic.py
rtk proxy "$PYTHON" -B -m ruff format --no-cache --check scripts/vlm_phase_diagnostic.py tests/test_vlm_phase_diagnostic.py
```

## Próxima comparação, somente se receber nova autorização

Para conservar o contraste completo, a proposta é quatro chamadas locais nas
mesmas células Dneg/Nneg/Npos/Dpos, com todos os pesos, runtime, prompt/schema,
flags, hashes e gates preservados; 1.075 tokens observados e decode completo
continuam necessários. Nenhum download, retry automático ou despesa externa.
Propõe-se **80 s por dispatch, incluindo 5 s para limpeza, e 340 s globais**
(quatro vezes 80 mais 20 de preparação). Os 75 s úteis acomodam a referência de
61,4629 s com aproximadamente 20% de margem; não garantem conclusão ou acerto.

Isso exige outra autorização e protocolo próprios. As filas v1/v2 continuam
seladas e seus saldos encerrados. Nenhuma fila nova foi preparada. A retenção
atual dos quatro PNGs permanece em 21/10/2026, 23h59 de São Paulo. Os oito PNGs
protegidos, trio da demo, teste reservado, M1 e A200 não foram alterados.
O ganho possível é completar a comparação diagnóstica no par já revelado;
não resolve por si o falso positivo D nem valida atributos ou B/C.
