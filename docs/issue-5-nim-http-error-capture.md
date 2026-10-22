# Captura da resposta NIM antes dos gates de aceitação

O cliente visual compartilhado em `scripts/nim_visual_http.py` grava uma projeção
privada da resposta antes de verificar identidade, envelope, schema ou percepção.
Não possui CLI, credenciais, fila, dispatcher, retry ou liberação remota. O
transporte continua no mesmo host/path HTTPS e usa a fábrica fornecida pelo
operador existente. A preparação desse worker passou a chamar esse cliente;
a cópia executada e seus recibos selados não foram reescritos.

## Ordem e conteúdo preservado

1. Ler uma única vez, no máximo 16 KiB mais um byte sentinela. Guardar status,
   contagem de bytes e somente os cabeçalhos diagnósticos permitidos.
2. Projetar modelo (presença, tipo, valor seguro), mensagens de resposta final,
   finish reason, indicadores de tool calls e uso numérico. Modelo desconhecido,
   resposta truncada ou JSON visual inválido não apagam o conteúdo final disponível.
3. Invocar obrigatoriamente o gravador privado antes de aceitar a resposta. O
   worker usa o `durable_create` existente: arquivo exclusivo 0600 com fsync,
   vinculado ao caso e aos hashes do pedido/imagem. Falha de gravação reprova;
   não há classificação sem captura. Diretório privado continua responsabilidade
   do operador, com 0700, sob a autorização e o prazo do ensaio específico.
4. Verificar o mesmo contrato de JSON, papel assistant, conclusão stop, identidade
   conhecida e o parser semântico específico da integração hospedada, descrito
   abaixo. `unknown` continua sem virar ausência.

A captura tem teto de 64 KiB serializados. Corpos inválidos/oversize preservam
estado explícito e metadados; não são despejados como texto bruto. Leituras
incompletas preservam os campos recuperáveis e continuam reprovadas. Erros JSON
ou `application/problem+json`, inclusive 410, passam pelo mesmo caminho de captura.

Somente conteúdo final é guardado, sem `reasoning_content`, tool arguments,
Authorization, cookies, cabeçalhos desconhecidos, chaves ou cópias de imagens.
Segredos conhecidos, padrões de credenciais, URLs e data URIs/base64 são removidos
antes dos cortes. Qualquer redação no conteúdo impede sua aceitação. IDs de modelo
seguros ficam completos até 256 bytes, sem a regra de corte de mensagens de erro;
nomes estranhos são preservados para diagnóstico e permanecem não verificados.

O callback recebe uma cópia da projeção. `assess_capture` é uma conferência local;
não autentica arquivos arbitrários como chamadas reais ou validações científicas.
O resultado resumido não imprime o conteúdo privado em stdout. O snapshot permite
revisão offline posterior; ela não substitui execução independente do fluxo.

## Identidade documentada

O identificador do pedido continua `nvidia/nemotron-3.5-super-vl-120b-a12b`.
A compatibilidade anterior com o basename permanece. O nome adicional exato
`nemotron-3.5-super-vl` consta no `--served-model-name` e nos exemplos de cliente
API do [cartão oficial NVIDIA](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4#quick-start).
Não há reconhecimento por substring, aproximação ou sufixos inventados. O título
do checkpoint NVFP4, sozinho, não é promovido automaticamente a alias de resposta.
A referência do [endpoint](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3_5-super-vl-120b-a12b-infer)
continua sendo a origem do identificador canônico.

## O que restou da resposta HTTP 200 anterior

A inspeção cobriu os 14 artefatos do diretório autorizado da rodada, os seis
arquivos da preparação e os temporários do próprio projeto relacionados ao teste.
Não foram lidas sessões privadas do Codex, credenciais ou dados não relacionados.
O stdout de `operator-result-0001.json` é exatamente a projeção de
`result-0001.json`; stderr tem zero bytes. Não há arquivo de resposta bruta nem
mensagem final entre esses artefatos. Os payloads são entradas, não respostas.

No cliente executado, a linha 107 lê os 703 bytes em `raw`, a linha 119 consulta
`model` e o retorno nas linhas 124–125 ocorre antes de `choices` na linha 128.
O recibo só é escrito depois que `exchange` retorna, na linha 227. O dono do
processo usa pipes/buffers em memória, sem escrever o corpo HTTP em temporário;
debug HTTP estava desabilitado. O processo terminou e a limpeza foi confirmada.

Continuam disponíveis HTTP 200, tamanho, latência e request ID
`b8b569e8-8150-4615-8bc6-85529429c6b9`. O identificador original e a resposta visual
não são recuperáveis nos arquivos autorizados. Não é possível avaliar a percepção
antiga ou afirmar que o alias agora documentado foi aquele que retornou. Os
recibos anteriores permanecem com seu resultado original, sem promoção retroativa.

## Verificação e estado

71 testes direcionados passaram: 50 do cliente visual e 21 do diagnóstico de
HTTP. Cobrem nomes canônico/documentado/estranho/ausente, conteúdo visual válido,
unknown, gates posteriores, 401/403/429/503, 410/problem+json, corpo limitado,
Unicode malformado, timeout/leitura incompleta, segredo e falha de persistência.
Três casos falsos executaram também a preparação do worker existente e
confirmaram captura ligada a caso/payload/imagem, inclusive antes de uma rejeição.
Todas as verificações usam transporte falso, sem chave real, modelo ou API.

A preparação corrigida não foi ativada. Nenhum ledger foi reaberto, nenhuma
inferência foi repetida e nenhuma nova chamada está autorizada por esta mudança.

## Parser hospedado prospectivo: semântica e ordem separadas

O [V16](issue-4-vlm-v16-protocolo.md) compara duas ordens de geração local sob
gramáticas diferentes. Seu decoder exige a ordem experimental, além dos mesmos
22 objetos semânticos. Essa checagem continua intacta e necessária à reprodução
desse contraste; não define se um produto foi apresentado na imagem.

Somente a preparação do cliente hospedado usa agora JSON estrito seguido do
decoder semântico já existente. Exige exatamente os mesmos três campos, tipos,
configurações, estados e categorias: duplicatas, campos extras, valores não
finitos e combinações inválidas continuam reprovados. Não reordena a resposta
nem corrige valores. O resultado registra `observed_key_order` separadamente e
identifica o parser como `nim-hosted-product-semantics-v1`. A captura privada
continua preservando o conteúdo final antes dos gates. `unknown` permanece uma
abstenção e não satisfaz um controle cujo gabarito exige true ou false.

A identidade ainda precede esse parser. A lista de aliases não mudou; o exemplo
`--served-model-name` do cartão NVIDIA é local e não comprova correspondência
com o backend hospedado `private/nvidia/nemotron-3.5-super-120b-a12b`.
Nenhum recibo ou resultado selado é reavaliado como aprovação. Esta correção
não ativa operador, chamada remota, auditoria, B/C ou avaliação final.

Verificação desta unidade prospectiva: **98 testes passaram em 0,86 s** — 75 do
cliente hospedado, 21 do diagnóstico HTTP e duas regressões de preservação/rejeição
da ordem no V16. A equivalência cobre os 22 objetos nativos em 132 serializações;
casos inválidos passam também pelo transporte falso e mantêm a captura antes da
rejeição. Não houve rede, credencial real, inferência, ativação ou promoção de
resultado histórico.
