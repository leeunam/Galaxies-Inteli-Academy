# Loader GGML: busca local e próximo passo delimitado

Base: `36071913da7fac18e70d8242a77e99854e3bb5ed`. Esta unidade complementa a
[auditoria estática](issue-4-vlm-runtime-audit-v1.md), sem alterar seus recibos.
Nenhuma biblioteca, loader, CLI, modelo ou encoder foi executado. Não houve rede,
download, instalação, inferência, nova autorização ou mudança de produto.

## O que a busca local fechou

O índice do archive conhecido `runtime.tar.gz` contém executáveis, bibliotecas,
links e LICENSE; não contém headers nem fontes C/C++. Na árvore Git e nos
objetos alcançáveis por refs, a conferência delimitada de nomes de arquivos
C/C++/headers encontrou somente `scripts/vlm_product_v13_grammar.cpp`, que não
implementa loader/score. Isso descreve esse Git e esse archive, sem afirmar
ausência em outros diretórios ou no computador inteiro.

O diretório de fontes do preflight conhecido contém somente `clip-impl.h`,
`clip-model.h` e `mtmd-image.cpp`. Os dois headers incluem `ggml.h` e um inclui
`ggml-cpp.h`; esses includes não estão ali. Não há declaração local verificada
da API do loader/score nesse conjunto. O CLI em cache também não a declara.

Novas âncoras estáticas no ELF: `libggml` identifica a unidade
`ggml/src/ggml-backend-reg.cpp`; variantes CPU x64 e alderlake identificam
`ggml/src/ggml-cpu/ggml-cpu.cpp` e a unidade `cpu-feats.cpp`, cujo diretório não
foi estabelecido. Ambas exportam `ggml_backend_score`; a desmontagem contém
instruções CPUID. No loader, uma chamada indireta retorna um valor comparado
como inteiro, com salto condicional `jg`. Isso sustenta investigar a política
de score; não estabelece sua ABI C, fórmula completa, resultado no host ou
seleção histórica. Nenhum score foi chamado ou calculado por esta auditoria.

Os cinco JSONs preservados examinados (estado/resultado do resource probe,
dois resultados v2 e um v3) não possuem campo de backend. O journal durável
acumula stderr em memória e persiste somente a projeção fechada dos eventos;
não escreve um arquivo bruto de stderr. As linhas de identificação do loader
não podem ser recuperadas desses recibos. Nenhum texto arbitrário de captura
foi projetado por esta inspeção.

A [frente de representação](issue-4-vlm-representacao-offline-v1.md) confirmou
um contrato parcial: `clip-impl.h:783–795` preserva a ordem em `from_u8` e
divide por `255.0f`; `802–810` aplica `(valor - mean[c]) / std[c]` em RGB.
`mtmd-image.cpp:770–790` usa `patch_size × n_merge`, resize e append com
normalização. Isso não prova dispatch Qwen, valores efetivos de mean/std ou
patch merger. O CLI chama `mtmd_helper_bitmap_init_from_file` e
`mtmd_tokenize_from_parts`; suas implementações não estão no conjunto local.

## Etapa 1 proposta: obter e revisar somente texto

Esta aquisição está **fora do recorte offline atual**. Cabe ao coordenador
decidir sua inclusão junto à outra frente; não exige inventar um consentimento
humano genérico para leitura pública sem custo. O comando abaixo é proposta,
não foi executado, e não constitui um helper de rede entregue.

Revisão observada: `797de63b2`, a mesma registrada para o CLI. As sete URLs
oficiais exatas, nesta ordem, sem archive ou dependências transitivas:

| Ordem | URL | Teto do corpo | Evidência do caminho |
| --- | --- | --- | --- |
| 1 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/mtmd-cli.cpp | 256 KiB | Controle local conhecido |
| 2 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/ggml/include/ggml-backend.h | 256 KiB | Candidato de declaração, ainda não verificado |
| 3 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/ggml/src/ggml-backend-reg.cpp | 256 KiB | Assert path do ELF |
| 4 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/ggml/src/ggml-cpu/ggml-cpu.cpp | 256 KiB | Assert path do ELF |
| 5 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/mtmd.cpp | 1 MiB | Caminho citado no projeto |
| 6 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/clip.cpp | 1 MiB | Caminho citado no projeto |
| 7 | https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/mtmd-helper.cpp | 1 MiB | Candidato derivado de include/chamadas helper |

O controle inicial tem SHA256 esperado
`72c9163dcc2e0e491c74b6b0ee15406765e6e4c1b868ea1d3e73c2a87c9369d3`;
divergência encerra antes dos textos novos. Os dois candidatos podem resultar
em ausência: não se presume ABI, implementação ou URL alternativa. Os caminhos
de `cpu-feats.cpp` e `mtmd-image.h` não estão comprovados e ficam fora do lote,
assim como `models/qwen3vl.cpp`, que não foi fundamentado. Não há descoberta
automática após 404 nem aquisição recursiva.

`OPERATOR_PARENT` é um diretório privado existente, absoluto, sem links,
pertencente ao operador e com modo 0700. O destino fixo sob ele precisa estar
ausente; a criação exclusiva ocorre antes de qualquer rede. Bash 5.3.9,
timeout uutils 0.10.0 e as ferramentas nomeadas existem localmente; foram
consultados somente versões/manual, sem transferência. Comando futuro completo:

```sh
rtk proxy /usr/bin/env -i PATH=/usr/bin:/bin OPERATOR_PARENT="$OPERATOR_PARENT" \
  /usr/bin/timeout --kill-after=2 78 /bin/bash --noprofile --norc <<'SH'
set -euo pipefail
umask 077
parent=${OPERATOR_PARENT:?private parent required}
[[ "$parent" = /* && -d "$parent" && ! -L "$parent" ]]
[[ "$(/usr/bin/readlink -e -- "$parent")" = "$parent" ]]
[[ "$(/usr/bin/stat -c %u -- "$parent")" = "$(/usr/bin/id -u)" ]]
[[ "$(/usr/bin/stat -c %a -- "$parent")" = 700 ]]
OPERATOR_TEXT="$parent/vlm-pinned-source-text-v1"
/usr/bin/mkdir -m 700 -- "$OPERATOR_TEXT"
paths=(
  tools/mtmd/mtmd-cli.cpp
  ggml/include/ggml-backend.h
  ggml/src/ggml-backend-reg.cpp
  ggml/src/ggml-cpu/ggml-cpu.cpp
  tools/mtmd/mtmd.cpp
  tools/mtmd/clip.cpp
  tools/mtmd/mtmd-helper.cpp
)
for i in "${!paths[@]}"; do
  rel=${paths[$i]}
  cap=262144
  if (( i >= 4 )); then cap=1048576; fi
  file="$OPERATOR_TEXT/${rel##*/}.part"
  code=$(/usr/bin/curl -q --proto '=https' --proto-redir '=https' \
    --proxy '' --noproxy '*' --silent --fail --max-redirs 0 --retry 0 \
    --connect-timeout 3 --max-time 10 --max-filesize "$cap" \
    --header 'Accept: text/plain' --write-out '%{response_code}' \
    --output "$file" \
    "https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/$rel")
  [[ "$code" = 200 ]]
  /usr/bin/python3 -I - "$file" "$cap" "$i" <<'PY'
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
raw = p.read_bytes()
assert 0 < len(raw) <= int(sys.argv[2])
text = raw.decode('utf-8-sig')
assert '\x00' not in text
assert not text.lstrip().startswith('<')
digest = hashlib.sha256(raw).hexdigest()
if sys.argv[3] == '0':
    assert digest == '72c9163dcc2e0e491c74b6b0ee15406765e6e4c1b868ea1d3e73c2a87c9369d3'
print(p.name.removesuffix('.part'), len(raw), digest)
p.rename(p.with_suffix(''))
PY
done
SH
```

O comando contém somente os sete caminhos literais; não recebe URL livre.
Orçamento: sete GETs no máximo, 4 MiB agregados de corpos, 10 s por transferência,
80 s globais incluindo término forçado, R$0. Sem config curl, tokens, cookies,
proxy, redirect ou retry. Controle divergente, HTML, erro, timeout ou excesso
encerra sem outra rota. Somente arquivo com exit code zero, status 200 e tamanho
dentro do teto deixa de ser `.part`; arquivo parcial não é fonte aceita.
Não há `--location`: um 3xx não é seguido e a exigência explícita de status 200
o recusa, independentemente de `--max-redirs 0`.
Validade textual superficial não autentica fonte: a revisão deve confirmar
identidade da revisão, SHA256 dos arquivos recebidos,
declarações, política de busca/score, inicializadores e dependências. Texto
recebido nunca é compilado, importado ou executado automaticamente. A identidade
fonte/binário continua sem equivalência de build comprovada.

Foi consultada somente a versão e o manual locais, sem transferência:
curl 8.18.0. O manual diz que, desde 8.4.0, `--max-filesize` também aborta quando
o limiar é atingido durante a transferência, mesmo sem tamanho prévio. Isso
não constitui teto de bytes de TLS/headers no fio. `-q` é o primeiro argumento
do curl, conforme o manual; a saída definida contém somente status/tamanho.
Hashes de fontes novas serão anotados após obtenção; nenhum foi inventado.

## Etapa 2 condicional: observar seleção atual sem modelo

Ainda não há um helper operacional nem argv dinâmico validável: falta a ABI e
a demonstração de confinamento. A implementação só pode ser desenhada após a
etapa 1 esclarecer as funções públicas e seus efeitos. Não se usará ctypes,
assinatura presumida ou símbolo alternativo para contornar essa lacuna.

O objetivo discriminante seria identificar a variante CPU escolhida **agora**
numa visão restrita do bundle, usando o loader original. Pré-condições: fontes
revisadas, funções declaradas, ausência demonstrada de fallback fora da visão,
lista e hashes de todas as DSOs/dependências e seus inicializadores revisados.
Uma visão CPU permitiria apenas `libggml`, `libggml-base`, as 14 variantes CPU
já listadas na auditoria e dependências de sistema explicitamente enumeradas.
RPC/GPU, `libllama`, `libmtmd`, CLIs e qualquer modelo ficariam ausentes.

A proposta de isolamento usa bwrap existente: raiz mínima somente leitura,
rede/IPC/PID separados, sem dispositivos GPU, sem diretórios do projeto ou do
usuário, ambiente vazio mais OMP_NUM_THREADS=4/OPENBLAS_NUM_THREADS=1 e locale
fixo, sem seletores GGML/LD herdados. Essa visão difere do bundle completo;
só se poderá afirmar equivalência da escolha CPU se a fonte demonstrá-la.
Rede isolada sozinha não resolve assinatura, inicializadores ou busca de DSOs.

O argv e os limites de processo desse ensaio ainda não estão definidos nem
implementados; não há alegação de teto de RSS ou de memória imposto. A etapa
atual fornece somente o lote textual concreto acima. O eventual ensaio exigirá
uma proposta revisada de duração, cleanup, CPU, memória e saída, sem modelo,
tensor, graph compute, encoder, NIM, credencial, conta ou custo externo.

Resultado permitido: categoria de término e basename/hashes conhecidos da
variante selecionada, com observação da seleção separada de simples mapeamento
de biblioteca. Saída desconhecida é descartada. Tentativa de acesso fora da
allowlist, timeout, excesso, falha ou limpeza incerta encerra sem resultado de
seleção. Seleção confirmada permitiria corrigir uma discrepância demonstrada
entre política e variante atual; não prova backend histórico, threads efetivas
do encoder ou causa do timeout. Seleção esperada elimina apenas essa hipótese
estreita. Falha exige corrigir a sonda/confinamento, sem inferência às cegas.
