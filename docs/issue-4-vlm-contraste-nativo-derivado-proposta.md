# Contraste posterior: informação nativa versus derivado ampliado

Proposta estática de 21/10/2026. **Sem autorização de geração, aquisição,
novo executor ou plano executável.** Não modifica o candidato `2817922` nem
o plano de recuperação `349cfbfec2b1ffc4dce5727d608672fd9fb5f1ddd5019042445ab212be3eaedc`.
Só poderá ser preparada depois de decisão específica e recuperação integral
das duas fontes pela [ponte já implementada](issue-4-vlm-fonte-nativa-preparacao.md).

## Pergunta e entradas

Pergunta: conservar informação anterior à redução/JPEG muda a decisão
mão–tecido nesses mesmos dois casos? São um positivo e um negativo de treino
já revelados, com esperados diagnósticos assistidos `yes`/`no`, não anotação
independente. Sem novos casos, frames, sublabels ou mudança de esperado.

- **N:** PNG RGB nativo 360× 640 do mesmo PTS congelado, com ponte completa.
- **D:** reproduzir o PNG 320× 330 congelado pelo hash, extrair o retângulo fixo
  `(0,0,186,330)` e ampliar para 360× 640 por Pillow/LANCZOS; salvar PNG RGB.
  As 134 colunas brancas ficam fora de ambos. Não selecionar ROI de mão/produto.

A tela final, enquadramento e posição normalizada do quadro são iguais;
o arredondamento histórico 186× 330 também integra o efeito estudado.
A transformação D não recupera detalhe. O contraste mede conjuntamente
**redução, JPEG e reamostragem da preparação histórica**; não separa suas
causas. Comparar quatro respostas contemporâneas: as respostas antigas com
margem ou geometria diferente não substituem D. Preservar todos os originais.

## Orçamento visual fixo e verificação necessária

Manter `image-min-tokens=image-max-tokens=1024` em todas as células, sem sweep.
O cabeçalho GGUF instalado foi lido somente nos primeiros **1.180 bytes**:
patch 16 e merge 2, sem tensores/carga/forward pass. A célula espacial efetiva
é 32 pixels; o orçamento 1024 corresponde a 1.048.576 pixels equivalentes,
acima dos 230.400 do frame nativo 360× 640. Essa margem fundamenta evitar nova
redução ao detalhe do thumbnail. A relação tokens/patches e os limites de
pixels estão no [fonte oficial fixado](https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/clip.cpp).

Isso é justificativa estática, não geometria interna observada. Antes de gerar,
conferir no pré-processamento/fórmula fixados que **nenhum eixo do nativo é
reduzido abaixo de 360× 640**, com a mesma grade prevista nos dois braços.
Sem essa conferência, não liberar o contraste. Não usar somente a contagem
de tokens como prova de geometria ou atenção. Se o orçamento não satisfizer
o requisito, parar para revisão; não mudar flags automaticamente.

Na execução eventual, exigir encoder/decoder completos e **contagem efetiva
inteira de pelo menos 1.024 tokens, igual nas quatro células**, além da geometria pré-verificada.
A flag não garante 1024 exatos; arredondamento é registrado. Desigualdade
encerra a etapa, sem ajustar flags, repetir ou comparar pares tecnicamente
desiguais. Mais tokens não garantem percepção correta.

## Quatro células e limites propostos

| Ordem fixa | Caso | Representação | Esperado diagnóstico |
| --- | --- | --- | --- |
| 1 | Negativo / PTS 2,8 s | D | `no` |
| 2 | Negativo / PTS 2,8 s | N | `no` |
| 3 | Positivo / PTS 0,2 s | N | `yes` |
| 4 | Positivo / PTS 0,2 s | D | `yes` |

Congelar a pergunta e schema atuais de `vlm_perception_grammar`, gramática
ligada e parser estrito `yes/no/uncertain`. SHA-256 do promptUTF-8:
`0f25101968e5d81ec8cf7108090d18e99b8acd358bb85cba45c6a4e1f22717a8`;
schema semântico:
`355cf251f75d8f2a355e010980e36afc8261c9d07a40aa98c272c7f97993c277`.

Mesmo Qwen 3-VL-2B Q 4_K_M, projetorQ 8_0, b 11716, CPU 4, seed 42,
temperatura 0, contexto 3072, saída 64, batch/ubatch 128 e verbosidade 4.
Hashes futuros dos quatro PNGs, proveniência, argv e fontes deverão ser
selados antes da primeira geração. Não reutilizar autorizações antigas.

Teto proposto: **4 chamadas,260 s globais**, incluindo 20 s de preparação;
até 60 s por dispatch com 5 s de cleanup reservados (até 55 s úteis).
Base: a sessão espacial anterior completou em 50,56 s; nova geometria não
garante o mesmo tempo. RSS 3,3 GiB; stdout 16 KiB, stderr 256 KiB, tee 16 KiB.
Reutilizar captura existente; nenhuma nova infraestrutura nesta proposta.

Falha de identidade, geometria, encoder, tokens, contexto, formato, orçamento
ou cleanup encerra sem retry. `uncertain` é abstenção; respostas semanticamente
erradas não alteram a ordem nem o saldo. Reservar antes de spawn, consumir
incerteza, persistir recibos antes da limpeza e conservar scratch sem ack.
Nenhum download ou novo peso nessa etapa; respeitar a retenção dos dois PNGs.

## Leitura permitida

Correção nativa do negativo frente a D, conservando o positivo correto, daria
apoio pontual ao efeito conjunto da preparação. Reportar quatro resultados,
ganhos/perdas e abstenções; não converter unknown em acerto. Nativo também
errado não prova ausência de benefício geral; ambos corretos não identificam
a causa histórica. Este par conhecido não estima qualidade populacional.

Nenhuma auditoria, candidata, atributo, gate, treino B/C ou promoção M 1 é
aprovado pelo contraste. Teste reservado, partições, oito folhas e três inputs
da demo permanecem protegidos. Esta unidade somente registra o protocolo.
