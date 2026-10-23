# Frente 1 — pacote v3 para autorização única

**Rodada posteriormente executada e encerrada:** veja o
[resultado v3](fechamento-frente-1-ensaio-v3-resultados.md). Este texto preserva
o escopo da preparação; seus comandos e orçamento não são reutilizáveis.

Preparado a partir de `f5f8d830db48cf68fd3ba7471a7cc1ee1e685347`, em clone
independente `/tmp/galaxies-frente-1-envelope-v3`, branch
`codex/frente-1-envelope-v3`. Nenhuma execução real está autorizada por esta
página. A [v2 encerrou no preflight](fechamento-frente-1-diagnostico-v2-resultados.md),
com zero chamadas de modelo; seus recibos e orçamento permanecem consumidos.

O Chat 3 concordou com o escopo de preparação e revisão independente. O pedido
humano ficará somente no chat da Frente 1. Depois de aprovação, o coordenador
deverá reconciliar as cargas e emitir um slot real, com validade curta e hashes
deste pacote. Disponibilidade declarada durante a preparação não reserva CPU/RAM.

## Perguntas e resultados que as distinguem

O [contexto externo observado](fechamento-frente-1-contexto-execucao.md) é
compatível com confinamento externo impedindo a criação da cápsula interna.
O ensaio muda **apenas o envelope externo** para `exec_command` com
`sandbox_permissions=require_escalated`, conservando o bwrap interno. Um
preflight bem-sucedido demonstrará a viabilidade desse envelope. Sua falha
encerra o ensaio e não identifica, por si só, a regra do kernel responsável.
Não haverá mudança de sysctl, AppArmor ou outro controle do sistema.

Se o preflight passar e houver prazo, a única chamada de modelo preencherá a
célula ainda ausente: positivo conhecido com prompt antigo, sem a cláusula
adicional sobre caracteres impressos. Pixels, schema `state_first`, seed 42,
pesos, CPU4, native225 e saída máxima de 64 tokens permanecem fixos. A v2 não
executou esse modelo; frente ao seu argv planejado muda somente o caminho
privado do schema. O contraste histórico continua sendo uma reconstrução
estática: o argv efetivamente executado naquela rodada não foi persistido.

O aceite desse caso exige `true`, categoria `garment` e configuração
`hand_holds_hanger_out` ou `isolated_physical_item`. `false` mostra que a
cláusula adicional não é necessária para o falso negativo desse caso; `unknown`
é inconclusivo; `true` sem suporte nas alternativas congeladas reprova. Um
`true` com suporte será apenas compatível com sensibilidade ao prompt nesse
caso revelado, sujeito a variação temporal/de execução. Nenhum resultado
aprova atributos ou libera auditoria, extração dos 269 casos ou B/C completos.

## Entradas e identidades fixadas

Diretório persistente, privado, sem substituir evidências anteriores:

```text
/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/
  unit-7-envelope-v3/
  diagnostic-old-prompt-positive-v3/
```

| Identidade | SHA-256 |
| --- | --- |
| Operador materializado `control_worker.py` | `6c23fd9afa4d1998c52dac3a6890a6603e5cdaf2b62ca73da45df9c13b4e26bf` |
| Plano, digest lógico | `7d7e3f449efa1cacbefe3300e22e5d39895f037a08fa5e129883d82ce1b75f20` |
| Plano, bytes de `plan.json` | `cea1d01c270b3682a30b6c6989d875b819787f26fa08e3549f77966b2c9b1370` |
| Proposta, digest lógico | `6f65c92a4d4eb2d246ad0fd30facc5265c5704f65ce19be9d6c828945ff88d56` |
| Crop positivo RGB 320×330 | `4a22deaca1910529f560c3af6da06270aae129a53e0cdcea76c597077fa4bda6` |
| Prompt antigo | `afaf965f12fd76b2426b4e6d2ef6e82a795a1c34d4d2bd83035ace7a8a5f0b12` |
| Schema ordenado | `47bf27350b557bb6223b1213654d3a1f21b7099c159408dd8960b0ecd387baef` |

O crop existente é
`data/private/issue-4-visual-prompt-text-discriminant-v1/inputs/positive-product.png`.
Pede-se renovação específica de seu uso somente para essa chamada. Não há
aquisição ou cópia de mídia, pesos, dados, `.env` ou ambiente para o clone.
Python, Qwen3VL Q4_K_M, projector Q8_0 e llama b11716 são referenciados nos
caminhos existentes. Os quatro assets foram novamente conferidos por SHA-256
streaming e fingerprints, em uma CPU, sem carregamento de modelo; o recibo
`unit-7-envelope-v3/preparation-receipt.json` registra cerca de 1,01 s e
28.464 KiB de pico RSS. Fontes e antecessores selados também conferem.

## Comandos externos e sequência autorizável

Workdir de ambos:
`/home/inteli/Documents/projetos/Galaxies-Inteli-Academy`.
As duas chamadas usam explicitamente `sandbox_permissions=require_escalated`,
`yield_time_ms=1000` e `max_output_tokens=2000`. Objetos completos, incluindo
justificativa, estão em `unit-7-envelope-v3/tool-requests.json` e no plano;
digest lógico da sequência:
`39f947d959dc47b2a5b3bb59ca115e705ce32cbf6f38267f0e479399c3144e5a`.

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/diagnostic-old-prompt-positive-v3/control_worker.py --preflight-only
```

Somente depois do sucesso técnico, limpeza confirmada e gates ainda válidos:

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/fechamento-20261023/frente-1/diagnostic-old-prompt-positive-v3/control_worker.py
```

Antes do primeiro pedido à ferramenta, o chamador deve importar o operador
privado, conferir `verify(external_attempt=False)` e chamar
`reserve_external_attempt()`, sem iniciar filho. Esse método cria com exclusão
e fsync `external-attempt.json`, vinculando plano, autorização, slot e objetos
das duas chamadas. Uma segunda reserva falha, mesmo se a revisão de permissão
recusar a primeira chamada antes de qualquer processo. A ferramenta externa
continua responsável por aplicar seu parâmetro de permissões: o operador não
consegue atestar por dentro qual parâmetro foi passado à ferramenta.

O operador exige autorização humana nova, renovação do crop, revisão
independente vinculada aos bytes dessa autorização e ao operador e slot do
Chat 3. Os quatro documentos devem declarar o mesmo envelope. Não materializar
nenhum desses recibos a partir de concordância de outro agente.

## Orçamento e parada

- R$0; zero rede, downloads, instalações e aquisições; sem retry ou fallback.
- Exatamente um preflight sem modelo, de até 8 s, e no máximo uma chamada
  condicional. Recusa automática, falha da cápsula, identidade divergente ou
  autoridade expirada encerra a rodada.
- CPU4 na inferência; RSS agregado cooperativo de 3,3 GiB; `MemAvailable`
  mínimo de 6 GiB e disco livre mínimo de 1 GiB na admissão/preflight e gates
  de memória antes de iniciar o modelo. O slot é coordenado; não é mutex global
  nem reserva física/cgroup de memória.
- Teto global de 120 s desde a primeira reserva durável do preflight, sem
  reiniciar o relógio entre comandos; 75 s úteis + 5 s de limpeza na chamada.
  Se restarem menos de 80 s, o segundo comando recusa. Pausas de revisão externa
  podem consumir o prazo e causar essa parada.
- Captura nativa: stdout até 16 KiB, stderr até 256 KiB; scratch até 128 MiB.
  Bwrap mantém raiz somente leitura, rede isolada, ambiente limpo, `/dev`/`proc`
  próprios, `/tmp` efêmero e escrita persistente somente no namespace próprio.
  A lista de argumentos da cápsula está fixada no plano; mudança reprova.
- Proprietário/watchdog recolhe somente seus descendentes. Limpeza incerta
  mantém o resultado consumido e bloqueado, sem repetir a chamada.
- Persistir recibos brutos limitados, reservas, terminais e resultado de
  eventual recusa da ferramenta. Remover scratch novo somente após quiescência
  confirmada. Preservar evidências antigas.

O holdout continua fechado; coorte, partições, receitas, serviço e critérios
não mudam. Esta preparação não é liberação de qualidade nem conclusão da Frente 1.

## Verificação offline

As suítes públicas usam proprietário e autoridades inventados antes de qualquer
importação privada. Foram **69 testes aprovados e 7 skips de casos específicos
da v3 quando parametrizados na v2**, em 0,49 s; zero preflight/modelo reais.
Cobrem reserva concorrente/exclusiva, crash, prazo herdado, memória, falha de
cápsula impedindo modelo, consumo antes de eventual recusa externa, envelope
nas quatro partes e conservação do argv/schema. Ruff e formatação passaram.
O Chat 3 reproduziu os 69 testes e 7 skips em 0,39 s e revisou 30 hashes de
fontes, 113 antecessores, os quatro fingerprints/referências de assets e a
equivalência da cápsula/argv, sem encontrar bloqueio à apresentação do pedido.
O parecer persistente está em
`unit-7-envelope-v3/independent-package-review-chat3.json`. Ele revisa o pacote
do commit `2c4591c8644671d7283eec3d46e162ac8dad9f87` e não substitui o
`review.json` que deverá estar vinculado à futura autorização humana. Nenhum
slot foi reservado e nenhum preflight ou modelo foi executado nessa revisão.

Reprodução dos testes no clone, referenciando apenas o Python existente:

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_front1_positive_diagnostic.py tests/test_front1_positive_diagnostic_v2.py
```
