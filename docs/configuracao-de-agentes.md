# Proposta: Codex Enterprise e Google AI Plus no desenvolvimento

Verificado em 18/10/2026. O aluno confirmou **Google AI Plus**, não Google AI Pro.
Este é um roteiro proposto; nenhuma ferramenta Google foi instalada/autenticada e os
arquivos globais de configuração do usuário não foram alterados. O arranjo trata das
ferramentas de desenvolvimento. A escolha do explicador da aplicação continua separada.

## Divisão recomendada até 21/10

| Responsável | Configuração inicial sugerida | Entrega |
| --- | --- | --- |
| Aluno | Uma prática curta por bloco | Formular hipótese, decidir critérios e explicar o percurso |
| Coordenador Codex | GPT-6.1 Sol, esforço high; xhigh quando a decisão justificar | Escopo, ML, contratos, revisão e integração |
| Executor Codex | GPT-6 Luna para tarefas estreitas, se disponível no workspace | Mudança pequena com verificação e relatório curto |
| Ferramenta Google independente | Gemini 3.8 Flash, se disponível na conta; conferir a listagem | Revisão de um pacote de arquivos permitido, sem editar o projeto |

As recomendações seguem a separação oficial entre Sol para trabalho complexo e Luna
para tarefas focadas. Subagentes usam tokens próprios e podem aumentar o consumo total;
economia depende de tarefas menores, contexto seletivo e pouco retrabalho, não apenas
do número de agentes. [Modelos](https://learn.chatgpt.com/docs/models) e
[subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Começar com coordenador, um executor de código e, quando útil, um revisor. Uma issue
relevante por chat de execução, com briefing por arquivo e retorno resumido. O primeiro
uso do Google será somente revisão. Edição paralela posterior exige worktree exclusiva,
contratos estáveis e revisão antes de integrar. Worktree separa arquivos de trabalho;
não constitui isolamento de credenciais ou de serviços externos.

## O que as assinaturas permitem presumir

- Google AI Plus não deve ser tratado como Pro/Ultra. A documentação Antigravity
  descreve cota básica para os demais planos, com atualização semanal, e modelos
  disponíveis conforme plano. Conferir a conta e `/usage`; não há cota numérica
  prometida para este projeto. [Planos](https://antigravity.google/docs/plans).
- ChatGPT/Codex Enterprise depende do contrato e das configurações do workspace.
  Novos chats/subagentes não criam cotas independentes. Faturamento de API é separado
  do uso por assinatura. [Uso e preços](https://learn.chatgpt.com/docs/pricing).
- Para integrar Gemini automaticamente em um agente de terceiros, o Google orienta
  usar acesso de API apropriado. Não presumir créditos de Gemini API por ter AI Plus;
  verificar projeto, chave, tier e faturamento separadamente.
  [Faturamento Gemini API](https://ai.google.dev/gemini-api/docs/billing).

## Por que não instalar o Gemini CLI antigo para essa assinatura

O aviso canônico do Google informa que Gemini CLI/Code Assist deixou de atender
consumidores e login Google nesse fluxo em 18/06/2026, direcionando ao Antigravity.
[Aviso de descontinuação](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals?hl=en).

Além disso, o Google não suporta encapsular `agy` autenticado por assinatura de
consumidor dentro de agentes de terceiros. Não usar ponte MCP, tokens extraídos,
cookies ou rotação de contas para transformar a assinatura em backend do Codex.
O fluxo proposto usa as duas ferramentas independentemente: Codex prepara o briefing,
o aluno executa a ferramenta Google, e o relatório volta para revisão.
[FAQ oficial](https://antigravity.google/docs/faq#can-i-use-antigravity-cli-headless-mode-in-third-party-coding-agents-or-automate-account-switching).

Uma integração automática por API pode ser avaliada depois, com limite de custo e
condições de dados próprios. Não é necessária para entregar este protótipo no prazo.

## Passo 1 — Ajustar o Codex sem reinstalar

Neste computador foram encontrados Codex CLI 0.162.1, Node 22.22.1, npm, Git e uv.
O arquivo `/home/inteli/.codex/config.toml` tem `gpt-6.1-sol` e esforço `xhigh`.
Para tarefas comuns, a sugestão é selecionar Sol/high no cliente; reservar xhigh
para decisões difíceis, incluindo protocolo de ML e revisão de falhas complexas.

Se quiser definir defaults para novos agentes, incorporar ao config existente,
preservando suas demais seções e somente após confirmar acesso a Luna no workspace:

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "high"

[agents]
max_concurrent_threads_per_session = 2
default_subagent_model = "gpt-6-luna"
default_subagent_reasoning_effort = "medium"
```

Não substituir o arquivo completo por esse trecho nem duplicar `[agents]` caso já
exista. O limite refere-se a agentes filhos, excluindo o coordenador. Modelo e esforço
podem ser definidos por tarefa; revisão de ML não deve depender automaticamente do
modelo menor. As configurações não substituem permissões e regras do workspace.
[Configuração oficial de subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Passo 2 — Instalar o cliente Google oficial, se optar pelo terminal

O caminho mais simples, sem instalação, é revisar o pacote no aplicativo web Gemini,
selecionando somente os arquivos aprovados para upload. Para trabalhar pelo terminal,
instalar **Antigravity CLI**, binário `agy`; não é necessário instalar o SDK Gemini ou
um framework de orquestração para esta proposta.

Executar pessoalmente no terminal, a partir de uma pasta vazia ou do pacote de revisão:

```bash
rtk proxy curl -fsSL https://antigravity.google/cli/install.sh -o /tmp/antigravity-install.sh
rtk proxy bash /tmp/antigravity-install.sh
rtk proxy /home/inteli/.local/bin/agy --version
```

É o instalador oficial, salvo antes da execução. O local padrão do binário é
`/home/inteli/.local/bin/agy`; usar o caminho absoluto evita depender do PATH.
[Instalação oficial](https://antigravity.google/docs/getting-started?tab=cli).

## Passo 3 — Configurar o primeiro uso como revisor

Antes de abrir o repositório na ferramenta Google, incorporar estas regras ao arquivo
`/home/inteli/.gemini/antigravity-cli/settings.json`, criando sua pasta se necessário.
Se já houver configurações, preservar as outras chaves e mesclar as regras existentes.
Este é um perfil global de revisão: afeta todas as sessões desse CLI.

```json
{
  "permissions": {
    "deny": [
      "write_file(*)",
      "command(*)",
      "unsandboxed(*)",
      "mcp(*)",
      "read_url(*)",
      "execute_url(*)",
      "read_file(/home/inteli/Documents/projetos/Galaxies-Inteli-Academy)"
    ]
  }
}
```

A negação de leitura do repositório exige que a ferramenta trabalhe sobre um pacote
fora dele, contendo apenas os arquivos aprovados. Deny prevalece sobre Ask/Allow;
escrita, comandos e navegação ficam bloqueados, inclusive dentro do workspace. A
conexão do cliente ao modelo continua necessária. Não conceder acesso ao projeto
original durante este piloto. [Permissões oficiais](https://antigravity.google/docs/permissions/).

Esse perfil não é uma lista exclusiva de arquivos legíveis nem isolamento do sistema
operacional. Outros caminhos continuam sujeitos às permissões e autorizações já
existentes no cliente. Não aprovar leitura fora do pacote durante o piloto; a
instrução no prompt, sozinha, não impede acesso a arquivos.

`.gitignore` não é uma barreira de acesso de agentes. Controles de privacidade do
ChatGPT Enterprise também não se transferem à conta Google pessoal. Conferir a
preferência de uso das interações nas configurações Google; compartilhar apenas
arquivos aprovados, nunca `.env`, credenciais, bases privadas, vídeos inéditos ou logs
com dados reais. [Termos Antigravity, itens 3 e 5](https://antigravity.google/terms).

## Passo 4 — Login e confirmação de acesso

Foi preparado um pacote local em `/tmp/galaxies-google-review-issue-2/`, somente com
briefing e trechos públicos de escopo, sem código de produção, segredos ou dados.
Uma cópia persistente está em `data/private/agent-setup-20261018/review-issue-2/`,
ignorada pelo Git. `/tmp` pode ser limpo após reiniciar o computador. Se necessário,
recriar a pasta temporária e copiar para ela apenas `TASK.md`, `SCOPE.md` e
`manifest.json` da cópia persistente, antes de iniciar o cliente. O CLI deve trabalhar
na cópia externa, pois a leitura do repositório está negada no perfil de revisão.

```bash
rtk proxy env -C /tmp/galaxies-google-review-issue-2 /home/inteli/.local/bin/agy
```

`env -C` inicia o processo na pasta de revisão. Usar o login normal no navegador com a mesma
conta do AI Plus. Conferir os modelos disponíveis e `/usage`. A ferramenta deve
confirmar o acesso efetivo; a existência da assinatura não comprova disponibilidade
de todos os modelos. [Autenticação](https://antigravity.google/docs/install?tab=cli).

## Passo 5 — Primeira tarefa, disparada pelo aluno

Executar a partir da pasta `/tmp/galaxies-google-review-issue-2/`:

```bash
rtk proxy env -C /tmp/galaxies-google-review-issue-2 /home/inteli/.local/bin/agy \
  -p 'Leia TASK.md e SCOPE.md. Produza somente o relatório pedido, em português. Não edite arquivos, execute comandos ou acesse fontes externas.' \
  --sandbox --print-timeout 5m --output-format text > /tmp/galaxies-google-review-issue-2/resultado.md
```

O terminal grava `resultado.md` pela saída padrão; o agente permanece sem a ferramenta
de escrita. O comando usa parâmetros documentados, mas sua execução e acesso na conta
ainda não foram testados neste computador. Falha ou resposta incompleta não conta
como revisão aprovada. [Modo headless](https://antigravity.google/docs/cli/headless/).

Trazer o relatório para o chat coordenador. Codex verifica as conclusões, resolve
contradições e usa somente as sugestões sustentadas. Mudanças de código continuam
exigindo inspeção do diff e verificações adequadas; o relatório de outra IA não é
aprovação automática. O aluno explica uma decisão ou corrige um exemplo a cada bloco.

## Limite de esforço e continuidade

Reservar no máximo cerca de 30 minutos humanos para instalação, login e primeira
revisão. Se isso consumir mais tempo ou a cota não permitir, usar Gemini web com o
mesmo pacote ou continuar somente no Codex. A ferramenta extra não entra como
dependência obrigatória da entrega de quarta.

Ao iniciar a #2, abrir novo chat de execução com `AGENTS.md`, briefing, seção P2 do
backlog e checkpoint da #1, sem copiar todo o histórico. A versão de protótipo aceita
treino/validação reais pendentes; isso não autoriza fabricar baseline, ranking,
intervalos ou métricas como se viessem de um modelo treinado em dados reais.
