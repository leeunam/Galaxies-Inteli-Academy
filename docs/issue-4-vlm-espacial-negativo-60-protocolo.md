# Diagnóstico negativo único: dispatch de 60 s

Unidade aditiva de preparação em 21/10/2026, com orçamento técnico novo,
independente da [fila encerrada por timeout](issue-4-vlm-espacial-1024-resultados.md).
Não modifica fontes/planos/recibos anteriores ou reaproveita seu saldo.
Modelo aguarda revisão concreta dos hashes e janela CPU; nenhuma geração
é autorizada apenas pela criação do plano. Não envolve NIM ou HTTP.

## Fundamento e escopo

A tentativa anterior concluiu o encoder em 29,482 s, completou cinco batches
de decoder com cerca de 1,5 s cada e iniciou o sexto de nove anunciados.
O prazo útil de 40 s terminou antes da resposta. Esse custo observado
fundamenta testar um prazo técnico maior, sem garantir conclusão.
O teto agora é 60 s por dispatch, incluindo cinco segundos de limpeza;
até 55 s úteis para a sessão. O relógio global fica em 70 s, com dez
segundos previstos para preparação/bookkeeping. Não ampliar esses limites.

Executar **somente o negativo real revelado da V14**, mesmo frame 3 a 2,8 s,
PNG RGB 320×330, hash/proveniência/esperado diagnóstico `no` já congelados.
Não há chamada positiva, seleção nova, aquisição ou anotação certificada nova.
Identidades e localizadores de mídia permanecem somente nos recibos privados.

Prompt, schema e gramática ligada, modelo/projetor, seed 42, temperatura zero,
contexto 3.072, saída 64, quatro threads CPU/batch, batch/ubatch 128,
verbosidade 4 e min/max de imagem **1.024/1.024** são idênticos à tentativa
espacial anterior. O argv nativo deve ser byte a byte igual após normalizar
apenas caminhos temporários. A mudança é o orçamento externo de execução.

O upscale interno não acrescenta detalhes nativos. A hipótese espacial
continua pendente: o ensaio anterior não produziu resposta semântica.
Nem o aviso de grounding nem a nova allowance demonstram qualidade do modelo.

## Medição e desfechos

Reutilizar a captura limitada, parser curto estrito, eventos e verificação
de intervenção. Exigir retorno 0, encoder/decodificação completos/ordenados,
limites íntegros e cleanup confirmado. Medir tokens reais; não presumir
exatamente 1.024 ou 1.056. Intervenção efetiva exige contagem inteira maior
que os 100 tokens da referência, sem retuning para perseguir número exato.

| Resultado | Leitura permitida |
|---|---|
| `no` válido, técnica/intervenção íntegras | Apoio pontual no negativo, sem avaliação do positivo ou aprovação de candidata. |
| `yes` válido | Não apoia a hipótese como correção desse negativo. |
| `uncertain` válido | Abstenção, separada de acerto/erro. |
| JSON inválido | `format_invalid`, sem extração, coerção ou reparo. |
| Falha técnica ou intervenção sem aumento | Sem comparação semântica; fila parcial/encerrada conforme o recibo. |

Todos os resultados encerram esta unidade de uma chamada. Não repetir,
substituir crop, chamar positivo ou ajustar prompt/flags após observar a saída.
O modo livre e o orçamento baixo anteriores são referências históricas,
sem apresentar isso como ablação contemporânea completa ou causa ampla da V16.

## Guardas e consumo

- Uma chamada, 70 s globais, até 60 s por dispatch incluindo cinco de cleanup.
- RSS amostrado 3,3 GiB; stdout 16 KiB / stderr 256 KiB; tee adicional
  de stdout limitado a 16 KiB. Ambiente literal offline, sem chave ou proxy.
- Zero remoto, aquisição, novo peso/caso, treino, holdout ou promoção de M1.
- Namespace novo único; marcador de início impede reentrada inclusive antes
  da reserva. Consumo durável antes do único spawn; incerteza não devolve saldo.
- Recibo sanitizado antes da limpeza. Timeout/RSS/bytes, identidade, encoder
  incerto, intervenção não efetiva ou cleanup incerto são terminais.
  Cleanup não confirmado conserva scratch próprio, sem promessa de recolhimento
  instantâneo após morte do pai/host.

Plano vincula caso, fontes, argv, referência do timeout selado e limites novos.
O helper continua exigindo decisão `released_for_this_perception_contrast_only`,
vinculada aos hashes **desta unidade**, com ID real/literal da revisão.
Não criar aprovação na preparação nem usar a revisão das filas anteriores.
Nenhum corpo bruto, exceção arbitrária ou hash de resposta rejeitada é retido.

## Preflight e preservação

Sem modelo: conferir referências/fontes/recibos anteriores, reproduzir o único
PNG, verificar identidade de argv/schema e custo de preparação. Reutilizar
o recibo da mesma gramática já verificada, sem recompilar ou repetir sua bateria.
Testes inventados devem cobrir 1/60/70, reserva prévia, recibo antes da limpeza,
desfechos separados, parada técnica/intervenção, ausência de positivo e reentrada.

Mesmo eventual `no` não aprova atributos: positivo em alta densidade segue não
avaliado, e gates originais/auditoria independente continuam necessários.
Partições, teste reservado, M1 e oito folhas permanecem preservados. B/C e
qualidade científica não serão declarados concluídos por esse diagnóstico.
