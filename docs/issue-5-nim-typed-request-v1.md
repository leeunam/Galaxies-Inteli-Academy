# NIM — pedido textual tipado para uma tentativa sintética

Camada aditiva mínima sobre a auditoria de tipos. A tentativa anterior permanece
consumida, sem recuperação de corpo nem alteração de fontes, planos ou recibos.
A autorização humana para **uma tentativa adicional** está em
`Sentinel_a49f19fb4c048191a49a669ff8f43f79`, de 21/10/2026, 10:44 UTC.
O limite informado de 40 rpm não demonstra saldo; a base financeira continua
sendo a confirmação anterior do plano gratuito e a oferta oficial já registrada.
Nenhuma cobrança ou mudança de acesso é autorizada. O novo POST aguarda revisão
técnica concreta, integração na árvore de execução e liberação da frente.

## Delta do pedido

Mesmo endpoint, modelo, fixture, temperatura, streaming, thinking e limites.
A única alteração é um apêndice à mensagem textual existente contendo schema
completo, tipos explícitos e exemplo tipológico de estrutura: objeto com hash
string e array de strings. O schema publica hash da fixture, enum dos cinco IDs,
campos obrigatórios, ausência de extras, unicidade e limites 1–12. Não envia
`response_format`, `guided_json` ou outro parâmetro de suporte incerto.

`nim_typed_request_v1.payload_bytes()` constrói somente esse candidato fixo.
Os dados são inteiramente inventados. Os validadores de autoridade continuam
iguais; nenhum tipo é convertido para obter aceitação.

## Observação após a autoridade

`nim_type_observer_v1.observe_open_response` recebe uma resposta já aberta de
um chamador confiável; não abre conexão, lê chave ou realiza HTTP. Reutiliza a
sessão, ponte e resumo fechado existentes. Só depois da autoridade calcula tipos
para nove posições públicas fixas: envelope, choices, choice, message, content,
seleção interna, hash, array de IDs e tipos dos seus elementos.

As categorias são apenas não observado, ausente, nulo, string, array, objeto,
número ou booleano. Não conserva valores, nomes desconhecidos, erros detalhados,
corpo, cabeçalhos ou hash do corpo. O digest novo identifica o schema esperado
público. A projeção de IDs permanece sob as regras anteriores. Um diagnóstico
de tipos incompatível com aceitação é recusado; ele nunca concede aceitação.

## Consumo e bloqueio

O namespace real novo e fixo é `data/private/issue-5-nim-typed-request-v1/`.
O recibo de revisão é separado, em
`data/private/issue-5-nim-typed-request-v1-review/technical-review.json`.
O CLI não cria aprovação. O operador só pode criar esse recibo após a revisão
do supervisor; ele vincula protocolo, decisão `approved_for_one_synthetic_attempt`,
SHA do plano e da configuração, ID da autorização humana, evidência financeira,
chat revisor, mensagem da decisão e SHA do caminho absoluto da árvore executora.
Esse vínculo é uma guarda de integridade/coordenação em armazenamento do operador,
não autenticação criptográfica contra seu proprietário.

O roteiro, após revisão e integração, é:

1. Conferir os novos hashes na árvore executora e ausência do novo ledger real.
2. Registrar a revisão específica vinculada a essa árvore, sem copiar credenciais.
3. Liberar a janela de execução sem concorrência com modelos reais.
4. Executar uma única vez `python -m scripts.nim_typed_request_v1 --execute-reviewed-once`
   com o Python já existente. Não há opção para endpoint, modelo, corpo, chave,
   ledger remoto ou aprovação automática.
5. Conservar consumo e recibo seguro; qualquer resultado incerto encerra a
   tentativa, sem repetir, reparar ou trocar alvo.

Antes de reservar, o pai verifica plano e revisão. A reserva exclusiva é durável
antes de criar o processo. O filho confere plano, revisão, vínculo, nonce e PID
do pai; grava o marcador exclusivo de dispatch antes de ler a chave existente.
Só esse ramo lê a chave na própria árvore integrada. O clone de preparação não
recebe `.env`, credencial ou dados privados.

O filho faz um POST com a conexão HTTPS direta e framing existente, sem proxy,
redirect, SDK, retry ou logs. Limites: uma tentativa, 45 s totais, 2.048 tokens,
16 KiB de corpo e teto R$0. O pai reutiliza o processo limitado v3, seu ambiente
literal, pipe limitado, isolamento e proteção de cancelamento durante spawn,
kill/reap. O protocolo IPC anterior conserva somente o resumo. O diagnóstico
é escrito como `typed-observation.json` privado e durável; o pai o valida e
exige igualdade do resumo com o IPC antes de incorporá-lo ao recibo final.
Timeout, cancelamento, crash, ausência ou inconsistência do recibo não permitem
reutilizar o namespace.

As simulações usam o mesmo pipeline com chave e conexão falsas, zero chamadas
reais e diretório novo. Recusam os namespaces v1, v3, release/revisão anterior,
novo ledger/revisão e descendentes, incluindo aliases por symlink e `..`.
Os arquivos privados usam modo 0600 e diretórios 0700.

## Verificação do candidato

Os testes escritos cobrem delta textual, aceitação preservada, três estruturas
inválidas, campos/IDs secretos inventados, contradição entre tipos e aceitação,
revisão ausente/incorreta, ordem do acesso à chave, nonce/vínculo/dispatch,
consumo único, namespaces protegidos, transporte limitado, sidecar ausente,
timeout e cancelamento. Passaram **32 testes novos em 7,37 s** e, na conferência
conjunta com dispatch v3 e release anterior, **140 testes em 16,27 s**. Ruff e
formatação passaram nos cinco arquivos Python novos. Todas as conexões e chaves
usadas nos testes são falsas; não houve leitura de credencial, HTTP real, modelo
de ML ou consumo do novo namespace remoto. As fontes rastreadas anteriores
permaneceram sem alteração. A revisão técnica e o POST ainda estão pendentes.

| Artefato | SHA-256 |
| --- | --- |
| Plano | `766f2974f0d759479e47d883a9f8734d1b2166a60d8fae13dfb1ada934ab369d` |
| Configuração | `e75f102c6094ca8ee545d9505f3d3a4c5f69462d7896db45f0ba00ec094d4951` |
| Corpo HTTP | `e5437059f2b490a23bbb1d1146fc3c510c63a63ae9ddc5c075d70e41fcdfe00f` |
| Schema público | `94aa021fd4244f8123fb0da25ad634695588e45598db2c679d21eb469f079d76` |

O plano sela os três módulos de implementação e o arquivo de testes. O selo fica
fora dessa lista para evitar autorreferência; sua constante fixa o hash do plano.
O recibo privado de revisão vincula esse mesmo hash, configuração e checkout.

Um resultado futuro verificaria aceitação contratual nesta fixture ou apontaria
posição/tipo público da falha. Não comprovaria a causa histórica, qualidade geral
do fornecedor, aderência, previsão científica ou conclusão da #5. Nenhum plano
ou ledger anterior é reaberto.
