# Diagnóstico da saída VLM rejeitada

Em19/10/2026, o lote parou no14º caso de treino, após13 conclusões. A mídia e
os pixels amostrados foram verificados; o adaptador levantou `ValueError`
depois da chamada local. A sessão removeu a mídia. Não houve ajuste preditivo,
liberação de colunas ou mudança de coorte/partição/M1. Os476 testes públicos,
Ruff/formatação e revisão independente do pipeline já passaram.

A resposta rejeitada não foi persistida pelo adaptador legado. Antes de
alterar parser, prompt, orçamento de tokens ou política de ausência, executar
**um diagnóstico separado do mesmo caso**, preservando modelo, pesos, prompt,
esquema, imagens320×330 e parâmetros. Instrumentar somente a captura privada
do retorno bruto e do erro do validador. Confirmar o mesmo hash de folha antes
da inferência, conservar a imagem apenas para a anotação cega e remover a
mídia da sessão. Não revelar a resposta ao anotador visual.

Esse diagnóstico não libera a retomada do lote nem transforma falha em valor
conhecido. Os13 sidecars e o checkpoint interrompido ficam preservados.
Registrar a causa antes de decidir uma correção global; não pular a linha,
selecionar uma tentativa por acerto ou misturar configurações silenciosamente.
Nenhum rótulo preditivo será consultado para resolver a falha.

O diagnóstico adicional é uma aquisição além do limite inicial; a execução
futura precisará contabilizá-la, assim como as tentativas anteriores, antes
de retomar. O orçamento original de27h permanece como teto da rodada; a
correção não autoriza outro serviço, outra fonte ou acesso ao teste reservado.
