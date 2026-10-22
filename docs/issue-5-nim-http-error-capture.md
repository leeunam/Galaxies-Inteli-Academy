# Captura de erros HTTP da NVIDIA

A preparação do cliente existente agora preserva erros no nível principal e em
`error`, incluindo a mensagem histórica `ResourceExhausted`. Uma função pura em
`scripts/nim_http_error_diagnostic.py` faz a projeção; ela não abre conexões,
não lê credenciais e não possui CLI ou dispatcher.

O cliente da rodada consumida e as fontes fixadas nos planos anteriores continuam
byte a byte iguais. A cópia de preparação de `control_worker.py` foi corrigida
para chamar essa função. SHA-256 dessa cópia: `babb2ba226268e0b5ba4da7e7ac09c7d6b6c44d8ecb7b4066905ac30cc5bf8fb`.
Essa preparação não libera o plano consumido nem permite reutilizar seu ledger.

- Corpo: leitura de até 16 KiB mais um byte sentinela; excesso e conteúdo não JSON
  não são copiados. Apenas `code/type/message/detail/title/status`, na raiz ou em
  `error`, são projetados, com até 256 bytes UTF-8 por valor, após redação.
- Cabeçalhos: somente `nvcf-reqid`, `x-request-id`, `content-type`,
  `content-length`, `date` e `retry-after`; valores duplicados, inválidos ou fora
  de 128 caracteres são omitidos. IDs devem ser UUIDs. Datas e números são normalizados.
- Chave em memória, Bearer, credenciais identificáveis, URLs, data URIs e blocos
  longos de token/base64 são removidos antes do corte. Authorization, cookies e
  cabeçalhos desconhecidos nunca são consultados pelo capturador.
- HTTP 200 permanece sob a autoridade anterior. O capturador recusa ler seu corpo.
  Nenhum limite científico, endpoint, payload, retry ou critério foi alterado.

Verificação: 21 testes públicos passaram; cobrem o erro conhecido principal/aninhado,
401/403/429/503, redação, truncamento e limites. O transporte falso confere os
10.065 bytes/SHA do pedido textual histórico. Mais sete casos falsos executaram
apenas a função `exchange` da preparação corrigida, incluindo 200 e os erros acima.
Os testes não chamaram dispatcher, credencial real, modelo ou rede.

O [plano de reteste](evidence/issue-5-nim-http-diagnostic-retest-inactive.json) está
**inativo**: zero chamadas liberadas, autorização e comando de envio ausentes.
SHA-256: `2bbcd16f50cc3116e288ffc1c91398f4f064575e2d73116149c127b1fa753f3b`. Proposta futura: um único POST textual igual ao HTTP 200
histórico, até 45 segundos totais, R$0, sem retry; nenhuma imagem. Requer nova
aprovação específica e vinculação pelo operador existente. Nenhum ledger foi criado.

Para inspecionar o plano sem executar requisição, na raiz do projeto:

```sh
rtk proxy .venv/bin/python -B -m json.tool docs/evidence/issue-5-nim-http-diagnostic-retest-inactive.json
```

A correção não recupera o corpo de 131 bytes nem os cabeçalhos descartados da
falha anterior e não demonstra que o serviço NVIDIA voltou a responder.
