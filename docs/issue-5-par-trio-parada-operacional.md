# Par completo do trio — parada operacional antes da extração

A execução única foi encerrada por falha do helper no primeiro lote, antes
de lançar o worker de extração de features. Foram **zero extrações e zero
chamadas ao bundle**; o segundo lote não começou. Não há comparação numérica
nova nem resultado científico deste par.

O [recibo agregado](evidence/issue-5-par-trio-parada-operacional-20261020.json)
registra exitcode 1, um job `child_failed` em 3,8901 s, recolhimento confirmado
e scratch vazio. A autorização foi consumida e a falha é terminal, sem retry
ou aproveitamento automático do orçamento não utilizado.

O defeito confirmado está no helper privado: o namespace copiado do launcher
substitui `subprocess` por um proxy com `Popen` e `TimeoutExpired`, mas omite
`DEVNULL`, que a função original usa ao construir os argumentos da chamada.
Um caso inteiramente inventado reproduziu `AttributeError` antes de chamar
o Popen falso. Acrescentar somente a constante resolveu esse caso sem criar
processos ou executar modelos.

A exceção bruta do runtime foi suprimida pelo helper. O defeito de fonte é
determinístico e suficiente para impedir o lançamento; um eventual erro nativo
anterior também impediria essa etapa. O contexto M1 pode ter inicializado
pesos antes da falha, mas o caminho não alcançou extração nem previsão. A
evidência de diagnóstico não é apresentada como uma captura numérica válida.

O helper aprovado, seu protocolo e as fontes seladas permanecem iguais.
Uma correção mínima foi descrita em patch privado **não aplicado**; não foram
criados helper executável corrigido, protocolo de retry ou outra rodada.
Os três inputs, relatórios, manifesto canônico e passagem privada `0600`
foram reconferidos e preservados. Somente o scratch novo, com recolhimento
confirmado, foi limpo.

Não houve aquisição, chamada remota/NIM/VLM, treino, acesso a conteúdo do
teste reservado ou escrita na árvore principal. A
[divergência histórica](issue-5-demo-local-python-mcp-resultado.md) continua
aberta e o [guia de consulta preservada](issue-5-consulta-canonica-demo.md)
permanece independente deste ensaio, dentro da retenção até
**21/10/2026 às 23h59, São Paulo**.
