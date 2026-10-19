# B-VLM v2: normalização de evidência repetida

Decisão anterior a qualquer ajuste preditivo, em19/10/2026. Complementa o
[diagnóstico](issue-4-experimento-b-vlm-saida-invalida.md) e preserva todos os
demais critérios de [qualidade/identidade](issue-4-experimento-b-vlm-identidade.md).

A captura limitada reproduziu a falha: JSON completo, mas uma lista de
evidência contém `[2,3,2]`. Os índices2 e3 são válidos e anteriores a3s;
a duplicata viola a exigência de unicidade do validador. Não houve truncamento
nem evidência de que seria preciso aumentar tokens, trocar pesos ou prompt.

O novo adaptador normaliza exclusivamente a representação de conjuntos de
frames: `[2,3,2]` vira `[2,3]`, preservando a primeira ocorrência e sua ordem.
Validar primeiro estrutura, tipos inteiros exatos (bool não vale), limites de
comprimento/índice e temporalidade; depois deduplicar e reaplicar o validador
completo. Não alterar valor perceptivo, preencher evidência ausente, converter
erro em falso/unknown ou reparar JSON incompleto. Esses erros seguem parando
o lote. A resposta bruta, seu hash, o objeto bruto e a derivação normalizada
ficam registrados. A barreira global de close-up/aplicação permanece intacta.

Manter os fontes legados GGUF e todas as entradas905 de B-cache congelados.
Novo adaptador e testes devem demonstrar prompt, esquema e parâmetros idênticos
aos legados, com normalização idempotente e recusa de outros erros. Persistir
saída rejeitada em armazenamento privado se outro erro estrutural surgir,
sem selecionar uma tentativa por percepção ou por resultado preditivo.

Usar **fila v2 separada e uniforme para os269 IDs de desenvolvimento**. Não
misturar os13 sidecars v1 com os novos. Arquivar os fontes/hash do lote v1,
seu checkpoint interrompido e os diagnósticos, sem sobrescrever evidências.
As14 anotações cegas já fixadas podem ser reutilizadas somente se ID/ordem,
timestamps e SHA256 da folha visual coincidirem exatamente. As restantes
continuam cegas às respostas, sem views/fala. O gate não muda por esta falha.

Já ocorreram17 aquisições: dois diagnósticos iniciais,14 tentativas do lote v1
e uma captura diagnóstica da saída inválida. O teto passa explicitamente a
**286 aquisições**:17 anteriores +269 da fila v2. Sem retries automáticos na
v2. Um recibo privado fixa hashes das quatro fontes de orçamento, soma os
tempos anteriores e inicializa o relógio da v2 com esse saldo consumido;
o teto cumulativo de27h não é reiniciado. As partições203/66/31, o teste
reservado e o M1 permanecem intactos. Nenhum modelo real foi treinado até aqui.
