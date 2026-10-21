# Diagnóstico direto do encoder: execução encerrada

Em 21/10/2026, o [protocolo de duas chamadas](issue-4-vlm-encoder-protocolo.md)
encerrou após a primeira por `diagnostics_insufficient`. O crop positivo foi
codificado, com início/fim observados; os eventos exigidos da decodificação
não foram reconhecidos. O branco não foi chamado e o saldo não será reutilizado.
Os [agregados verificáveis](evidence/issue-4-vlm-encoder-resultados.json) vinculam
plano, configuração, revisão e recibos, sem texto livre ou pixels.

## Evidência medida

| Medida | Resultado |
|---|---|
| Implementação | `3a4fe4c` |
| Chamadas / aquisições / NIM | 1 / 0 / 0 |
| Relógio global | 14,2671 s de 180 s |
| Sessão nativa | 14,1929 s; retorno 0 |
| Pico RSS amostrado | 2.601,707 MiB; teto 3,3 GiB |
| stdout / stderr recebidos | 125 / 1.145 bytes |
| Codificação | 1 chunk; início `(1, 1, 3)`; fim em 1.987 ms |
| Decodificação / tokens | sem eventos reconhecidos; contagem indisponível |
| Contrato original de saída | JSON válido `item_first`, projeção `true` |
| Limpeza / workers ao terminar | confirmada / zero |

O recibo nativo validado contém `hand_holds_hanger_out`, `presented_target`
e `garment`. Isso é a resposta do modelo ao positivo conhecido; não é nova
anotação nem evidência de aprovação perceptiva. A combinação início/fim
confirma a chamada bem-sucedida a `mtmd_batch_encode` no caminho de mídia
do fonte CLI verificado. Não há contagem observada de tokens nem captura
de embeddings/atenção. O requisito integral do diagnóstico não passou.

A reserva foi persistida antes do processo. Resultado sanitizado foi
persistido antes da remoção do scratch. O checkpoint está selado com uma
operação concluída, sem segunda reserva e sem retry. O stderr bruto foi
descartado: não se pode reconstruir quais linhas desconhecidas ele continha.

## Causa estática da lacuna de observabilidade

A inspeção posterior dos binários locais, sem outra chamada com modelo,
encontrou uma diferença entre os logs diretos da CLI e o callback do helper:

- `mtmd-cli.cpp:530` liga o helper a `common_log_default_callback`.
- `libmtmd.so.0.7.0` usa argumento interno de nível **2** para os dois
  formatos `decoding %s batch...` e `%s decoded (batch...)`: instruções
  `0xe2d93` e `0xe3303`, respectivamente.
- Em `libllama-common.so`, `common_log_get_verbosity`, endereço `0x2ff990`,
  consulta a tabela em `0x45a800`: níveis internos 1–5 mapeiam para
  `[5, 4, 2, 1, 4]`. O nível 2 requer, portanto, verbosidade **4**.
- O callback em `0x2ffa60` descarta o evento quando seu nível mapeado excede
  o limiar. O ensaio conservou o limiar **3** aprovado.

Essa leitura explica por que o plano não podia exigir os eventos do helper
nesse limiar. Não prova a qualidade do encoder, nem permite recuperar a
contagem do processo encerrado. A falha foi do desenho de observabilidade;
o gate foi aplicado corretamente e a ausência de marcadores não foi tratada
como falha perceptiva. As identidades dos dois ELF e os endereços ficaram
no recibo privado `post-run-logger-static.json`, fora do versionamento.

## Próxima correção proposta

Preparar **outra** fila mínima com o mesmo positivo congelado,
`item_first`, modelo, projetor, prompt, schema, seed, temperatura, pixels,
tempos e limites de memória/saída, mudando apenas verbosidade **3 → 4**. Seria uma
chamada e 90 s globais novos, com a mesma parada na primeira insuficiência,
consumo prévio, canais separados e filtro estrito. Antes, verificar estaticamente
que o nível 4 não habilita o dump de prompt do nível 5; conservar limites de
bytes e descarte de linhas desconhecidas. Essa proposta ainda não foi executada
ou reservada e não reabre a fila encerrada.

Só após comprovar os eventos de inserção e tokens reais faria sentido selar
um contraste de gramática/percepção. As quatro chamadas opcionais descritas
no protocolo continuam fora do orçamento executado e não estão habilitadas.
Não há correção semântica, auditoria cega ou treino B/C liberados por este ensaio.

## Verificação e preservação

Passaram 23 testes direcionados com processos/pixels inventados e rede
proibida, Ruff e formatação. A preparação reproduziu os dois PNGs por hash
e comprovou que somente a verbosidade difere no argv normalizado. Após a
execução, os 26 arquivos protegidos e a configuração selada conferem,
incluindo as oito folhas e os recibos antigos; identidades anteriores dos
pesos foram conferidas por metadados, sem nova leitura integral dos GGUF.
Zero workers e zero scratch deste ensaio ao terminar. Partições, teste
reservado, M1 e autorizações encerradas permanecem preservados. Nenhum
campo, candidata ou modelo foi promovido.

Plano: `cd8da6d6bc62cf217b457597222929f9e670cc4b9301e7313fddd6a6e32f2721`.
Configuração: `afc43f2b718ca20f59c184a0368a644218d189af40924f55a9e9e830d6016624`.
Fila privada: `data/private/issue-4-vlm-encoder-probe-v1/`.
