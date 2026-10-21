# Contraste nativo/derivado: candidato offline

Implementação aditiva do [protocolo de quatro células](issue-4-vlm-contraste-nativo-derivado-proposta.md).
Preparação autorizada somente para código, testes e selos; **não libera geração**.
Não modifica extrator, atributos, gates, M1 ou fontes/planos anteriores.

O novo controlador reutiliza a captura limitada, parser curto, argv espacial,
checagem de workers e recibo de gramática existentes. Não acrescenta supervisor,
transporte, outra pergunta, novo modelo ou procedimento de busca de candidatos.
São Dneg/Nneg/Npos/Dpos, quatro PNGs RGB360×640 preparados sem inferência.
N conserva bytes do PNG recuperado; D usa o crop histórico verificado, retângulo
fixo186×330 sem a margem branca, LANCZOS360×640 e PNG, sem alterar os originais.

## Cálculo de grade antes do selo

O fonte oficial fixado despacha Qwen3VL para o pré-processador dinâmico.
Patch16 e merge2 dão alinhamento32; os limites1024/1024 dão1.048.576 pixels.
A função real de resize usa `float`, `std::round`, `std::sqrt` e `std::ceil`.
Foi extraída literalmente e compilada com cabeçalhos padrão, `-std=c++17 -O0`,
sem bibliotecas de modelo, tensores ou forward pass.

| Entrada | Alinhamento inicial | Resize calculado | Grade / tokens previstos |
| --- | --- | --- | --- |
|360×640, N e D |352×640 |**800×1376** |**25×43 /1075** |
|320×330, referência histórica |320×320 |1024×1056 |32×33 /1056 |

O segundo cálculo coincide com os1056 tokens observados na referência anterior;
não é nova execução do encoder. No primeiro, a área inicial é225.280, abaixo
do mínimo, e o ramo de aumento aplica `ceil` por32 aos dois eixos após a raiz
em precisão simples. O arredondamento real prevê800 de largura; uma conta
ideal em outra precisão não substitui esse resultado. Nenhum eixo nativo é reduzido.

O bloco escalar real de padding também foi conferido, com operações de pixels
substituídas por funções vazias somente nesse cálculo: conteúdo **775×1376**
em canvas800×1376, offset(12,0), para os dois braços. Os dois eixos de conteúdo
também são maiores que360×640. O segundo recibo sela esse código e seu binário;
não produz imagem nem executa o encoder. O candidato verifica ambos os recibos.

Fonte da função:
[mtmd-image.cpp fixado](https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/mtmd-image.cpp),
SHA-256 `2552b9200162160ccb29122371601586c8cd29e5c07f075f0c156f1c47ac38e6`.
O recibo privado sela fonte extraída, flags, compilador e binário aritmético.
Isso demonstra cálculo estático, não geometria ou atenção observada em inferência.

## Guardas e execução futura

Plano vincula recuperação concluída, seus dois PNGs/recibos, folhas/crops,
quatro hashes de entrada, fórmula, prompt/schema, runtime/modelo e fontes.
Reconfere toda a identidade antes de cada dispatch. O decoder estrito aceita
apenas o contrato antigo yes/no/uncertain; não recompila ou repete a auditoria
da gramática já validada.

Exigir contagem efetiva **1075**, coerente com a fórmula aplicável e igual nas
quatro células; divergência encerra sem alterar flags, substituir entrada,
descartar a resposta ou repetir. O recibo da célula divergente fica preservado.
Respostas semanticamente erradas e abstenções mantêm a sequência congelada.
Erro técnico/formato/expiração ou cleanup incerto encerra a etapa.

Orçamento fixo4 chamadas/260 s globais,60 s por dispatch incluindo5 s reservados
ao cleanup; min=max1024, contexto3072/saída64, CPU4, batch/ubatch128 e parâmetros
anteriores. A preparação usa somente pixels e validações locais. A expiração
dos dois PNGs continua21/10/2026,23h59 São Paulo, sem extensão automática.

CLI de preparação na raiz:

```sh
rtk proxy .venv/bin/python -B -m scripts.vlm_native_contrast prepare
rtk proxy .venv/bin/python -B -m scripts.vlm_native_contrast inspect
```

Comando futuro, **não liberado**, após decisão específica e revisão dos hashes:

```sh
rtk proxy .venv/bin/python -B -m scripts.vlm_native_contrast execute
```

Nenhum CLI cria aprovação. Revisão futura reutiliza o contrato existente
`released_for_this_perception_contrast_only`, vinculada ao plano/configuração
novos, mensagem real/literal e revisor. Marcador exclusivo impede reentrada,
inclusive após interrupção anterior à primeira reserva. Incerteza não devolve saldo.
Recibos precedem limpeza; sem ack, preservar scratch próprio e selar.

Os testes usam somente pixels e observações inventados, com subprocessos,
rede e credencial bloqueados. Nenhuma resposta simulada aprova provedor ou
percepção. JPEG, redução e reamostragem são um efeito conjunto neste par já
revelado; mesmo eventual melhoria não é auditoria independente ou aprovação.

Passaram **19 testes offline** com supervisão/observações inventadas, Ruff e
formatação dos dois arquivos Python novos. Cobrem quatro células mesmo diante
de erros semânticos, abstenção, token divergente, formato/encoder, expiração,
orçamento global, falta de revisão, reentrada e preservação do scratch sem ack.
Não houve modelo, mídia nova, chave ou socket nesses testes.
