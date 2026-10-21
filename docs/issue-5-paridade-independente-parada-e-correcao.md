# Paridade independente — parada antes do despacho e correção do observador

A primeira tentativa do protocolo v3 encerrou em **1,390 s**, com job
`child_failed` recolhido. Só a Python foi reservada; não houve recibo de
invocação, resposta, despacho de grafo/M1, extração, previsão ou SHAP. A MCP
não foi reservada. Imports de bibliotecas não equivalem a carregar pesos.
Autorização encerrada, scratch vazio e nenhum retorno à tentativa consumida.

O preparador original configura limites e executa `os.execv`, preservando o
PID. O observador usava um nome exclusivo por PID; assim o startup do
preparador consumia o nome, e o interpretador seguinte ficava sem observador.
Python pode imprimir o erro de `.pth` e continuar. A primeira guarda da função
de rota rejeitou esse estado antes de criar o recibo e antes de qualquer
despacho. A exceção bruta original foi suprimida pelo operador; uma reprodução
inventada da preparação exata confirmou `RuntimeError: observer_required`.

O preflight v3 conferia as respostas downstream, mas não exigia observador
ativo no interpretador após o `exec`. Essa cobertura foi insuficiente para
a entrada real. A correção preserva `O_EXCL` e acrescenta uma sequência de
startup por PID, sem RNG, overwrite ou mudança do cálculo de produção.

Na prova offline, a função original de preparação foi executada para ambas as
rotas, com os mesmos metadados/configuração e análise, transporte e clientes
explicitamente falsos. Processos, carregamento de modelos, previsão, SHAP e
extração foram bloqueados. O observador antigo falhou na guarda; o corrigido
chegou às duas fronteiras falsas, com pedido/cadastro/config e argv/ambiente
conferidos. Zero chamadas reais e recolhimento confirmado.

O protocolo final v5 vincula essa prova, os snapshots anteriores, o run
consumido e sua autorização encerrada. Mantém todos os tetos e exige liberação
técnica própria para um namespace novo. O preflight ampliado verifica dois
registros de startup do mesmo PID, observador ativo no alvo após `exec`,
igualdade integral off/on, zero erros de observação e zero modelos reais.
Passaram **14 testes leves**: colisão de nomes, indisponibilidade nativa,
falha de observação, estado RNG, troca de inputs, limite do trace, escrita
parcial, falha de escrita, terminal ausente e sucessor de `exec` verificável.

O preflight seguinte, ainda inventado, encontrou processamento duplicado do
`.pth`: quatro registros onde o check esperava dois. As respostas completas
continuaram iguais e não houve erro de observação ou modelo real. A instalação
agora é única por interpretador, preservando o novo registro após `exec`.
Na revisão, o terminal ganhou arquivo próprio, fora do teto do JSONL, com
rejeição de truncamento, erro de escrita e encerramento não comprovado. Os
checks adicionais permanecem separados das autorizações de execução real.

A preparação final das duas rotas também passou com os despachos falsos:
dois startups do mesmo PID, observador ativo no alvo, todos os terminais e
ligações de `exec` válidos, zero modelos/decodificações e limpeza confirmada.

Os três inputs, relatórios históricos, manifesto e fonte canônica Python
continuam preservados. Esta correção do operador não explica os 22 campos
históricos divergentes e não constitui um resultado do par real.
