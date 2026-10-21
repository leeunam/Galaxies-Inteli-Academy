# Adendo mínimo: um positivo com logger em nível 4

Proposta em 21/10/2026 após a [parada documentada](issue-4-vlm-encoder-resultados.md).
Não altera o código, plano ou recibos selados da fila anterior. A execução
depende de revisão técnica vinculada aos novos hashes e nova janela CPU.

## Hipótese e evidência local

Os logs diretos da CLI apareceram em nível 3. Os dois logs do helper usam
nível interno 2, que o callback instalado converte para verbosidade 4.
Disassembly dos ELF identificou as duas chamadas e o filtro. Uma chamada
**pura** à função exportada `common_log_get_verbosity` da biblioteca instalada
confirmou `[5, 4, 2, 1, 4]` para níveis internos 1–5, sem carregar pesos ou
executar inferência. O recibo privado vincula o hash da biblioteca.

O adendo troca somente **3 → 4** em relação ao ensaio anterior. Conserva
o positivo conhecido, crop RGB 320×330 em 0,2 s, prompt/schema ordenado
`item_first`, modelo, projetor, contexto, tokens, seed e temperatura.
Não chama o branco. O nível 5, que habilita dump de prompt no fonte CLI,
permanece proibido. Linhas desconhecidas de nível 4 são descartadas; nenhum
texto bruto ou hash de texto rejeitado é persistido.

## Fila e limites

- Fila nova única: `data/private/issue-4-vlm-encoder-trace-v1/`.
- **Uma chamada**, **90 s globais** desde o marcador, com reserva conjunta
  de cinco segundos para limpeza dentro do saldo; nenhum retry/reentrada.
- RSS amostrado de 3,3 GiB; stdout 16 KiB e stderr 256 KiB.
- Zero aquisições, chamadas externas, treino, holdout, troca de M1 ou casos novos.
- Reutiliza captura, eventos, parser e verificação dos casos já testados;
  não modifica o adaptador histórico nem relaxa o critério do diagnóstico.

O plano vincula fontes, configuração anterior, resultado/checkpoint encerrados
e recibo da função pura. O PNG deve reproduzir o hash congelado antes e
depois da chamada. A revisão deve conter o ID real e a decisão literal.
Reserva durável antes de spawn; marcador exclusivo impede repetir resultado
incerto. Persistir diagnóstico sanitizado antes de remover scratch próprio.
Limpeza incerta conserva scratch e sela a fila.

Exigir encoder início/fim, batches de imagem completos/ordenados com tokens
positivos, retorno 0 e stdout validado pelo decoder original. Falha operacional,
marcador insuficiente, saída inválida ou limpeza incerta encerram. Não aumentar
verbosidade, resolução, tokens ou modelo automaticamente após falha.

Sucesso provará somente o percurso visual observado e sua contagem de tokens.
Qualidade da representação e uso semântico continuam sem prova; gates originais,
auditoria cega e B/C não são aprovados por esse caso conhecido. Qualquer contraste
posterior de gramática/percepção exige plano próprio.
