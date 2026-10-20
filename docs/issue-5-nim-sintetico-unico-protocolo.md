# Issue #5 — uma tentativa NIM sintética com reserva durável

Autorização específica do aluno em **20/10/2026, 13:06 UTC**, resposta “sim”
à proposta encaminhada pelo chat coordenador. A instalação isolada e o
[StateGraph](issue-5-stategraph-isolado.md) precederam esta etapa. Primeiro
concluir implementação, testes locais, revisão e commit; depois congelar plano
e fazer **no máximo uma tentativa**, sem retry, reparo ou fallback.

## Alvo, conteúdo e limites

- POST fixo `https://integrate.api.nvidia.com/v1/chat/completions`.
- Modelo `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.
- Somente texto completamente inventado do arquivo público versionado
  `orchestration/fixtures/nim-synthetic-request.json`. Os números, IDs, hashes e
  relatório de origem são fabricados. Não há vídeo, transcrição, rótulo, vetor,
  evidência de coorte, brief, caminho local ou dado privado no prompt.
- Até **2.048 tokens** de saída, **45 s** totais da tentativa e **16 KiB** de
  corpo HTTP recebido. Sem streaming, raciocínio solicitado desativado.
- **Gasto autorizado R$0**: somente endpoint gratuito NVIDIA. A
  [página oficial](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning)
  informa endpoint gratuito disponível na consulta de 20/10; isso não verifica
  cota, saldo ou validade da credencial específica. Não configurar cobrança,
  aceitar termos novos, trocar para parceiros ou adquirir créditos.
- Reutilizar apenas a chave NVIDIA_API_KEY existente, no cabeçalho do alvo e em
  memória. Não criar chave, login ou configuração persistente de acesso; não
  imprimir/gravar credencial, cabeçalhos, exceção ou corpo bruto.

O [card oficial](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning)
declara suporte somente a inglês. A seleção de IDs sobre fatos determinísticos
em português não demonstra geração livre ou aderência qualitativa em português.

## Reserva, processo e parada

Fila única privada: `data/private/issue-5-nim-sintetico-unico-v1/`. O plano
anterior à execução fixa fontes, testes, protocolo, fixture, corpo HTTP, locks
e pins protegidos. O SHA do arquivo inteiro do plano fica pinado externamente
em `nim_seal.py`, versionado antes da chamada. Esse arquivo é a âncora confiável
e fica fora do próprio mapa para evitar dependência circular. Remover/truncar
o mapa ou qualquer campo muda o hash e impede reserva/envio. Conferir
filas/recibos anteriores e processos antes de operar;
se já houver uma tentativa desta autorização ou resultado incerto, não repetir.

O grafo chama o worker sintético pelo ambiente raiz sem abrir mídia ou pesos.
O seletor aceita **somente bytes iguais à fixture fixada**; um parâmetro de usuário
chamado synthetic não autoriza seu conteúdo. O pai grava `reservation.json`
com criação exclusiva, modo0600 e fsync antes de iniciar o filho HTTP.
O filho confere o plano e grava `dispatch.json` exclusivo antes de acessar a
credencial e tentar a requisição. Arquivos existentes não são apagados/reusados.
Além disso, exige PID do pai vivo e token efêmero recebido por pipe anônimo:
somente seu hash fica na reserva. Invocar o módulo filho diretamente não permite
retomar uma reserva incerta depois que o pai/token foram perdidos.
Interrupção entre reserva, envio e resposta consome a tentativa e fica incerta.

HTTPS usa validação TLS normal, host/rota fixos, sem proxy herdado, redirects,
SDK com retries ou endpoint alternativo. Só há um `request`. HTTP diferente de
200, inclusive cobrança/termos/autorização/limite/indisponibilidade, encerra sem
ler nem persistir seu corpo. O corpo de sucesso é lido com limite16KiB+1; o byte
extra serve exclusivamente para detectar excesso e rejeitar. Resposta longa,
truncada, ferramenta, envelope incompatível ou seleção inválida não é reparada.

O pai impõe prazo de parede no processo, mata seu grupo e aguarda término em
timeout/cancelamento/falha. `result.json` registra somente estado sanitizado,
status HTTP, tamanho, tokens se informados e tempo. Não contém resposta livre.
O worker raiz valida seleção e renderiza os fatos; `graph-result.json` registra
se o transporte e a seleção passaram, sem inferir qualidade semântica.
Uma reserva incerta não é convertida em sucesso nem liberada para repetir.

Se a aprovação automática negar a operação, não executar novamente sem examinar
recibos/processos. No máximo uma nova tentativa da operação negada apenas com
evidência material nova e certeza de que não foi executada; não colocar texto de
aprovação nos argumentos do comando. Se persistir o bloqueio, reportar.

## Verificação local e execução autorizada

Testes locais usam somente fixtures e conexões falsas: alvo único, reserva antes
de operar, orçamento, corpo limitado, ausência de retry/redirect, sanitização,
timeout de filho não cooperativo, cancelamento, plano adulterado, recusa de dados
arbitrários e seleção validada no grafo/worker sintéticos reais. Não chamar o NIM
como parte de pytest ou da suíte completa. Não criar serviço NIM genérico.

Antes da selagem passaram **39 testes isolados** (29 novos desta unidade),
**11 direcionados na raiz** (três novos), Ruff/formatação de143 arquivos e
revisão independente somente leitura. A revisão motivou o hash externo do plano
e a autorização efêmera do despacho; ambos têm testes de recusa. O resultado
da suíte completa e da tentativa real será registrado separadamente.

Partindo de `orchestration/`, os comandos de verificação são:

```sh
rtk proxy .venv/bin/python -m pytest -q
rtk proxy .venv/bin/python -m galaxies_orchestration.nim_probe
```

O segundo é diagnóstico inerte e retorna `not_executed`. Após o plano congelado,
revisão, commit e conferência de ausência de operação prévia, o comando exclusivo
da autorização atual é:

```sh
rtk proxy .venv/bin/python -m galaxies_orchestration.nim_probe --execute-authorized-once
```

Não é comando de reprodução futura: a autorização é consumida uma vez.
Não alterar fontes/protocolo/fixture/plano após iniciar a tentativa. Registrar
resultado em documento separado. Preservar M1/A200, partições, teste reservado,
lock/ambiente raiz, filas seladas, oito PNGs e README não rastreado. Sem nova
mídia, VLM, treino, auditoria, push, deploy ou encerramento remoto de issue.
