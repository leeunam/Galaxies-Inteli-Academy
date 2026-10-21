# Probe visual: lançamento não iniciado por expiração da revisão automática

O [probe preparado](issue-4-vlm-resource-probe-proposta.md) recebeu autorização
humana específica e selo técnico externo em 21/10/2026. O operador solicitou
uma única execução; a ferramenta encerrou em `CreateProcess` porque a revisão
automática de permissão não terminou antes de seu prazo. Não houve processo
criado nem identificador de sessão de execução. O timeout desse controle não
estabelece que a ação seja insegura e não é um timeout do VLM.

A reconciliação em leitura às **21:43:04 UTC** confirmou:

- `calls=0`, `sealed=false`, um slot não consumido;
- ausência de started, reserva, capture e lock;
- stdout/stderr agregados vazios e zero workers pertinentes;
- autorização e selo preservados, sem alteração de fonte/plano/entrada;
- nenhuma inferência ou coleta de telemetria, sem resultado de fase/percepção.

O estado não representa uma chamada consumida pelo modelo. A orientação
posterior encerrou esta etapa sem relançamento; o slot não consumido não
autoriza nova submissão automática. Nenhuma rota alternativa ou repetição foi
usada. O NIM posterior teve autorização/revisão e operação próprias; não foi
substituto para o comando visual bloqueado.

Código `48e5eb1b0d740deb96961b8e3b2087e9eae5ae64`. Plano lógico
`ddf0da1e1ee9b915521fe4f780c45bd387c2f0545b8b4f575aa8d5166e22549f`,
arquivo `d7f1899b5890d887c7b4805a5f1a8fde72cef88625543a9add015311e3321c31`,
configuração `00aefd4e0efa20d34ce0301640910cf7853c1f601b8bb208cdf896ebf0d01fe2`.
Os recibos privados novos foram preservados; a [projeção sanitizada](evidence/issue-4-vlm-resource-probe-bloqueio.json)
vincula a reconciliação ao plano, sem expor dados privados.

Não houve testes adicionais, benchmark, download, mudança do sistema, abertura
do teste, alteração de M1/partições ou de retenção. As filas v1/v2/v3 seladas e
seus resultados continuam intactos. Não foi produzida evidência nova sobre
recursos durante uma inferência ou sobre a qualidade perceptiva.
