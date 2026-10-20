# Produto v9: protocolo de desenvolvimento autorizado

Solicitação de 19/10/2026, após `825bb9d`: implementar a
[correção proposta](issue-4-vlm-produto-diagnostico-e-proxima-correcao.md) e
avaliá-la nos controles e nos 64 casos revelados. Esta é uma correção delimitada
do experimento offline. Não selecionar auditoria nova, aumentar resolução,
treinar B-VLM, promover M1 ou alterar serviço/MCP. Partições 203/66/31 e teste
reservado preservados. Nenhuma fonte/rodada antiga é modificada.

## Contrato congelado antes da execução

Nova versão `visual-attributes-v9-product-states`, somente produto. Uma chamada
por frame retorna `state` e `presented_categories`, sem texto livre:

- no_target: nenhum objeto-alvo visível → false;
- incidental_only: apenas alvos inequivocamente incidentais, sem outro
  apresentado ou ambíguo → false;
- presented_target: pelo menos um alvo apresentado segundo a rubrica vigente
  → true; exige lista não vazia de categorias de testemunhas apresentadas;
- uncertain: apresentação/ausência não resolvida, sem apresentado confirmado
  → unknown.

Categorias: cosmetic, applicator, garment, accessory, até quatro e sem
duplicatas. Lista vazia nos estados não positivos. Categoria e apresentação
devem pertencer ao mesmo item. Um apresentado confirmado prevalece sobre outros
incidentais/ambíguos; vários apresentados podem contribuir categorias. Roupa
incidental não prova apresentação, e escolher um item incidental não permite
ignorar outro apresentado. Não inferir intenção comercial, OCR, movimento ou
outro frame. Contradições, chaves duplicadas/extras e categorias inválidas são
rejeitadas sem reparo; preservar saída bruta antes do parser e parar sem retry.

Subestados/categorias são diagnóstico privado, sem rótulos próprios ou aprovação
de treino. Avaliar apenas o produto composto contra a anotação original, que
permanece imutável. Usar parser estrito e agregação temporal v7: OR de true,
false apenas se todos os elegíveis forem false, demais unknown; produto ≤3 s.
Pessoa/texto são recuperados do cache v8; demais atributos seguem unknown.

Mesmos Qwen3-VL-2B Q4_K_M, projetor Q8_0, runtime b11716, CPU4, seed42,
temperatura0, saída64 tokens e limites visuais solicitados64/128, sem alegar
medição dos tokens efetivos. PNG RGB320×330, sem mudar padding, recortes,
folhas ou tempos. Verificar hashes antes/depois de cada chamada. Congelar
fontes, prompts, schemas, fonte tipográfica e este protocolo no plano privado.
Nenhuma variante ou ajuste após a primeira chamada.

## Controles e critérios de continuidade

Reconstruir os 12 controles v8 com a mesma receita/fonte e conferir os hashes
contra os recibos v8. Cache v8 é a referência, sem novas chamadas dele.
Quatro variantes predefinidas, uma chamada por controle, total48:

1. enum_false_first: somente permutar true/false na enumeração do schema;
2. examples_false_first: somente permutar os exemplos de presença/ausência;
3. neutral_key: somente trocar a chave por answer no schema/exemplos e
   mapear o resultado ao atributo original;
4. structured: a decomposição acima, única candidata autorizada nos vídeos.

As três primeiras são contrastes diagnósticos, não candidatas alternativas.
Rodar todas as48 enquanto o contrato operacional funcionar; não escolher pela
taxa de acerto em controles exclusivamente negativos. **Structured precisa
acertar12/12 como false para liberar reaquisição/inferência real.** Unknown não
é ausência correta. Falha perceptiva sela essa condição ao concluir os controles;
falha operacional/contrato interrompe imediatamente. Não prosseguir aos64 para
repetir uma falha já evidente, nem substituir o candidato por outro contraste.

## Casos revelados, piloto e comparação

Copiar exatamente as64 linhas/identidades do plano v8, todos treino, sem
reposições. Ambos os grupos de origem32 são desenvolvimento, com16/setor;
não há holdout independente. Selecionar o piloto por regra predefinida: todos
os oito negativos de produto e oito positivos, dois por origem×setor,
ordenados por hash com seed fixo antes das chamadas, sem usar erros anteriores.
O piloto tem16 casos: dez beleza/seis moda; oito negativos (seis beleza/dois
moda) e oito positivos (quatro por setor).

Reobter primeiro os16 do piloto, validando propriedades, SHA de folha/crops e
tempos contra v8/v7. Limpar vídeo por sessão. Avaliar a única candidata sem
retuning. Continuidade exige pelo menos **um acerto de valor+frames em cada
célula setor×classe anotada**, apenas controle de não colapso, sem aprovação.
Se falhar, relatar e parar antes dos48 restantes. Se passar, completar os64.
Não confundir esse mínimo com o gate de qualidade.

Comparar produto com v8 e A/v7 em cache nos64; B/v7 somente nos32 antigos.
Relatar piloto, demais48, total64, origem, setor, classes, confusão, conhecidos/
unknown, valor, valor+frames, índices sem suporte e frames explicitamente
positivos/ausentes. Não preencher frames não citados como negativos. Pessoa e
texto devem permanecer exatamente iguais ao cache v8. O gate original aplicado
separadamente às origens32 é apenas prontidão descritiva: ≥12 conhecidos/setor,
≥90% valor+frames entre conhecidos, zero índices sem suporte, ≥3 previsões por
valor no grupo e ≥1 por setor. Nenhuma coluna é liberada por desenvolvimento.
Comparação incompleta deve informar a parada e não inventar resultados nos64.

## Limites, falhas e descarte

Nova fila privada: `data/private/issue-4-vlm-produto-v9-desenvolvimento/`.
Ancorar o recibo final do diagnóstico
`6a76c1483b94ef0c3d761a97b54c54c08060be70441d9f098b1d6089100ea485`,
todos seus arquivos protegidos/recibos, e a v8 selada. Base cumulativa:182
aquisições,1.453 chamadas v7+diagnósticos+v8 e15.159,677960556044 s de sessões.
Até304 chamadas novas (48controles+256produto),1.757 nesse contador; até256
aquisições cumulativas (182+64+até10 extras DNS),27h cumulativas. Manter180s
por operação/chamada, RSS filho≤3,3GiB, um executor. Registrar tentativa/chamada
antes de executar, preservar falhas, não reiniciar contadores na retomada.

Somente DNS temporário tipado permite uma repetição/ID e10 na fila, após
limpeza confirmada, espera5s e DNS positivo, usando a recuperação anterior.
Auth/403/429/timeout/memória/identidade/limpeza incerta interrompem. Nenhuma
repetição de inferência, salto de caso ou troca de unknown por false.

Guarda de acesso ao teste ativa em toda CLI; não abrir views, títulos, ASR,
rótulos preditivos, arquivos mistos de registros/inputs, evidências ou rótulos
de teste. Preservar M1/A200, A300 e B-cache, metadados/partições e recibos antigos.
Guardar folhas só durante comparação e revisão; depois descartar as adquiridas
com journal recuperável, mantendo identidades/respostas/hashes. Controles são
temporários e removidos por sessão. Selar relatório inclusive em parada de
qualidade ou falha, bloquear novas operações, verificar pins e limpeza.

Testar contrato, variantes, fronteiras de imagem/tempo, cache, piloto,
isolamento, orçamento e recuperação de comparação/descarte interrompidos.
Revisão independente somente leitura e commits por unidades verificadas.
