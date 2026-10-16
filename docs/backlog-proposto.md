# Issues propostas para revisão

Data: 16/10/2026. Estado: **rascunho; nenhuma issue deste documento foi publicada**. IDs P1–P7 são referências locais e serão substituídos pelos números reais do GitHub após aprovação. Desenho técnico: `proposta-tecnica.md`.

Os critérios de segurança, disponibilidade temporal, commits coerentes e registro de aprendizagem se aplicam a todas as issues. Cada issue termina com demonstração, verificações e limites conhecidos. Dependências condicionadas aos dados não serão marcadas como prontas para execução autônoma antes do checkpoint.

## P1 — Importar uma amostra auditável e verificar a viabilidade dos dados

**Entrega prevista:** sexta/primeiro bloco de sábado. **Bloqueada por:** nenhuma. **História:** como responsável pelo experimento, quero saber quais referências posso usar e qual alvo elas sustentam antes de treinar.

### O que construir

Percurso de uma fonte autorizada até manifesto validado e relatório de elegibilidade para moda e beleza. Implementar uma importação local mínima e, somente se o uso for validado, o adaptador da API. Auditar até 20 vídeos procurando dez canais e ambos os setores. Verificar a oferta dentro de 30–37 dias e medir extração em poucos exemplos antes de escalar.

### Aceite

- [ ] Manifesto registra origem, permissão/licença, setor, canal, datas de publicação/observação, métrica, formato e hash da mídia; rejeita registros incompletos ou incompatíveis.
- [ ] Relatório apresenta referências/canais por setor, exclusões, duplicatas e densidade por canal, sem afirmar qualidade preditiva a partir do piloto.
- [ ] Poucas amostras reais autorizadas percorrem ASR, CLIP e SmolVLM2; qwen3:4b recebe evidências sintéticas num smoke test. Tempo, memória e falhas ficam registrados antes de escalar.
- [ ] Fonte e limites do alvo são aceitos antes da coleta em escala; fonte inviável gera decisão explícita e dependências pendentes, sem dados simulados apresentados como treino real.
- [ ] Segredos não aparecem nos artefatos ou logs; manifesto público não inclui dados confidenciais.

**Aprendizagem:** distinguir dado bruto, rótulo, data de observação e informação disponível antes da previsão.

## P2 — Comparar três criativos com baseline pela função e pelo MCP

**Entrega prevista:** sábado. **Bloqueada por:** P1. **História:** como produtor, quero enviar três criativos identificados e receber uma primeira comparação completa, explicitamente marcada como baseline.

### O que construir

Cadastro local dos arquivos com IDs opacos, manifesto congelado de partições por canal e comparação pelo baseline calculado no treino. Devolver faixa empírica por setor, ranking estável, definição do alvo e explicação simples de como a referência foi calculada. Expor o mesmo caso de uso como função Python e FastMCP stdio. A baseline pode empatar os três candidatos; não inventar diferenciação por conteúdo.

### Aceite

- [ ] Ambiente instalável e dependências travadas; processo recebe exatamente três IDs distintos, setor, divulgação e brief.
- [ ] Arquivo fora da pasta permitida, escape por link, formato inválido e entrada incompatível retornam erro seguro e estruturado.
- [ ] Partições por canal são congeladas antes de calcular baselines e reutilizadas nas próximas etapas; canal novo usa fallback de setor. Saída identifica modo baseline e não sugere previsão aprendida do conteúdo.
- [ ] Função e cliente MCP por stdio produzem saídas equivalentes; diagnóstico do servidor não corrompe o protocolo.
- [ ] Demo autorizada reproduz o caminho completo, com teste de integração e instruções mínimas de uso.

**Aprendizagem:** contratos, baseline e diferença entre transporte MCP e lógica de negócio.

## P3 — Servir previsão aprendida de metadados e texto da fala

**Entrega prevista:** sábado. **Bloqueada por:** P2. **História:** como produtor, quero uma estimativa calculada com sinais disponíveis no arquivo, comparada honestamente à referência simples.

### O que construir

Transcrição local e embedding multilíngue versionado, unidos às propriedades do arquivo e ao setor. Treinar M1 com quantis CatBoost e disponibilizar o artefato pelo mesmo percurso de comparação. Reutilizar o manifesto congelado de canais da P2 e criar registro reproduzível de experimento; usar apenas treino/validação para selecionar ajustes.

### Aceite

- [ ] Nenhum canal/duplicata reconhecida atravessa partições; transformações aprendidas não são ajustadas no teste.
- [ ] ASR, particionamento de texto e embeddings seguem a mesma política em referências e candidatos; silêncio e falhas são explícitos.
- [ ] Artefato e features têm versões/hashes compatíveis; previsões e limites são finitos e convertidos corretamente; reparo de cruzamento preserva q50 e é avaliado na forma servida.
- [ ] Comparação com B0/Bcanal usa as mesmas referências; não há outcomes do vídeo nem estatísticas atuais de canal nas features.
- [ ] Função e MCP devolvem previsão, faixa e ranking de M1, com definição do alvo e avisos de suporte; teste final permanece fechado.

**Aprendizagem:** log do alvo, generalização por canal, validação, embeddings congelados e quantis.

## P4 — Acrescentar visão e atributos estruturados ao mesmo fluxo

**Entrega prevista:** sábado/domingo. **Bloqueada por:** P3. **História:** como produtor, quero que o sistema examine o conteúdo visual e demonstre se esses sinais ajudam na comparação.

### O que construir

Frames, CLIP, sete atributos SmolVLM2 e medidas técnicas de imagem/áudio, com evidências e cache. Treinar M2 sobre o mesmo conjunto elegível do M1; comparar na validação e servir a versão selecionada sem alterar o contrato de entrada.

### Aceite

- [ ] Regra de frames funciona também em vídeos muito curtos; processador VLM respeita dimensões e recortes definidos.
- [ ] Atributos têm enumerações, unknown e evidências; exemplos auditados manualmente, sem tratar JSON válido como percepção correta.
- [ ] Extratores e PCA respeitam versões e fronteiras de treino; thumbnail externa não entra sem equivalente no candidato.
- [ ] M1/M2 usam as mesmas linhas/partições; relatório identifica que ASR é comum e mede o acréscimo visual/VLM/acústico.
- [ ] Cache invalida quando muda mídia, modelo, prompt ou configuração; tempos e memória de processamento frio e repetido são registrados.
- [ ] Arquivos privados não são enviados a inferência externa; falha de modalidade produz ausência suportada pelo treino ou resultado incompleto.

**Aprendizagem:** fusão de atributos, ablação, custo computacional e auditoria de extratores.

## P5 — Explicar a comparação com SHAP, referências e LangGraph

**Entrega prevista:** segunda, 3h; pode iniciar após o contrato de P3 estabilizar. **Bloqueada por:** P3; conclusão integrada depende de P4. **História:** como produtor, quero entender as evidências da previsão e sua relação com o objetivo de divulgação.

### O que construir

Coordenar a comparação em StateGraph, recuperar até três comparáveis autorizados do treino e calcular SHAP do preditor central. Um subgrafo explicador com Ollama/qwen3:4b transforma esse pacote em explicação em português, validada por esquema e referências de evidência.

### Aceite

- [ ] Grafo executável explicita extração, comparáveis, previsão, explicação e ordenação; o explicador é uma chamada real de modelo, sem alegar reasoning quando há apenas um template.
- [ ] SHAP é descrito na escala correta; embeddings são agrupados por modalidade, sem causalidade ou significados inventados para componentes.
- [ ] LLM não altera números/ranking nem executa instruções encontradas no vídeo/brief; cada afirmação factual aponta para evidência fornecida.
- [ ] Comparáveis vêm somente do treino, com critério e origem declarados; sem suporte, lista vazia e justificativa.
- [ ] Ollama local e sem segredos/ferramentas arbitrárias; limites, timeout e falhas do explicador são verificáveis.
- [ ] Demo integrada compara três arquivos e mostra números, evidências, aderência e limites do uso em patrocínio.

**Aprendizagem:** separar predição, explicação estatística, evidência observada e interpretação por LLM.

## P6 — Congelar a solução e avaliar o teste reservado

**Entrega prevista:** terça, 3h. **Bloqueada por:** P4 e P5. **História:** como avaliador, quero conferir se a solução supera referências e onde falha, sem seleção de resultados pelo teste.

### O que construir

Fixar configuração selecionada na validação e executar o relatório final de baselines/M1/M2 no mesmo teste. Consolidar diagnóstico temporal retrospectivo, ranking intra-canal, cobertura e análise dos erros, com rastreabilidade até manifestos e artefatos.

### Aceite

- [ ] Teste não participa da seleção; abertura e configuração escolhida ficam registradas. Mudança posterior motivada pelo teste é declarada como tal.
- [ ] MAE log por vídeo/canal, MAE em views, MAPE com exclusões, Spearman/pares quando estimáveis e cobertura/largura são apresentados com contagens por setor/canal.
- [ ] Diagnóstico temporal informa datas, suporte e confusão entre idade e publicação; não é apresentado como backtest prospectivo.
- [ ] Relatório compara configurações no mesmo conjunto, mostra falhas de extração, incerteza e exemplos de maiores erros, incluindo resultados negativos.
- [ ] Números do relatório são reproduzíveis a partir de registros locais; resumos públicos não expõem dados ou credenciais.

**Aprendizagem:** interpretar erro, ordenação, cobertura, suporte amostral e limites da evidência.

## P7 — Reproduzir a demonstração e preparar a entrega

**Entrega prevista:** quarta, 3h, com documentação atualizada ao longo das anteriores. **Bloqueada por:** P6. **História:** como avaliador, quero instalar, executar e entender a solução e suas limitações sem depender do histórico dos chats.

### O que construir

Consolidar README, relatório e roteiro de demonstração. Executar a instalação e o percurso função/MCP em ambiente limpo, revisar arquivos públicos e conferir o pacote entregue. Não acrescentar funcionalidades neste bloco.

### Aceite

- [ ] Instruções descrevem instalação, pesos, fonte autorizada, treino, avaliação, execução e acesso aos artefatos com versão/hash.
- [ ] Diagrama e documentação permitem explicar o que acontece, como, onde e por que; incluem restrições de privacidade, descarte e validade científica.
- [ ] Verificações públicas rodam sem segredos ou dados privados; demo real autorizada foi ensaiada pela função e por cliente MCP.
- [ ] Repositório contém apenas arquivos intencionais; logs, mídia, caches, chaves e pesos grandes permanecem fora do Git.
- [ ] Pendências e requisitos do TAPI não atendidos são explícitos; entrega conferida antes de 21/10 às 23h59.

**Aprendizagem:** o aluno explica o fluxo completo com um exemplo, justifica escolhas e reconhece o que o experimento não demonstrou.

## Dependências e execução autônoma

Ordem principal: P1 → P2 → P3 → P4 → P6 → P7. P5 pode começar sobre o contrato estável de P3, em árvore separada, mas a validação integrada usa a saída final de P4. Não abrir execução paralela antes de estabelecer esse contrato.

Noturno: extração cacheada de lote autorizado e experimentos já definidos, após piloto e com orçamento de tempo/cota/disco, condições de parada e relatório de falhas. Não alterar protocolo, consultar teste final ou adotar novos serviços externos autonomamente. Commits respeitam unidades lógicas também durante a noite.
