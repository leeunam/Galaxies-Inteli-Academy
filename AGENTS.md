# Instruções do projeto

Siga também as instruções em @/home/inteli/.codex/RTK.md.

- Registros de desenvolvimento, checkpoints, planos e relatórios auxiliares devem ficar em `data/private/`; prefira atualizar guias públicos existentes. Preserve bytes dos protocolos congelados.

Leia `docs/briefing-de-trabalho.md` para os acordos de trabalho, restrições e decisões confirmadas. Use `CONTEXT.md` como glossário do domínio.

## Commits

- Faça commits frequentes ao concluir unidades lógicas de trabalho, com uma intenção principal e mensagem clara.
- Mantenha juntos o código, os testes e a documentação necessários à mesma mudança.
- Separe assuntos independentes e divida entregas grandes em passos coerentes e verificáveis.
- Evite tanto acumular mudanças sem relação em um commit quanto fragmentar uma mudança por arquivo, número de linhas ou intervalo de tempo.
- Revise o conteúdo e execute as verificações apropriadas antes de cada commit. Não versione segredos, dados sensíveis nem arquivos temporários.
- Aplique esses acordos também a subagentes, chats em worktrees e execução noturna.

## Manutenção

- Use o `Makefile` como fonte dos comandos de lint, formatação, testes, demonstrações e resultados. Consulte `make help`; a conveniência de `make` é opcional e não instala dependências.
- Preserve os ambientes Python separados da raiz e de `orchestration/`. `make check` cobre apenas as verificações e seleções rápidas declaradas; testes completos são alvos separados.
- Mantenha `.superpowers/` ignorado pelo Git; não versione registros de agentes ou arquivos privados.
