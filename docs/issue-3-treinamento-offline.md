# Experimento A — treinamento offline

O bloco offline da #3 reutiliza a coorte e as partições da liberação ampliada.
A integração de M1 na função/MCP permanece uma etapa posterior da mesma issue.

`scripts/experiment_a_data.py` revalida coorte, baseline, evidências, configuração,
arquivos dos extratores e versões instaladas. Compara as entradas persistidas com
as entradas reimportadas. Essa leitura integral verifica a integridade, incluindo
as observações congeladas do teste; não calcula previsões ou métricas do teste.
A fronteira de ajuste recebe somente dois `DevelopmentSplit`: treino e validação.
Não há parâmetro para avaliar teste nem rotina para refazer sua divisão.

A matriz tem 388 colunas: setor e estado do texto categóricos, duração, proporção
altura/largura e 384 componentes MiniLM da fala. Canal/ID ficam no agrupamento e
na auditoria; rótulos ficam em outro vetor. Não há transformação aprendida,
normalização, PCA ou imputação ajustada nos dados. A representação fixa para
texto ausente é embedding zero com estado explícito, utilizável somente quando
esse estado teve suporte no treino. Falha de extração não é silêncio.

## Exemplo para acompanhar

Uma referência de treino fornece `x = [setor, duração, proporção, estado,
embedding...]` e, separadamente, `y = log1p(views)`. Para um exemplo **sintético**
de 999 views, `y = log(1000) ≈ 6,9078`; `expm1(y)` recupera 999.
O baseline atribui a mediana do setor no treino a todos os candidatos desse setor.
O CatBoost usa os sinais do arquivo para estimar uma mediana condicional.

Uma referência de validação fornece as mesmas colunas, mas seu rótulo serve
somente à parada antecipada e à escolha da configuração. Calculamos o erro de
cada vídeo, a média dentro de cada canal e então a média entre canais; canais
com mais publicações não dominam a escolha. O teste reservado não participa.
Reproduzir essa seleção de IDs/colunas e interpretar a comparação de validação
é a prática prevista; este texto não afirma que o aluno já a realizou.
