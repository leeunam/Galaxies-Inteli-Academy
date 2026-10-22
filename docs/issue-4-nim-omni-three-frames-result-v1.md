# Teste visual hospedado Nemotron Omni — encerrado no primeiro HTTP 503

A única rodada autorizada foi encerrada no primeiro erro. O primeiro POST retornou **HTTP 503 em 0.566 s**, sem classificação e sem modelo retornado. As outras duas imagens não foram enviadas. Não houve retry, mudança de modelo, reparo, fallback ou polling.

| Caso previsto | Estado comprovado |
| --- | --- |
| Negativo 5 | Um POST; HTTP 503; nenhum resultado perceptivo |
| Negativo 6 | Não despachado após a parada |
| Positivo de produto anotado | Não despachado após a parada |

## Contrato e limites

Modelo solicitado: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, em
`https://integrate.api.nvidia.com/v1/chat/completions`. O [contrato oficial](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning-infer) aceita `image_url.url` com base64. O [catálogo](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning/build) publica endpoint gratuito para prototipagem; o usuário confirmou a gratuidade desse modelo na conta e autorizou o envio apenas destes três frames. Nenhuma nova contratação, aceite ou credencial foi criada.

Os três payloads foram conferidos offline por hash, PNG RGB 320×330 e roundtrip base64. Uma imagem por chamada, sem hospedagem intermediária, URL remota de imagem, rótulo esperado ou referência ao dataset no pedido. Apenas o primeiro controle sintético foi transmitido, em um corpo de 13355 bytes. Os arquivos e payloads privados não foram publicados.

Parâmetros congelados: seed 42, temperatura 0, `stream=false`, `max_tokens=512`, `reasoning_budget=128`. Mesma pergunta semântica de produto apresentado e schema local `state_first`; unknown reprovaria. O limite era de três chamadas sequenciais, 80 s por chamada e 260 s globais. O cliente HTTPS utilizou a autenticação existente somente no filho, sem registrar chave, cabeçalhos, exceções ou raciocínio interno. Não houve SDK, proxy, redirect ou retry.

## Evidência e alcance

A resposta teve 131 bytes; o resultado sanitizado retém status, latência e tamanho. Não há código de erro seguro retido que identifique a causa. **HTTP 503 não demonstra crédito esgotado, credencial inválida, indisponibilidade global ou qualidade visual do modelo.** A requisição não recebeu resposta de classificação. O modelo retornado e uma versão do backend hospedado permanecem desconhecidos; um commit local identifica somente o código operador, nunca o endpoint da NVIDIA.

A rodada do operador durou 1.093 s. Limpeza confirmada, stderr vazio e zero processos restantes. Custo permitido: **R$0**, com base na oferta gratuita e na confirmação do usuário; não houve consulta ou medição independente do faturamento. As 12 simulações de transporte e três verificações de base64 passaram antes de qualquer chave ou POST real.

A rodada está selada: uma tentativa consumida, duas não despachadas e nenhum saldo liberado. As nove chamadas visuais locais e suas rodadas continuam intactas; 35 hashes do último run local e 31 pins conferem. M1, teste reservado, dados, números e critérios não mudaram. Nenhuma auditoria ou etapa B/C foi liberada.

Plano lógico: `1185eaba6d9cad7ca42a4ac62eb2ce8a61d2d7decbf8f7f88344cd20e5119b05`. Os parâmetros e estados sanitizados estão na [evidência JSON](evidence/issue-4-nim-omni-three-frames-result-v1.json). Este resultado não substitui nem apaga o [teste local reprovado](issue-4-three-case-prompt-result-v1.md).
