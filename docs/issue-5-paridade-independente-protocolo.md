# Paridade independente das rotas completas — protocolo

Ensaio novo: **uma Python + uma MCP**, nessa ordem, com as três entradas,
pedido, cadastro, configuração e M1/A200 existentes. Sem aquisição ou retry.
Os 148 arquivos de código/locks comparados têm bytes iguais aos da base
`0e851705b359de751c12f5590fa76f69e1f714f6`; adições alheias ao fluxo não foram
importadas. Trabalho apenas no clone, sem escrever na árvore principal.

Cada rota executa supervisor → StateGraph isolado → worker raiz → extrator
nativo → M1 → SHAP → comparáveis de treino → packet. A MCP usa cliente/servidor
stdio reais. As respostas completas são preservadas antes do aceite e
comparadas integralmente: números, ranking, SHAP, evidências, packet e flags.
Não há consulta canônica ou resposta de cache usada como aceite.

| Teto | Valor |
| --- | --- |
| Rotas / extrações / `predict_views` | 2 / 6 / 6 |
| SHAP / buscas de comparáveis | 2 lotes / 6 buscas |
| Chamadas usuais dos modelos de quantil | 24: 18 da previsão + 6 da etapa SHAP |
| SHAP nativo | 2 chamadas, sem inferências auxiliares |
| Prazo interno | 480 s por análise |
| Envelope externo | 510 s: análise + até 30 s de encerramento |
| Prazo global | 1.200 s, incluindo os dois encerramentos |
| RSS / workspace, amostrados a cada 50 ms | 3,5 GiB / 384 MiB |
| Arquivo / stdout ou stderr por job | 32 MiB / 64 KiB |
| Trace privado por processo | 512 KiB |

A instrumentação usa overlays somente leitura dos dois `_virtualenv.pth`,
preservando suas linhas originais, e `sys.setprofile`. Não substitui funções,
comandos, ambientes de produção, seeds, afinidade, parâmetros ou resultados.
Registra startup antes dos encoders, origens/hashes dos imports, ambiente em
allowlist, afinidade, pools de threads e hashes de RNG já inicializados.
Estados internos não expostos de CTranslate2/ONNX permanecem desconhecidos.
Há imports stdlib antecipados, leituras adicionais e overhead do perfilador;
o preflight inventado não prova ausência universal de efeito numérico.

Os retornos originais fornecem os digests privados de áudio, ASR, embedding,
PredictorInputs, CandidateFeatures, previsão, SHAP, comparáveis e packet.
O áudio usa o hash calculado nativamente, sem nova decodificação. A vinculação
por posição confere os inputs extraídos, entregues e efetivamente previstos.
Nenhum texto, vetor, ID, URL ou previsão individual entra no recibo público.

Preflight: rotas inventadas com/sem overlay, igualdade integral das quatro
respostas, estados RNG preservados, zero inferências reais e zero erros do
observador. Uma falha inicial de classificação de `TimeoutExpired` foi
preservada e corrigida para reconhecer especificamente `Popen.__init__`.
O preflight final e os pins constam do recibo agregado desta preparação.

Antes de ML: revisão dos pins e liberação técnica vinculada ao plano, janela
válida e ausência de outro job de modelos. Parar diante de limite, alteração
de fonte/entrada, falha de observação, rota incompleta ou limpeza incerta;
não repetir automaticamente. Remover somente scratch novo após recolhimento
confirmado, preservando todos os recibos e as três entradas até
**21/10/2026, 23h59, São Paulo**, sem exclusão automática.

Se houver igualdade, concluir apenas paridade **do par atual instrumentado**.
Os 22 campos históricos divergentes e sua causa desconhecida continuam
registrados; o Python histórico permanece fonte canônica. Corrigir código
do produto exige um defeito demonstrado. Sem rede, NIM, VLM, treino, conteúdo
do teste reservado, gates relaxados, publicação ou alteração do modelo.
