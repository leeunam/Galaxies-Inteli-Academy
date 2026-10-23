# iSee — contexto externo da falha de preflight

Consulta posterior **somente de leitura**, solicitada pelo coordenador após o
STOP da v2. Não houve nova tentativa de bwrap, unshare, preflight, modelo ou
outro modo de execução.

Na chamada externa do preflight, `sandbox_permissions` foi omitido; portanto
foi usado **`use_default`**, não `require_escalated`. A execução não solicitou
elevação. O perfil declarado do ambiente era workspace-write/restricted.

Uma consulta posterior sob o mesmo modo padrão registrou:

| Observação | Valor |
| --- | --- |
| `kernel.unprivileged_userns_clone` | 1 |
| `user.max_user_namespaces` | 2147483647 |
| `kernel.apparmor_restrict_unprivileged_userns` | 1 |
| `/proc/self/attr/current` | `bwrap//&unpriv_bwrap (enforce)` |
| `NoNewPrivs` | 1 |
| `Seccomp` / filtros | 2 / 1 |
| CapEff / CapPrm / CapBnd | Zero |
| uid_map / gid_map | `1000 0 1` |
| PID / PPID no contexto consultado | 3 / 2 |

O processo consultado e o PID 1 visível partilhavam os mesmos identificadores
de namespaces user/pid/mnt/net. Os valores estão preservados em
`data/private/fechamento-20261023/frente-1/unit-4-operator-v2/readonly-execution-context.json`,
com hashes dos arquivos lidos. Hash lógico:
`a00a0e051a8ceee0be36c0568cc8f1e7f47f23afbb79beeb8fd917d675017f1f`.

Esse contexto é compatível com uma execução externa já confinada, tentando
iniciar a cápsula interna. Ele não identifica qual regra exata negou a criação
do namespace. A consulta não capturou as syscalls da tentativa anterior nem
logs de auditoria do kernel. Não se conclui que user namespaces estejam
globalmente desabilitados; tampouco se atribui causalidade exclusivamente a
AppArmor, seccomp ou falta de capacidades.

## Próximo envelope proposto, não autorizado

Uma alternativa concreta para revisão é executar o invólucro por
`exec_command` com **`sandbox_permissions=require_escalated` explicitamente**,
preservando integralmente a cápsula interna revisada: bwrap com rede isolada,
raiz somente leitura, escrita apenas no namespace privado próprio, ambiente
limpo, proprietário/watchdog e limites de RAM/CPU/tempo. A disponibilidade
desse modo e sua aprovação automática/humana não foram testadas ou presumidas.
Não se propõe modificar sysctls, AppArmor, seccomp do sistema ou retirar o
isolamento interno.

Como a primeira preparação v2 já está consumida, seria necessário um namespace
novo, plano concreto com argv/caminhos/hashes próprios, revisão independente e
autorização nova antes de qualquer execução. A proposta de escopo seria **um
preflight e no máximo uma chamada condicional ao seu sucesso**, nos mesmos
pixels/prompt/schema/seed/modelos e limites R$0/CPU4/RSS3,3 GiB/120 s/75+5,
RAM disponível ≥6 GiB, sem rede, aquisição ou retry. Qualquer recusa na revisão
de permissões ou no preflight encerra, sem tentar modos alternativos.

Esta página não cria versão v3, orçamento, autoridade, selo, slot, reserva ou
comando executado. O coordenador decide se prepara esse envelope e encaminha
um pedido humano único. O diagnóstico continua exploratório; qualidade visual,
269 sidecars, B/C completos e teste final não são liberados por essa mudança.
