# V16 — checkpoint técnico anterior à geração

O [protocolo congelado](issue-4-vlm-v16-protocolo.md) implementa o diagnóstico
limitado definido pelo canal principal e supervisor. Neste checkpoint,
**zero chamadas VLM, zero aquisições e nenhuma liberação técnica registrada**.
O executor foi testado contra a fila real sem recibo de revisão: recusou o
despacho e manteve o checkpoint byte a byte, sem chamar o invoker.
A implementação não depende de uma nova aprovação humana, mas aguardará a
conferência técnica explicitamente exigida antes da geração.

Branch `codex/issue-4-v16-ordem-serializacao`, baseada no HEAD integrado #5
`9c4177a4ddc3b44710d0b39435d1df02d4f2201e`, preservando a branch v15 em `69a5832`.
Commits de implementação: **`340fc7c`** (contrato/gate nativo) e **`c911761`**
(fila limitada e liberação técnica vinculada). Não houve retorno à árvore antiga.

## Equivalência e contraste nativos

O prompt comum não ordena campos. É igual nas duas condições e altera somente
a frase final de serialização do v15 histórico. Cada schema mantém22 objetos,
dez ramos na mesma ordem, as mesmas categorias, projeção e listas required.
Somente a ordem das propriedades muda; o campo local fields a identifica.
O digest canônico dos schemas é igual, como esperado, pois ordena chaves.
Os hashes que preservam ordem são distintos e foram registrados separadamente.

| Verificação real, sem geração | item_first | state_first |
| --- | ---: | ---: |
| Sondas da gramática instalada | 13.703 | 13.703 |
| Divergências | 0 | 0 |
| Objetos válidos aceitos na ordem própria | 22 | 22 |
| Objetos válidos recusados na ordem oposta | 22 | 22 |
| Variações de whitespace entre campos aceitas | 22 | 22 |
| Mutações brutas recusadas | 19 | 19 |
| Serializações tokenizadas | 44 | 44 |
| Tokens JSON | 17–32 | 17–29 |

As sondas incluem todo o domínio finito de13.640 objetos por condição.
O conjunto semântico aceito é o mesmo. As gramáticas são diferentes e fixam as
ordens diferentes: a conversão não normalizou o contraste. No limite64 cabem
as88 serializações, com máximo33 incluindo reserva de término. Arrays enum
continuam literais; não se garante whitespace interno arbitrário.

A ponte v13 imutável foi compilada contra as bibliotecas b11716 instaladas e
nove headers oficiais em cache. `readelf`/loader confirmaram que CLI e ponte
usam as mesmas bibliotecas libllama-common/libllama, com arquivos resolvidos e
hashes iguais. Conversão json_schema_to_grammar(..., false), aceitação por
caracteres e término completo. Runtime/pesos conferidos em leitura contra o
arquivo oficial; nenhum download, instalação, troca de arquivo ou forward pass.

A construção do comando foi capturada do adaptador original com Popen stubado,
sem iniciar o runtime. Os argv normalizados são idênticos: Qwen3-VL-2B Q4_K_M,
mmprojQ8_0, CPU4, seed42, temperatura0, saída64, contexto3072 e limites de imagem
64/128. Os arquivos de schema efetivamente escritos pelo adaptador preservam
as duas ordens e correspondem aos schemas convertidos. Esse recorder não é
ensaio visual ou substituto de uma chamada real.

## Cinco positivos predefinidos

O plano guarda os cinco crops, tempos e alternativas descritos no protocolo:
três calças no cabide de epAKcoQrirk, barra do vestido em toNRze0de1M e cabide
xadrez em xln8Ioqk1jU. Os cinco tinham held/garment suportado na revisão v14.
A inspeção anterior à v11 menciona literalmente held ou isolated nos quatro
cabides e o recorte no canto como isolated no vestido.

Cada alternativa tem uma testemunha própria no plano: ligação mão/cabide ou
peça física em primeiro plano; barra puxada ou recorte gráfico separado. Não
emprestar a mão ao recorte nem tornar uma arara de fundo foreground. Categoria
única garment; configurações admissíveis fixadas antes da geração, iguais
nas duas condições. O recibo guarda texto literal, fonte/hash, PNG/tempo,
índice original e instância visual que sustenta cada alternativa. Nenhum
rótulo foi reescrito. São cinco crops de três vídeos já revelados, sem
independência estatística ou certificação humana nova.

## Gates, consumo e testes

Executar24 negativos pareados, alternando a primeira condição em cada par.
Somente as condições com12/12 false recebem os mesmos5 positivos: total máximo
34 chamadas. Exigir5/5 true com categoria/configuração admissíveis, além do
primeiro gate. Falha perceptiva termina o bloco previsto; falha operacional,
JSON, ordem ou identidade encerra toda a rodada, sem retry. O executor não tem
caminho de aquisição. Não haverá nova rodada, liberação de atributos, treino
B/C ou auditoria, mesmo se alguma condição passar.

Nova autorização: ≤34 chamadas /zero aquisições /1.200 s,180 s por chamada,
RSS3,3 GiB. Base1.811 /256 /37.044,30741882603 s; teto1.845 /256 /
38.244,30741882603 s. Os32 saldos encerrados da v15 não são reaproveitados.
A liberação técnica será vinculada ao plano/configuração e à mensagem real do
supervisor; nenhum recibo de autorização foi fabricado no checkpoint.

Passaram **171 testes direcionados em72,25 s** (91 da v16 e80 de regressão v15),
com mídia/respostas inventadas e sem geração ou dados privados. Cobrem as duas
ordens, projeção/tempos, controles→positivos condicionais, falhas globais,
consumo durável, imutabilidade e recusa de relatórios rehashados que inventem
candidatura, suporte, pareamento ou causalidade. Não foi repetida a suíte
completa de integração/MCP, cujo código não mudou. Ruff e formatação dos
**222 arquivos Python rastreados** passaram. Fontes iguais às testadas.

Conferidos **1.388 pins anteriores**, incluindo os1.345 da passagem #5 e43
fontes/recibos adicionais da integração. O plano acrescenta seu snapshot:
**1.389 pins**. Oito folhas presentes e32 crops reproduzidos em memória com
hashes/tempos iguais. Partições203/66/31, M1/A200 e três modelos, A300/B-cache,
integração Python/MCP/StateGraph, runtime, locks e ambientes raiz130/isolado42
preservados. Holdout31 sem leitura semântica. README e briefing não editados;
clone NIM fora do escopo. Nenhuma publicação, push ou deploy.

## Identificadores para a revisão técnica

- Plano: `a1120d46a64d7984ba80e4fb14603923873859a65e37d6baa585d485f7fa62dc`.
- Configuração: `de3651ebeae8455b8fa80b286ca7489e3fc158846b75a3b176d208e3f2431f36`.
- Preflight lógico: `db04df2c8b53d996a8bacba46135aa01be5a9f1c56b420fc06bef9aeac497555`.
- Prompt comum: `8d8409bb27160460d38d71fc94914b68412504ce3db8437b16876053aed8ae3d`.
- Schema ordenado item_first: `3ad765214176a92d6b166ceb835b1824635719b4395f470b61bfa39ad477ed06`.
- Schema ordenado state_first: `47bf27350b557bb6223b1213654d3a1f21b7099c159408dd8960b0ecd387baef`.
- Gramática item_first: `5ef403f14df75c08396d9280dee3a49ac1b1aec7b536a316a140172623fb35e6`.
- Gramática state_first: `be0ae6d3cd9315273962ff3bdc8f010c80d0e32476cca52a999b0153a1fbb803`.
- Cinco casos com anotações: `382ab73dc0d03b0b930c0c2f8de36f64e6ceb8ce949ae2b232dde256cf890aef`.

Recibos privados em `data/private/issue-4-vlm-v16-verificacao-v1/` e fila nova
`data/private/issue-4-vlm-v16-v1/`. O estado deste documento é anterior à geração;
o resultado posterior será registrado separadamente, sem reescrever este marco.
