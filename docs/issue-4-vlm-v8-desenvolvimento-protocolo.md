# VLM v8: desenvolvimento nos 64 casos revelados

Solicitação de 19/10/2026, após `9f7fc81`: implementar a
[correção proposta](issue-4-vlm-diagnostico-e-proxima-correcao.md) e comparar
nos 64 casos já revelados, mantendo pixels/tempos. Não selecionar auditoria
nova, abrir validação/teste, treinar B-VLM ou promover M1. Preservar partições
203/66/31, modelos, serviço/MCP e todos os recibos anteriores.

Uma única versão v8, sem variantes ou ajustes após a primeira chamada:
três perguntas curtas por frame, uma por atributo, com JSON literal true,
false e unknown. Pessoa inclui partes humanas; produto exige objeto e
apresentação observável, distinguindo roupa incidental; texto é presença
de letras/números mesmo sem conseguir ler. Rubrica preservada, sem relabelar
anotações para favorecer a versão. Não acrescentar razões livres, OCR, pesos
novos ou alterações de resolução. Congelar prompts/esquemas/fontes antes
dos controles e das inferências reais.

Reutilizar parser estrito e agregação v7: OR para presença com todos os frames
positivos citados; false só com todos os elegíveis false; demais unknown.
Produto somente <=3 s; ambiente/formato/close-up/aplicação desconhecidos.
Mesmos Qwen3-VL-2B Q4_K_M, projetor Q8_0, runtime b11716, CPU4, seed42,
temperatura 0, mínimo/máximo visual solicitado de 64/128 tokens e crop PNG
RGB de 320×330. Isso não é medição dos tokens visuais efetivos. O limite de
saída, independente do visual, permanece em 64 tokens por chamada.
Nenhuma seleção de evidências pela anotação ou repetição de chamada inválida.

Fixar primeiro 12 controles sintéticos: ABC123 em tamanhos 14/48, preto/cinza160
sobre branco e posições superior/inferior (oito positivos); branco, preto,
linhas e formas sem caracteres (quatro negativos). Aplicar o mesmo extrator
aos três campos, total 36 chamadas. Usar para diagnóstico de contrato e
comportamento; erros de qualidade ficam registrados, sem ajustar prompts.
Falhas operacionais/JSON/limpeza interrompem. Os 64 casos continuam autorizados
se o contrato funcionar, mesmo com erros perceptivos nos controles; estes
não são validação independente ou justificativa de aprovação.

Reobter exatamente as 64 folhas do plano v7 em fila distinta, sem substituição
ou novas observações públicas. Validar propriedades, tempos, SHA256 de folha
e de cada crop contra o recibo v7 antes de inferir; bytes do contêiner podem
divergir. Descartar vídeo ao fim de cada sessão. Ambos os grupos agora são
desenvolvimento: 32 antigos e 32 da auditoria revelada, 16/setor em cada um.
As mesmas anotações assistidas permanecem imutáveis. Não abrir views, títulos,
descrições, ASR ou evidências/rótulos do teste. Guarda de acesso ativa em toda CLI.

Comparar v8 com A/v7 em cache nos mesmos 64 casos. B/v7 nos 32 antigos é apenas
comparador adicional em cache. Relatar por grupo/setor/campo: valor+frames,
valor isolado, conhecidos/unknown, evidências sem suporte, suporte e confusão
das classes; frames positivos/ausentes explicitamente anotados, sem transformar
frames não citados em negativos. Relatar o total64 e os dois grupos32 para
não esconder regressão com médias. As saídas dos frames não são independentes.

Aplicar o gate original de 32 separadamente aos dois grupos, apenas como
diagnóstico de prontidão: >=12 conhecidos/setor, >=90% valor+evidência,
zero evidência sem suporte e suporte booleano >=3 por valor no total e >=1
por setor. Prontidão de um campo exige passar em ambos; nenhuma coluna é
liberada para treino por este desenvolvimento. Não usar desenvolvimento como
auditoria cega nem alterar gate/amostra após o resultado. Registrar também o
suporte das classes anotadas: ambos os grupos têm somente dois negativos de
pessoa, portanto um resultado perfeito de 30 true/2 false não atende ao mínimo
de três previsões false. Isso limita a prontidão medida, sem justificar erros
propositais, mudança do gate ou reposição. Se falhar, registrar
sem iniciar automaticamente resolução nativa ou outra correção.

Carregar 118 aquisições, 649 chamadas v7+diagnóstico e 8.306,90845013706 s dos
recibos selados. Autorizar 64 reaquisições +até10 extras DNS: teto cumulativo 192.
Até 804 chamadas novas (36 controles+768 reais), sem retry de inferência.
Manter 27h cumulativas, 180s/operação, RSS filho<=3,3GiB e um executor.
Registrar tentativa/chamada antes de executar e preservar falhas. DNS temporário
tipado permite uma repetição/ID e10 na fila, somente após limpeza, espera5s e
DNS positivo, reutilizando a recuperação auditada. Auth/403/429/timeout/memória,
identidade divergente ou limpeza incerta param; nenhum contador é reiniciado.

Saídas privadas novas: `data/private/issue-4-vlm-v8-desenvolvimento-64/`.
Guardar folhas somente durante a comparação/revisão; remover 64 após selar
o relatório, preservando identidade, respostas e hashes. Controles sintéticos
também têm descarte. Fonte v7 e rodadas seladas não mudam. Verificar parser,
agregação, isolamento, identidade, retomada, limites, comparação pareada e
descarte, incluindo recuperação idempotente de comparação e de remoção parcial
das folhas, sem repetir inferências; revisão independente somente leitura.
Commits por unidades verificadas.
